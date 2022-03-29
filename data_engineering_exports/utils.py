from pathlib import Path
from typing import List, Tuple, Dict

import yaml


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


def load_push_config_data(
    config_filepaths: List[Path],
) -> Tuple[Dict[str, str], Dict[str, str]]:
    """Extract information from a collection of push dataset yaml files.

    Parameters
    ----------
    config_filepaths : list
        List of Path objects pointing to yaml files (as created by list_yaml_files).

    Returns
    -------
    tuple
        First item is a dictionary where keys are dataset names and values are their
        target buckets.

        Second item is a dictionary where keys are usernames and values are lists
        of project names for that user.
    """
    datasets_to_buckets = {}  # will contain target bucket for each dataset
    users = {}  # will contain list of permitted export bucket prefixes for each user

    for file in config_filepaths:
        with open(file, mode="r") as f:
            dataset = yaml.safe_load(f)

        dataset_name = dataset["name"]
        target_bucket = dataset["bucket"]
        datasets_to_buckets[dataset_name] = target_bucket

        for user in dataset["users"]:
            users[user] = users.get(user, [])
            users.setdefault(user, []).append(dataset_name)

    return datasets_to_buckets, users
