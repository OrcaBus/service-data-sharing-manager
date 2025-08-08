#!/usr/bin/env python
import typing

from urllib.parse import urlparse
import boto3
import json

if typing.TYPE_CHECKING:
    from mypy_boto3_s3 import S3Client


def get_s3_client() -> 'S3Client':
    return boto3.client("s3")


def handler(event, context):
    """
    Create JSONL file for S3 steps copy and upload it to S3.

    Event must include:
    - sourceUrisList: List of S3 URIs to copy
    - s3StepsCopyBucket: Destination bucket to store the JSONL
    - s3StepsCopyKey: Key (path) for the JSONL file in that bucket
    """
    # Create JSONL for steps copy and upload to S3
    source_uris_list = event.get("sourceUrisList")
    s3_steps_copy_bucket = event.get("s3StepsCopyBucket")
    s3_steps_copy_key = event.get("s3StepsCopyKey")

    # Ensure all inputs exist
    if not source_uris_list or not s3_steps_copy_bucket or not s3_steps_copy_key:
        raise ValueError("Missing required parameters: sourceUrisList, s3StepsCopyBucket, s3StepsCopyKey")

    # Generate list of copy instructions
    copy_instructions = [
        {
            "sourceBucket": urlparse(uri).netloc,
            "sourceKey": urlparse(uri).path.lstrip("/")
        }
        for uri in source_uris_list
    ]

    # Convert to JSONL format
    jsonl_content = "\n".join(json.dumps(item) for item in copy_instructions)

    # Upload to s3
    get_s3_client().put_object(
        Bucket=s3_steps_copy_bucket,
        Key=s3_steps_copy_key,
        Body=jsonl_content.encode("utf-8"),
    )
