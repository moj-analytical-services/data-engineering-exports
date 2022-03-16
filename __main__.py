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
# When files are added to a bucket, move them to the Performance Hub
HUB_LANDING_BUCKET = "performance-hub-land"

stack = get_stack()
tagger = Tagger(environment_name=stack)
export_bucket = Bucket(name="mojap-hub-exports", tagger=tagger)

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
rolePolicy = RolePolicy(
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
                    resources=[f"arn:aws:s3:::{HUB_LANDING_BUCKET}/*"],
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
function = Function(
    resource_name="export",
    code=FileArchive("data_engineering_exports/lambda_/export"),
    description="Export objects from the Analytical Platform to the Hub",
    environment={"variables": {"HUB_LANDING_BUCKET": HUB_LANDING_BUCKET}},
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

# Gather push config files
filter_prefixes = []
push_config_files = list(Path("push_datasets").glob("*.yaml"))

# For each config, create a role policy for each user to let them add to bucket
# TODO: let users appear in multiple configs without overwriting
for file in push_config_files:
    with open(file, mode="r") as f:
        dataset = yaml.safe_load(f)
        name = dataset["name"]
        filter_prefixes.append(f"{name}/")
    for user in dataset["users"]:
        RolePolicy(
            resource_name=user,
            policy=Output.all(export_bucket.arn, name).apply(
                lambda args: get_policy_document(
                    statements=[
                        GetPolicyDocumentStatementArgs(
                            actions=[
                                "s3:PutObject",
                                "s3:PutObjectAcl",
                                "s3:PutObjectTagging",
                            ],
                            resources=[f"{args[0]}/{args[1]}/*"],
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
            filter_prefix=filter_prefix,
            lambda_function_arn=function.arn,
        )
        for filter_prefix in filter_prefixes
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
    policy = Output.all(bucket_arn=pull_bucket.arn, pull_arns=pull_arns).apply(
        policies.create_pull_bucket_policy
    )
    BucketPolicy(
        resource_name=f"{name}-bucket-policy",
        bucket=pull_bucket.id,
        policy=policy,
        opts=ResourceOptions(parent=pull_bucket),
    )

    # Add role policy for each user
    for user in users:
        RolePolicy(
            resource_name=user,
            policy=Output.all(pull_bucket.arn).apply(
                lambda args: policies.create_read_write_role_policy(args)
            ),
            role=user,
            name=f"hub-exports-pull-{name}",
        )
