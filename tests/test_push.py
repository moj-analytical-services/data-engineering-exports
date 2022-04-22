from data_engineering_pulumi_components.utils import Tagger
import pytest

from data_engineering_exports.push import (
    PushExportDatasets,
    PushExportDataset,
    # WriteToExportBucketRolePolicy,
)


@pytest.fixture(scope="module")
def export_bucket_name():
    return "test-export-bucket"


@pytest.fixture(scope="module")
def test_tagger():
    return Tagger(environment_name="unit-tests")


def assert_matching_datasets(dataset_1, dataset_2):
    assert dataset_1.name == dataset_2.name
    assert dataset_1.export_bucket == dataset_2.export_bucket
    assert dataset_1.users == dataset_2.users
    assert dataset_1.keep_files == dataset_2.keep_files
    assert dataset_1.tagger == dataset_2.tagger
    assert dataset_1.lambda_function == dataset_2.lambda_function


class TestPushExportDatasets:
    @pytest.fixture(autouse=True, scope="class")
    def make_test_datasets(self, yaml_file_list, export_bucket_name, test_tagger):
        self.__class__.test_datasets = PushExportDatasets(
            yaml_file_list, export_bucket_name, test_tagger
        )

    def test_init(self, yaml_file_list, export_bucket_name, test_tagger):
        """Check initial attributes are set corectly."""
        assert self.test_datasets.config_paths == yaml_file_list
        assert self.test_datasets.export_bucket == export_bucket_name
        assert self.test_datasets.tagger == test_tagger

    def test_load_datasets_and_users(
        self, test_config_1, test_config_2, export_bucket_name, test_tagger
    ):
        """Check dataset and user info correctly read from config files."""
        self.test_datasets.load_datasets_and_users()

        # Probably redo this once I've written other tests
        assert_matching_datasets(
            self.test_datasets.datasets[0],
            PushExportDataset(test_config_1, export_bucket_name, test_tagger),
        )
        assert_matching_datasets(
            self.test_datasets.datasets[1],
            PushExportDataset(test_config_2, export_bucket_name, test_tagger),
        )
        assert self.test_datasets.users == {
            "alpha_user_test_person": ["test_dataset", "test_dataset_2"],
            "alpha_user_test_person_2": ["test_dataset_2"],
        }

    def test_build_lambda_functions(self):
        """"""

    def test_build_role_profiles(self):
        """"""


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


class TestWriteToExportBucketRolePolicy:
    def test_init(self):
        """"""

    def test_arn(self):
        """"""
