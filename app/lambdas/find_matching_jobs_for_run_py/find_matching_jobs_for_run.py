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
    for the given list of library_ids .

    Args:
        library_ids (List[str]): List of library IDs to query.

    Returns:
        pd.DataFrame: DataFrame with columns: library_id, owner_id, project_id.
    """
    # Prepare SQL IN clause for the list of library IDs
    library_ids_in = ", ".join([f"'{lib_id}'" for lib_id in library_ids])
    sql = f"""
        SELECT library_id, owner_id, project_id
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


    # Iterate over job definitions and check for matches with the libraries in the instrument run.
    # If a job definition is enabled and has matching libraries based on owner and project criteria,
    # add it to the list of jobs to be triggered downstream.
    job_list = []

    for _, job in job_definitions_df.iterrows():
        if not job["enabled"]:
            continue

        job_name = job["jobName"]

        matching_libs = lib_owner_proj_df[
            (lib_owner_proj_df["owner_id"] == job["ownerId"]) &
            (lib_owner_proj_df["project_id"].isin(job["projectIdList"]))
        ]["library_id"].unique().tolist()

        if not matching_libs:
            continue

        job_list.append({
            "packageName": f"{job_name}-{instrument_run_id}",
            "packageRequest": {
                "libraryIdList": matching_libs,
                "dataTypeList": job["dataTypeList"],
                "instrumentRunIdList": [instrument_run_id],
            },
            "shareDestination": job["shareDestination"],
        })


    return {
        "matchingJobsFound": bool(job_list),
        "jobList": job_list
    }
