# Contributing to data engineering hub exports

To get started, set up a new virtual environment and `pip install -r requirements.txt`.

Then install the pre-commit hooks with `pre-commit install`.

## Access the Pulumi stack

1. Activate the `restricted-admin-data` AWS role
2. Log in to the Pulumi backend with `pulumi login s3://data-engineering-pulumi.analytics.justice.gov.uk`
3. Run `pulumi stack select` and pick `data-engineering-hub-exports`
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

These are stored in the tests_end_to_end/ directory. They should run automatically when you open a pull request. To check them locally, first set the following environment variables:

export TEST_PULUMI_BACKEND=<url for the Pulumi sandbox backend>
export AWS_ROLE_TO_ASSUME=<arn of the Github Actions infrastructure role>
export PULUMI_CONFIG_PASSPHRASE=""
export GIT_BRANCH=$(git rev-parse --abbrev-ref HEAD)

See our LastPass shared folders for the backend and role values.

To set these values easily, create a file called .env in the directory, copy/paste the environment variables above and save.

To run the tests, make sure you're in your virtual environment, aws-vault into the sandbox-restricted-admin account and source the .env file:

```
aws-vault exec sandbox-restricted-admin -d 4h
source .env
pytest tests_end_to_end/ -W ignore::DeprecationWarning -vv
```

You will need to replace sandbox-restricted-admin with the profile name used in your local .aws/config file.

pytest should destroy all resources once tests are completed, whether the tests pass or fail. However the resources will not be destroyed if the tests error out, and must be deleted manually.
