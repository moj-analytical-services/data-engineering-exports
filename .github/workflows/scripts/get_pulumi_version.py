from pathlib import Path
import pkg_resources
import sys

sys.path.insert(0, str(Path(sys.path[0]).parents[2]))

from data_engineering_exports.utils_for_tests import get_pulumi_version


if __name__ == "__main__":
    pulumi_version = get_pulumi_version()
    print(pulumi_version)
