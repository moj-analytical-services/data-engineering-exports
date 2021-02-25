from pathlib import Path

import yaml
from data_engineering_pulumi_components.aws import Bucket
from dataengineeringutils3.pulumi import Tagger
from pulumi_aws.iam import (
    GetPolicyDocumentStatementArgs,
    GetPolicyDocumentStatementPrincipalArgs,
    Role,
    RolePolicy,
    RolePolicyAttachment,
    get_policy_document,
)
from pulumi_aws.lambda_ import Function, Permission
from pulumi_aws.s3 import BucketNotification, BucketNotificationLambdaFunctionArgs

from pulumi import AssetArchive, FileArchive, ResourceOptions, get_stack

TARGET_BUCKET = "alpha-everyone"

stack = get_stack()

tagger = Tagger(environment_name=stack)

bucket = Bucket(
    resource_name="export",
    name=f"mojap-hub-exports-{stack}",
    tags=tagger.create_tags(f"mojap-hub-exports-{stack}"),
)

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
    name=f"analytical-platform-hub-export-{stack}",
    path="/service-role/",
    tags=tagger.create_tags(f"analytical-platform-hub-export-{stack}"),
)

rolePolicy = RolePolicy(
    resource_name="export",
    policy=bucket.arn.apply(
        lambda arn: get_policy_document(
            statements=[
                GetPolicyDocumentStatementArgs(
                    actions=["s3:GetObject", "s3:DeleteObject"],
                    resources=[f"{arn}/*"],
                ),
                GetPolicyDocumentStatementArgs(
                    actions=["s3:PutObject", "s3:PutObjectAcl"],
                    resources=[f"arn:aws:s3:::{TARGET_BUCKET}/*"],
                ),
            ]
        ).json
    ),
    role=role.id,
    name="analytical-platform-hub-copy",
    opts=ResourceOptions(parent=role),
)

rolePolicyAttachment = RolePolicyAttachment(
    resource_name="export",
    policy_arn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
    role=role.id,
    opts=ResourceOptions(parent=role),
)

function = Function(
    resource_name="export",
    code=FileArchive("./lambda_/export"),
    description="Export objects from the Analytical Platform to the Hub",
    environment={"variables": {"TARGET_BUCKET": TARGET_BUCKET}},
    handler="export.handler",
    name=f"analytical-platform-hub-export-{stack}",
    role=role.arn,
    runtime="python3.8",
    tags=tagger.create_tags(f"analytical-platform-hub-export-{stack}"),
    timeout=60,
)

permission = Permission(
    resource_name="export",
    action="lambda:InvokeFunction",
    function=function.name,
    principal="s3.amazonaws.com",
    source_arn=bucket.arn,
    opts=ResourceOptions(parent=function),
)

filter_prefixes = []
files = list(Path("../datasets").glob("*.yaml"))

for file in files:
    with open(file, mode="r") as f:
        dataset = yaml.safe_load(f)
        name = dataset["name"]
        filter_prefixes.append(f"{name}/")
    for user in dataset["users"]:
        RolePolicy(
            resource_name=user,
            policy=bucket.arn.apply(
                lambda arn: get_policy_document(
                    statements=[
                        GetPolicyDocumentStatementArgs(
                            actions=["s3:PutObject"],
                            resources=[f"{arn}/{name}/*"],
                        )
                    ]
                ).json
            ),
            role=user,
            name="hub-exports",
        )

bucket_notification = BucketNotification(
    resource_name="export",
    bucket=bucket.id,
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
