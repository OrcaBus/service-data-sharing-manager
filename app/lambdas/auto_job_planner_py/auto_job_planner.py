#!/usr/bin/env python
import json
import os
from typing import List, Dict
import boto3

SSM = boto3.client("ssm")
SSM_JOBS_PREFIX = os.environ.get("SSM_JOBS_PREFIX", "/umccr/data-sharing/auto-package-push").rstrip("/")

def _iter_parameters_by_path(prefix: str):
    next_token = None
    while True:
        kwargs = dict(Path=prefix, Recursive=True, WithDecryption=False)
        if next_token:
            kwargs["NextToken"] = next_token
        resp = SSM.get_parameters_by_path(**kwargs)
        for p in resp.get("Parameters", []):
            yield p
        next_token = resp.get("NextToken")
        if not next_token:
            break

def _load_jobs_from_ssm(prefix: str) -> List[Dict]:
    jobs: List[Dict] = []
    for param in _iter_parameters_by_path(prefix):
        job = json.loads(param["Value"])
        jobs.append(job)

    # deterministic ordering
    jobs.sort(key=lambda j: j["name"])
    return jobs

def _package_name(instrument_run_id: str, job_name: str) -> str:
    return f"autosharing-{instrument_run_id}-{job_name}"

def handler(event, context):
    instrument_run_id = event["detail"]["instrumentRunId"]

    jobs = _load_jobs_from_ssm(SSM_JOBS_PREFIX)

    plans: List[Dict] = []
    for job in jobs:
        project_id = job["projectId"]

        plans.append({
            "packageName": _package_name(instrument_run_id, job["name"]),
            "packageRequest": {
                "instrumentRunIdList": [instrument_run_id],
                "dataTypeList": ["fastq"],
                "projectIdList": [project_id],
            },
            "shareDestination": job["shareDestination"],
        })

    return {"plans": plans}
