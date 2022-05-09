import pkg_resources


class PackageNotFoundError(Exception):
    pass


def get_pulumi_version(aws: bool = False, include_v: bool = False) -> str:
    """Check what version of the pulumi-aws package is installed.

    Parameters
    ----------
    aws : bool
        If True, look for the pulumi-aws package instead of pulumi.
    include_v : bool
        If True, return v1.2.3 rather than 1.2.3

    Returns
    -------
    str
        The version number of the requested pulumi package
    """
    if aws:
        package_to_find = "pulumi-aws"
    else:
        package_to_find = "pulumi"

    packages = {p.project_name: p.version for p in pkg_resources.working_set}
    if package_to_find in packages:
        version = packages[package_to_find]
        if include_v:
            return "v" + version
        else:
            return version
    else:
        raise PackageNotFoundError(f"{package_to_find} is not installed")
