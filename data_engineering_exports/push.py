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
from pulumi import Output, export, ResourceOptions
from pulumi_aws.iam import GetPolicyDocumentStatementArgs, RolePolicy
from pulumi_aws.iam.get_policy_document import get_policy_document
from pulumi_aws.s3 import BucketNotificationLambdaFunctionArgs, BucketNotification

from data_engineering_exports.utils import load_yaml


class UsersNotLoadedError(Exception):
    pass


class DatasetsNotLoadedError(Exception):
    pass


class PushExportDatasets:
    """Hold information about push datasets, starting from a list of yaml filepaths.
    Use methods to load those files and create AWS resources based on their data:

    - extract user and dataset information from yaml files using load_datasets_and_users
    - create a Lambda function (and associated infrastructure) for each dataset with
      build_lambda_functions
    - add a role policy to each user with build_role_policies - this gives permissions
      to write to the relevant prefix for each of the datasets that include their name
    """

    def __init__(self, config_paths: List[Path], export_bucket: Bucket, tagger: Tagger):
        """Store a list of relevant yaml files, then set export_bucket and tagger.
        At this point, read no config files and create no AWS resources.

        Parameters
        ----------
        config_paths : list
            List of Path objects pointing to yaml files (as created by list_yaml_files).
        export_bucket : Bucket
            The bucket the data will be exported from.
        tagger : Tagger
            A Tagger object from data-engineering-pulumi-components.utils
        """
        self.config_paths = config_paths
        self.export_bucket = export_bucket
        self.tagger = tagger
        self.datasets = None  # Added with load_datasets_and_users
        self.lambdas = None  # Added with build_lambda_functions
        self.users = None  # Added with load_datasets_and_users
        self.role_policies = None  # Added with build_role_policies

    def load_datasets_and_users(self):
        """Read the yaml config files and store:
        - a list of PushExportDataset objects, one for each dataset
        - a dictionary of usernames, each with a list of datasets they can access
        """
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
        """Create a Lambda function for each dataset, using the datasets'
        build_lambda_function methods."""
        if self.datasets:
            self.lambdas = []  # Empty the list first if run for a second time
            for dataset in self.datasets:
                dataset.build_lambda_function()
                self.lambdas.append(dataset.lambda_function)
                export(  # Have Pulumi export the ARN of the role for each Lambda
                    name=f"{dataset.name}_lambda_role_arn",
                    value=dataset.lambda_function._role.arn,
                )
        else:
            raise DatasetsNotLoadedError(
                "Run load_datasets_and_users before building Lambda functions"
            )

    def build_role_policies(self):
        """Create a role policy for each username mentioned in the datasets. For each
        dataset that mentions a user, they will get permission to write to a specific
        prefix of the export bucket."""
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
    """Define a push dataset, including its name, export and target buckets, users,
    tagger, and whether to keep files after copying them (default to deleting them).

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
        self.keep_files = config.get("keep_files", False)  # optional - default to False
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
            name=f"export_{self.name}",
            source_bucket=self.export_bucket,
            tagger=self.tagger,
            prefix=self.name,
            create_notification=False,
        )

    def _build_copy_object_function(self):
        """Create a CopyObjectFunction based on the dataset's name and target bucket."""
        return CopyObjectFunction(
            destination_bucket=self.target_bucket,
            name=f"export_{self.name}",
            source_bucket=self.export_bucket,
            tagger=self.tagger,
            prefix=self.name,
            create_notification=False,
        )


class WriteToExportBucketRolePolicy:
    """Create a role policy to allow an existing role to write to part of an export
    bucket. An export bucket is a bucket whose contents will be sent to other platforms.
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
        self._policy_document = Output.all(export_bucket.arn, prefixes).apply(
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
            )
        )
        self._role_policy = RolePolicy(
            resource_name=username,
            policy=self._policy_document.json,
            role=username,
            name="hub_exports",
        )


def make_notification_lambda_args(
    dataset: PushExportDataset,
) -> BucketNotificationLambdaFunctionArgs:
    """Turn dataset name and Lambda ARN into a BucketNotificationLambdaFunctionArgs.

    Needed because MoveObjectLambda and similar try to create a BucketNotification for
    each Lambda (and therefore each prefix). But Pulumi only allows one
    BucketNotification per bucket. So instead we create a single BucketNotification
    containing a list of BucketNotificationLambdaFunctionArgs.

    Parameters
    ----------
    dataset : push.PushExportDataset
        A push dataset - must have already run the build_lambda_functions method.

    Returns
    -------
    BucketNotificationLambdaFunctionArgs
    """
    return BucketNotificationLambdaFunctionArgs(
        lambda_function_arn=dataset.lambda_function._function.arn,
        events=["s3:ObjectCreated:*"],
        filter_prefix=f"{dataset.name}/",
    )


def make_combined_bucket_notification(
    name: str, export_bucket: Bucket, datasets: PushExportDatasets
) -> BucketNotification:
    """Create a combined BucketNotification for the export bucket, based on all the
    push datasets that can export from it.

    Parameters
    ----------
    name : str
        What to call the resulting BucketNotification.
    export_bucket : Bucket
        The Pulumi Bucket object representing the AWS resource.
    datasets : PushExportDatasets
        The push datasets to create notifications for - must already have run
        build_lambda_functions.

    Returns
    -------
    BucketNotification
        A single BucketNotification for the export bucket, containing a
        BucketNotificationLambdaFunctionArgs for each of the Lambda functions that use
        the export bucket.
    """
    return BucketNotification(
        resource_name=name,
        bucket=export_bucket.id,
        lambda_functions=[make_notification_lambda_args(d) for d in datasets.datasets],
        opts=ResourceOptions(
            depends_on=[
                lambda_function._function for lambda_function in datasets.lambdas
            ]
            + [export_bucket]
        ),
    )
