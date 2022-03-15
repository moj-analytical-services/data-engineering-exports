import json
from typing import Dict

def create_get_policy(args) -> Dict[str, str]:
    bucket_arn = args.pop("bucket_arn")
    pull_arns = args.pop("pull_arns")

    statements = [
        {
            "Effect": "Allow",
            "Principal": {"AWS": pull_arns},
            "Action": [
                "s3:GetObject",
                "s3:GetObjectAcl",
                "s3:GetObjectVersion",
            ],
            "Resource": bucket_arn + "/*",
        },
        {
            "Effect": "Allow",
            "Principal": {"AWS": pull_arns},
            "Action": ["s3:ListBucket"],
            "Resource": bucket_arn,
        },
    ]
    return json.dumps({"Version": "2012-10-17", "Statement": statements})
