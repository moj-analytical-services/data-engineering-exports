from pulumi import Output
import pulumi.runtime

from data_engineering_exports.pull import (
    create_pull_bucket_policy,
    create_read_write_role_policy,
)


def assert_pulumi_output_equals_expected(args):
    output, expected = args
    assert output == expected


@pulumi.runtime.test
def test_create_pull_bucket_policy():
    """Checks policy statements for a bucket that lets external roles read from it."""
    policy = create_pull_bucket_policy(
        {"bucket_arn": "arn:aws:s3:::test-bucket", "pull_arns": ["arn-one", "arn-two"]}
    )
    expected = [
        {
            "actions": ["s3:GetObject", "s3:GetObjectAcl", "s3:GetObjectVersion"],
            "principals": [{"identifiers": ["arn-one", "arn-two"], "type": "AWS"}],
            "resources": ["arn:aws:s3:::test-bucket/*"],
        },
        {
            "actions": ["s3:ListBucket"],
            "principals": [{"identifiers": ["arn-one", "arn-two"], "type": "AWS"}],
            "resources": ["arn:aws:s3:::test-bucket"],
        },
        {
            "actions": ["s3:*"],
            "conditions": [
                {
                    "test": "NumericLessThan",
                    "variable": "s3:TlsVersion",
                    "values": ["1.2"],
                }
            ],
            "effect": "Deny",
            "principals": [{"identifiers": ["*"], "type": "AWS"}],
            "resources": ["arn:aws:s3:::test-bucket", "arn:aws:s3:::test-bucket/*"],
        },
    ]
    return Output.all(policy.statements, expected).apply(
        assert_pulumi_output_equals_expected
    )


@pulumi.runtime.test
def test_create_read_write_role_policy():
    policy = create_read_write_role_policy({"bucket_arn": "arn:aws:s3:::test-bucket"})
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
            "resources": ["arn:aws:s3:::test-bucket/*"],
        },
        {
            "actions": ["s3:ListBucket"],
            "resources": ["arn:aws:s3:::test-bucket"],
        },
    ]
    return Output.all(policy.statements, expected).apply(
        assert_pulumi_output_equals_expected
    )
