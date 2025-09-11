#!/usr/bin/env python3
from orcabus_api_tools.data_sharing import get_push_job
from orcabus_api_tools.data_sharing import get_package



def handler(event, context=None):
    """
    Generic status checker for Data Sharing jobs.
    Works with both packaging and push jobs.

    event must contain:
      - id: str (job ID)
    """
    job_id = event["id"]

    if job_id.startswith(("psh.")):
        status = get_push_job(job_id)["status"]
    if job_id.startswith(("pkg.")):
        status = get_package(job_id)["status"]

    return status
