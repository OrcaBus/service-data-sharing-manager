#!/usr/bin/env python3

"""
Given a job id, and a location uri:

- Query the DynamoDB table to get the data
- Collect the destination and source uri mappings
"""

# Standard imports
from typing import List, Dict
import pandas as pd
from urllib.parse import urlparse
from pathlib import Path
import re

# Layer imports
from data_sharing_tools.utils.dynamodb_helpers import query_dynamodb_table


# Globals
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



def handler(event, context):
    """
    :param event:
    :param context:
    :return:
    """
    # Get the job id from the event
    # Extract the jobId and pushLocation from the event
    job_id = event.get("packagingJobId")
    push_location = event.get("pushLocation")
    count_only = event.get("countOnly", False)
    pagination_index = event.get("paginationIndex", None)

    # Check if the jobId and pushLocation are provided
    if not job_id or not push_location:
        raise ValueError("jobId and pushLocation are required")

    # Get the push location as a url object
    push_location_url_obj = urlparse(push_location)

    # Confirm the push location is a valid icav2 url
    if push_location_url_obj.scheme != "icav2":
        raise ValueError(f"Error: pushLocation must be a valid icav2 url, {push_location} does not start with icav2://")
    if not push_location_url_obj.netloc:
        raise ValueError(f"Error: pushLocation must be a valid icav2 url, {push_location} does not have a project id")
    if not push_location_url_obj.path:
        raise ValueError(f"Error: pushLocation must be a valid icav2 url, {push_location} does not have a path")

    # Initialize the destination and source uri mappings list
    destination_and_source_uri_mappings_list: List[Dict[str, str]] = []

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

    if pagination_index < len(sorted(primary_data_df['instrumentRunId'].unique().tolist())):
        instrument_run_id = sorted(primary_data_df['instrumentRunId'].unique().tolist())[pagination_index]
        data_df = primary_data_df.query("instrumentRunId == @instrument_run_id")
        # Get the relative path parent for each file
        data_df["relativeParent"] = data_df['relativePath'].apply(
            lambda relative_path_iter_: str(Path(relative_path_iter_).parent) + "/"
        )
    else:
        pagination_index -= len(sorted(primary_data_df['instrumentRunId'].unique().tolist()))
        portal_run_id = sorted(secondary_data_df['portalRunId'].unique().tolist())[pagination_index]
        data_df = secondary_data_df.query("portalRunId == @portal_run_id")
        # Get the relative path parent for each file
        data_df["relativeParent"] = data_df['relativePath'].apply(
            lambda relative_path_iter_: str(Path(relative_path_iter_).parent) + "/"
        )


    # Groupby parent paths
    for parent_path, parent_path_group_df in data_df.groupby("relativeParent"):
        # Get the destination uri
        destination_uri = f"{push_location_url_obj.scheme}://{push_location_url_obj.netloc}/{str(Path(push_location_url_obj.path).joinpath(parent_path)).lstrip("/")}/"

        # Get the source uris
        source_uris = parent_path_group_df[[
            'bucket',
            'key'
        ]].apply(
            lambda row_iter_: f"s3://{row_iter_['bucket']}/{row_iter_['key']}",
            axis='columns'
        ).tolist()

        # Append the destination and source uri mappings to the list
        destination_and_source_uri_mappings_list.append({
            "destinationUri": destination_uri,
            "sourceUriList": source_uris
        })

    return {
        "destinationAndSourceUriMappingsList": destination_and_source_uri_mappings_list,
    }

# if __name__ == "__main__":
#     from os import environ
#
#     environ['AWS_PROFILE'] = 'umccr-production'
#     environ['PACKAGING_TABLE_NAME'] = 'DataSharingPackagingLookupTable'
#     environ['CONTENT_INDEX_NAME'] = 'content'
#     environ['ICAV2_ACCESS_TOKEN_SECRET_ID'] = 'ICAv2JWTKey-umccr-prod-service-production'
#
#     print(
#         handler(
#             {
#                 "packagingJobId": "pkg.01K23Y6V4RNE15G3K0DN8XRDYQ",
#                 "pushLocation": "icav2://wgs_data1/2025-08-18-data-transfer/",
#                 "countOnly": True,
#             },
#             None
#         )
#     )
