#!/usr/bin/env python3

"""
Either 'count' the number of s3 steps copy we will generate
OR 'generate' the jsonl and upload to s3 for the given package / file.
"""
# Imports
import typing
from pathlib import Path
from urllib.parse import urlparse
import pandas as pd
import re
from typing import Dict, Optional
from tempfile import NamedTemporaryFile
import boto3

# Layer imports
from data_sharing_tools.utils.dynamodb_helpers import query_dynamodb_table

if typing.TYPE_CHECKING:
    from mypy_boto3_s3 import S3Client


PORTAL_REGEX = re.compile(
    r"\d{8}[0-9a-f]{8}"
)


def get_data_from_dynamodb(job_id: str, context: str) -> pd.DataFrame:
    """
    Given a job id, query the dynamodb table to get all data that belongs to that job id for that given data type,
    where data type is one of:
     * library
     * fastq
     * workflow
     * files
    :param job_id:
    :param context:
    :return:
    """

    # If not library, we grab the metadata anyway since we merge it on the other data types.
    return pd.DataFrame(
        query_dynamodb_table(
            job_id,
            context
        )
    )


def get_portal_run_id_from_relative_path(relative_path: Path) -> str:
    # Get key relative to portal run id
    return next(filter(
        lambda part_iter_: PORTAL_REGEX.match(part_iter_) is not None,
        relative_path.parts
    ))


def get_instrument_run_id_from_relative_path(relative_path: Path) -> str:
    # Instrument run id will be the second part of the relative path
    return relative_path.parts[1]


def handler(event, context) -> dict[str, str]:
    """
    Given the following inputs:
      * jobId
      * pushLocation

    Generate the following outputs:
      * destinationAndSourceUriMappingsList

    This performs the following:
    * Queries the files in the dynamodb database for this packaging job id
    * For each subfolder, it generates a destination and source uri mapping based on a common parent location
    * Returns the destination and source uri mappings list for each folder
    :param event:
    :param context:
    :return:
    """

    # Extract the jobId and pushLocation from the event
    job_id: str = event.get("packagingJobId")
    push_location: str = event.get("pushLocation")
    count_only: bool = event.get("countOnly", False)
    pagination_index: int = event.get("paginationIndex", None)
    s3_steps_copy_bucket: str = event.get("s3StepsCopyBucket", None)
    s3_steps_copy_key: str = event.get("s3StepsCopyKey", None)

    # Check if the jobId and pushLocation are provided
    if not job_id or not push_location:
        raise ValueError("jobId and pushLocation are required")

    # Confirm that paginationIndex is specified if countOnly is false
    if not count_only and pagination_index is None:
        raise ValueError("paginationIndex is required when countOnly is false")

    # Get the push location as a url object
    push_location_url_obj = urlparse(push_location)

    # Confirm the push location is a valid s3 url
    if push_location_url_obj.scheme != "s3":
        raise ValueError(f"Error: pushLocation must be a valid s3 url, {push_location} does not start with s3://")
    if not push_location_url_obj.netloc:
        raise ValueError(f"Error: pushLocation must be a valid s3 url, {push_location} does not have a bucket name")
    if not push_location_url_obj.path:
        raise ValueError(f"Error: pushLocation must be a valid s3 url, {push_location} does not have a path")

    # Get the data from DynamoDB
    data_df = get_data_from_dynamodb(
        job_id=job_id,
        context="file"
    )

    # Calculate the relative parent path for all source files
    # Get the portal run id by the relative path (for secondary analysis)
    data_df["portalRunId"] = data_df.apply(
        lambda row_iter_: (
            get_portal_run_id_from_relative_path(Path(row_iter_['relativePath']).parent)
            if row_iter_['relativePath'].startswith("secondary-analysis")
            else None
        ),
        axis='columns'
    )

    data_df["instrumentRunId"] = data_df.apply(
        lambda row_iter_: (
            get_instrument_run_id_from_relative_path(Path(row_iter_['relativePath']).parent)
            if row_iter_['relativePath'].startswith("fastq")
            else None
        ),
        axis='columns'
    )

    # Group by parent path and collect the relative paths
    secondary_data_df = data_df.query("~portalRunId.isnull()", engine='python')
    primary_data_df = data_df.query("~instrumentRunId.isnull()", engine='python')

    # Get the number of primary data folders
    items_list = (
        sorted(primary_data_df['instrumentRunId'].unique().tolist()) +
        sorted(secondary_data_df['portalRunId'].unique().tolist())
    )

    # If count only is true, return the count of the destination and source uri mappings list
    if count_only:
        return {
            "listCount": len(items_list)
        }

    # Okay we mean business and were uploading
    s3_client: S3Client = boto3.client("s3")

    if pagination_index < len(sorted(primary_data_df['instrumentRunId'].unique().tolist())):
        instrument_run_id = sorted(primary_data_df['instrumentRunId'].unique().tolist())[pagination_index]
        data_df = primary_data_df.query("instrumentRunId == @instrument_run_id")
        destination_folder_key = Path(f"fastq/{instrument_run_id}")
        # Get the relative path parent for each file
        data_df["relativeFolderKey"] = data_df['relativePath'].apply(
            lambda relative_path_iter_: str(Path(relative_path_iter_).parent.relative_to(destination_folder_key)) + "/"
        )
    else:
        pagination_index -= len(sorted(primary_data_df['instrumentRunId'].unique().tolist()))
        portal_run_id = sorted(secondary_data_df['portalRunId'].unique().tolist())[pagination_index]
        data_df = secondary_data_df.query("portalRunId == @portal_run_id")
        destination_folder_key = Path(f"secondary-analysis/{portal_run_id}")
        # Get the relative path parent for each file
        data_df["relativeFolderKey"] = data_df['relativePath'].apply(
            lambda relative_path_iter_: str(Path(relative_path_iter_).parent.relative_to(destination_folder_key)) + "/"
        )

    # Now generate the jsonl data
    with NamedTemporaryFile(suffix="*.jsonl") as temp_file:
        data_df[[
            "bucket",
            "key",
            "relativeFolderKey"
        ]].rename(
            columns={
                "bucket": "sourceBucket",
                "key": "sourceKey",
                "relativeFolderKey": "destinationRelativeFolderKey"
            }
        ).to_json(
            temp_file,
            orient="records",
            lines=True
        )

        temp_file.flush()

        # Upload the file to S3
        s3_client.upload_file(
            Bucket=s3_steps_copy_bucket,
            Key=s3_steps_copy_key,
            Filename=temp_file.name
        )

    return {
        "destinationBucket": push_location_url_obj.netloc,
        "destinationFolderKey": str(Path(push_location_url_obj.path.lstrip('/')).joinpath(destination_folder_key)) + "/",
    }
