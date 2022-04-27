from ast import literal_eval

from data_engineering_pulumi_components.utils import Tagger
from data_engineering_pulumi_components.aws import Bucket
from data_engineering_pulumi_components.aws.lambdas.move_object_function import (
    MoveObjectFunction,
)
from data_engineering_pulumi_components.aws.lambdas.copy_object_function import (
    CopyObjectFunction,
)

import pulumi
import pytest

from data_engineering_exports.push import (
    PushExportDatasets,
    PushExportDataset,
    WriteToExportBucketRolePolicy,
    DatasetsNotLoadedError,
    UsersNotLoadedError,
)


@pytest.fixture(scope="module")
def export_bucket_name():
    return "test-export-bucket"


@pytest.fixture(scope="module")
def test_tagger():
    return Tagger(environment_name="unit-tests")


@pytest.fixture(scope="module")
def export_bucket(export_bucket_name, test_tagger):
    return Bucket(name=export_bucket_name, tagger=test_tagger)


class TestPushExportDatasets:
    @pytest.fixture(autouse=True, scope="class")
    def make_test_datasets(self, yaml_file_list, export_bucket, test_tagger):
        self.__class__.test_datasets = PushExportDatasets(
            yaml_file_list, export_bucket, test_tagger
        )

    def test_init(self, yaml_file_list, export_bucket, test_tagger):
        """Check initial attributes are set corectly."""
        assert self.test_datasets.config_paths == yaml_file_list
        assert self.test_datasets.export_bucket == export_bucket
        assert self.test_datasets.tagger == test_tagger
        assert self.test_datasets.datasets is None
        assert self.test_datasets.lambdas is None

    def test_errors(self):
        """Check the build methods fail if run before data is loaded."""
        with pytest.raises(DatasetsNotLoadedError) as e:
            self.test_datasets.build_lambda_functions()
            assert e == "Run load_datasets_and_users before building Lambda functions"

        with pytest.raises(UsersNotLoadedError) as e:
            self.test_datasets.build_role_policies()
            assert e == "Run load_datasets_and_users before building role policies"

    def test_load_datasets_and_users(self):
        """Check dataset and user info correctly read from config files."""
        self.test_datasets.load_datasets_and_users()

        # Check the right datasets are here - but test their details separately
        assert len(self.test_datasets.datasets) == 2
        assert isinstance(self.test_datasets.datasets[0], PushExportDataset)
        assert isinstance(self.test_datasets.datasets[1], PushExportDataset)

    def test_build_lambda_functions(self):
        """Check Pulumi will create the right Lambda functions for the datasets."""
        self.test_datasets.build_lambda_functions()

        # Check Lambdas now part of datasets - check their details separately
        assert len(self.test_datasets.lambdas) == 2
        assert isinstance(self.test_datasets.lambdas[0], MoveObjectFunction)
        assert isinstance(self.test_datasets.lambdas[1], CopyObjectFunction)

    def test_build_role_policies(self):
        """Check Pulumi will create the right role policies for the users."""
        # Check role policies initially None
        assert self.test_datasets.role_policies is None

        # Build the role policies
        self.test_datasets.build_role_policies()

        # Check the role policies are now in the list - check their details separately
        assert len(self.test_datasets.role_policies) == 2
        assert all(
            isinstance(policy, WriteToExportBucketRolePolicy)
            for policy in self.test_datasets.role_policies
        )


class TestPushExportDataset:
    @pytest.fixture(autouse=True, scope="class")
    @pulumi.runtime.test
    def make_test_datasets(self, test_config_1, export_bucket, test_tagger):
        self.__class__.dataset_1 = PushExportDataset(
            test_config_1, export_bucket, test_tagger
        )
        self.__class__.dataset_2 = PushExportDataset.from_filepath(
            "tests/data/test_2.yaml", export_bucket, test_tagger
        )

    @pulumi.runtime.test
    def test_init(self):
        """Check the initial values of first dataset, which is loaded from a dict."""

        def validate_properties(args):
            (
                dataset_1_name,
                dataset_1_export_bucket_name,
                dataset_1_users,
                dataset_1_keep_files,
                dataset_1_lambda,
            ) = args

            assert dataset_1_name == "test_dataset"
            assert dataset_1_export_bucket_name == "test-export-bucket"
            assert dataset_1_users == ["alpha_user_test_person"]
            assert not dataset_1_keep_files
            assert dataset_1_lambda is None

        return pulumi.Output.all(
            self.dataset_1.name,
            self.dataset_1.export_bucket.name,
            self.dataset_1.users,
            self.dataset_1.keep_files,
            self.dataset_1.lambda_function,
        ).apply(validate_properties)

    @pulumi.runtime.test
    def test_from_filepath(self):
        """Check the initial values of the second dataset, which is loaded using
        .from_filepath
        """

        def validate_properties(args):
            (
                dataset_2_name,
                dataset_2_export_bucket_name,
                dataset_2_users,
                dataset_2_keep_files,
                dataset_2_lambda,
            ) = args

            assert dataset_2_name == "test_dataset_2"
            assert dataset_2_export_bucket_name == "test-export-bucket"
            assert dataset_2_users == [
                "alpha_user_test_person",
                "alpha_user_test_person_2",
            ]
            assert dataset_2_keep_files
            assert dataset_2_lambda is None

        return pulumi.Output.all(
            self.dataset_2.name,
            self.dataset_2.export_bucket.name,
            self.dataset_2.users,
            self.dataset_2.keep_files,
            self.dataset_2.lambda_function,
        ).apply(validate_properties)

    def test_build_lambda_function(self):
        """Check both datasets build the correct type of Lambda function."""
        self.dataset_1.build_lambda_function()
        self.dataset_2.build_lambda_function()
        assert isinstance(self.dataset_1.lambda_function, MoveObjectFunction)
        assert isinstance(self.dataset_2.lambda_function, CopyObjectFunction)

    @pulumi.runtime.test
    def test_build_move_object_function(self):
        """Check the right details are passed to a MoveObjectFunction."""
        # Checking the role policy makes sure the source_bucket and prefix are correct
        def validate_properties(args):
            name, role_policy = args
            assert name == "export_test_dataset-move"
            assert literal_eval(role_policy) == {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Sid": "GetDeleteSourceBucket",
                        "Effect": "Allow",
                        "Resource": ["arn:aws:s3:::test-export-bucket/test_dataset/*"],
                        "Action": ["s3:GetObject*", "s3:DeleteObject*"],
                    },
                    {
                        "Sid": "PutDestinationBucket",
                        "Effect": "Allow",
                        "Resource": ["arn:aws:s3:::test-bucket/*"],
                        "Action": ["s3:PutObject*"],
                    },
                ],
            }

        return pulumi.Output.all(
            self.dataset_1.lambda_function._role.name,
            self.dataset_1.lambda_function._rolePolicy.policy,
        ).apply(validate_properties)

    @pulumi.runtime.test
    def test_build_copy_object_function(self):
        """Check the right details are passed to a CopyObjectFunction."""
        # Checking the role policy makes sure the source_bucket and prefix are correct
        def validate_properties(args):
            name, role_policy = args
            assert name == "export_test_dataset_2-copy"
            assert literal_eval(role_policy) == {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Sid": "GetSourceBucket",
                        "Effect": "Allow",
                        "Resource": [
                            "arn:aws:s3:::test-export-bucket/test_dataset_2/*"
                        ],
                        "Action": ["s3:GetObject*"],
                    },
                    {
                        "Sid": "PutDestinationBucket",
                        "Effect": "Allow",
                        "Resource": ["arn:aws:s3:::test-bucket-2/*"],
                        "Action": ["s3:PutObject*"],
                    },
                ],
            }

        return pulumi.Output.all(
            self.dataset_2.lambda_function._role.name,
            self.dataset_2.lambda_function._rolePolicy.policy,
        ).apply(validate_properties)


@pulumi.runtime.test
def test_write_to_export_bucket_role_policy(export_bucket):
    """Check name, user and policy statements of a WriteToExportBucketRolePolicy"""

    def validate_properties(args):
        (
            name,
            user,
            policy_statements,
        ) = args
        assert name == "hub_exports"
        assert user == "alpha_test_user"
        assert policy_statements == [
            {
                "actions": [
                    "s3:PutObject",
                    "s3:PutObjectAcl",
                    "s3:PutObjectTagging",
                ],
                "resources": [
                    "arn:aws:s3:::test-export-bucket/prefix_1/*",
                    "arn:aws:s3:::test-export-bucket/prefix_2/*",
                ],
            },
            {
                "actions": ["s3:ListBucket"],
                "resources": ["arn:aws:s3:::test-export-bucket"],
            },
        ]

    test_role_policy = WriteToExportBucketRolePolicy(
        "alpha_test_user", export_bucket, ["prefix_1", "prefix_2"]
    )
    return pulumi.Output.all(
        test_role_policy._role_policy.name,
        test_role_policy._role_policy.role,
        test_role_policy._policy_document.statements,
    ).apply(validate_properties)
