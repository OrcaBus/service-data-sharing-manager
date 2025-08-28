#!/usr/bin/env python
import json
import os
from typing import List, Dict



# ---- This is a fake “DB” to be implemente later on in a proper db infrastructure ----
# Tothill--> CUP, LAyton --> VENTURE
JOBS: List[Dict] = [
    {
        "jobId": "job-1",
        "enabled": True,
        "packageRequest": {
            "dataTypeList": ["fastq"],
            "instrumentRunIdList": ["241024_A00130_0336_BHW7MVDSXC"],
            "projectIdList": ["VENTURE"],
        },
        "shareDestination": "s3://umccr-temp-dev/fji/VENTURE/",
    },
    {
        "jobId": "job-2",
        "enabled": True,
        "packageRequest": {
            "dataTypeList": ["fastq"],
            "instrumentRunIdList": ["241024_A00130_0336_BHW7MVDSXC"],
            "projectIdList": ["CUP"],
        },
        "shareDestination": "s3://umccr-temp-dev/fji/CUP/",
    },

]
# ---- End of fake “DB” ----



def _package_name(instrument_run_id: str, job_id: str) -> str:

    template = "autosharing-${instrumentRunId}-${jobId}"

    return (
        template
        .replace("${instrumentRunId}", instrument_run_id)
        .replace("${jobId}", job_id)
    )


def handler(event, context):
    instrument_run_id = event["detail"]["instrumentRunId"]

    plans: List[Dict] = []
    for job in JOBS:
        if not job.get("enabled", False):
            continue

        plans.append({
            "packageName": _package_name(instrument_run_id, job["jobId"]),
            "packageRequest": job["packageRequest"],
            "shareDestination": job["shareDestination"],
        })

    return {"plans": plans}
