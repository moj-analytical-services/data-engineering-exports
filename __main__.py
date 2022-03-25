from collections import defaultdict
from pathlib import Path

from data_engineering_pulumi_components.aws import Bucket
from data_engineering_pulumi_components.utils import Tagger
from pulumi import FileArchive, ResourceOptions, get_stack, export, Output
from pulumi_aws.iam import (
    GetPolicyDocumentStatementArgs,
    GetPolicyDocumentStatementPrincipalArgs,
    Role,
    RolePolicy,
    RolePolicyAttachment,
    get_policy_document,
)
from pulumi_aws.lambda_ import Function, Permission
from pulumi_aws.s3 import (
    BucketNotification,
    BucketNotificationLambdaFunctionArgs,
    BucketPolicy,
)
import yaml

import data_engineering_exports.policies as policies


# PUSH INFRASTRUCTURE
# When files are added to a bucket, move them to their target bucket
stack = get_stack()
tagger = Tagger(environment_name=stack)
export_bucket = Bucket(name="mojap-hub-exports", tagger=tagger)

# Gather push config files
push_config_files = list(Path("push_datasets").glob("*.yaml"))

# Collect data from the configs
target_buckets = set()
datasets_to_buckets = {}  # which target bucket each dataset should use
users = {}  # who can write to the export bucket (and permitted prefixes)
for file in push_config_files:
    with open(file, mode="r") as f:
        dataset = yaml.safe_load(f)

    dataset_name = dataset["name"]
    target_bucket = dataset["bucket"]

    target_buckets.add(target_bucket)
    datasets_to_buckets[dataset_name] = target_bucket

    for user in dataset["users"]:
        users[user] = users.get(user, [])
        users.setdefault(user, []).append(dataset_name)

# Export role
role = Role(
    resource_name="export",
    assume_role_policy=get_policy_document(
        statements=[
            GetPolicyDocumentStatementArgs(
                actions=["sts:AssumeRole"],
                principals=[
                    GetPolicyDocumentStatementPrincipalArgs(
                        identifiers=["lambda.amazonaws.com"], type="Service"
                    )
                ],
            )
        ]
    ).json,
    name="analytical-platform-hub-export",
    path="/service-role/",
    tags=tagger.create_tags("analytical-platform-hub-export"),
)

# Export role policy
# Can get and delete from the export bucket
# Can write to the target buckets
role_policy = RolePolicy(
    resource_name="export",
    policy=export_bucket.arn.apply(
        lambda arn: get_policy_document(
            statements=[
                GetPolicyDocumentStatementArgs(
                    actions=["s3:GetObject", "s3:DeleteObject"],
                    resources=[f"{arn}/*"],
                ),
                GetPolicyDocumentStatementArgs(
                    actions=["s3:PutObject", "s3:PutObjectAcl"],
                    resources=[f"arn:aws:s3:::{bucket}/*" for bucket in target_buckets],
                ),
            ]
        ).json
    ),
    role=role.id,
    name="analytical-platform-hub-copy",
    opts=ResourceOptions(parent=role),
)

# Export role policy attachment
rolePolicyAttachment = RolePolicyAttachment(
    resource_name="export",
    policy_arn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
    role=role.id,
    opts=ResourceOptions(parent=role),
)

# Lambda function that sends files from export bucket to hub landing bucket
env_variables = {
    project.upper(): bucket for project, bucket in datasets_to_buckets.items()
}
function = Function(
    resource_name="export",
    code=FileArchive("data_engineering_exports/lambda_/export"),
    description="Export objects from the Analytical Platform to the Hub",
    environment={"variables": env_variables},
    handler="export.handler",
    name="analytical-platform-hub-export",
    role=role.arn,
    runtime="python3.8",
    tags=tagger.create_tags("analytical-platform-hub-export"),
    timeout=60,
)

# Permissions for the Lambda function
permission = Permission(
    resource_name="export",
    action="lambda:InvokeFunction",
    function=function.name,
    principal="s3.amazonaws.com",
    source_arn=export_bucket.arn,
    opts=ResourceOptions(parent=function),
)

# For each user, create a role policy to let them add to the export bucket
for user, prefixes in users.items():
    RolePolicy(
        resource_name=user,
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
        role=user,
        name="hub-exports",
    )

bucket_notification = BucketNotification(
    resource_name="export",
    bucket=export_bucket.id,
    lambda_functions=[
        BucketNotificationLambdaFunctionArgs(
            events=["s3:ObjectCreated:*"],
            filter_prefix=f"{filter_prefix}/",
            lambda_function_arn=function.arn,
        )
        for filter_prefix in datasets_to_buckets.keys()
    ],
    opts=ResourceOptions(depends_on=[permission]),
)

export(name="role_arn", value=role.arn)

# PULL INFRASTRUCTURE
# Let an external role get files from a bucket
pull_config_files = list(Path("pull_datasets").glob("*.yaml"))

# For each config, create a bucket
for file in pull_config_files:
    with open(file, mode="r") as f:
        dataset = yaml.safe_load(f)
        name = dataset["name"]
        pull_arns = dataset["pull_arns"]
        users = dataset["users"]

    pull_bucket = Bucket(
        name=f"mojap-{name}",
        tagger=tagger,
    )

    # Add bucket policy allowing the specified arn to read
    bucket_policy = Output.all(bucket_arn=pull_bucket.arn, pull_arns=pull_arns).apply(
        policies.create_pull_bucket_policy
    )
    BucketPolicy(
        resource_name=f"{name}-bucket-policy",
        bucket=pull_bucket.id,
        policy=bucket_policy.json,
        opts=ResourceOptions(parent=pull_bucket),
    )

    # Add role policy for each user
    role_policy = Output.all(bucket_arn=pull_bucket.arn).apply(
        policies.create_read_write_role_policy
    )
    for user in users:
        RolePolicy(
            resource_name=user,
            policy=role_policy.json,
            role=user,
            name=f"hub-exports-pull-{name}",
        )
