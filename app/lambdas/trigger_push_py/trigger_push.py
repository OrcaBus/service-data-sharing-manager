# #!/usr/bin/env python3
"""
Lambda handler to trigger the push step in the data sharing auto_package_push workflow.

This script sends a POST request to the OrcaBus Data Sharing API
(e.g., https://data-sharing.dev.umccr.org/ for development)
to start a data push job based on the event payload.
"""

from orcabus_api_tools.data_sharing import push_package

def handler(event, context):
    package_id = event["id"]
    share_dest = event.get("shareDestination")

    return {
        "pushRequestObject": push_package(
            package_id=package_id,
            location_uri=share_dest
            )
    }
