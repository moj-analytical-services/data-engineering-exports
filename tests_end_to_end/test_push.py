import json

import boto3
from data_engineering_pulumi_components.aws import Bucket
from data_engineering_pulumi_components.utils import Tagger
from pulumi import export
from pulumi_aws.iam import Role

from data_engineering_exports.utils_for_tests import PulumiTestInfrastructure

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
    target_bucket_1 = Bucket(
        name="target-bucket-1",
        tagger=tagger,
    )
    target_bucket_2 = Bucket(
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
                        "Principal": {"Service": "lambda.amazonaws.com"},
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
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {"Service": "lambda.amazonaws.com"},
                        "Action": "sts:AssumeRole",
                    }
                ],
            }
        ),
    )


def test_infrastructure():
    """
    Use test
    Create PushExportDatasets

    """
    with PulumiTestInfrastructure(pulumi_program=pulumi_program, region=test_region):
        # List buckets
        s3 = boto3.client(
            "s3",
            endpoint_url="http://localhost:4566",
            aws_access_key_id="test_key",
            aws_secret_access_key="test_secret",
        )
        response = s3.list_buckets()

        # Output the bucket names
        for bucket in response["Buckets"]:
            print(f'{bucket["Name"]}')

        assert 0
