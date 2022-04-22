from typing import Tuple

import pulumi
import pytest


class Mocks(pulumi.runtime.Mocks):
    def new_resource(self, args: pulumi.runtime.MockResourceArgs) -> Tuple[str, dict]:
        if args.typ == "aws:s3/bucket:Bucket":
            state = {"arn": f"arn:aws:s3:::{args.inputs['bucket']}"}
            return [args.name, dict(args.inputs, **state)]
        else:
            return [args.name, args.inputs]

    def call(self, args: pulumi.runtime.MockCallArgs):
        if args.token == "aws:iam/getPolicyDocument:getPolicyDocument":
            return args.args
        else:
            return {}


@pytest.fixture(scope="session")
def yaml_file_list():
    return [
        "tests/data/test.yaml",
        "tests/data/test_2.yaml",
    ]


@pytest.fixture(scope="session")
def test_config_1():
    return {
        "name": "test_dataset",
        "target_bucket": "test-bucket",
        "users": ["alpha_user_test_person"],
    }


@pytest.fixture(scope="session")
def test_config_2():
    return {
        "name": "test_dataset_2",
        "target_bucket": "test-bucket_2",
        "users": ["alpha_user_test_person", "alpha_user_test_person_2"],
    }


pulumi.runtime.set_mocks(Mocks())
