#!/usr/bin/env python3
"""
Resolve a Step Functions task token when a data sharing job reaches a terminal state.

Triggered by job state change events. Looks up the job id in the task token
table and, on a terminal status, sends the recorded task token back to the
waiting execution.

  - SUCCEEDED         -> SendTaskSuccess
  - FAILED / ABORTED  -> SendTaskFailure

Non-terminal statuses and jobs with no recorded token are ignored.

Expected event:
  {
    "id": "pkg.xxx" | "psh.xxx",
    "status": "PENDING" | "RUNNING" | "FAILED" | "ABORTED" | "SUCCEEDED"
  }
"""

import json
from os import environ

import boto3
from botocore.exceptions import ClientError

TASK_TOKEN_TABLE_NAME_ENV_VAR = "TASK_TOKEN_TABLE_NAME"

TERMINAL_SUCCESS_STATUSES = ("SUCCEEDED",)
TERMINAL_FAILURE_STATUSES = ("FAILED", "ABORTED")

# SendTask calls that fail because the token is already resolved or expired
IGNORABLE_ERROR_CODES = ("TaskDoesNotExist", "TaskTimedOut")


def get_dynamodb_table():
    return boto3.resource("dynamodb").Table(environ[TASK_TOKEN_TABLE_NAME_ENV_VAR])


def get_sfn_client():
    return boto3.client("stepfunctions")


def get_task_token(job_id: str):
    item = get_dynamodb_table().get_item(Key={"id": job_id}).get("Item")
    if item is None:
        return None
    return item.get("task_token")


def delete_task_token_row(job_id: str) -> None:
    """
    Remove the row once the token is resolved so the heartbeat lambda no longer
    queries a finished job. TTL remains as a safety net for rows that are never
    resolved.
    """
    get_dynamodb_table().delete_item(Key={"id": job_id})


def send_task_success(task_token: str, job_id: str, status: str) -> None:
    get_sfn_client().send_task_success(
        taskToken=task_token,
        output=json.dumps({"id": job_id, "status": status}),
    )


def send_task_failure(task_token: str, job_id: str, status: str) -> None:
    get_sfn_client().send_task_failure(
        taskToken=task_token,
        error=f"DataSharingJob{status}",
        cause=f"Data sharing job {job_id} ended with status {status}",
    )


def handler(event, context):
    job_id = event["id"]
    status = event["status"]

    if status not in TERMINAL_SUCCESS_STATUSES + TERMINAL_FAILURE_STATUSES:
        return {"resolved": False, "reason": "non-terminal status"}

    task_token = get_task_token(job_id)
    if task_token is None:
        return {"resolved": False, "reason": "no task token recorded"}

    try:
        if status in TERMINAL_SUCCESS_STATUSES:
            send_task_success(task_token, job_id, status)
        else:
            send_task_failure(task_token, job_id, status)
    except ClientError as error:
        error_code = error.response.get("Error", {}).get("Code")
        if error_code not in IGNORABLE_ERROR_CODES:
            raise
        # Token already resolved or expired - the row is done either way, remove it
        delete_task_token_row(job_id)
        return {"resolved": False, "reason": error_code}

    # Token resolved - remove the row so the heartbeat no longer queries this job
    delete_task_token_row(job_id)

    return {"resolved": True, "id": job_id, "status": status}
