from data_engineering_pulumi_components.aws import Bucket
from data_engineering_pulumi_components.utils import Tagger
from pulumi import ResourceOptions, get_stack, export, Output
from pulumi_aws.iam import RolePolicy
from pulumi_aws.s3 import BucketPolicy

import data_engineering_exports.pull as pull
import data_engineering_exports.push as push
import data_engineering_exports.utils as utils


# PUSH INFRASTRUCTURE
# When files are added to the export bucket, move or copy them to their target bucket
stack = get_stack()
tagger = Tagger(environment_name=stack)
export_bucket = Bucket(name="mojap-hub-exports", tagger=tagger)
export("export_bucket", export_bucket._bucket.arn)

# Load the datasets and build AWS resources from them
push_config_files = utils.list_yaml_files("push_datasets")
datasets = push.PushExportDatasets(push_config_files, export_bucket, tagger)
datasets.load_datasets_and_users()
datasets.build_lambda_functions()
datasets.build_role_policies()

# Create combined bucket notification
# You can only have one BucketNotification per bucket, so create a single combined one
bucket_notification = push.make_combined_bucket_notification(
    name="export-bucket-notification", export_bucket=export_bucket, datasets=datasets
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
    if "allow_push" in dataset.keys():
        writable = dataset["allow_push"]
    else:
        writable = False

    pull_bucket = Bucket(
        name=f"mojap-{name}",
        tagger=tagger,
    )

    # Add bucket policy allowing the specified arn to read
    bucket_policy = Output.all(
        bucket_arn=pull_bucket.arn,
        pull_arns=pull_arns,
        allow_push=writable
    ).apply(
        pull.create_pull_bucket_policy
    )
    BucketPolicy(
        resource_name=f"{name}-bucket-policy",
        bucket=pull_bucket.id,
        policy=bucket_policy.json,
        opts=ResourceOptions(parent=pull_bucket),
    )

    # Add role policy for each user
    role_policy = Output.all(bucket_arn=pull_bucket.arn).apply(
        pull.create_read_write_role_policy
    )
    for user in users:
        RolePolicy(
            resource_name=user + "_exports_pull",
            policy=role_policy.json,
            role=user,
            name=f"hub-exports-pull-{name}",
        )
