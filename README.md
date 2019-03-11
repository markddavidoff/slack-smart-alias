# slack-smart-alias
A lambda that lets you dynamically set a user group/alias like `@oncall` based on a schedule

## Installation From Source

#### Clone this repo
```bash
git clone git@github.com:markddavidoff/slack-smart-alias.git
```

#### Install python requirements
Make sure you have python 3.7 (or downgrade the `runtime` setting in `serverless.yml` to your version)
```bash
pip install -r requirements.txt
```

## Setup Slack
- todo setup app
- todo setup usergroup

## Configuration / Running Locally
Configs come from 3 places:
 - Application configs in `settings.py` which each have descriptive comments there.
 - Sensitive configs/tokens are pulled from environment vars and loaded to python vars in `settings.py`
 - Lambda scheduling and run options in `serverless.yml` which are discussed in the `serverless` docs and below

In production, `serverless` loads env vars from [AWS Secrets Manager](https://us-west-1.console.aws.amazon.com/secretsmanager/home?region=us-west-1#/home) or [AWS Parameter Store](https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-paramstore.html) as mapped in `serverless.yml`.

#### Set the sensitive configs
 - `SLACK_SMART_ALIAS_SLACK_API_TOKEN` - The Slack API token to use for authentication to the Slack WebAPI you set up
  in [Setup Slack](#setup-slack). Needs the Slack permissions: `usergroups:read`, `usergroups:write`, `users:read`, 
  `users:read.email`, `users.profile:read`
 - `GOOGLE_SERVICE_ACCOUNT_KEYFILE` - The json dict of the keyfile for the [service account](https://developers.google.com/api-client-library/python/auth/service-accounts)
 to use for Google Cal.

For production:
 - Add the key to Parameter Store/Secrets Manager and then update the path for the variable under 
 `provider>environment>[var name]` in  `serverless.yml` as described in [serverless variable docs](https://serverless.com/framework/docs/providers/aws/guide/variables/)
When running locally:
 - Just load config to a local env var such as with `export [var name]=[var value]` before running.

## Run locally
Once all env vars are set locally you can run the alias code locally with 
```bash
``` 
or you can load production env vars to a local lambda emulator using `serverless`'s [invoke local](
https://serverless.com/framework/docs/providers/aws/cli-reference/invoke-local/) with
```bash
serverless invoke local --function set_alias
```
/#todo add data to the above call

## Deploying to Lambda using `serverless`
This lambda uses [serverless](https://serverless.com/framework/docs/), a toolkit that makes building, deploying and 
maintaining serverless apps like this lambda painless. The instructions assume you're using AWS, if you're not, you'll
have to tweak some things in `serverless.yml` to make it work with your provider

#### Setup `serverless`
Their getting started page is [here](https://serverless.com/framework/docs/getting-started/), copy pasted for your 
convenience below (you'll also need to [install npm](https://www.npmjs.com/get-npm) first):
```bash
# Installing the serverless cli
npm install -g serverless
# Updating serverless from a previous version of serverless
npm install -g serverless
```
Then install some useful `serverless` plugins (you can uses `sls` as short for `serverless`)

**serverless-python-requirements**

*Its pretty annoying to add external requirements to a lambda when deploying manually. You have to build the wheels
for the packages on an aws linux ami and include those in the zip that you upload. Luckily, there's a serverless plugin
to make that all super easy.*
```
sls plugin install -n serverless-python-requirements
```

**serverless-local-schedule**

*No more translating times to UTC! This plugin lets you setup your crons at local time with a specified timezone and 
takes care of the translation for you *
```
sls plugin install -n serverless-local-schedule
```

#### Setup your provider (AWS) credentials
The Serverless Framework needs access to your cloud provider's account so that it can create and manage resources 
on your behalf.

If you already have the `awscli` installed locally:
  - If you have profile configured and setup in `~/.aws/credentials`, you're good to go.
  - If you don't have a profile setup you can use the [serverless config credentials](https://serverless
 .com/framework/docs/providers/aws/guide/credentials#setup-with-serverless-config-credentials-command) command to 
set one up for you

Else, read the [serverless aws setup docs](https://serverless.com/framework/docs/providers/aws/guide/credentials/)

Make sure the profile you're using to deploy has the permissions to modify all resources serverless needs. This is a 
good base to start with but may need tweaking as the `serverless` framework evolves:
 ```json
{
    "Sid": "BaseServerlessPermissions",
    "Effect": "Allow",
    "Action": [
        "cloudformation:CreateStack",
        "cloudformation:DescribeStacks",
        "cloudformation:DescribeStackEvents",
        "cloudformation:DescribeStackResource",
        "cloudformation:ValidateTemplate",
        "cloudformation:UpdateStack",
        "cloudformation:ListStacks",
        "iam:GetRole",
        "lambda:UpdateFunctionCode",
        "lambda:UpdateFunctionConfig",
        "lambda:GetFunctionConfiguration",
        "lambda:ListVersionsByFunction",
        "lambda:AddPermission",
        "s3:DeleteObject",
        "s3:GetObject",
        "s3:ListBucket",
        "s3:PutObject"
    ],
    "Resource": "*"
},
```

#### Setup the role your lambda runs with
Above we made sure our developer account had the permissions to deploy and manage a serverless application. But we also
need to setup the permissions for the lambda itself. It needs to access other aws resources, such as CloudWatch so it
 can write to a log and receive triggers.

- TODO

Serverless guide for this is [here](https://serverless.com/framework/docs/providers/aws/guide/iam/).

Permissions needed:
 - AWSLambdaVPCAccessExecutionRole

We created a role with the following policy:
todo:


### Setup your lambda run frequency

- See the notes in the `serverless.yml` file under `functions>set_alias>events>schedule`.
