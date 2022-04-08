from pathlib import Path
from typing import List, Tuple, Dict, Union, Any

import yaml

from data_engineering_pulumi_components.aws import Bucket
from data_engineering_pulumi_components.utils import Tagger

from data_engineering_exports.policies import PushExportDataset


def list_yaml_files(folder_name: str) -> List[Path]:
    """Get a list of yaml files in a specific folder.

    Parameters
    ----------
    folder_name : str
        Name of the folder to get yaml from.

    Returns
    -------
    list
        List of Paths to all the yaml files in the folder.
    """
    return list(Path(folder_name).glob("*.yaml"))


def load_yaml(filepath: Union[Path, str]) -> Dict[Any, Any]:
    """Open a yaml file and read it into a dictionary."""
    with open(filepath, mode="r") as f:
        return yaml.safe_load(f)


def get_datasets_and_users(
    config_filepaths: List[Path],
    export_bucket: Bucket,
    tagger: Tagger,
) -> Tuple[List[PushExportDataset], Dict[str, str]]:
    """Extract information from a collection of push dataset yaml files.

    Parameters
    ----------
    config_filepaths : list
        List of Path objects pointing to yaml files (as created by list_yaml_files).
    export_bucket : Bucket
        The bucket the data will be exported from.
    tagger : Tagger
        A Tagger object from data-engineering-pulumi-components.utils

    Returns
    -------
    tuple
        First item is a list of PushExportDatasets.

        Second item is a dictionary where keys are usernames and values are lists
        of project names for that user.
    """
    datasets = []  # will contain target bucket for each dataset
    users = {}  # will contain list of permitted export bucket prefixes for each user

    for file in config_filepaths:
        dataset_config = load_yaml(file)
        dataset = PushExportDataset(dataset_config, export_bucket, tagger)
        datasets.append(dataset)

        for user in dataset_config["users"]:
            users[user] = users.get(user, [])
            users.setdefault(user, []).append(dataset.name)

    return datasets, users
