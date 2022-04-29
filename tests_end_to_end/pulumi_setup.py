from json import dumps
import os
from pprint import pprint
import re
from typing import Callable

import boto3
import pkg_resources
from pulumi import automation as auto

test_region = "eu-west-1"
session = boto3.Session(region_name=test_region)
s3_client = session.client("s3")
# backend = os.environ["TEST_PULUMI_BACKEND"]


# FROM UTILS
def extract_bucket_name(stack_list):
    bucketname_list = []
    extracted_names = re.findall(r"aws:s3:Bucket\s+[a-zA-Z0-9_-]+", stack_list)
    for value in extracted_names:
        bucket_name = re.sub(r"aws:s3:Bucket\s", "", value)
        bucket_name = re.sub(r"-bucket", "", bucket_name)
        if bucket_name not in bucketname_list:
            bucketname_list.append(bucket_name)
    return bucketname_list


def bucket_list_response(bucket_name):
    try:
        response = s3_client.list_objects_v2(
            Bucket=bucket_name,
            MaxKeys=2,
        )
        return response
    except Exception as e:
        print("Permission issue")
        print(e)
        return None


def empty_bucket(bucket, Session):
    """This function will empty a bucket if it can find it and return True,
    even if the bucket is already empty.
    If it can't find the bucket the function will return false.
    """
    try:
        s3_resource = Session.resource("s3")
        bucket = s3_resource.Bucket(bucket)
        bucket.object_versions.delete()
        return True
    except Exception as e:
        print("Permission issue")
        print(e)
        return False


# FROM PULUMI CONTEXT
def get_pulumi_aws_version():
    packages = {p.project_name: p.version for p in pkg_resources.working_set}
    if "pulumi-aws" in packages:
        return "v" + packages["pulumi-aws"]
    else:
        raise Exception("pulumi-aws is not installed")


class InfrastructureForTests:
    def __init__(
        self,
        test_id: str,
        pulumi_program: Callable,
        delete_on_exit: bool = True,
        region: str = test_region,
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
        self.stack_name = "localstack"
        self.region = region
        self.stack = auto.create_or_select_stack(
            stack_name=self.stack_name,
            project_name=self.stack_name,
            program=pulumi_program,
            opts=auto.LocalWorkspaceOptions(
                project_settings=auto.ProjectSettings(
                    name=self.stack_name,
                    runtime=auto.ProjectRuntimeInfo(name="python"),
                    # backend=auto.ProjectBackend(url=backend),
                )
            ),
        )
        self.delete_status = delete_on_exit
        pprint("installing plugins...")
        pulumi_aws_version = get_pulumi_aws_version()
        self.stack.workspace.install_plugin("aws", pulumi_aws_version)
        pprint("plugins installed")
        pprint("setting up config")
        self.stack.set_config("aws:region", auto.ConfigValue(value=region))
        pprint("config set")
        pprint("refreshing stack...")
        self.stack.refresh(on_output=pprint)
        pprint("refresh complete")

    def _pulumi_up(self):
        pprint("updating stack...")
        # Parrallelisation on the ups has been turned off
        # Otherwise get conflicts on the resources
        try:
            up_results = self.stack.up(
                parallel=1,
                on_output=pprint,
            )
            pprint(
                f"update summary: "
                f"\n{dumps(up_results.summary.resource_changes, indent=4)}"
            )
            return up_results
        # TODO: what exceptions am I catching here? Just a catch all.
        except Exception as e:
            pprint("There was an error updating the stack")
            pprint(e)

    def __enter__(self):
        self.up_results = self._pulumi_up()
        return self

    def __exit__(self, type, value, traceback):
        pprint("exit phase...")

        if self.delete_status is True:

            bucket_name_list = extract_bucket_name(self.up_results.stdout)

            for bucket_name in bucket_name_list:
                response = bucket_list_response(bucket_name)
                if response is not None and response["KeyCount"] > 0:
                    pprint("Bucket was not empty. Empty bucket operation performed")
                    empty_bucket(bucket_name, session)
                elif response is None:
                    pprint(
                        "Bucket not in data engineering account. "
                        + "Empty bucket operation performed"
                    )
                    empty_bucket(bucket_name, session)

            try:
                # Parallel deletions are turned off as was causing conflicts:
                # 'A conflicting conditional operation is currently in
                # progress against this resource.'

                self.stack.destroy(parallel=1, on_output=pprint)
                self.stack.workspace.remove_stack(stack_name=self.stack_name)
                pprint("stack destroy complete")

            except Exception:
                pprint("stack destroy failed")

        else:
            pprint("stack not destroyed, remember to clean later!")
