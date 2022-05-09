from data_engineering_exports.utils import get_pulumi_version


if __name__ == "__main__":
    pulumi_version = get_pulumi_version()
    print(pulumi_version)
