#!/usr/bin/env python
import json
import os
from typing import List, Dict


from orcabus_api_tools.sequence import get_libraries_from_instrument_run_id
from orcabus_api_tools.metadata import (get_library_from_library_id,
                                        get_library_orcabus_id_from_library_id,
                                        get_project_orcabus_id_from_project_id
                                        )

from orcabus_api_tools.utils.requests_helpers import get_request





# ---- This is a fake “DB” to be implemente later on in a proper db infrastructure ----

JOBS: List[Dict] = [
    {
        "jobId": "job-1",
        "enabled": True,
        "filter": {
            "projectIdIn": "CUP",
            "contactIdIn": "Tothill",
            "dataTypeList": ["fastq"],
        },
        "destination": {"type": "s3", "uri": "s3://umccr-temp-dev/fji/Tothill/CUP/"},
        "packageNameTemplate": "auto-${instrumentRunId}-${jobId}",
    },
    {
        "jobId": "job-2",
        "enabled": True,
        "filter": {
            "projectIdIn": "VENTURE",
            "contactIdIn": "LAyton",
            "dataTypeList": ["fastq"],
        },
        "destination": {"type": "s3", "uri": "s3://umccr-temp-dev/fji/LAyton/VENTURE/"},
        "packageNameTemplate": "auto-${instrumentRunId}-${jobId}",
    },
]
# ---- End of fake “DB” ----





# Utility functions to get project and contact IDs from library and project IDs (potentially
# to be implemented in orcabus_api_tools/metadata/library_helpers.py

)
def get_project_ids_from_library_id(library_id: str) -> list[str]:
    library_orcabus_id = get_library_orcabus_id_from_library_id(library_id)
    library_url = f"https://metadata.dev.umccr.org/api/v1/library/{library_orcabus_id}/" # TODO: Remove hardcoding here
    project_set = get_request(url=library_url)['projectSet']

    project_ids= []

    for project in project_set:
        project_ids.append(project["projectId"])

    return project_ids


def get_contact_ids_from_project_id(project_id: str) -> list[str]:
    project_orcabus_id = get_project_orcabus_id_from_project_id(project_id)
    project_url = f"https://metadata.dev.umccr.org/api/v1/project/{project_orcabus_id}/" # TODO: Remove hardcoding here
    contact_set = get_request(url=project_url)['contactSet']

    contact_ids= []

    for contact in contact_set:
        contact_ids.append(contact["contactId"])

    return contact_ids

# --- End of utility functions for library_helpers.py --




def _package_name(template: str, instrument_run_id: str, job_id: str) -> str:
    # minimal templating
    return (
        template
        .replace("${instrumentRunId}", instrument_run_id)
        .replace("${jobId}", job_id)
    )


def handler(event, context):
    # Get EventBridge minimal event
    instrument_run_id = event["detail"]["instrumentRunId"]

    # 1) Get all libraries once
    library_id_list = sorted(set(get_libraries_from_instrument_run_id(instrument_run_id)))

    # 2) Filter and build plans (one per job with matches). Filter may need to happend outsithe this lambda.
    plans: List[Dict] = []
    for job in JOBS:
        if not job.get("enabled", False):
            continue

        filt = job["filter"]
        projectId = filt.get("projectIdIn")
        contactId = filt.get("contactIdIn")
        want_dtypes  = filt.get("dataTypeList", [])

        sharing_library_list = []

        contacts_for_project = set(get_contact_ids_from_project_id(projectId)) if projectId else set()

        for library_id in library_id_list:
            project_ids = get_project_ids_from_library_id(library_id)

            if projectId and projectId not in project_ids:
                continue

            if contactId:
                if projectId:
                    if contactId not in contacts_for_project:
                        continue
                else:
                    has_contact = False
                    for pid in project_ids:
                        if contactId in get_contact_ids_from_project_id(pid):
                            has_contact = True
                            break
                    if not has_contact:
                        continue

            sharing_library_list.append(library_id)


        if not sharing_library_list:
            continue

        plans.append({
            "packageName": _package_name(job["packageNameTemplate"], instrument_run_id, job["jobId"]),
            "packageRequest": {
                "libraryIdList": sharing_library_list,
                "dataTypeList": want_dtypes,
            },
            "shareDestination": job["destination"]["uri"],
            # handy to carry context
            "jobId": job["jobId"],
            "instrumentRunId": instrument_run_id,
        })

    return {"plans": plans}
