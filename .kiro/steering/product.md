# Product: Data Sharing Service

The Data Sharing Service is part of the OrcaBus platform, operated by the University of Melbourne Centre for Cancer Research (UMCCR).

## Purpose

Collate primary and secondary genomics data from a list of samples and share it externally via S3 push, ICAv2 push, or presigned URLs.

## Core Workflow

1. **Packaging** — Collect FASTQ files and secondary analysis outputs (e.g. tumor-normal workflows), unarchive if needed, generate an HTML summary report, and register the package in DynamoDB.
2. **Sharing** — Push the package to an S3 or ICAv2 destination, or generate time-limited presigned URLs packaged into a downloadable shell script.

## Automatic Data Sharing

The service also supports unattended packaging triggered by completed sequencing runs, matched against job definitions stored in S3. A human approves the push via a Slack button.

## Key Interfaces

- **REST API** — FastAPI application (Python) served via Lambda + API Gateway with Cognito auth. Swagger available at `https://data-sharing.prod.umccr.org/schema/swagger-ui#/`.
- **CLI** — Python CLI (`data-sharing-tool`) for manual package generation, validation, push, and presigning.
- **Slack Integration** — The `auto-data-sharing` Slack app posts notifications and provides push trigger buttons.

## Environments

Three deployment stages: `beta`, `gamma`, `prod`. Deployment is fully automated via CodePipeline on merge to `main`.
