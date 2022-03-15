import os

import boto3

client = boto3.client("s3")


def handler(event, context):
    record = event["Records"][0]

    source_bucket = record["s3"]["bucket"]["name"]
    source_key = record["s3"]["object"]["key"]

    target_bucket = os.environ["TARGET_BUCKET"]
    target_key = source_key

    client.copy_object(
        ACL="bucket-owner-full-control",
        Bucket=target_bucket,
        CopySource={"Bucket": source_bucket, "Key": source_key},
        Key=target_key,
        ServerSideEncryption="AES256",
    )

    client.delete_object(Bucket=source_bucket, Key=source_key)
