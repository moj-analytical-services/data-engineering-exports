from data_engineering_pulumi_components.aws import Bucket
from data_engineering_pulumi_components.utils import Tagger
from pulumi import export

from data_engineering_exports.utils_for_tests import PulumiTestInfrastructure

test_region = "eu-west-1"


def pulumi_program():
    """Define the infrastructure you want to create in Pulumi."""
    tagger = Tagger(environment_name="test")
    test = Bucket(
        name="pde-1574-test",
        tagger=tagger,
    )
    export("test_bucket_name", test.name)


def test_infrastructure():
    """Make assertions about the infrastructure created in pulumi_program."""
    with PulumiTestInfrastructure(
        pulumi_program=pulumi_program, region=test_region
    ) as stack:
        test_bucket = stack.up_results.outputs["test_bucket_name"].value

    assert test_bucket == "pde-1574-test"
