Data Sharing Service
================================================================================

- [Service Description](#service-description)
  - [Name \& responsibility](#name--responsibility)
  - [Description](#description)
  - [API Endpoints](#api-endpoints)
- [CLI Installation](#cli-installation)
- [CLI Usage](#cli-usage)
  - [Generating CLI manifests](#generating-cli-manifests)
  - [Generating the package](#generating-the-package)
  - [Package validation](#package-validation)
  - [Package Sharing](#package-sharing)
    - [Pushing Packages](#pushing-packages)
    - [Presigning packages](#presigning-packages)
- [CLI Troubleshooting](#cli-troubleshooting)
- [Automatic Data Sharing](#automatic-data-sharing)
- [Infrastructure \& Deployment](#infrastructure--deployment)
  - [Stateful](#stateful)
  - [Stateless](#stateless)
  - [CDK Commands](#cdk-commands)
  - [Stacks](#stacks)
  - [Release management](#release-management)
- [Development](#development)
  - [Project Structure](#project-structure)
  - [Setup](#setup)
    - [Requirements](#requirements)
    - [Install Dependencies](#install-dependencies)
    - [First Steps](#first-steps)
  - [Conventions](#conventions)
  - [Linting \& Formatting](#linting--formatting)
  - [Testing](#testing)
- [Glossary \& References](#glossary--references)


Service Description
--------------------------------------------------------------------------------

### Name & responsibility

### Description

Collate a set of primary and secondary data from a list of samples.
Share the data via 'push' (recommended) via S3 or ICAv2, or
through presigned urls.

There are two main steps to the process:

1. Data packaging:
  * Unarchives data (if data is being pulled)
  * Generates an RMarkdown based HTML report of the data in the package
2. Data sharing:
  * Either via a push to S3 or ICAv2,
  * or via presigned URLs

### API Endpoints

You can interact with the [data-sharing API swagger page](https://data-sharing.prod.umccr.org/schema/swagger-ui#/).
or alternatively use the CLI.

CLI Installation
--------------------------------------------------------------------------------

Two steps to install this CLI

1. Clone this repo
```shell
git clone git@github.com:OrcaBus/service-data-sharing-manager
cd service-data-sharing-manager
```

2. Install the CLI

```shell
bash scripts/install.sh
```

The installation script will add in the following line to your .rc file

```shell
alias data-sharing-tool="$HOME/.local/data-sharing-cli-venv/bin/python3 $HOME.local/data-sharing-cli-venv/bin/data-sharing-tool'
```

You will need to log out and log back in for the alias to take effect.

CLI Usage
--------------------------------------------------------------------------------

> Make sure you are logged into AWS CLI with the correct credentials before running the commands below.

```shell
aws sso login
export AWS_PROFILE='umccr-production'
```

### Generating CLI manifests

> This component expects the user to have some familiarity with AWS athena

We use the 'mart' tables to generate the appropriate manifests for package generation.

You may use the UI to generate the manifests, or you can use the command line interface as shown below.

In the example below, we collect the libraries that are associated with the project 'CUP' and the
sequencing run date is greater than or equal to '2025-04-01'.

We require only the lims-manifest when collecting fastq data.

The workflow manifest (along with the lims-manifest) is required when collecting secondary analysis data.

```bash
WORK_GROUP="orcahouse"
DATASOURCE_NAME="orcavault"
DATABASE_NAME="mart"

# Initialise the query
query_execution_id="$( \
  aws athena start-query-execution \
      --no-cli-pager \
      --query-string " \
        SELECT *
        FROM lims
        WHERE
          project_id = 'CUP' AND
          sequencing_run_date >= CAST('2025-04-01' AS DATE)
      " \
      --work-group "${WORK_GROUP}" \
      --query-execution-context "Database=${DATABASE_NAME}, Catalog=${DATASOURCE_NAME}" \
      --output json \
      --query 'QueryExecutionId' | \
  jq --raw-output
)"

# Wait for the query to complete
while true; do
  query_state="$( \
    aws athena get-query-execution \
      --no-cli-pager \
      --output json \
      --query-execution-id "${query_execution_id}" \
      --query 'QueryExecution.Status.State' | \
    jq --raw-output
  )"

  if [[ "${query_state}" == "SUCCEEDED" ]]; then
    break
  elif [[ "${query_state}" == "FAILED" || "${query_state}" == "CANCELLED" ]]; then
    echo "Query failed or was cancelled"
    exit 1
  fi

  sleep 5
done

# Collect the query results
query_results_uri="$( \
  aws athena get-query-execution \
    --no-cli-pager \
    --output json \
    --query-execution-id "${query_execution_id}" \
    --query 'QueryExecution.ResultConfiguration.OutputLocation' | \
  jq --raw-output
)"

# Download the results
aws s3 cp "${query_results_uri}" ./lims_manifest.csv
```

For the workflow manifest, we can use the same query as above, but we will need to change the final table name to 'workflow'.

An example of the SQL might be as follows:

```sql
/*
Get the libraries associated with the project 'CUP' and their sequencing run date is greater than or equal to '2025-04-01'.
*/
WITH libraries AS (
    SELECT library_id
    FROM lims
    WHERE
      project_id = 'CUP' AND
      sequencing_run_date >= CAST('2025-04-01' AS DATE)
)
/*
Select matching TN workflows for the libraries above
*/
SELECT *
from workflow
WHERE
    workflow_name = 'tumor-normal' AND
    library_id IN (SELECT library_id FROM libraries)
```

### Generating the package

Using the lims manifest we can now generate the package of primary data.

By using the `--wait` parameter, the CLI will only return once the package has been completed.

This may take around 5 mins to complete depending on the size of the package.

```bash
data-sharing-tool generate-package \
  --package-name 'my-package' \
  --lims-manifest-csv lims_manifest.csv \
  --wait
```

This will generate a package and print the package to the console like so:

```bash
Generating package 'pkg.123456789'...
```

### Package validation

Once the package has completed generating we can validate the package using the following command:

> By using the BROWSER env var, the package report will be automatically opened up in our browser!

```bash
data-sharing-tool view-package-report \
  --package-id pkg.12345678910
```

Look through the metadata, fastq and secondary analysis tabs to ensure that the package is correct.


### Package Sharing

#### Pushing Packages

We can use the following command to push the package to a destination location.  This will generate a push job id.

Like the package generation, we can use the `--wait` parameter to wait for the job to complete.

```bash
data-sharing-tool push-package \
  --package-id pkg.12345678910 \
  --share-location s3://bucket/path-to-prefix/
```

#### Presigning packages

Not all data receivers will have an S3 bucket or ICAV2 project for us to dump data in.

Therefore, we also support the old-school presigned url method.

We can use the following command to generate presigned urls in a script for the package

```bash
data-sharing-tool presign-package \
  --package-id pkg.12345678910
```

This will return a presigned url for a shell script that can be used to download the package.

> The presigned urls inside the shell script will be valid for at least 6 days, however the presigned url of the shell script
> itself will only be valid for 24 hours, therefore, you should download the shell script and then send it to its intended
> recipient rather than sending them the presigned url of the shell script.

CLI Troubleshooting
--------------------------------------------------------------------------------

A common place of failure is the package generation step.
The package generation runs through an AWS Step Function, if that step function fails,
a message will be put to the alerts-prod Slack channel.

Navigate the failed AWS Step Function in the AWS UI to determine the source of the failure.

Automatic Data Sharing
--------------------------------------------------------------------------------

Automatic Data Sharing extends the core service by automatically packaging new sequencing runs and then requiring a human to trigger the push.

Upon completion of a sequencing run, the following process is triggered:

- Check the projects in the sequencing run against the job definitions (see [Job Definitions](#job-definitions) below) to identify if any automatic sharing jobs apply.

- If there’s a match, performs packaging fully unattended.

- After packaging completes, posts a Slack notification with package details and link to the package report, together with a button to trigger the push to the defined destination. Note that only users defined in `AutoDataSharingSlackConfig` are able to trigger the push via the Slack button (see [Slack Secret definitions](#slack-secret-definitions) below).

- After push completes, posts another Slack notification confirming the push result.


### Job Definitions

Each automatic sharing job is defined as a JSON object and stored in the `auto_package_push_jobs/jobs.json` file, in the data sharing bucket (`DataSharingBucket`).
Multiple jobs can be defined within a single JSON array. Below is a template for one job definition:

```json
{
  "jobName": "project-shortname",
  "enabled": true,
  "projectIdList": ["PROJECT1"],
  "dataTypeList": ["fastq"],
  "shareDestination": "s3://target-bucket/path/"
}
```


`jobName` (str) – short name for the job. Used in logs and Step Functions.

`enabled` (bool) – set to true to activate the job; disabled jobs are ignored.

`projectIdList` (list[str]) – list of project IDs; run must match at least one.

`dataTypeList` (list[str]) – which data types to include (e.g. `fastq`).

`shareDestination` (str) – destination S3 path where the data will be pushed.


### Slack Integration

Automatic data sharing leverages Slack notifications and push trigger buttons, which are handled by the [`auto-data-sharing`](https://api.slack.com/apps/A0A28QK9752/general?) app in the [UMCCR Slack workspace](https://umccr.slack.com). The app must be configured with the following settings:

- **Required OAuth Scope:**
  - `chat:write` — Allows the app to send messages as the bot in channels it is a member of.

- **Channel Integration:**
  - The `auto-data-sharing` Slack app must be added as an integration to each channel it will post in. In production, this is the private channel `#auto-data-sharing`; in development, it is `#alerts-dev`.

- **Interactivity:**
  - Under Slack App > “Interactivity & Shortcuts”, set the **Request URL** to the API Gateway endpoint deployed for the stack (`AutoPushSlackApi`, see `infrastructure/stage/api/index.ts`). Find it under "Invoke URL" for `AutoPushSlackApi` in AWS API Gateway Console. The final URL should be:
  ```
  https://<api-gateway-id>.execute-api.<region>.amazonaws.com/prod/slack/actions
  ```


### Slack Secret Definitions

To ensure proper Slack integration, the following secrets must be present in AWS Secrets Manager (see definitions in `infrastructure/stage/secrets/index.ts`):

1. **`AutoDataSharingSlackBotToken`:** The bot token used to authenticate API requests (found in the Slack App under "OAuth & Permissions" → "Bot User OAuth Token").
2. **`AutoDataSharingSlackSigningSecret`:** Slack signing secret for validating requests (found in "Basic Information" → "App Credentials" → "Signing Secret").
3. **`AutoDataSharingSlackConfig`:** Contains the channel ID for posting and a list of users allowed to trigger push commands. Format:

    ```json
    {
      "channel_id": "C1234567890",
      "allowed_users": [
        { "username": "user1.name", "id": "U111111" },
        { "username": "user2.name", "id": "U222222" }
      ]
    }
    ```

> **Note:** These secret values are NOT set during deployment and must be configured manually in AWS Secrets Manager after deployment.



Infrastructure & Deployment
--------------------------------------------------------------------------------

Short description with diagrams where appropriate.
Deployment settings / configuration (e.g. CodePipeline(s) / automated builds).

Infrastructure and deployment are managed via CDK. This template provides two types of CDK entry points: `cdk-stateless` and `cdk-stateful`.

### Stateful

- Buckets
  - We use S3 buckets to store html reports and a registry of all files sent through PUSH services.
- DynamoDB
  - We use DynamoDB to power our FastAPI interface.
  - we use DynamoDB to store the package metadata.

### Stateless

- Lambdas
- StepFunctions
- ECS
- API Gateway

### CDK Commands

You can access CDK commands using the `pnpm` wrapper script.

- **`cdk-stateless`**: Used to deploy stacks containing stateless resources (e.g., AWS Lambda), which can be easily redeployed without side effects.
- **`cdk-stateful`**: Used to deploy stacks containing stateful resources (e.g., AWS DynamoDB, AWS RDS), where redeployment may not be ideal due to potential side effects.

The type of stack to deploy is determined by the context set in the `./bin/deploy.ts` file. This ensures the correct stack is executed based on the provided context.

i.e

```shell
pnpm cdk-stateless list
```

### Stacks

This CDK project manages multiple stacks. The root stack (the only one that does not include `DeploymentPipeline` in its stack ID) is deployed in the toolchain account and sets up a CodePipeline for cross-environment deployments to `beta`, `gamma`, and `prod`.

**CDK Stateful**

```
StatefulDataSharingStackPipeline
StatefulDataSharingStackPipeline/StatefulDataSharingStackPipeline/OrcaBusBeta/StatefulDataSharingStack (OrcaBusBeta-StatefulDataSharingStack)
StatefulDataSharingStackPipeline/StatefulDataSharingStackPipeline/OrcaBusGamma/StatefulDataSharingStack (OrcaBusGamma-StatefulDataSharingStack)
StatefulDataSharingStackPipeline/StatefulDataSharingStackPipeline/OrcaBusProd/StatefulDataSharingStack (OrcaBusProd-StatefulDataSharingStack)
```

**CDK Stateless**

```
StatelessDataSharingStackPipeline
StatelessDataSharingStackPipeline/StatelessDataSharingStackPipeline/OrcaBusBeta/StatelessDataSharingStack (OrcaBusBeta-StatelessDataSharingStack)
StatelessDataSharingStackPipeline/StatelessDataSharingStackPipeline/OrcaBusGamma/StatelessDataSharingStack (OrcaBusGamma-StatelessDataSharingStack)
StatelessDataSharingStackPipeline/StatelessDataSharingStackPipeline/OrcaBusProd/StatelessDataSharingStack (OrcaBusProd-StatelessDataSharingStack)
```


Example output:

```sh
OrcaBusStatelessServiceStack
OrcaBusStatelessServiceStack/DeploymentPipeline/OrcaBusBeta/DeployStack (OrcaBusBeta-DeployStack)
OrcaBusStatelessServiceStack/DeploymentPipeline/OrcaBusGamma/DeployStack (OrcaBusGamma-DeployStack)
OrcaBusStatelessServiceStack/DeploymentPipeline/OrcaBusProd/DeployStack (OrcaBusProd-DeployStack)
```

### Release management

The service employs a fully automated CI/CD pipeline that automatically builds and releases all changes to the `main` code branch.

Development
--------------------------------------------------------------------------------

### Project Structure

The root of the project is an AWS CDK project where the main application logic lives inside the `./app` folder.

The project is organized into the following key directories:

- **`./app`**: Contains the main application logic. You can open the code editor directly in this folder, and the application should run independently.

- **`./bin/deploy.ts`**: Serves as the entry point of the application. It initializes two root stacks: `stateless` and `stateful`. You can remove one of these if your service does not require it.

- **`./infrastructure`**: Contains the infrastructure code for the project:
  - **`./infrastructure/toolchain`**: Includes stacks for the stateless and stateful resources deployed in the toolchain account. These stacks primarily set up the CodePipeline for cross-environment deployments.
  - **`./infrastructure/stage`**: Defines the stage stacks for different environments:
    - **`./infrastructure/stage/config.ts`**: Contains environment-specific configuration files (e.g., `beta`, `gamma`, `prod`).
    - **`./infrastructure/stage/stack.ts`**: The CDK stack entry point for provisioning resources required by the application in `./app`.

- **`.github/workflows/pr-tests.yml`**: Configures GitHub Actions to run tests for `make check` (linting and code style), tests defined in `./test`, and `make test` for the `./app` directory. Modify this file as needed to ensure the tests are properly configured for your environment.

- **`./test`**: Contains tests for CDK code compliance against `cdk-nag`. You should modify these test files to match the resources defined in the `./infrastructure` folder.


### Setup

#### Requirements

```sh
node --version
v22.9.0

# Update Corepack (if necessary, as per pnpm documentation)
npm install --global corepack@latest

# Enable Corepack to use pnpm
corepack enable pnpm
```

#### Install Dependencies

To install all required dependencies, run:

```sh
make install
```

#### First Steps

Before using this template, search for all instances of `TODO:` comments in the codebase and update them as appropriate for your service. This includes replacing placeholder values (such as stack names).


### Conventions

### Linting & Formatting

Automated checks are enforces via pre-commit hooks, ensuring only checked code is committed. For details consult the `.pre-commit-config.yaml` file.

Manual, on-demand checking is also available via `make` targets (see below). For details consult the `Makefile` in the root of the project.


To run linting and formatting checks on the root project, use:

```sh
make check
```

To automatically fix issues with ESLint and Prettier, run:

```sh
make fix
```

### Testing


Unit tests are available for most of the business logic. Test code is hosted alongside business in `/tests/` directories.

```sh
make test
```

Glossary & References
--------------------------------------------------------------------------------

For general terms and expressions used across OrcaBus services, please see the platform [documentation](https://github.com/OrcaBus/wiki/blob/main/orcabus-platform/README.md#glossary--references).

Service specific terms:

| Term      | Description                                      |
|-----------|--------------------------------------------------|
| Foo | ... |
| Bar | ... |
