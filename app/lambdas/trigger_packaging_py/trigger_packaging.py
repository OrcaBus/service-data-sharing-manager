#!/usr/bin/env python3
"""
Lambda handler to trigger the packaging step in the data sharing launcher workflow.

This script sends a POST request to the OrcaBus Data Sharing API
(e.g., https://data-sharing.dev.umccr.org/ for development)
to start a packaging job based on the event payload.
"""

from orcabus_api_tools.data_sharing import get_data_sharing_url
from orcabus_api_tools.utils.requests_helpers import post_request

def handler(event, context):
    """
    Handler function that calls the OrcaBus Data Sharing API to start a packaging job.
    """


    packaging_request = event
    packaging_api_url = get_data_sharing_url("api/v1/package/")

    return post_request(
        url=packaging_api_url,
        json_data=packaging_request
    )
