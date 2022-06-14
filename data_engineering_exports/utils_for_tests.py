import json
import pkg_resources
from typing import Callable, List

from pulumi import automation as auto
from pulumi_aws.iam import Role
import yaml


class PackageNotFoundError(Exception):
    pass


def get_pulumi_version(aws: bool = False) -> str:
    """Check what version of either pulumi or pulumi-aws is installed.

    Parameters
    ----------
    aws : bool
        If True, get version of pulumi-aws. If False, get version of pulumi

    Returns
    -------
    str
        The version number of the specified package, with a v in front of it.
    """
    if aws:
        package_to_find = "pulumi-aws"
    else:
        package_to_find = "pulumi"

    packages = {p.project_name: p.version for p in pkg_resources.working_set}
    if package_to_find in packages:
        return "v" + packages[package_to_find]
    else:
        raise PackageNotFoundError(f"{package_to_find} is not installed")


class PulumiTestInfrastructure:
    def __init__(
        self,
        pulumi_program: Callable,
        region: str = "eu-west-1",
        stack_name: str = "localstack",
    ) -> None:
        """
        Test infrastructure for end-to-end pipeline testing.

        Parameters
        ----------
        pulumi_program : Callable
            The program to be tested. Provides Pulumi resources to be created
            temporarily for testing.
        region : str
            AWS region to use - defaults to eu-west-1
        stack_name : str
            Name for the test stack - should have a matching config file.
            Defaults to localstack.
        """
        # Get the Pulumi config for localstack
        with open(f"Pulumi.{stack_name}.yaml", "r") as localstack_config:
            config = yaml.safe_load(localstack_config)["config"]

        self.stack_name = stack_name
        self.region = region
        # Define the stack using settings from the localstack config
        self.stack = auto.create_or_select_stack(
            stack_name=self.stack_name,
            project_name=self.stack_name,
            program=pulumi_program,
            opts=auto.LocalWorkspaceOptions(
                project_settings=auto.ProjectSettings(
                    name=self.stack_name,
                    runtime=auto.ProjectRuntimeInfo(name="python"),
                ),
                env_vars={
                    "AWS_SECRET_ACCESS_KEY": "test_secret",
                    "AWS_ACCESS_KEY_ID": "test_key",
                    "DEFAULT_REGION": self.region,
                    "AWS_ACCOUNT_ID": "000000000000",
                },
                stack_settings={
                    "localstack": auto._stack_settings.StackSettings(config=config)
                },
            ),
        )
        print("Installing plugins")
        pulumi_aws_version = get_pulumi_version(aws=True)
        self.stack.workspace.install_plugin("aws", pulumi_aws_version)
        print("Plugins installed")
        print("Refreshing stack")
        self.stack.refresh(on_output=print)
        print("Refresh complete")

    def _pulumi_up(self):
        print("Updating stack")
        # No parallel processing, to avoid conflicts on the resources
        # TODO: check if parallel might work when using localstack
        try:
            up_results = self.stack.up(parallel=1, on_output=print)
            print(
                f"Update summary: "
                f"\n{json.dumps(up_results.summary.resource_changes, indent=4)}"
            )
            return up_results

        except Exception as e:
            print("There was an error updating the stack")
            print(e)

    def __enter__(self):
        self.up_results = self._pulumi_up()
        return self

    def __exit__(self, type, value, traceback):
        # Destroy the stack's resources
        self.stack.destroy()
        print("Tests complete - exiting Pulumi test infrastructure")


def mock_alpha_user(username: str, account: str = "000000000000") -> Role:
    """Create a Pulumi Role that resembles an Analytical Platform alpha user.

    Parameters
    ----------
    username : str
        Username for the role. Starts with "alpha_user" on the real Analytical Platform.
    account : str (default 000000000000)
        String of 12 digits representing the AWS account number.

    Returns
    -------
    Role
        A Pulumi Role that creates an AWS IAM role.
    """
    return Role(
        resource_name=username,
        name=username,
        assume_role_policy=json.dumps(
            {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {"AWS": f"arn:aws:sts::{account}:user/localstack"},
                        "Action": "sts:AssumeRole",
                    }
                ],
            }
        ),
    )


def check_bucket_contents(
    bucket_name: str, expected_keys: List[str], s3_client
) -> None:
    """Assert that contents of bucket_name match the list of filenames in expected_keys.

    When importing using this in pytest, by default it won't display the full
    AssertionError text on a fail. To solve this, add this to the __init__.py
    in the test directory:

    pytest.register_assert_rewrite('utils_for_tests')
    """
    bucket_contents = s3_client.list_objects_v2(Bucket=bucket_name)
    if expected_keys:
        assert [
            item["Key"] for item in bucket_contents.get("Contents")
        ] == expected_keys
    else:
        assert not bucket_contents.get("Contents")
