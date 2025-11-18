#!/usr/bin/env python3

"""
Get fastqs in packaging job by packaging job id.
We assume that fastqs are stored in filemanager monitored location.
"""

# Standard imports
from pathlib import Path
import pandas as pd
from urllib.parse import urlparse, urlunparse

# Layered imports
from data_sharing_tools.utils.dynamodb_helpers import query_dynamodb_table


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


def handler(event, context):
    """
    Get fastqs in packaging job by packaging job id.
    :param event:
    :param context:
    :return:
    """

    # Inputs
    packaging_job_id = event["packagingJobId"]
    push_location = event["pushLocation"]
    count_only = event.get("countOnly", False)
    pagination_index = event.get("paginationIndex", None)

    # Check if the jobId and pushLocation are provided
    if not packaging_job_id or not push_location:
        raise ValueError("jobId and pushLocation are required")

    # Check one and only one of count_only and pagination_index are provided
    if count_only and pagination_index is not None:
        raise ValueError("Only one of countOnly and paginationIndex can be provided")
    if not count_only and pagination_index is None:
        raise ValueError("One of countOnly or paginationIndex must be provided")

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
        job_id=packaging_job_id,
        context="file"
    )

    # Filter out non fastq files
    data_df = (
        data_df.query(
        "key.str.endswith('.fastq.gz') or key.str.endswith('.fastq.ora')",
        engine="python"
        )
        .sort_values(by="key")
        .reset_index(drop=True)
    )

    # If count only, return the count of fastqs
    if count_only:
        return {
            "listCount": data_df.shape[0]
        }

    # Filter to pagination tuple
    data_df = data_df.loc[pagination_index[0]:pagination_index[1]]

    return {
        "destinationUriAndIngestIdMappingsList": list(map(
            lambda row: {
                "destinationUri": str(urlunparse((
                    push_location_url_obj.scheme,
                    push_location_url_obj.netloc,
                    str(Path(push_location_url_obj.path) / row["relativePath"]),
                    None, None, None
                ))),
                "ingestId": row["ingestId"]
            },
            data_df.to_dict(orient="records")
        ))
    }
