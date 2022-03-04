# Contributing to data engineering hub exports

To get started, set up a new virtual environment and `pip install -r requirements.txt`.

## Access the Pulumi stack

1. Activate the `restricted-admin@data` AWS role
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
