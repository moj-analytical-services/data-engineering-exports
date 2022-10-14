from pathlib import Path
from typing import List, Dict, Union, Any

import yaml


from pulumi_aws import Provider, ProviderAssumeRoleArgs, get_region

current = get_region()

dataProvider = Provider(
    resource_name="data",
    assume_role=ProviderAssumeRoleArgs(
        role_arn="arn:aws:iam::593291632749:role/DataEngineeringGitHubAction"
    ),
    region=current.name,
)


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
    return sorted(list(Path(folder_name).glob("*.yaml")))


def load_yaml(filepath: Union[Path, str]) -> Dict[Any, Any]:
    """Open a yaml file and read it into a dictionary."""
    with open(filepath, mode="r") as f:
        return yaml.safe_load(f)
