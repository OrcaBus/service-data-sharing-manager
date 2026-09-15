#!/usr/bin/env python3
"""
Handle a data sharing sync request carrying a Step Functions task token.

Forwards the request to the Data Sharing API to create the job, then records the
job id and task token in the task token table so the token can be resolved when
the job reaches a terminal state.

Request type is selected by the event detail-type (values injected via env vars):
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

import hashlib
from datetime import datetime, timezone, timedelta
from os import environ

import boto3
from botocore.exceptions import ClientError

from orcabus_api_tools.data_sharing import create_package, push_package

# Detail-types are injected by the infrastructure (single source of truth in constants.ts)
PACKAGING_SYNC_DETAIL_TYPE_ENV_VAR = "PACKAGING_SYNC_DETAIL_TYPE"
PUSH_SYNC_DETAIL_TYPE_ENV_VAR = "PUSH_SYNC_DETAIL_TYPE"

# TTL for task token rows, in days
TASK_TOKEN_TTL_DAYS = 1

TASK_TOKEN_TABLE_NAME_ENV_VAR = "TASK_TOKEN_TABLE_NAME"


def get_dynamodb_table():
    return boto3.resource("dynamodb").Table(environ[TASK_TOKEN_TABLE_NAME_ENV_VAR])


def get_claim_id(task_token: str) -> str:
    """
    Build the idempotency claim key for a task token.

    EventBridge delivers at-least-once, so the same request (carrying the same
    task token) can arrive more than once. The token is hashed to keep the key
    tidy.
    """
    return f"claim#{hashlib.sha256(task_token.encode()).hexdigest()}"


def claim_request(task_token: str) -> bool:
    """
    Atomically claim a request before creating the job.

    Returns True if this invocation won the claim (no job created yet for this
    token), or False if the request was already claimed by a previous delivery.
    """
    now = datetime.now(timezone.utc)
    expire_at = int((now + timedelta(days=TASK_TOKEN_TTL_DAYS)).timestamp())

    try:
        get_dynamodb_table().put_item(
            Item={
                "id": get_claim_id(task_token),
                "claimed_at": now.isoformat(),
                "expire_at": expire_at,
            },
            ConditionExpression="attribute_not_exists(id)",
        )
    except ClientError as error:
        if error.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException":
            return False
        raise

    return True


def create_job(detail_type: str, payload: dict) -> str:
    """
    Forward the request to the Data Sharing API and return the created job id.
    """
    if detail_type == environ[PACKAGING_SYNC_DETAIL_TYPE_ENV_VAR]:
        package = create_package(
            package_name=payload["packageName"],
            package_request=payload["packageRequest"],
        )
        return package["id"]

    if detail_type == environ[PUSH_SYNC_DETAIL_TYPE_ENV_VAR]:
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

    # Claim the request before creating the job. EventBridge is at-least-once, so
    # a duplicate delivery (or a retry) could otherwise create a second package/push job.
    if not claim_request(task_token):
        return {"claimed": False, "reason": "request already claimed"}

    job_id = create_job(detail_type, payload)
    record_task_token(job_id, task_token)

    return {
        "claimed": True,
        "id": job_id,
    }
