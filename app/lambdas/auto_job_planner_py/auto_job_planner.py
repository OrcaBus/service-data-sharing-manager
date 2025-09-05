#!/usr/bin/env python
import json
import os
from typing import List, Dict
import boto3

SSM = boto3.client("ssm")
SSM_JOBS_PREFIX = os.environ.get("SSM_JOBS_PREFIX", "/umccr/data-sharing/auto-package-push")

def _iter_parameters_by_path(prefix: str):
    """Yield all SSM parameters under prefix (handles pagination)."""
    next_token = None
    while True:
        kwargs = dict(Path=prefix, Recursive=True, WithDecryption=True)
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
        try:
            job = json.loads(param["Value"])
            # minimal validation
            if not job.get("enabled", False):
                continue
            for key in ("name", "projectId", "shareDestination"):
                if key not in job:
                    raise ValueError(f"Missing '{key}' in job from {param['Name']}")
            jobs.append(job)
        except Exception as e:
            # Keep going if one param is malformed
            print(f"[WARN] Skipping param {param.get('Name')}: {e}")
    # deterministic order
    jobs.sort(key=lambda j: j["name"])
    return jobs

def _package_name(instrument_run_id: str, job_name: str) -> str:
    return f"autosharing-{instrument_run_id}-{job_name}"

def handler(event, context):
    # Expect instrumentRunId from the event (as in your SFN)
    instrument_run_id = event["detail"]["instrumentRunId"]

    jobs = _load_jobs_from_ssm(SSM_JOBS_PREFIX)

    plans: List[Dict] = []
    for job in jobs:
        plans.append({
            "packageName": _package_name(instrument_run_id, job["name"]),
            "packageRequest": {
                # simple default; expand later as you add options
                "dataTypeList": ["fastq"],
                "projectIdList": [job["projectId"]],
            },
            "shareDestination": job["shareDestination"],
        })

    return {"plans": plans}
