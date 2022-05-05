from json import dumps
from typing import Callable

from pulumi import automation as auto
import yaml

from tests_end_to_end.utils_for_tests import get_pulumi_aws_version

# session = boto3.Session(region_name=test_region)
# s3_client = session.client("s3")
# backend = os.environ["TEST_PULUMI_BACKEND"]


class InfrastructureForTests:
    def __init__(
        self,
        pulumi_program: Callable,
        delete_on_exit: bool = True,
        region: str = "eu-west-1",
        stack_name: str = "localstack",
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
        delete_on_exit : bool
            A debug option, allowing resources to be retained rather than destroyed
            at the end of the test. These resources will need to be manually deleted
            from AWS, as the TestInfrastructure won't delete them.
        region : str
            AWS region to use - defaults to eu-west-2
        """
        # manual_config = {
        #    "aws:accessKey": "test",
        #    "aws:endpoints": {
        #        "s3": "http://localhost:4566",
        #        "iam": "http://localhost:4566",
        #    },
        #    "aws:region": "us-east-1",
        #    "aws:s3ForcePathStyle": True,
        #    "aws:secretKey": "test",
        #    "aws:skipCredentialsValidation": True,
        #    "aws:skipRequestingAccountId": True,
        # }

        with open(f"Pulumi.{stack_name}.yaml", "r") as localstack_config:
            config = yaml.safe_load(localstack_config)["config"]

        self.stack_name = stack_name
        self.region = region
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
        self.delete_status = delete_on_exit
        print("Installing plugins")
        pulumi_aws_version = get_pulumi_aws_version()
        self.stack.workspace.install_plugin("aws", pulumi_aws_version)
        print("Plugins installed")
        print("Setting up config")
        print("Refreshing stack")
        self.stack.refresh(on_output=print)
        print("Refresh complete")

    def _pulumi_up(self):
        print("Updating stack")
        # No parallel processing, to avoid conflicts on the resources
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
        print("Exiting")


#
#    if self.delete_status is True:
#
#        bucket_name_list = extract_bucket_name(self.up_results.stdout)
#
#        for bucket_name in bucket_name_list:
#            response = bucket_list_response(bucket_name)
#            if response is not None and response["KeyCount"] > 0:
#                pprint("Bucket was not empty. Empty bucket operation performed")
#                empty_bucket(bucket_name, session)
#            elif response is None:
#                pprint(
#                    "Bucket not in data engineering account. "
#                    + "Empty bucket operation performed"
#                )
#                empty_bucket(bucket_name, session)
#
#        try:
#            # Parallel deletions are turned off as was causing conflicts:
#            # 'A conflicting conditional operation is currently in
#            # progress against this resource.'
#
#            self.stack.destroy(parallel=1, on_output=pprint)
#            self.stack.workspace.remove_stack(stack_name=self.stack_name)
#            pprint("stack destroy complete")
#
#        except Exception:
#            pprint("stack destroy failed")
#
#    else:
#        pprint("stack not destroyed, remember to clean later!")
