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

def _load_job_configs_from_ssm(prefix: str) -> List[Dict]:
    job_configs: List[Dict] = []
    for param in _iter_parameters_by_path(prefix):
        cfg = json.loads(param["Value"])
        job_configs.append(cfg)

    # deterministic sorting
    job_configs.sort(key=lambda c: c["jobName"])
    return job_configs

def _package_name(instrument_run_id: str, job_name: str) -> str:
    return f"autosharing-{job_name}-{instrument_run_id}"

def handler(event, context):
    instrument_run_id = event["instrumentRunId"]

    job_configs = _load_job_configs_from_ssm(SSM_JOBS_PREFIX)

    plans: List[Dict] = []
    for job_config in job_configs:

        package_name = _package_name(instrument_run_id, job_config["jobName"])
        project_id = job_config["projectId"]
        share_destination = job_config["shareDestination"]

        plans.append({
            "packageName": package_name,
            "packageRequest": {
                "instrumentRunIdList": [instrument_run_id],
                "dataTypeList": ["fastq"],
                "projectIdList": [project_id],
            },
            "shareDestination": share_destination,
        })

    return {"plans": plans}
