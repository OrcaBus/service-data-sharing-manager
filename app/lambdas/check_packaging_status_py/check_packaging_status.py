#!/usr/bin/env python3

from orcabus_api_tools.data_sharing import get_data_sharing_url
from orcabus_api_tools.utils.requests_helpers import get_request

def handler(event, context):

    package_id = event["id"]
    status = get_request(url=get_data_sharing_url(f"api/v1/package/{package_id}"))["status"]

    return status
