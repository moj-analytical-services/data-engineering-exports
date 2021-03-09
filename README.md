# Data Engineering Hub Exports

This repository allows you to export data from the Analytical Platform to the
HMPPS Performance Hub.

## How to use

To register a new data for export:

1. Create a new branch from `main` with the name `dataset/<dataset-name>`. Here,
   and throughout, `<dataset-name>` should replaced with the name of the dataset
   you want to export and should only contain lower case letters and underscores,
   for example, `prison_incidents`.
3. Create a new file in the `datasets` directory called `<dataset-name>.yaml`,
   for example, `incidents.yaml`.
3. Complete the following fields:
   - `.name`: the name of the dataset – this should match the filename
   - `.users`: a list of users that should have permission to export data – each
     user should begin with `alpha_user_`, `alpha_app_` or `airflow_`
4. Commit the file and push to GitHub.
5. Create a new pull request and request a review from the data engineering team

Once approved, the data engineering team will deploy the changes on your behalf.

Any of the listed users will then be able to put objects to the following
location in S3: `s3://mojap-hub-exports/<dataset-name>/*`.

Whenever you put an object to this location it will automatically be copied to
the HMPPS Performance Hub AWS account.
