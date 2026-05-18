"""

Given the following inputs:

workingCsvBucket
workingCsvKey

Pull in the CSV shown in the format below

# FAIL Example

OBJECTNAME,TRANSFERSTATUS,MBPERSEC,MESSAGE,DESTINATION,BYTESTRANSFERRED,ELAPSEDSECONDS
L2300950_S11_L002_R1_001.fastq.ora,ERROR,0,exit of copy with code 1 but no JSON statistics block generated,s3://umccr-test-destination-prod/alexiswl/L2300950/outputs/fastq-only-test/fastq/230629_A01052_0154_BH7WF5DSX7/Lane_2/L2300950/L2300950_S11_L002_R1_001.fastq.ora,0,0
L2300950_S11_L002_R2_001.fastq.ora,ERROR,0,exit of copy with code 1 but no JSON statistics block generated,s3://umccr-test-destination-prod/alexiswl/L2300950/outputs/fastq-only-test/fastq/230629_A01052_0154_BH7WF5DSX7/Lane_2/L2300950/L2300950_S11_L002_R2_001.fastq.ora,0,0

# SUCCEEDED Example
OBJECTNAME,TRANSFERSTATUS,MBPERSEC,MESSAGE,DESTINATION,BYTESTRANSFERRED,ELAPSEDSECONDS
L2300950_S11_L002_R1_001.fastq.ora,COPIED,99.0337683879862,,s3://umccr-test-destination-prod/alexiswl/L2300950/outputs/fastq-only-test/fastq/230629_A01052_0154_BH7WF5DSX7/Lane_2/L2300950/L2300950_S11_L002_R1_001.fastq.ora,11088024489,106.775338826
L2300950_S11_L002_R2_001.fastq.ora,COPIED,79.82039818880112,,s3://umccr-test-destination-prod/alexiswl/L2300950/outputs/fastq-only-test/fastq/230629_A01052_0154_BH7WF5DSX7/Lane_2/L2300950/L2300950_S11_L002_R2_001.fastq.ora,15525787883,185.498262123

# Then return
{
  "hasError": bool,
  "errorMessage": str | None
}

"""

# Standard imports
import pandas as pd
import typing
from typing import Dict, Union, Optional
import boto3
from tempfile import NamedTemporaryFile

if typing.TYPE_CHECKING:
    from mypy_boto3_s3 import S3Client


def get_s3_client() -> 'S3Client':
    return boto3.client('s3')


def handler(event, context) -> Dict[str, Union[bool, Optional[str]]]:
    """
    Pull in inputs

    Download and extract csv

    Determine if all files have been successfully copied over
    """

    # Get the inputs
    working_csv_bucket = event["workingCsvBucket"]
    working_csv_key = event["workingCsvKey"]

    # Pull in the csv from s3
    with NamedTemporaryFile(suffix='.csv') as csv_file_h:
        # Download file
        get_s3_client().download_file(
            Bucket=working_csv_bucket,
            Key=working_csv_key,
            Filename=csv_file_h.name
        )

        # Flush
        csv_file_h.flush()

        # Read from file path
        df = pd.read_csv(csv_file_h.name, header=0)

    # Check dataframe is not empty
    if df.empty:
        raise ValueError("Could not download or read csv file")

    # Find failed copies
    failed_df = df.query("TRANSFERSTATUS != 'COPIED'")

    if not failed_df.empty:
        return {
            "hasError": True,
            "errorMessage": f"{failed_df.shape[0]} files failed to copy, see s3://{working_csv_bucket}/{working_csv_key} for more information",
        }

    return {
        "hasError": False,
        "errorMessage": None,
    }
