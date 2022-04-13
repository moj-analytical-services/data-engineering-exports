from data_engineering_pulumi_components.aws import Bucket
from data_engineering_pulumi_components.utils import Tagger
from pulumi import ResourceOptions, get_stack, export, Output
from pulumi_aws.iam import RolePolicy
from pulumi_aws.s3 import BucketPolicy

import data_engineering_exports.infrastructure as infrastructure
import data_engineering_exports.utils as utils


# PUSH INFRASTRUCTURE
# When files are added to a bucket, move them to their target bucket
stack = get_stack()
tagger = Tagger(environment_name=stack)
export_bucket = Bucket(name="mojap-hub-exports", tagger=tagger)

# Collect data from the config files
push_config_files = utils.list_yaml_files("push_datasets")
datasets, users = utils.get_datasets_and_users(push_config_files, export_bucket, tagger)

# Create move or copy Lambda function for each dataset
for dataset in datasets:
    dataset.build_lambda_function()
    export(
        name=f"{dataset.name}_export_role_arn", value=dataset.lambda_function._role.arn
    )

# For each user, create a role policy to let them add to the export bucket
for user, prefixes in users.items():
    role_policy = infrastructure.WriteToExportBucketRolePolicy(
        user, export_bucket, prefixes
    )

# PULL INFRASTRUCTURE
# Let an external role get files from a bucket
pull_config_files = utils.list_yaml_files("pull_datasets")

# For each config, create a bucket
for file in pull_config_files:
    dataset = utils.load_yaml(file)

    name = dataset["name"]
    pull_arns = dataset["pull_arns"]
    users = dataset["users"]

    pull_bucket = Bucket(
        name=f"mojap-{name}",
        tagger=tagger,
    )

    # Add bucket policy allowing the specified arn to read
    bucket_policy = Output.all(bucket_arn=pull_bucket.arn, pull_arns=pull_arns).apply(
        infrastructure.create_pull_bucket_policy
    )
    BucketPolicy(
        resource_name=f"{name}-bucket-policy",
        bucket=pull_bucket.id,
        policy=bucket_policy.json,
        opts=ResourceOptions(parent=pull_bucket),
    )

    # Add role policy for each user
    role_policy = Output.all(bucket_arn=pull_bucket.arn).apply(
        infrastructure.create_read_write_role_policy
    )
    for user in users:
        RolePolicy(
            resource_name=user,
            policy=role_policy.json,
            role=user,
            name=f"hub-exports-pull-{name}",
        )
