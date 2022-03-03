# Data engineering hub exports

This repository lets you export data from the Analytical Platform to the HMPPS Performance Hub. This will save you having to download your results and email people to get them on the Performance Hub.

To export data you'll first need to get permission set up for your team.

## Getting your team set up

This guide uses an example dataset called 'new_project'. Wherever this appears, insert the name of your own dataset.

Only use lower case and underscores in your dataset name.

These steps use GitHub branches. If you're not familiar with these, check the Analytical Platform guide to [working on a GitHub branch](https://user-guidance.services.alpha.mojanalytics.xyz/github.html#working-on-a-branch).

1. Create a new branch in this repository called `dataset/new_project` 
2. Create a new file in the `datasets` directory called `new_project.yaml`
3. Add your project name and list of Analytical Platform usernames to the new file, like this:

``` yaml
  name: new_project
  users:
    - alpha_user_one
    - alpha_user_two
```

4. Commit the file and push it to GitHub
5. Create a new pull request and request a review from the data engineering team

The data engineering team will check your changes, deploy them and tell you when it's ready.


## Exporting data to the Performance Hub

All the users in your dataset file will have permission to add files to this
location in S3: `s3://mojap-hub-exports/new_project/`.

You can send a file using Python:

``` python
```

Or R:

``` R
```

After you send files to that location they will be copied to the Performance Hub. You won't be able to view the files in the Analytical Platform location above - we delete them once they're sent to the Performance Hub. 


## Reporting bugs and asking for features



