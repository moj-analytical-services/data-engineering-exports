# Create a Pulumi program
# Create a TestInfrastructure which uses the program
# Create a test that runs with TestInfrastructure
# 2 tests, one for pull and one for push
# Is it possible to fake the cross-account part?
import os
import secrets

from data_engineering_pulumi_components.aws import RawHistoryBucket
from data_engineering_pulumi_components.utils import Tagger
from pulumi_aws import Provider
from pulumi import ResourceOptions, export

from tests_end_to_end.infrastructure_for_tests import TestInfrastructure, test_region

test_run = os.environ["GIT_BRANCH"][:8].replace("/", "-").lower()


def generate_test_run_id(test_run):
    return test_run + "-" + secrets.token_hex(3)


test_run_id = generate_test_run_id()


def pulumi_program():
    tagger = Tagger(environment_name="test")

    provider = Provider(
        resource_name="base_london_provider",
        region=test_region,
    )
    test = RawHistoryBucket(
        name="test-bucket-name",
        tagger=tagger,
        opts=ResourceOptions(provider=provider),
    )
    export("test_bucket_name", test.name)


def test_infrastructure():
    with TestInfrastructure(
        test_id=test_run_id, pulumi_program=pulumi_program, region=test_region
    ) as stack:
        test_bucket = stack.up_results.outputs["test_bucket_name"].value

    assert test_bucket == "test-bucket-name"
