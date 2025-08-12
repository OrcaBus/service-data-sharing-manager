#!/usr/bin/env python3

from orcabus_api_tools.data_sharing import get_data_sharing_url
from orcabus_api_tools.utils.requests_helpers import get_request



# This implemetation is weak as dependent on the job ID format.
def _infer_type_from_id(job_id: str) -> str | None:
    """
    Best-effort inference from known prefixes.
    Extend this map if you introduce new job types/prefixes.
    """
    if job_id.startswith(("psh.")):
        return 'push'
    if job_id.startswith(("pkg.")):
        return 'package'
    return None



def handler(event, context=None):
    """
    Generic status checker for OrcaBus Data Sharing jobs.
    Works with both packaging and push jobs.

    event must contain:
      - type: str ('package' or 'push')
      - id: str (job ID)
    """
    job_id = event["id"]
    job_type = _infer_type_from_id(job_id)

    status = get_request(
        url=get_data_sharing_url(f"api/v1/{job_type}/{job_id}")
    )["status"]

    return status
