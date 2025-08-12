# #!/usr/bin/env python3

# import json
# import os
# import requests
# import logging

# logger = logging.getLogger(__name__)
# logger.setLevel(logging.INFO)

# ORCABUS_API_TOKEN = os.environ.get("ORCABUS_API_TOKEN")
# BASE_URL = "https://data-sharing.dev.umccr.org/api/v1/package"

# def handler(event=None, context=None):
#     if not ORCABUS_API_TOKEN:
#         raise RuntimeError("Missing ORCABUS_API_TOKEN env var")

#     event = event or {}

#     # Use the package_id passed from Step Functions; fallback keeps local test easy
#     package_id = event.get("package_id")
#     share_dest = "s3://umccr-temp-dev/fji/"

#     logger.info(f"start_data_copy: package_id={package_id} (from SFN: {'yes' if 'package_id' in event else 'no'})")

#     url = f"{BASE_URL}/{package_id}:push"
#     payload = {"shareDestination": share_dest}

#     headers = {
#         "Authorization": f"Bearer {ORCABUS_API_TOKEN}",
#         "Content-Type": "application/json",
#     }

#     logger.info(f"Sending push request to {url} with payload: {payload}")
#     resp = requests.post(url, headers=headers, json=payload)

#     logger.info("API status: %s", resp.status_code)
#     logger.info("API body: %s", resp.text)

#     if not resp.ok:
#         raise Exception(f"Push API failed: {resp.status_code} - {resp.text}")

#     return {"message": "Push job started successfully", "response": resp.json()}

# if __name__ == "__main__":
#     # Local test still works with no input
#     print(json.dumps(handler({}), indent=2))




from orcabus_api_tools.data_sharing import get_data_sharing_url
from orcabus_api_tools.utils.requests_helpers import post_request

def handler(event, context):
    package_id = event["package_id"]
    share_dest = event.get("shareDestination")
    payload = {"shareDestination": share_dest}

    return post_request(
        url=get_data_sharing_url(f"api/v1/package/{package_id}:push"),
        json_data=payload
    )
