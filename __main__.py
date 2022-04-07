from data_engineering_pulumi_components.aws import Bucket
from data_engineering_pulumi_components.utils import Tagger
from data_engineering_pulumi_components.aws.lambdas.move_object_function import (
    MoveObjectFunction,
)
from pulumi import ResourceOptions, get_stack, export, Output
from pulumi_aws.iam import RolePolicy
from pulumi_aws.s3 import BucketPolicy
import yaml

import data_engineering_exports.policies as policies
import data_engineering_exports.utils as utils


# PUSH INFRASTRUCTURE
# When files are added to a bucket, move them to their target bucket
stack = get_stack()
tagger = Tagger(environment_name=stack)
export_bucket = Bucket(name="mojap-hub-exports", tagger=tagger)

# Collect data from the config files
push_config_files = utils.list_yaml_files("push_datasets")
datasets_to_buckets, users = utils.load_push_config_data(push_config_files)
target_buckets = set(datasets_to_buckets.values())

# Lambda function for each dataset
for dataset, target_bucket in datasets_to_buckets.items():
    move_object_function = MoveObjectFunction(
        destination_bucket=target_bucket,
        name=f"export-{dataset}",
        source_bucket=export_bucket,
        tagger=tagger,
        prefix=dataset,
    )
    export(name=f"{dataset}-export-role-arn", value=move_object_function._role.arn)

# For each user, create a role policy to let them add to the export bucket
for user, prefixes in users.items():
    role_policy = policies.WriteToExportBucketRolePolicy(user, export_bucket, prefixes)

# PULL INFRASTRUCTURE
# Let an external role get files from a bucket
pull_config_files = utils.list_yaml_files("pull_datasets")

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
