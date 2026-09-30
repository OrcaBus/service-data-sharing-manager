#!/usr/bin/env python3

"""
Get the primary data path prefix for a packaging job.

Given a packaging job id, query the data sharing packaging API DynamoDB table,
pull the 'package_request' map from the job record and return its
'primary_data_path_prefix' value.

This prefix is used to extend the push location before running a filemanager
sync, so that the sync only crawls the data we have pushed rather than the
entire push location bucket.
"""

# Standard imports
from os import environ

import boto3
from boto3.dynamodb.types import TypeDeserializer

# The attribute on the package request that holds the primary data path prefix.
# Attributes are stored in the DynamoDB table in snake_case.
PACKAGE_REQUEST_ATTRIBUTE_NAME = "package_request"
PRIMARY_DATA_PATH_PREFIX_ATTRIBUTE_NAME = "primary_data_path_prefix"


def get_dynamodb_client():
    """
    Get a dynamodb client.
    """
    return boto3.client("dynamodb")


def get_packaging_job(packaging_job_id: str) -> dict:
    """
    Get the packaging job record from the packaging API table by its id.
    :param packaging_job_id:
    :return: the deserialized job record
    """
    get_item_response = get_dynamodb_client().get_item(
        TableName=environ["PACKAGING_API_TABLE_NAME"],
        Key={
            "id": {"S": packaging_job_id}
        }
    )

    if "Item" not in get_item_response:
        raise ValueError(
            f"Could not find packaging job with id '{packaging_job_id}' "
            f"in table '{environ['PACKAGING_API_TABLE_NAME']}'"
        )

    deserializer = TypeDeserializer()
    return {
        key: deserializer.deserialize(value)
        for key, value in get_item_response["Item"].items()
    }


def handler(event, context):
    """
    Get the primary data path prefix for a packaging job.
    :param event: expects { "packagingJobId": "pkg.xxx" }
    :param context:
    :return: { "primaryDataPathPrefix": "<prefix>" }
    """
    # Inputs
    packaging_job_id = event.get("packagingJobId")

    if not packaging_job_id:
        raise ValueError("packagingJobId is required")

    # Get the packaging job record
    packaging_job = get_packaging_job(packaging_job_id)

    # Pull the package request map
    package_request = packaging_job.get(PACKAGE_REQUEST_ATTRIBUTE_NAME)

    if not package_request:
        raise ValueError(
            f"Packaging job '{packaging_job_id}' does not have a "
            f"'{PACKAGE_REQUEST_ATTRIBUTE_NAME}' attribute"
        )

    # Pull the primary data path prefix from the package request map
    primary_data_path_prefix = package_request.get(PRIMARY_DATA_PATH_PREFIX_ATTRIBUTE_NAME)

    return {
        "primaryDataPathPrefix": primary_data_path_prefix
    }
