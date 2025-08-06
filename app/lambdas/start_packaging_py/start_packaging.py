#!/usr/bin/env python3

import json
import os
import requests
import logging

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Config
ORCABUS_API_TOKEN = os.environ.get("ORCABUS_API_TOKEN")
API_BASE_URL = "https://data-sharing.dev.umccr.org/api/v1/package/"

def handler(event, context=None):
    """
    Lambda entrypoint to trigger a packaging job via OrcaBus API.
    Includes AWS Step Function task token to allow async callback.
    """

    # # Validate inputs
    # # if not token:
    # #     raise ValueError("Missing Step Function task token in event['token']")

    # logger.info("Received task token: %s", token)

    # Read payload from the json
    payload = event
    logger.info("Packaging input: %s", json.dumps(event))


    headers = {
        "Authorization": f"Bearer {ORCABUS_API_TOKEN}",
        "Content-Type": "application/json"
    }

    logger.info("🚀 Sending request to OrcaBus packaging API...")
    response = requests.post(API_BASE_URL, headers=headers, json=payload)

    logger.info("API responded with status: %s", response.status_code)
    logger.info("API response body: %s", response.text)

    if not response.ok:
        raise Exception(f"API call failed: {response.status_code} - {response.text}")

    return {
        "message": "Packaging job started successfully",
        "response": response.json()
    }


if __name__ == "__main__":
    # Local test runner
    with open("start_packaging_input.json") as f:
        event = json.load(f)
    result = handler(event)
    print(json.dumps(result, indent=2))
