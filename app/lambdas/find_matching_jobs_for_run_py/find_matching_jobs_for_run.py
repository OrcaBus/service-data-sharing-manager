import typing
from typing import List, Tuple
import json
import pandas as pd
import boto3
from orcabus_api_tools.sequence import get_libraries_from_instrument_run_id
from orcabus_api_tools.mart import run_athena_sql_query


if typing.TYPE_CHECKING:
    from mypy_boto3_s3 import S3Client


def get_s3_client() -> 'S3Client':
    return boto3.client('s3')



def load_job_definitions_from_s3(bucket: str, key: str) -> pd.DataFrame:
    """
    Reads the jobs configuration JSON file from S3 and
    returns as a Pandas DataFrame.Each row corresponds
    to one job definition from the JSON array.
    """
    obj =  get_s3_client().get_object(Bucket=bucket, Key=key)
    content = obj['Body'].read()  # bytes
    json_data = json.loads(content)
    return pd.DataFrame(json_data)



def get_owner_id_and_project_ids_for_library_ids(library_ids: List[str]) -> pd.DataFrame:
    """
    Query the mart.lims to retrieve owner_id and project_id
    for the given list of library_ids.

    Args:
        library_ids (List[str]): List of library IDs to query.

    Returns:
        pd.DataFrame: DataFrame with columns: libraryId, ownerId, projectId.
    """
    library_ids_in = ", ".join([f"'{lib_id}'" for lib_id in library_ids])
    sql = f"""
        SELECT library_id as libraryId, owner_id as ownerId, project_id as projectId
        FROM lims
        WHERE library_id IN ({library_ids_in})
    """
    result_df = run_athena_sql_query(sql)
    return result_df


def handler(event, context):
    """
    Check if there are libraries matching the owner and project criteria
    specified in any of the job definitions.
    """
    instrument_run_id = event["instrumentRunId"]
    jobs_config_bucket = event["jobsConfigBucket"]
    jobs_config_key = event["jobsConfigKey"]


    # Libraries included in the instrument run and their associated owner and project IDs from mart.lims
    lib_ids_in_run = get_libraries_from_instrument_run_id(instrument_run_id)
    lib_owner_proj_df = get_owner_id_and_project_ids_for_library_ids(lib_ids_in_run)


    #  Job definitions from the jobs definitions JSON file in S3.
    job_definitions_df = load_job_definitions_from_s3(jobs_config_bucket, jobs_config_key)


    # Convert projectIdList to projectid
    job_definitions_df = (
    job_definitions_df.explode("projectIdList").rename(
        columns={
        "projectIdList": "projectId"
        }
    )
    )

    # Merge dataframes on ownerId and projectId
    merged_df = pd.merge(
    lib_owner_proj_df,
    job_definitions_df,
    how='inner',  # Keep only matching in both tables
    on=['ownerId', 'projectId'],  # Must match both ownerId and projectId
    )


    job_list = [
        {
            "packageName": merged_df_group_iter_['jobName'].unique().item(),
            "packageRequest": {
                "libraryIdList": merged_df_group_iter_['libraryId'].tolist(),
                "dataTypeList": merged_df_group_iter_["dataTypeList"].tolist(),
                "instrumentRunIdList": [instrument_run_id],
            },
        }
        for ownerId, merged_df_group_iter_ in merged_df.groupby('ownerId')
    ]



    return {
        "matchingJobsFound": bool(job_list),
        "jobList": job_list
    }
