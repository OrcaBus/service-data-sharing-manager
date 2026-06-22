#!/usr/bin/env python3
"""
Lambda handler to trigger the packaging step in the data sharing auto_package workflow.

This script sends a POST request to the OrcaBus Data Sharing API
(e.g., https://data-sharing.dev.umccr.org/ for development)
to start a packaging job based on the event payload.
"""

from orcabus_api_tools.data_sharing import create_package

def handler(event, context):
    package_name = event["packageName"]
    package_request = event["packageRequest"]

    return {
        "packagingRequestObject": create_package(
        package_name= package_name,
        package_request= package_request,
    )
    }
