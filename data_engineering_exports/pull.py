from typing import Dict

from pulumi_aws.iam import GetPolicyDocumentStatementArgs
from pulumi_aws.iam.get_policy_document import (
    get_policy_document,
    AwaitableGetPolicyDocumentResult,
)


def create_pull_bucket_policy(args: Dict[str, str]) -> Dict:
    """Create policy for a bucket to permit get access for a specific list of ARNs.
    The ARNs can be from another account.

    Parameters
    ----------
    args : dict
        Should contain 2 keys:
        - bucket_arn (str): ARN of the bucket to attach the policy to.
        - pull_arns (list): list of ARNs that should be allowed to read from the bucket.

    Returns
    -------
    Dict
        AWS bucket policy.
    """
    bucket_arn = args.pop("bucket_arn")
    pull_arns = args.pop("pull_arns")
    allow_push = args.pop("allow_push", False)
    writable_actions = [
        "s3:RestoreObject",
        "s3:PutObjectTagging",
        "s3:PutObjectAcl",
        "s3:PutObject",
        "s3:GetObjectVersion",
        "s3:GetObjectAcl",
        "s3:GetObject",
        "s3:DeleteObjectVersion",
        "s3:DeleteObject",
    ]
    standard_actions = ["s3:GetObjectVersion", "s3:GetObjectAcl", "s3:GetObject"]
    if allow_push:
        bucket_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "",
                    "Effect": "Allow",
                    "Action": writable_actions,
                    "Principal": {"AWS": pull_arns},
                    "Resource": bucket_arn + "/*",
                },
                {
                    "Sid": "",
                    "Effect": "Allow",
                    "Action": "s3:ListBucket",
                    "Principal": {"AWS": pull_arns},
                    "Resource": bucket_arn,
                },
                {
                    "Sid": "",
                    "Effect": "Deny",
                    "Action": "s3:*",
                    "Principal": "*",
                    "Resource": [bucket_arn, bucket_arn + "/*"],
                    "Condition": {"NumericLessThan": {"s3:TlsVersion": "1.2"}},
                },
            ],
        }
    else:
        bucket_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "",
                    "Effect": "Allow",
                    "Action": standard_actions,
                    "Principal": {"AWS": pull_arns},
                    "Resource": bucket_arn + "/*",
                },
                {
                    "Sid": "",
                    "Effect": "Allow",
                    "Action": "s3:ListBucket",
                    "Principal": {"AWS": pull_arns},
                    "Resource": bucket_arn,
                },
                {
                    "Sid": "",
                    "Effect": "Deny",
                    "Action": "s3:*",
                    "Principal": "*",
                    "Resource": [bucket_arn, bucket_arn + "/*"],
                    "Condition": {"NumericLessThan": {"s3:TlsVersion": "1.2"}},
                },
            ],
        }
    return bucket_policy


def create_read_write_role_policy(
    args: Dict[str, str]
) -> AwaitableGetPolicyDocumentResult:
    """Create role policy that gives get, put, delete and restore access to a bucket.

    Parameters
    ----------
    args : dict
        Should contain 1 key:
        - bucket_arn (str): ARN of the bucket to attach the policy to.

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
