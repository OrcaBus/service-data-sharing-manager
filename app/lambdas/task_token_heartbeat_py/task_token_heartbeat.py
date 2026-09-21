#!/usr/bin/env python3
"""
Send Step Functions task token heartbeats for in-progress data sharing jobs.

Runs on a schedule. Iterates over the task token table, queries each job's
current status via the Data Sharing API, and sends a heartbeat for jobs that
are still running so their waiting execution does not time out.

Terminal jobs are skipped (resolved by the completion listener). If a token is
dead (gone, expired, or invalid), its row is removed so it is not queried again.
A failure on one row never stops heartbeats for the remaining rows.
"""

from os import environ

import boto3
from botocore.exceptions import ClientError

from orcabus_api_tools.data_sharing import get_package, get_push_job

TASK_TOKEN_TABLE_NAME_ENV_VAR = "TASK_TOKEN_TABLE_NAME"

RUNNING_STATUSES = ("PENDING", "RUNNING")

# Errors that mean the token is dead and its row should be removed
DEAD_TOKEN_ERROR_CODES = ("TaskDoesNotExist", "TaskTimedOut", "InvalidToken")

# Heartbeat outcomes
HEARTBEAT_SENT = "SENT"
HEARTBEAT_DEAD_TOKEN = "DEAD_TOKEN"
HEARTBEAT_ERROR = "ERROR"

PACKAGE_CONTEXT_PREFIX = "pkg."
PUSH_CONTEXT_PREFIX = "psh."


def get_dynamodb_table():
    return boto3.resource("dynamodb").Table(environ[TASK_TOKEN_TABLE_NAME_ENV_VAR])


def get_sfn_client():
    return boto3.client("stepfunctions")


def delete_task_token_row(job_id: str) -> None:
    get_dynamodb_table().delete_item(Key={"id": job_id})


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


def send_heartbeat(task_token: str) -> str:
    """
    Send a heartbeat for the token and report the outcome.

      - HEARTBEAT_SENT       heartbeat delivered
      - HEARTBEAT_DEAD_TOKEN token is gone/expired/invalid; its row should be removed
      - HEARTBEAT_ERROR      transient/unexpected failure; leave the row and move on
    """
    try:
        get_sfn_client().send_task_heartbeat(taskToken=task_token)
    except ClientError as error:
        error_code = error.response.get("Error", {}).get("Code")
        if error_code in DEAD_TOKEN_ERROR_CODES:
            return HEARTBEAT_DEAD_TOKEN
        return HEARTBEAT_ERROR

    return HEARTBEAT_SENT


def handler(event, context):
    heartbeats_sent = 0

    for row in scan_task_token_rows():
        job_id = row["id"]
        task_token = row.get("task_token")

        # Skip rows without a task token (e.g. idempotency claim rows)
        if task_token is None:
            continue

        status = get_job_status(job_id)
        if status not in RUNNING_STATUSES:
            continue

        # A failure on one row must never stop heartbeats for the remaining rows.
        outcome = send_heartbeat(task_token)
        if outcome == HEARTBEAT_SENT:
            heartbeats_sent += 1
        elif outcome == HEARTBEAT_DEAD_TOKEN:
            # Token is dead, remove the row so it is not queried again
            delete_task_token_row(job_id)
        # HEARTBEAT_ERROR: leave the row for a later run, do not delete or raise

    return {
        "heartbeatsSent": heartbeats_sent,
    }
