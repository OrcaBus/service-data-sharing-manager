#!/usr/bin/env python3


# #  This is the locally trigger version
# import json
# import requests
# import logging
# import boto3

# # Set up logging
# logger = logging.getLogger()
# logger.setLevel(logging.INFO)

# # API entry point for OrcaBus packaging
# # This is the base URL for the OrcaBus API packaging endpoint
# API_BASE_URL = "https://data-sharing.dev.umccr.org/api/v1/package/"

# # This API token retrieval logic follows the approach (almost a copy)
# # from data-sharing-tool.py for retrieving the OrcaBus API token from AWS
# # Secrets Manager. In the future, this could be refactored into a shared
# # module so that the authentication routine is callable across services.
# AWS_ORCABUS_TOKEN_SECRET_ID = 'orcabus/token-service-jwt'

# def get_orcabus_token() -> str:
#     sm = boto3.client("secretsmanager")
#     sec = sm.get_secret_value(SecretId=AWS_ORCABUS_TOKEN_SECRET_ID)["SecretString"]
#     token = json.loads(sec).get("id_token")
#     if not token:
#         raise ValueError("id_token missing in Secrets Manager secret")
#     return token

# def handler(event, context=None):
#     ORCABUS_API_TOKEN = get_orcabus_token()
#     if not ORCABUS_API_TOKEN:
#         raise RuntimeError("Could not retrieve OrcaBus API token from Secrets Manager")

#     logger.info("Received event: %s", json.dumps(event or {}))

#     # Validate required input
#     if not event or "packageInput" not in event:
#         raise ValueError("Missing 'packageInput' in event")

#     payload = event["packageInput"]
#     logger.info("Packaging input payload: %s", json.dumps(payload))

#     headers = {
#         "Authorization": f"Bearer {ORCABUS_API_TOKEN}",
#         "Content-Type": "application/json",
#         "Accept": "application/json",
#     }

#     logger.info("Sending request to OrcaBus packaging API...")
#     response = requests.post(API_BASE_URL, headers=headers, json=payload, timeout=30)

#     logger.info("API responded with status: %s", response.status_code)
#     logger.info("API response body: %s", response.text)

#     if not response.ok:
#         raise Exception(f"API call failed: {response.status_code} - {response.text}")

#     resp_json = response.json()
#     package_id_value = resp_json.get("id") or resp_json.get("package_id")
#     if not package_id_value:
#         raise ValueError("Could not find package_id in API response")

#     logger.info(f"Extracted package_id: {package_id_value}")
#     return {"message": "Packaging job started successfully", "package_id": package_id_value}

# if __name__ == "__main__":
#     fake_event = {
#         "packageInput": {
#             "packageName": "fji-test",
#             "packageRequest": {
#                 "libraryIdList": ["L2401544"],
#                 "dataTypeList": ["fastq"],
#                 "useWorkflowFilters": "true"
#             }
#         }
#     }
#     print(json.dumps(handler(fake_event), indent=2))



from orcabus_api_tools.data_sharing import get_data_sharing_url
from orcabus_api_tools.utils.requests_helpers import post_request

def handler(event, context):

    payload = event

    return post_request(
        url=get_data_sharing_url("api/v1/package/"),
        json_data=payload
    )
