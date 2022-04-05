import pytest

from data_engineering_exports.utils import list_yaml_files, load_push_config_data


@pytest.fixture(scope="module")
def yaml_file_list():
    return [
        "tests/data/test.yaml",
        "tests/data/test_2.yaml",
    ]


def test_list_yaml_files(yaml_file_list):
    results = list_yaml_files("tests/data")
    assert [str(r) for r in results] == yaml_file_list


def test_load_push_config_data(yaml_file_list):
    results = load_push_config_data(yaml_file_list)
    assert results == (
        {"test_dataset": "test-bucket", "test_dataset_2": "test-bucket-2"},
        {
            "alpha_user_test_person": ["test_dataset", "test_dataset_2"],
            "alpha_user_test_person_2": ["test_dataset_2"],
        },
    )
