# Contributing to data engineering hub exports

## Check user changes and update the code

Users should make requests in the form of pull requests, [as described in the readme](README.md).

1. Check the team who run the destination system expect and are happy with the proposed exports.

2. Make sure your users have a data protection impact assessment (DPIA) or similar document confirming the export is okay. Your users are responsible for writing this and getting it approved.

3. If creating a push bucket, get the owner of that bucket to grant put permission to the role ARN for the relevant project. You can find the ARN in the stack's Pulumi outputs.

Either:
4. write a new config yaml file, create the relevant pull request, then ask your users to approve

or

5. check that a user-submitted config file is correct, approve the corresponding pull request

6. Merge to main **and pull to your local machine** (since pulumi will operate on the locally-held version of your code).

## Pre-requisites

1. Clone the repo locally and `cd` to this folder.

2. Set up a new virtual environment:
`python3 -m venv <env_name>`
We'll call our environment `env` from here onwards.

3. Activate it:

`source ./env/bin/activate`

Check that it is activated:

`which python3`

should return `<path_to_this_repo>/env/bin/python3` instead of your OS's global python executable (which will be something like `/opt/bin/python3`).

4. Install the packages:

`pip3 install -r requirements.txt && pip3 install -r requirements-dev.txt`

Use the `--force-reinstall` flag to replace an existing version if necessary.  This may take several minutes depending upon your internet connection.

5. Then install the pre-commit hooks with `pre-commit install`.

## Access the Pulumi stack

1. Activate the AWS SSO role you use to access `analytical-platform-data-production`:
    `aws-vault exec <name_of_your_role>`
   If you're not sure which profile to use, consult `aws-vault list` or for even more detail, your `~/.aws/config` file.
3. Log in to the Pulumi backend with `pulumi login --cloud-url s3://data-engineering-pulumi.analytics.justice.gov.uk`.
4. Run `pulumi stack select` and pick `data-engineering-exports`.
5. Run `pulumi stack` to check you can see what's currently deployed.
6. Run `pulumi preview` to check the resources look correct. Use the `--diff` flag to see details.

You may see changes to update the local archive path, which can be ignored. If you are using a different version of `pulumi-aws` to the current deplyment you may see changes relating to the provider, you can avoid these by installing the specific version curently in use, for example, `pip install --force-reinstall pulumi-aws==5.40.0`.


6. Deploy the changes with `pulumi up` (there's a ticket to [automate the deployment](https://dsdmoj.atlassian.net/browse/PDE-1441)).

You may also need to set `export PULUMI_CONFIG_PASSPHRASE=""` if you've changed this for other projects.

7. Ask the user to test the export. This should include making sure the destination system gets the test file, as we can't see the destination buckets ourselves.

## Running tests

There are normal unit tests that mock Pulumi resources. There is also an end-to-end test that uses Localstack, which creates a mock AWS environment. The test infrastructure should behave like real resources, but none of it needs access to a real AWS account.

The tests should run automatically when you open a pull request.

To run just the unit tests, run `pytest tests -vv -k "not end_to_end" -W ignore::DeprecationWarning`

To include the end-to-end test:

1. install and open Docker
2. install packages from the dev requirements file: `pip install -r requirements-dev.txt`
3. navigate to your project directory and activate your virtual environment
4. in your terminal, run `docker-compose up`
5. open another terminal window and again navigate to your project directory
6. log into your local Pulumi backend with `pulumi login --local` (so it doesn't try to connect to our S3-stored Pulumi backends)
7. run tests with `pytest tests -vv -W ignore::DeprecationWarning`

If you get warnings that `Other threads are currently calling into gRPC, skipping fork() handlers`, you can suppress them by setting `export GRPC_ENABLE_FORK_SUPPORT=0`.

If you have problems with the tests, try restarting Localstack between test runs. In its terminal window, press `ctrl-c` to stop it, then run `localstack start` again. You shouldn't _have_ to do this, as resources will be destroyed after each test run, but it can be useful as it will completely destroy and recreate your fake AWS environment.
