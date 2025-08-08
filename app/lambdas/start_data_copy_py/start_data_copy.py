#!/usr/bin/env python3

import json
import os
import requests
import logging

# Logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Config
ORCABUS_API_TOKEN = os.environ.get("ORCABUS_API_TOKEN")
BASE_URL = "https://data-sharing.dev.umccr.org/api/v1/package"

def handler(event, context=None):
    """
    Trigger a data push job via OrcaBus API.
    Expects event with:
    - package_id
    - shareDestination
    """
    if not ORCABUS_API_TOKEN:
        raise RuntimeError("Missing ORCABUS_API_TOKEN env var")

    package_id = event.get("package_id")
    share_dest = event.get("shareDestination")

    if not package_id or not share_dest:
        raise ValueError("Missing required fields: package_id and/or shareDestination")

    url = f"{BASE_URL}/{package_id}:push"
    payload = {"shareDestination": share_dest}

    logger.info(f"Sending push request to {url} with payload: {payload}")
    headers = {
        "Authorization": f"Bearer {ORCABUS_API_TOKEN}",
        "Content-Type": "application/json"
    }

    resp = requests.post(url, headers=headers, json=payload)

    logger.info("API status: %s", resp.status_code)
    logger.info("API body: %s", resp.text)

    if not resp.ok:
        raise Exception(f"Push API failed: {resp.status_code} - {resp.text}")

    return {
        "message": "Push job started successfully",
        "response": resp.json()
    }

if __name__ == "__main__":
    # Local test
    with open("start_data_copy_input.json") as f:
        event = json.load(f)
    result = handler(event)
    print(json.dumps(result, indent=2))
