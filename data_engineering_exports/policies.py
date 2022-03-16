from typing import Dict, List

from pulumi_aws.iam import (
    GetPolicyDocumentStatementArgs,
    GetPolicyDocumentStatementPrincipalArgs,
    get_policy_document,
)


def create_pull_bucket_policy(args: Dict[str, str]) -> Dict[str, str]:
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
    dict
        Json of the policy document.
    """
    bucket_arn = args.pop("bucket_arn")
    pull_arns = args.pop("pull_arns")

    policy = get_policy_document(
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
    ).json
    return policy


def create_read_write_role_policy(args: List[str]) -> Dict[str, str]:
    """Create role policy that gives get, put, delete and restore access to a bucket.

    Parameters
    ----------
    args : list
        Should contain 1 item: the Arn of the bucket to attach the policy to.

    Returns
    -------
    dict
        Json of the policy document.
    """
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
                resources=[f"{args[0]}/*"],
            ),
            GetPolicyDocumentStatementArgs(
                actions=["s3:ListBucket"],
                resources=[args[0]],
            ),
        ]
    )
    return role_policy.json