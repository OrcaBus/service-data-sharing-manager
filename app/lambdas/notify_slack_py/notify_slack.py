import json, urllib.request


from orcabus_api_tools.data_sharing import get_data_sharing_url
from orcabus_api_tools.utils.requests_helpers import get_request



def get_package_report(package_id):

    packaging_report_api_url = get_data_sharing_url(f"/api/v1/package/{package_id}:getSummaryReport")

    return get_request(
        url=packaging_report_api_url,
    )


def handler(event, context):
    package_id = event["id"]
    package_name = event["packageName"]
    share_destination = event["shareDestination"]
    package_report_presigned_url = get_package_report(package_id).strip('"')

    text = (
        f"*{package_name}* is ready.\n"
        f"*Package ID:* {package_id}\n"
        f"Review the packaging report <{package_report_presigned_url}|HERE>. \n\n"
        f"To manually trigger the push to *{share_destination}*, run:\n"
        f"```"
        f"aws stepfunctions start-execution \\\n"
        f"  --state-machine-arn arn:aws:states:ap-southeast-2:843407916570:stateMachine:data-sharing-autoPush \\\n"
        f"  --input '{{\"id\": \"{package_id}\", \"packageName\": \"{package_name}\", \"shareDestination\": \"{share_destination}\"}}'\n"
        f"```"

    )
    payload = json.dumps({"text": text}).encode("utf-8")

    req = urllib.request.Request(
        WEBHOOK_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        print("Response:", resp.read().decode())

    return {"ok": True}
