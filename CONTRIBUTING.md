# Contributing to data engineering hub exports

To get started, set up a new virtual environment and `pip install -r requirements.txt`.

Then install the pre-commit hooks with `pre-commit install`.

## Access the Pulumi stack

1. Activate the `restricted-admin-data` AWS role
2. Log in to the Pulumi backend with `pulumi login s3://data-engineering-pulumi.analytics.justice.gov.uk`
3. Run `pulumi stack select` and pick `data-engineering-exports`
4. Run `pulumi stack` to check you can see what's currently deployed

## Check and deploy user changes

Users should make requests in the form of pull requests, [as described in the readme](README.md).

1. Check the Performance Hub expect and are happy with the proposed exports (there's a ticket to [automate asking for Performance Hub approval](https://dsdmoj.atlassian.net/browse/PDE-1518))

2. Check the user-submitted yaml file is correct.

3. Run `pulumi preview` to check the resources look correct

4. Approve and merge the pull request

5. Deploy the changes with `pulumi up` (there's a ticket to [automate the deployment](https://dsdmoj.atlassian.net/browse/PDE-1441))

6. Ask the user to test the export - including making sure the Performance Hub get the test file, as we can't see the Performance Hub bucket ourselves

## Running end-to-end tests

End-to-end tests run using Localstack, which creates a mock AWS environment. The test infrastructure should behave like real resources, but none of it needs access to a real AWS account.

The tests are are stored in the `tests_end_to_end/` directory. They should run automatically when you open a pull request.

To run the end-to-end tests locally:

1. install and open Docker
2. install packages from the dev requirements file: `pip install -r requirements-dev.txt`
3. navigate to your project directory and activate your virtual environment
4. in your terminal, run `localstack start`
5. open another terminal window and again navigate to your project directory
6. log into your local Pulumi backend with `pulumi login --local` (so it doesn't try to connect to our S3-stored Pulumi backends)
7. run tests with `pytest tests_end_to_end/ --disable-warnings -vv`

When running locally you should restart Localstack between test runs. In its terminal window, press `ctrl-c` to sto it, then run `localstack start` again.

Otherwise the Localstack container will still contain resources created from your last test run.
