import json
import os

import boto3
from data_engineering_pulumi_components.aws import Bucket
from data_engineering_pulumi_components.utils import Tagger
from pulumi import export
from pulumi_aws.iam import Role

from data_engineering_exports.utils_for_tests import PulumiTestInfrastructure
from data_engineering_exports.utils import list_yaml_files
from data_engineering_exports import push

test_region = "eu-west-1"


def pulumi_program():
    """Create:
    - an export bucket
    - 2 target buckets
    - 2 user roles
    """
    tagger = Tagger(environment_name="test")
    test_export_bucket = Bucket(
        name="test-export-bucket",
        tagger=tagger,
    )
    Bucket(
        name="target-bucket-1",
        tagger=tagger,
    )
    Bucket(
        name="target-bucket-2",
        tagger=tagger,
    )
    # In AWS terms, what we call an Analytical Platform 'user' is a role.
    user_1 = Role(
        resource_name="alpha_user_test_1",
        name="alpha_user_test_1",
        assume_role_policy=json.dumps(
            {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {
                            "AWS": "arn:aws:sts::000000000000:user/localstack"
                        },
                        "Action": "sts:AssumeRole",
                    }
                ],
            }
        ),
    )
    user_2 = Role(
        resource_name="alpha_user_test_2",
        name="alpha_user_test_2",
        assume_role_policy=json.dumps(
            {
                "Version": "2012-10-17",
                "Statement": [],
            }
        ),
    )
    push_config_files = list_yaml_files("tests_end_to_end/data")
    datasets = push.PushExportDatasets(push_config_files, test_export_bucket, tagger)
    datasets.load_datasets_and_users()
    datasets.build_lambda_functions()
    datasets.build_role_policies()

    # Create combined bucket notification for test export bucket
    push.make_combined_bucket_notification(
        "test-bucket-notification", test_export_bucket, datasets
    )

    # Export the role arns for the users
    export("user_role_1", user_1.arn)
    export("user_role_2", user_2.arn)


def test_infrastructure():
    """
    Use test
    Create PushExportDatasets

    """
    with PulumiTestInfrastructure(
        pulumi_program=pulumi_program, region=test_region
    ) as stack:
        # Create boto3 client and assumed role objects
        os.environ["AWS_ACCESS_KEY_ID"] = "test_key"
        os.environ["AWS_SECRET_ACCESS_KEY"] = "test_secret"
        user_role_1 = stack.up_results.outputs["user_role_1"].value
        # user_role_2 = stack.up_results.outputs["user_role_2"].value

        session = boto3.Session()
        s3_client = session.client("s3", endpoint_url="http://localhost:4566")
        sts_client = boto3.client("sts", endpoint_url="http://localhost:4566")
        assumed_user_1 = sts_client.assume_role(
            RoleArn=user_role_1,
            RoleSessionName="user_1_session",
        )
        user_1_creds = assumed_user_1["Credentials"]

        user_1_session = boto3.Session(
            region_name="eu-west-1",
            aws_access_key_id=user_1_creds["AccessKeyId"],
            aws_secret_access_key=user_1_creds["SecretAccessKey"],
            aws_session_token=user_1_creds["SessionToken"],
        )
        user_1_s3_client = user_1_session.client("s3")
        print(user_1_s3_client.list_objects_v2(Bucket="test-export-bucket"))

        # Check both target buckets are empty
        bucket_1_contents = s3_client.list_objects_v2(
            Bucket="target-bucket-1",
        )
        bucket_2_contents = s3_client.list_objects_v2(
            Bucket="target-bucket-2",
        )
        assert "Contents" not in bucket_1_contents
        assert "Contents" not in bucket_2_contents

        # Check user 1 can export to target bucket 1
        user_1_s3_client.put_object(
            Bucket="test-export-bucket",
            Body="test text",
            Key="push_test_1/file_1.txt",
            # ServerSideEncryption="AES256",
            # ACL="bucket-owner-full-control",
        )

        # Check user 1 and user 2 can both export to target bucket 2

        # Check user 2 can't put files in export bucket's prefix for dataset 1
        # Check user 1 can't put files in export bucket root

        # Check files have been deleted from the export bucket
        assert 0
