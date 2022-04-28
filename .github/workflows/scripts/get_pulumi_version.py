import pkg_resources


def get_pulumi_version():
    packages = {p.project_name: p.version for p in pkg_resources.working_set}
    if "pulumi" in packages:
        return packages["pulumi"]
    else:
        raise Exception("pulumi is not installed")


if __name__ == "__main__":
    pulumi_version = get_pulumi_version()
    print(pulumi_version)
