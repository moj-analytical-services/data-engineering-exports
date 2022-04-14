from typing import Tuple

import pulumi
import pytest


class Mocks(pulumi.runtime.Mocks):
    def new_resource(self, args: pulumi.runtime.MockResourceArgs) -> Tuple[str, dict]:
        # Not called in the policy tests
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


@pytest.fixture(scope="module")
def yaml_file_list():
    return [
        "tests/data/test.yaml",
        "tests/data/test_2.yaml",
    ]


pulumi.runtime.set_mocks(Mocks())
