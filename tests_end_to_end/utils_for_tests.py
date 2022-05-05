import pkg_resources
import re
import secrets
from typing import List


def generate_test_run_id(test_run: str) -> str:
    """Add a random suffix to the end of a test run ID."""
    return test_run + "-" + secrets.token_hex(3)


def get_pulumi_aws_version():
    packages = {p.project_name: p.version for p in pkg_resources.working_set}
    if "pulumi-aws" in packages:
        return "v" + packages["pulumi-aws"]
    else:
        raise Exception("pulumi-aws is not installed")


def extract_bucket_name(stack_list: str) -> List[str]:
    """Extract a list of bucket names from a Pulumi stack output."""
    print(stack_list)
    bucket_names = set()
    extracted_names = re.findall(r"aws:s3:Bucket\s+([\w-]+)", stack_list)
    for bucket_name in extracted_names:
        bucket_name = re.sub(r"-bucket", "", bucket_name)
        bucket_names.add(bucket_name)
    return list(bucket_names)


def is_bucket_empty(bucket_name: str, s3_client):
    """Check if a bucket contains any files."""
    try:
        return s3_client.list_objects_v2(Bucket=bucket_name, MaxKeys=2)
    except Exception as e:
        print(f"Error when listing objects from {bucket_name}")
        print(e)
        return None


def empty_bucket(bucket, Session):
    """This function will empty a bucket if it can find it and return True,
    even if the bucket is already empty.
    If it can't find the bucket the function will return false.
    """
    try:
        s3_resource = Session.resource("s3")
        bucket = s3_resource.Bucket(bucket)
        bucket.object_versions.delete()
        return True
    except Exception as e:
        print("Permission issue")
        print(e)
        return False
