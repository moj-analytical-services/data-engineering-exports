from tests_end_to_end.pulumi_test_utils import get_pulumi_version


if __name__ == "__main__":
    pulumi_version = get_pulumi_version()
    print(pulumi_version)
