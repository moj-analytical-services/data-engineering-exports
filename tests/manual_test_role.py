# Placeholder test
# Check sandbox role has access to incentives dev
import boto3
from dataengineeringutils3.s3 import read_json_from_s3

session = boto3.Session()
s3 = session.client("s3")

bucket = "mojap-pull-permission-test"
filename = "test_file.json"

contents = s3.list_objects_v2(Bucket=bucket)
file_list = [c["Key"] for c in contents["Contents"]]
print(file_list, end="\n\n")

table = read_json_from_s3(f"s3://{bucket}/{filename}")
print(table)
