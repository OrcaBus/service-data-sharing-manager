#!/usr/bin/env python3
"""
Send Step Functions task token heartbeats for in-progress data sharing jobs.

Runs on a schedule. Iterates over the task token table, queries each job's
current status via the Data Sharing API, and sends a heartbeat for jobs that
are still running so their waiting execution does not time out.

Terminal jobs are skipped (resolved by the completion listener), and heartbeats
for tokens that are already resolved or expired are ignored.
"""

from os import environ

import boto3
from botocore.exceptions import ClientError

from orcabus_api_tools.data_sharing import get_package, get_push_job

TASK_TOKEN_TABLE_NAME_ENV_VAR = "TASK_TOKEN_TABLE_NAME"

RUNNING_STATUSES = ("PENDING", "RUNNING")

# SendTaskHeartbeat calls that fail because the token is already resolved or expired
IGNORABLE_ERROR_CODES = ("TaskDoesNotExist", "TaskTimedOut")

PACKAGE_CONTEXT_PREFIX = "pkg."
PUSH_CONTEXT_PREFIX = "psh."


def get_dynamodb_table():
    return boto3.resource("dynamodb").Table(environ[TASK_TOKEN_TABLE_NAME_ENV_VAR])


def get_sfn_client():
    return boto3.client("stepfunctions")


def get_job_status(job_id: str):
    if job_id.startswith(PUSH_CONTEXT_PREFIX):
        return get_push_job(job_id)["status"]
    if job_id.startswith(PACKAGE_CONTEXT_PREFIX):
        return get_package(job_id)["status"]
    return None


def scan_task_token_rows():
    table = get_dynamodb_table()
    response = table.scan()
    items = response.get("Items", [])
    while "LastEvaluatedKey" in response:
        response = table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
        items.extend(response.get("Items", []))
    return items


def send_heartbeat(task_token: str) -> None:
    try:
        get_sfn_client().send_task_heartbeat(taskToken=task_token)
    except ClientError as error:
        error_code = error.response.get("Error", {}).get("Code")
        if error_code not in IGNORABLE_ERROR_CODES:
            raise


def handler(event, context):
    heartbeats_sent = 0

    for row in scan_task_token_rows():
        job_id = row["id"]
        task_token = row["task_token"]

        status = get_job_status(job_id)
        if status not in RUNNING_STATUSES:
            continue

        send_heartbeat(task_token)
        heartbeats_sent += 1

    return {
        "heartbeatsSent": heartbeats_sent,
    }
