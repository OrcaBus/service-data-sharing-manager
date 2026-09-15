#!/usr/bin/env python3
"""
Handle a data sharing sync request carrying a Step Functions task token.

Forwards the request to the Data Sharing API to create the job, then records the
job id and task token in the task token table so the token can be resolved when
the job reaches a terminal state.

Request type is selected by the event detail-type:
  - DataPackagingSync -> create_package
  - DataPushSync      -> push_package

Expected event:
  {
    "taskToken": "<task token>",
    "detailType": "DataPackagingSync" | "DataPushSync",
    "payload": {
      # packaging: packageName, packageRequest
      # push:      packageId, shareDestination
    }
  }
"""

from datetime import datetime, timezone, timedelta
from os import environ

import boto3

from orcabus_api_tools.data_sharing import create_package, push_package

PACKAGING_SYNC_DETAIL_TYPE = "DataPackagingSync"
PUSH_SYNC_DETAIL_TYPE = "DataPushSync"

# TTL for task token rows, in days
TASK_TOKEN_TTL_DAYS = 1

TASK_TOKEN_TABLE_NAME_ENV_VAR = "TASK_TOKEN_TABLE_NAME"


def get_dynamodb_table():
    return boto3.resource("dynamodb").Table(environ[TASK_TOKEN_TABLE_NAME_ENV_VAR])


def create_job(detail_type: str, payload: dict) -> str:
    """
    Forward the request to the Data Sharing API and return the created job id.
    """
    if detail_type == PACKAGING_SYNC_DETAIL_TYPE:
        package = create_package(
            package_name=payload["packageName"],
            package_request=payload["packageRequest"],
        )
        return package["id"]

    if detail_type == PUSH_SYNC_DETAIL_TYPE:
        push_job = push_package(
            package_id=payload["packageId"],
            location_uri=payload["shareDestination"],
        )
        return push_job["id"]

    raise ValueError(f"Unsupported sync request detail-type: {detail_type}")


def record_task_token(job_id: str, task_token: str) -> None:
    """
    Write the job id -> task token mapping to the task token table.
    """
    now = datetime.now(timezone.utc)
    expire_at = int((now + timedelta(days=TASK_TOKEN_TTL_DAYS)).timestamp())

    get_dynamodb_table().put_item(
        Item={
            "id": job_id,
            "task_token": task_token,
            "status": "PENDING",
            "request_time": now.isoformat(),
            "expire_at": expire_at,
        }
    )


def handler(event, context):
    task_token = event["taskToken"]
    detail_type = event["detailType"]
    payload = event["payload"]

    job_id = create_job(detail_type, payload)
    record_task_token(job_id, task_token)

    return {
        "id": job_id,
    }
