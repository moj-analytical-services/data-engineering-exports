from json import dumps
import pkg_resources
from typing import Callable, Optional

from pulumi import automation as auto
import yaml


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


class InfrastructureForTests:
    def __init__(
        self,
        pulumi_program: Callable,
        region: Optional[str] = "eu-west-1",
        stack_name: Optional[str] = "localstack",
    ) -> None:
        """
        Test infrastructure for end-to-end pipeline testing.

        Parameters
        ----------
        test_id : str
            An ID to be used as the 'name' variable for most purposes. Usually a
            short, hexadecimal code.
        pulumi_program : Callable
            The program to be tested. Provides Pulumi resources to be created
            temporarily for testing.
        region : Optional[str]
            AWS region to use - defaults to eu-west-1
        stack_name : Optional[str]
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
                    "DEFAULT_REGION": "eu-west-1",
                    "AWS_ACCOUNT_ID": "000000000000",
                },
                stack_settings={
                    "localstack": auto._stack_settings.StackSettings(config=config)
                },
            ),
        )
        print("Installing plugins")
        pulumi_aws_version = get_pulumi_version(aws=True, include_v=True)
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
                f"\n{dumps(up_results.summary.resource_changes, indent=4)}"
            )
            return up_results

        except Exception as e:
            print("There was an error updating the stack")
            print(e)

    def __enter__(self):
        self.up_results = self._pulumi_up()
        return self

    def __exit__(self, type, value, traceback):
        print("Tests complete - exiting Pulumi test infrastructure ")
