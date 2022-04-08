from typing import Dict, List

from data_engineering_pulumi_components.aws import Bucket
from data_engineering_pulumi_components.utils import Tagger
from data_engineering_pulumi_components.aws.lambdas.move_object_function import (
    MoveObjectFunction,
)
from data_engineering_pulumi_components.aws.lambdas.copy_object_function import (
    CopyObjectFunction,
)
from pulumi import Output
from pulumi_aws.iam import (
    GetPolicyDocumentStatementArgs,
    GetPolicyDocumentStatementPrincipalArgs,
    RolePolicy,
)
from pulumi_aws.iam.get_policy_document import (
    get_policy_document,
    AwaitableGetPolicyDocumentResult,
)


class PushExportDataset:
    def __init__(self, config: dict, export_bucket: Bucket, tagger: Tagger):
        """Load all the details of a push dataset. Has no initial lambda_function.

        Parameters
        ----------
        config : dict
            A dictionary loaded from a yaml config file.
        export_bucket : Bucket
            The bucket the data will be exported from.
        tagger : Tagger
            A Tagger object from data-engineering-pulumi-components.utils
        """
        self.name = config["name"]
        self.target_bucket = config["target_bucket"]
        self.keep_files = config["keep_files"]
        self.export_bucket = export_bucket
        self.tagger = tagger
        self.lambda_function = None

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
    def __init__(self, username: str, export_bucket: Bucket, prefixes: List[str]):
        """Let a user put items in specific parts of the export bucket.

        NEEDS DOCS
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


def create_pull_bucket_policy(args: Dict[str, str]) -> AwaitableGetPolicyDocumentResult:
    """Create policy for a bucket to permit get access for a specific list of Arns.
    The Arns can be from another account.

    Parameters
    ----------
    args : dict
        Should contain 2 keys:
        - bucket_arn (str): Arn of the bucket to attach the policy to.
        - pull_arns (list): list of Arns that should be allowed to read from the bucket.

    Returns
    -------
    AwaitableGetPolicyDocumentResult
        Pulumi output of the get_policy_document function.
    """
    bucket_arn = args.pop("bucket_arn")
    pull_arns = args.pop("pull_arns")

    bucket_policy = get_policy_document(
        statements=[
            GetPolicyDocumentStatementArgs(
                actions=[
                    "s3:GetObject",
                    "s3:GetObjectAcl",
                    "s3:GetObjectVersion",
                ],
                principals=[
                    GetPolicyDocumentStatementPrincipalArgs(
                        identifiers=pull_arns, type="AWS"
                    )
                ],
                resources=[bucket_arn + "/*"],
            ),
            GetPolicyDocumentStatementArgs(
                actions=["s3:ListBucket"],
                principals=[
                    GetPolicyDocumentStatementPrincipalArgs(
                        identifiers=pull_arns, type="AWS"
                    )
                ],
                resources=[bucket_arn],
            ),
        ]
    )
    return bucket_policy


def create_read_write_role_policy(
    args: Dict[str, str]
) -> AwaitableGetPolicyDocumentResult:
    """Create role policy that gives get, put, delete and restore access to a bucket.

    Parameters
    ----------
    args : dict
        Should contain 1 key:
        - bucket_arn (str): Arn of the bucket to attach the policy to.

    Returns
    -------
    AwaitableGetPolicyDocumentResult
        Pulumi output of the get_policy_document function.
    """
    bucket_arn = args.pop("bucket_arn")

    role_policy = get_policy_document(
        statements=[
            GetPolicyDocumentStatementArgs(
                actions=[
                    "s3:GetObject",
                    "s3:GetObjectAcl",
                    "s3:GetObjectVersion",
                    "s3:DeleteObject",
                    "s3:DeleteObjectVersion",
                    "s3:PutObject",
                    "s3:PutObjectAcl",
                    "s3:PutObjectTagging",
                    "s3:RestoreObject",
                ],
                resources=[f"{bucket_arn}/*"],
            ),
            GetPolicyDocumentStatementArgs(
                actions=["s3:ListBucket"],
                resources=[bucket_arn],
            ),
        ]
    )
    return role_policy
