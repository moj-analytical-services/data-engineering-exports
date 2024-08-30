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
            "Sid": "",
            "Effect": "Allow",
            "Action": ["s3:GetObjectVersion", "s3:GetObjectAcl", "s3:GetObject"],
            "Principal": {"AWS": ["arn-one", "arn-two"]},
            "Resource": "arn:aws:s3:::test-bucket/*",
        },
        {
            "Sid": "",
            "Effect": "Allow",
            "Action": "s3:ListBucket",
            "Principal": {"AWS": ["arn-one", "arn-two"]},
            "Resource": "arn:aws:s3:::test-bucket",
        },
        {
            "Sid": "",
            "Effect": "Deny",
            "Action": "s3:*",
            "Principal": "*",
            "Resource": ["arn:aws:s3:::test-bucket", "arn:aws:s3:::test-bucket/*"],
            "Condition": {"NumericLessThan": {"s3:TlsVersion": "1.2"}},
        },
    ]
    return Output.all(policy["Statement"], expected).apply(
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
