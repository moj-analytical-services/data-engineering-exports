import os
from time import sleep

import boto3
from data_engineering_pulumi_components.aws import Bucket
from data_engineering_pulumi_components.utils import Tagger
from pulumi import ResourceOptions, export
from pulumi_aws.iam import (
    get_policy_document,
    GetPolicyDocumentStatementArgs,
    GetPolicyDocumentStatementPrincipalArgs,
)
from pulumi_aws.s3 import BucketPolicy

from data_engineering_exports.utils_for_tests import (
    PulumiTestInfrastructure,
    mock_alpha_user,
    check_bucket_contents,
)
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
    target_bucket_1 = Bucket(
        name="target-bucket-1",
        tagger=tagger,
    )
    target_bucket_2 = Bucket(
        name="target-bucket-2",
        tagger=tagger,
    )
    # In AWS terms, what we call an Analytical Platform 'user' is a role
    # Both roles let the Localstack user assume them, and grant no other permissions
    user_1 = mock_alpha_user("alpha_user_test_1")
    user_2 = mock_alpha_user("alpha_user_test_2")

    push_config_files = list_yaml_files("tests/data/end_to_end")
    datasets = push.PushExportDatasets(push_config_files, test_export_bucket, tagger)
    datasets.load_datasets_and_users()
    datasets.build_lambda_functions()
    datasets.build_role_policies()

    # Create combined bucket notification for test export bucket
    push.make_combined_bucket_notification(
        "test-bucket-notification", test_export_bucket, datasets
    )

    # Let the target buckets accept put commands from the Lambdas
    # In production the Cloud Platform/Performance Hub team have to do this
    bucket_policy = BucketPolicy(
        resource_name="target-bucket-1-policy",
        bucket=target_bucket_1.id,
        policy=get_policy_document(
            statements=[
                GetPolicyDocumentStatementArgs(
                    actions=[
                        "s3:PutObject*",
                        "s3:PutObjectAcl",
                        "s3:PutObjectTagging",
                    ],
                    principals=[
                        GetPolicyDocumentStatementPrincipalArgs(
                            identifiers=[
                                lambda_func._role.arn
                                for lambda_func in datasets.lambdas
                            ],
                            type="AWS",
                        )
                    ],
                    resources=["arn:aws:s3:::target-bucket-1/*"],
                ),
                GetPolicyDocumentStatementArgs(
                    actions=["s3:ListBucket"],
                    principals=[
                        GetPolicyDocumentStatementPrincipalArgs(
                            identifiers=[
                                lambda_func._role.arn
                                for lambda_func in datasets.lambdas
                            ],
                            type="AWS",
                        )
                    ],
                    resources=["arn:aws:s3:::target-bucket-1"],
                ),
            ]
        ).json,
        opts=ResourceOptions(
            parent=target_bucket_1,
            depends_on=[role._role for role in datasets.lambdas],
        ),
    )
    # Export the role arns for the users and Lambda functions
    export("user_role_1", user_1.arn)
    export("user_role_2", user_2.arn)
    export("lambda_role_0", datasets.lambdas[0]._role.arn)
    export("lambda_role_1", datasets.lambdas[1]._role.arn)


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
        os.environ["AWS_DEFAULT_REGION"] = test_region
        user_role_1 = stack.up_results.outputs["user_role_1"].value
        user_role_2 = stack.up_results.outputs["user_role_2"].value

        session = boto3.Session()
        s3_client = session.client("s3", endpoint_url="http://localhost:4566")
        sts_client = session.client("sts", endpoint_url="http://localhost:4566")

        # Use the sts client to assume the user roles
        # User 1
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
        user_1_s3_client = user_1_session.client(
            "s3", endpoint_url="http://localhost:4566"
        )

        # User 2
        assumed_user_2 = sts_client.assume_role(
            RoleArn=user_role_2,
            RoleSessionName="user_2_session",
        )
        user_2_creds = assumed_user_2["Credentials"]

        user_2_session = boto3.Session(
            region_name="eu-west-1",
            aws_access_key_id=user_2_creds["AccessKeyId"],
            aws_secret_access_key=user_2_creds["SecretAccessKey"],
            aws_session_token=user_2_creds["SessionToken"],
        )
        user_2_s3_client = user_2_session.client(
            "s3", endpoint_url="http://localhost:4566"
        )

        # Check both target buckets and export bucket are empty
        export_bucket_contents = s3_client.list_objects_v2(
            Bucket="test-export-bucket",
        )
        bucket_1_contents = s3_client.list_objects_v2(
            Bucket="target-bucket-1",
        )
        bucket_2_contents = s3_client.list_objects_v2(
            Bucket="target-bucket-2",
        )
        assert "Contents" not in export_bucket_contents
        assert "Contents" not in bucket_1_contents
        assert "Contents" not in bucket_2_contents

        # Check user 1 can upload to push_test_1 but user 2 can't
        user_1_s3_client.put_object(
            Bucket="test-export-bucket",
            Body="test text",
            Key="push_test_1/pass.txt",
        )
        user_2_s3_client.put_object(
            Bucket="test-export-bucket",
            Body="test text",
            Key="push_test_1/fail.txt",
        )

        # Check only pass.txt reaches the target bucket
        sleep(5)
        check_bucket_contents("target-bucket-1", ["push_test_1/pass.txt"], s3_client)

        # Check the export bucket is empty
        check_bucket_contents("test-export-bucket", None, s3_client)

        # Check they can both export to target bucket 2
        user_1_s3_client.put_object(
            Bucket="test-export-bucket",
            Body="test text",
            Key="push_test_2/pass_1.txt",
        )
        user_2_s3_client.put_object(
            Bucket="test-export-bucket",
            Body="test text",
            Key="push_test_2/pass_2.txt",
        )
        # Check both files reach the target bucket
        sleep(5)
        check_bucket_contents(
            "target-bucket-2",
            [
                "push_test_2/pass_1.txt",
                "push_test_2/pass_2.txt",
            ],
            s3_client,
        )

        # Finally, check the export bucket is once again empty
        check_bucket_contents("test-export-bucket", None, s3_client)
