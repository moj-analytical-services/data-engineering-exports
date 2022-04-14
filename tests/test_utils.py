from data_engineering_exports.utils import list_yaml_files, load_yaml


def test_list_yaml_files(yaml_file_list):
    results = list_yaml_files("tests/data")
    assert [str(r) for r in results] == yaml_file_list


def test_load_yaml():
    content = load_yaml("tests/data/test_2.yaml")
    assert content == {
        "name": "test_dataset_2",
        "bucket": "test-bucket-2",
        "users": ["alpha_user_test_person", "alpha_user_test_person_2"],
    }
