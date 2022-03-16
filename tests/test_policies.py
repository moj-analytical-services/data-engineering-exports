import json

import pulumi.runtime

from data_engineering_exports.policies import create_pull_bucket_policy, create_read_write_role_policy


@pulumi.runtime.test
def test_create_pull_bucket_policy():
    result = create_pull_bucket_policy({"bucket_arn": "test-bucket", "pull_arns": ["arn-one", "arn-two"]})
    expected = json.dumps({"Version": "2012-10-17", "Statement": [
        {
            "Effect": "Allow",
            "Principal": {"AWS": ["arn-one", "arn-two"]},
            "Action": [
                "s3:GetObject",
                "s3:GetObjectAcl",
                "s3:GetObjectVersion",
            ],
            "Resource": "test-bucket/*",
        },
        {
            "Effect": "Allow",
            "Principal": {"AWS": ["arn-one", "arn-two"]},
            "Action": ["s3:ListBucket"],
            "Resource": "test-bucket",
        },
    ]
    })
    assert result == expected


def test_create_read_write_role_policy():
    assert not create_read_write_role_policy()
