from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Union

from data_engineering_pulumi_components.aws import Bucket
from data_engineering_pulumi_components.utils import Tagger
from data_engineering_pulumi_components.aws.lambdas.move_object_function import (
    MoveObjectFunction,
)
from data_engineering_pulumi_components.aws.lambdas.copy_object_function import (
    CopyObjectFunction,
)
from pulumi import Output, export
from pulumi_aws.iam import GetPolicyDocumentStatementArgs, RolePolicy
from pulumi_aws.iam.get_policy_document import get_policy_document

from data_engineering_exports.utils import load_yaml


class UsersNotLoadedError(Exception):
    pass


class DatasetsNotLoadedError(Exception):
    pass


class PushExportDatasets:
    """Load all push dataset details from a list of yaml filepaths.

    Then create AWS resources based on those details:

    -
    """

    def __init__(self, config_paths: List[Path], export_bucket: Bucket, tagger: Tagger):
        """Extract information from a collection of push dataset yaml files.

        Parameters
        ----------
        config_paths : list
            List of Path objects pointing to yaml files (as created by list_yaml_files).
        export_bucket : Bucket
            The bucket the data will be exported from.
        tagger : Tagger
            A Tagger object from data-engineering-pulumi-components.utils

        Returns
        -------
        tuple
            First item is a list of PushExportDatasets.

            Second item is a dictionary where keys are usernames and values are lists
            of project names for that user.
        """
        self.config_paths = config_paths
        self.export_bucket = export_bucket
        self.tagger = tagger
        self.datasets = None
        self.lambdas = None
        self.users = None
        self.role_policies = None

    def load_datasets_and_users(self):
        """"""
        self.datasets = []
        self.users = defaultdict(list)

        for config in self.config_paths:
            dataset = PushExportDataset.from_filepath(
                config, self.export_bucket, self.tagger
            )
            self.datasets.append(dataset)

            for user in dataset.users:
                self.users[user].append(dataset.name)

    def build_lambda_functions(self):
        """ """
        if self.datasets:
            self.lambdas = []
            for dataset in self.datasets:
                self.lambdas.append(dataset.build_lambda_function())
                export(
                    name=f"{dataset.name}_export_role_arn",
                    value=dataset.lambda_function._role.arn,
                )
        else:
            raise DatasetsNotLoadedError(
                "Run load_datasets_and_users before building Lambda functions"
            )

    def build_role_policies(self):
        """ """
        if self.users:
            self.role_policies = [
                WriteToExportBucketRolePolicy(user, self.export_bucket, prefixes)
                for user, prefixes in self.users.items()
            ]
        else:
            raise UsersNotLoadedError(
                "Run load_datasets_and_users before building role policies"
            )


class PushExportDataset:
    """Structure that defines a push dataset, including its name, export and target
    buckets, users, tagger, and whether or not to keep files after copying them.

    Use the .build_lambda_function() method to create a Lambda function based on the
    details of the dataset. The lambda function will move or copy files from the export
    bucket to the dataset's target bucket.
    """

    def __init__(
        self,
        config: Dict[str, Union[str, List[str]]],
        export_bucket: Bucket,
        tagger: Tagger,
    ):
        """Load the details of a push dataset from its config.

        The config should contain:
            - name - name of the dataset, written with underscores for spaces
            - target_bucket - name of the bucket files should be exported to
            - keep_files - boolean specifying whether to delete files after
                copying them to the target bucket
            - users - list of Analytical Platform usernames that work with the dataset

        Parameters
        ----------
        config : Dict[str, Union[str, List[str]]]
            A dictionary loaded from a yaml config file.
        export_bucket : Bucket
            The bucket the data will be exported from.
        tagger : Tagger
            A Tagger object from data-engineering-pulumi-components.utils
        """
        self.name = config["name"]
        self.export_bucket = export_bucket
        self.target_bucket = config["target_bucket"]
        self.users = config["users"]
        self.keep_files = config["keep_files"]
        self.tagger = tagger
        self.lambda_function = None

    @classmethod
    def from_filepath(
        cls, filepath: Union[str, Path], export_bucket: Bucket, tagger: Tagger
    ):
        """Create a PushExportDataset directly from the path of a config file.

        Parameters
        ----------
        filepath : Union[str, Path]
            Location of the yaml file to be loaded as a dataset.
                config : Dict[str, Union[str, List[str]]]
        export_bucket : Bucket
            The bucket the data will be exported from.
        tagger : Tagger
            A Tagger object from data-engineering-pulumi-components.utils
        """
        config = load_yaml(filepath)
        return PushExportDataset(config, export_bucket, tagger)

    def build_lambda_function(self):
        """Create either a MoveObjectFunction or a CopyObjectFunction (depending on
        the value of self.keep_files) and store it as self.lambda_function.
        """
        if self.keep_files:
            self.lambda_function = self._build_copy_object_function()
        else:
            self.lambda_function = self._build_move_object_function()

    def _build_move_object_function(self):
        """Create a MoveObjectFunction based on the dataset's name and target bucket."""
        return MoveObjectFunction(
            destination_bucket=self.target_bucket,
            name=f"export-{self.name}",
            source_bucket=self.export_bucket,
            tagger=self.tagger,
            prefix=self.name,
        )

    def _build_copy_object_function(self):
        """Create a CopyObjectFunction based on the dataset's name and target bucket."""
        return CopyObjectFunction(
            destination_bucket=self.target_bucket,
            name=f"export-{self.name}",
            source_bucket=self.export_bucket,
            tagger=self.tagger,
            prefix=self.name,
        )


class WriteToExportBucketRolePolicy:
    """Create a role policy to allow an existing role to write to part of an export
    bucket. An export bucket is a bucket whose contents will be sent to other platforms.

    No methods, and only one attribute: .arn, the role policy's AWS identifier.
    """

    def __init__(self, username: str, export_bucket: Bucket, prefixes: List[str]):
        """Create a role policy on AWS to let a user put items in specific parts of the
        export bucket.

        Parameters
        ----------
        username : str
            Analytical Platform username (including the 'alpha_' prefix) of the person
            who should be allowed to write to the specified part of the export bucket.
        export_bucket : Bucket
            The bucket the user should be allowed to write to.
        prefixes : list
            List of the subfolders in the bucket the user can write to.
        """
        self._role_policy = RolePolicy(
            resource_name=username,
            policy=Output.all(export_bucket.arn, prefixes).apply(
                lambda args: get_policy_document(
                    statements=[
                        GetPolicyDocumentStatementArgs(
                            actions=[
                                "s3:PutObject",
                                "s3:PutObjectAcl",
                                "s3:PutObjectTagging",
                            ],
                            resources=[f"{args[0]}/{prefix}/*" for prefix in args[1]],
                        ),
                        GetPolicyDocumentStatementArgs(
                            actions=["s3:ListBucket"],
                            resources=[args[0]],
                        ),
                    ]
                ).json
            ),
            role=username,
            name="hub-exports",
        )

    @property
    def arn(self):
        """AWS Arn of the role policy."""
        return self._role_policy.arn
