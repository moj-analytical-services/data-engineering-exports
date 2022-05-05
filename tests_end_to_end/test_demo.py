import os

from data_engineering_pulumi_components.aws import Bucket
from data_engineering_pulumi_components.utils import Tagger
from pulumi import export

from tests_end_to_end.pulumi_test_setup import InfrastructureForTests
from tests_end_to_end.utils_for_tests import generate_test_run_id

test_region = "eu-west-1"
test_run = os.environ["GIT_BRANCH"][:8].replace("/", "-").lower()
test_run_id = generate_test_run_id(test_run)


def pulumi_program():
    tagger = Tagger(environment_name="test")
    test = Bucket(
        name="pde-1574-test",
        tagger=tagger,
    )
    export("test_bucket_name", test.name)


def test_infrastructure():
    with InfrastructureForTests(
        pulumi_program=pulumi_program, region=test_region
    ) as stack:
        test_bucket = stack.up_results.outputs["test_bucket_name"].value

    assert test_bucket == "pde-1574-test"
