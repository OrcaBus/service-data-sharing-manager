
from orcabus_api_tools.sequence import get_libraries_from_instrument_run_id


from os import environ
import pandas as pd
from io import BytesIO
from typing import Dict, List, Tuple
import boto3
from urllib.parse import urlparse
from time import sleep
import typing
import json


def load_job_definitions_from_s3(bucket, key):
    """
    Reads the jobs configuration JSON file from S3 and
    returns as a Pandas DataFrame with 'jobName' as index.
    """
    s3 = boto3.client("s3")
    obj = s3.get_object(Bucket=bucket, Key=key)
    content = obj['Body'].read()  # bytes
    json_data = json.loads(content)
    return pd.DataFrame(json_data).set_index("jobName")


# ========================= ANCILLARY FUNCTIONS =========================

# Data sharing layer
if typing.TYPE_CHECKING:
    from mypy_boto3_athena import AthenaClient
    from mypy_boto3_s3 import S3Client



# Globals
# ATHENA
WORKGROUP_ENV_VAR = 'ATHENA_WORKGROUP_NAME'
DATA_SOURCE_ENV_VAR = 'ATHENA_DATASOURCE_NAME'
DATABASE_ENV_VAR = 'ATHENA_DATABASE_NAME'




def get_athena_client() -> 'AthenaClient':
    return boto3.client('athena')


def get_bucket_key_tuple_from_s3_uri(s3_uri: str) -> Tuple[str, str]:
    urlobj = urlparse(s3_uri)
    return urlobj.netloc, urlobj.path.lstrip('/')


def get_s3_client() -> 'S3Client':
    return boto3.client('s3')

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



def get_owner_id_and_project_ids_for_library_ids(library_ids: List[str]) -> pd.DataFrame:
    """
    Query Athena to retrieve owner_id and project_id
    for the provided list of library IDs (plus the provided library_id).

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
# ========================= END ANCILLARY FUNCTIONS =========================


def handler(event, context):
    """
    Check if any requested projects are found in the specified instrument run.
    """
    instrument_run_id = event["instrumentRunId"]
    jobs_config_bucket = event["jobsConfigBucket"]
    jobs_config_key = event["jobsConfigKey"]


    # Libraries includede in the instrument run and their associated owner and project IDs
    # lib_ids_in_run = get_libraries_from_instrument_run_id(instrument_run_id)
    # lib_owner_proj_df = get_owner_id_and_project_ids_for_library_ids(lib_ids_in_run)



    # =============================== TESTING ONLY: HARDCODED LIBRARY-OWNER-PROJECT MAPPING ===============================
    lib_owner_proj_df = pd.DataFrame([
        {"library_id": "L2300943", "owner_id": "UMCCR", "project_id": "Validation"},
        {"library_id": "L2300950", "owner_id": "UMCCR", "project_id": "Validation"},
        {"library_id": "L2301217", "owner_id": "UMCCR", "project_id": "Validation"},
        {"library_id": "L2301218", "owner_id": "UMCCR", "project_id": "Validation"},
        {"library_id": "L2401531", "owner_id": "UMCCR", "project_id": "Control"},
        {"library_id": "L2500384", "owner_id": "UMCCR", "project_id": "Control"},
        {"library_id": "L2500568", "owner_id": "UMCCR", "project_id": "Control"}
    ])

    # =============================================== END TESTING ONLY ===============================================

    job_definitions_df = load_job_definitions_from_s3(jobs_config_bucket, jobs_config_key)

    # Check the libreries in the run match owers and projects
    # in the job definitions

    job_library_map = {}

    for job_name, job in job_definitions_df.iterrows():
        owner = job['ownerId']
        project_ids = set(job['projectIdList'])
        matching_libs = lib_owner_proj_df[
            (lib_owner_proj_df['owner_id'] == owner) &
            (lib_owner_proj_df['project_id'].isin(project_ids))
        ]['library_id'].tolist()
        if matching_libs:  # Only add if list is not emptys
            job_library_map[job_name] = matching_libs


    # Generates the list of jobs (provided they are set as enable)

    job_list = []
    for job_name in job_library_map:

        if job_definitions_df.loc[job_name, 'enabled']:

            package_name = job_name + "-" + instrument_run_id
            package_request = {
                "libraryList": job_library_map[job_name],
                "dataTypeList": job_definitions_df.loc[job_name, 'dataTypeList']
            }
            share_destination = job_definitions_df.loc[job_name, 'shareDestination']

            job_list.append({
                "packageName": package_name,
                "packageRequest": package_request,
                "shareDestination": share_destination
            })


    return {
        "matchingJobsFound": bool(job_list),
        "jobList": job_list
    }
