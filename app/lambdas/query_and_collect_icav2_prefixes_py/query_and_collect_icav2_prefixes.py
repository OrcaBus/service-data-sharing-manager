#!/usr/bin/env python3

"""
Given a job id, and a location uri:

- Query the DynamoDB table to get the data
- Collect the destination and source uri mappings
"""
from typing import List, Dict

import pandas as pd

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
    TODO
    :param event:
    :param context:
    :return:
    """
    # Get the job id from the event
    job_id = event.get("jobId", None)
    push_location = event.get("pushLocation", None)

    # Initialize the destination and source uri mappings list
    destination_and_source_uri_mappings_list: List[Dict[str, str]] = []

    # Get the data from DynamoDB
    data_df = get_data_from_dynamodb(
        job_id=job_id,
        context="file"
    )
