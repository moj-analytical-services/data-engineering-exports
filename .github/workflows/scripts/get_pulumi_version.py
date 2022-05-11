import os
import pkg_resources

from utils_for_tests import get_pulumi_aws_version


class PackageNotFoundError(Exception):
    pass


def get_pulumi_version() -> str:
    """Check what version of the pulumi package is installed.

    Returns
    -------
    str
        The version number of the pulumi package.
    """
    package_to_find = "pulumi"
    packages = {p.project_name: p.version for p in pkg_resources.working_set}
    if package_to_find in packages:
        return "v" + packages[package_to_find]
    else:
        raise PackageNotFoundError(f"{package_to_find} is not installed")


if __name__ == "__main__":
    pulumi_version = get_pulumi_aws_version()
    print(pulumi_version)
