# # #!/usr/bin/env python3
# """
# Lambda handler to trigger the push step in the data sharing auto_push workflow.

# This script sends a POST request to the OrcaBus Data Sharing API
# (e.g., https://data-sharing.dev.umccr.org/ for development)
# to start a data push job based on the event payload.
# """

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
import json
import urllib.parse

from orcabus_api_tools.data_sharing import push_package


def _event_from_slack_body(slack_body: str) -> dict:
    """
    Convert the raw Slack body (application/x-www-form-urlencoded) into:
      {
        "id": "pkg.xxx",
        "packageName": "...",
        "shareDestination": "s3://..."
      }
    """
    # Example slack_body: "payload=%7B%22type%22%3A%22block_actions%22,...%7D"
    params = urllib.parse.parse_qs(slack_body)
    payload_str = params.get("payload", ["{}"])[0]

    slack_payload = json.loads(payload_str)

    actions = slack_payload.get("actions") or []
    if not actions:
        raise ValueError("Slack payload did not contain any actions")

    action = actions[0]
    raw_value = action.get("value")
    if not raw_value:
        raise ValueError("Slack action did not contain a value field")

    # value is the JSON we set in the notify lambda: {"id", "packageName", "shareDestination"}
    value = json.loads(raw_value)

    return value  # {"id": ..., "packageName": ..., "shareDestination": ...}


def handler(event, context):
    """
    Lambda handler to trigger the push step in the data sharing auto_push workflow.
    """
    event_data = _event_from_slack_body(event["slackBody"])

    package_id = event_data.get("id")
    share_dest = event_data.get("shareDestination")
    package_name = event_data.get("packageName")

    print(
        f"Starting push for package_id={package_id}, "
        f"package_name={package_name}, share_dest={share_dest}"
    )

    return {
        "pushRequestObject": push_package(
            package_id=package_id,
            location_uri=share_dest,
        )
    }
