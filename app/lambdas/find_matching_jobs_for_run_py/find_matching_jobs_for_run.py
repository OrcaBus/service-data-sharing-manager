from os import environ
from io import BytesIO
from typing import List, Tuple
from urllib.parse import urlparse
from time import sleep
import json
import pandas as pd
import boto3
from orcabus_api_tools.sequence import get_libraries_from_instrument_run_id


# ========================= COMMON ANCILLARY FUNCTIONS =========================
# These functions are already used in other lambdas (get_workflow_runs_for_portal_run
# and list_portal_run_ids_in_library) and are general enough for moving them into a
#  common module (?)


WORKGROUP_ENV_VAR = 'ATHENA_WORKGROUP_NAME'
DATA_SOURCE_ENV_VAR = 'ATHENA_DATASOURCE_NAME'
DATABASE_ENV_VAR = 'ATHENA_DATABASE_NAME'


def get_athena_client():
    return boto3.client('athena')


def get_s3_client():
    return boto3.client('s3')

def get_bucket_key_tuple_from_s3_uri(s3_uri: str) -> Tuple[str, str]:
    urlobj = urlparse(s3_uri)
    return urlobj.netloc, urlobj.path.lstrip('/')


def run_athena_sql_query(sql_query: str) -> pd.DataFrame:
    athena_query_execution_id = get_athena_client().start_query_execution(
        QueryString=sql_query,
        QueryExecutionContext={
            "Database": environ[DATABASE_ENV_VAR],
            "Catalog": environ[DATA_SOURCE_ENV_VAR]
        },
        WorkGroup=environ[WORKGROUP_ENV_VAR],
    )['QueryExecutionId']

    while True:
        status = get_athena_client().get_query_execution(
            QueryExecutionId=athena_query_execution_id
        )['QueryExecution']['Status']['State']

        if status in ['SUCCEEDED', 'FAILED', 'CANCELLED']:
            break

        sleep(5)

    if status in ['FAILED', 'CANCELLED']:
        raise RuntimeError(f"Query failed: {status}")

    # Get the results
    result_location = get_athena_client().get_query_execution(
        QueryExecutionId=athena_query_execution_id
    )['QueryExecution']['ResultConfiguration']['OutputLocation']

    bucket, key = get_bucket_key_tuple_from_s3_uri(result_location)

    return pd.read_csv(
        BytesIO(
            get_s3_client().get_object(
                Bucket=bucket,
                Key=key
            )['Body'].read()
        ),
        dtype={
            "portalRunId": "object"
        }
    )

# ==============================================================================


def load_job_definitions_from_s3(bucket, key):
    """
    Reads the jobs configuration JSON file from S3 and
    returns as a Pandas DataFrame with 'jobName' as index.
    """
    s3 = boto3.client("s3")
    obj = s3.get_object(Bucket=bucket, Key=key)
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
            },
            "shareDestination": job["shareDestination"],
        })


    return {
        "matchingJobsFound": bool(job_list),
        "jobList": job_list
    }
