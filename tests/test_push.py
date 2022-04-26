from data_engineering_pulumi_components.utils import Tagger
from data_engineering_pulumi_components.aws import Bucket
import pulumi
import pytest

from data_engineering_exports.push import (
    PushExportDatasets,
    PushExportDataset,
    WriteToExportBucketRolePolicy,
    DatasetsNotLoadedError,
    UsersNotLoadedError,
)
from tests.utils_for_tests import assert_pulumi_output_equals_expected


@pytest.fixture(scope="module")
def export_bucket_name():
    return "test-export-bucket"


@pytest.fixture(scope="module")
def test_tagger():
    return Tagger(environment_name="unit-tests")


@pytest.fixture(scope="module")
def export_bucket(export_bucket_name, test_tagger):
    return Bucket(name=export_bucket_name, tagger=test_tagger)


def assert_matching_datasets(dataset_1, dataset_2):
    assert dataset_1.name == dataset_2.name
    assert dataset_1.export_bucket == dataset_2.export_bucket
    assert dataset_1.users == dataset_2.users
    assert dataset_1.keep_files == dataset_2.keep_files
    assert dataset_1.tagger == dataset_2.tagger
    assert dataset_1.lambda_function == dataset_2.lambda_function


class TestPushExportDatasets:
    @pytest.fixture(autouse=True, scope="class")
    def make_test_datasets(self, yaml_file_list, export_bucket, test_tagger):
        self.__class__.test_datasets = PushExportDatasets(
            yaml_file_list, export_bucket, test_tagger
        )

    def test_init(self, yaml_file_list, export_bucket, test_tagger):
        """Check initial attributes are set corectly."""
        assert self.test_datasets.config_paths == yaml_file_list
        assert self.test_datasets.export_bucket == export_bucket
        assert self.test_datasets.tagger == test_tagger

    def test_load_datasets_and_users(
        self, test_config_1, test_config_2, export_bucket, test_tagger
    ):
        """Check dataset and user info correctly read from config files."""
        # First make sure build methods fail if data not yet loaded
        with pytest.raises(DatasetsNotLoadedError) as e:
            self.test_datasets.build_lambda_functions()
            assert e == "Run load_datasets_and_users before building Lambda functions"

        with pytest.raises(UsersNotLoadedError) as e:
            self.test_datasets.build_role_policies()
            assert e == "Run load_datasets_and_users before building role policies"

        self.test_datasets.load_datasets_and_users()

        # Probably redo this once I've written other tests
        assert_matching_datasets(
            self.test_datasets.datasets[0],
            PushExportDataset(test_config_1, export_bucket, test_tagger),
        )
        assert_matching_datasets(
            self.test_datasets.datasets[1],
            PushExportDataset(test_config_2, export_bucket, test_tagger),
        )
        assert self.test_datasets.users == {
            "alpha_user_test_person": ["test_dataset", "test_dataset_2"],
            "alpha_user_test_person_2": ["test_dataset_2"],
        }

    def test_build_lambda_functions(self):
        """Check Pulumi will create the right Lambda functions for the datasets."""
        assert self.test_datasets.lambdas is None
        self.test_datasets.build_lambda_functions()
        assert self.test_datasets.lambdas == ["No"]

    def test_build_role_profiles(self):
        """Check Pulumi will create the right role policies for the users."""
        assert self.test_datasets.role_policies is None
        self.test_datasets.build_role_policies()
        assert isinstance(self.test_datasets.role_policies, list)
        assert len(self.test_datasets.role_policies) == 2
        # assert self.test_datasets.role_policies[0]._role_policy.policy == "something"
        # assert self.test_datasets.role_policies[1]._role_policy.policy == "something"
        assert 0


class TestPushExportDataset:
    def test_init(self):
        """"""

    def test_from_filepath(self):
        """"""

    def test_build_lambda_function(self):
        """"""

    def test_build_move_object_function(self):
        """"""

    def test_copy_object_function(self):
        """"""


@pulumi.runtime.test
def test_arn(export_bucket):
    """"""
    test_policy = WriteToExportBucketRolePolicy(
        "alpha_test_user", export_bucket, ["prefix_1", "prefix_2"]
    )
    expected_name = "hub-exports"
    return pulumi.Output.all(test_policy._role_policy.name, expected_name).apply(
        assert_pulumi_output_equals_expected
    )
    # HOW TO CHECK THE POLICY ITSELF? I'VE MANAGED BEFORE


class TestWriteToExportBucketRolePolicy:
    @pytest.fixture(autouse=True, scope="class")
    @pulumi.runtime.test
    def make_test_role_policy(self, export_bucket):
        self.__class__.test_role_policy = WriteToExportBucketRolePolicy(
            "alpha_test_user", export_bucket, ["prefix_1", "prefix_2"]
        )

    @pulumi.runtime.test
    def test_name(self):
        """"""
        expected_name = "hub-exports"
        return pulumi.Output.all(
            self.test_role_policy._role_policy.name, expected_name
        ).apply(assert_pulumi_output_equals_expected)
