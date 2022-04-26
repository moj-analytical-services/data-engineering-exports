from pulumi import Output
import pulumi.runtime

from data_engineering_exports.pull import (
    create_pull_bucket_policy,
    create_read_write_role_policy,
)
from tests.utils_for_tests import assert_pulumi_output_equals_expected


@pulumi.runtime.test
def test_create_pull_bucket_policy():
    """Checks policy statements for a bucket that lets external roles read from it."""
    policy = create_pull_bucket_policy(
        {"bucket_arn": "test-bucket", "pull_arns": ["arn-one", "arn-two"]}
    )
    expected = [
        {
            "actions": ["s3:GetObject", "s3:GetObjectAcl", "s3:GetObjectVersion"],
            "principals": [{"identifiers": ["arn-one", "arn-two"], "type": "AWS"}],
            "resources": ["test-bucket/*"],
        },
        {
            "actions": ["s3:ListBucket"],
            "principals": [{"identifiers": ["arn-one", "arn-two"], "type": "AWS"}],
            "resources": ["test-bucket"],
        },
    ]
    return Output.all(policy.statements, expected).apply(
        assert_pulumi_output_equals_expected
    )


@pulumi.runtime.test
def test_create_read_write_role_policy():
    policy = create_read_write_role_policy({"bucket_arn": "test-bucket"})
    expected = [
        {
            "actions": [
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
            "resources": ["test-bucket/*"],
        },
        {
            "actions": ["s3:ListBucket"],
            "resources": ["test-bucket"],
        },
    ]
    return Output.all(policy.statements, expected).apply(
        assert_pulumi_output_equals_expected
    )
