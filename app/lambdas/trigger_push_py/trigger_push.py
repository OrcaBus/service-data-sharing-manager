# #!/usr/bin/env python3
"""
Lambda handler to trigger the push step in the data sharing auto_package_push workflow.

This script sends a POST request to the OrcaBus Data Sharing API
(e.g., https://data-sharing.dev.umccr.org/ for development)
to start a data push job based on the event payload.
"""

from orcabus_api_tools.data_sharing import get_data_sharing_url
from orcabus_api_tools.utils.requests_helpers import post_request

def handler(event, context):
    """Handler function that calls the OrcaBus Data Sharing API to start a data push job."""
    package_id = event["id"]
    share_dest = event.get("shareDestination")
    push_request = {"shareDestination": share_dest}

    push_api_url = get_data_sharing_url(f"api/v1/package/{package_id}:push")

    return {
        "pushRequestObject": post_request(
                url=push_api_url,
                json_data=push_request
                )
    }


# from orcabus_api_tools.data_sharing import push_package

# def handler(event, context):
#     package_id = event["id"]
#     share_dest = event.get("shareDestination")

#     return {
#         "pushRequestObject": push_package(
#             package_id=package_id,
#             location_uri=share_dest
#             )
#     }
