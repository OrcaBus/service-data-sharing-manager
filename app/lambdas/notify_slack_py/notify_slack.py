import json
import urllib.request
import boto3


from orcabus_api_tools.data_sharing import get_data_sharing_url
from orcabus_api_tools.utils.requests_helpers import get_request


# Should haddle this better in the future, defining it in constants and so on...
def _get_webhook_url():
    _sm = boto3.client("secretsmanager")
    return _sm.get_secret_value(SecretId="auto-data-sharing-slack-webhook")["SecretString"] # pragma: allowlist secret



def get_package_report(package_id):

    packaging_report_api_url = get_data_sharing_url(f"/api/v1/package/{package_id}:getSummaryReport")

    return get_request(
        url=packaging_report_api_url,
    )

def _post_to_slack(webhook_url: str, payload: dict):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        webhook_url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:  # noqa: S310 (Lambda, trusted URL)
        resp.read()



def handler(event, context):
    WEBHOOK_URL = _get_webhook_url()
    orcabus_id = event["id"]

    # If it's a package
    if orcabus_id.startswith('pkg.'):
        package_name = event["packageName"]
        share_destination = event["shareDestination"]
        package_report_presigned_url = get_package_report(orcabus_id).strip('"')
        auto_push_state_machine_arn = event["autoPushStateMachineArn"]


        pretty_dest = share_destination.replace("://", ":\u200b//")  # zero-width space

        button_value = json.dumps(
            {
                "id": orcabus_id,
                "packageName": package_name,
                "shareDestination": share_destination,
                # Include anything else you might need (env, account, etc.)
            }
        )

        slack_payload = {
                "text": f"Auto Package for {package_name} is ready.",  # fallback
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": (
                                f":package: *Auto Package*\n"
                                f"*{package_name}* is ready.\n"
                                f"*Package ID:* `{orcabus_id}`\n"
                                f"Review the packaging report <{package_report_presigned_url}|here>."
                            ),
                        },
                    },
                    {
                        "type": "context",
                        "elements": [
                            {
                                "type": "mrkdwn",
                                "text": f"Destination: `{pretty_dest}`",
                            }
                        ],
                    },
                    {
                        "type": "actions",
                        "elements": [
                            {
                                "type": "button",
                                "text": {
                                    "type": "plain_text",
                                    "text": f"Push to {pretty_dest}",
                                    "emoji": True,
                                },
                                "style": "primary",
                                "action_id": "auto_push_package",  # you’ll match on this
                                "value": button_value,
                            }
                        ],
                    },
                ],
            }

        _post_to_slack(WEBHOOK_URL, slack_payload)

        return {"status": "ok"}


    # If it's a push
    elif orcabus_id.startswith('psh.'):

        status = event["status"]
        package_id = event["packageId"]
        share_destination = event["shareDestination"]

        if status == "SUCCEEDED":
            text = (
                f":white_check_mark: *Push Completed*\n"
                f"*Push ID:* {orcabus_id} *{status}*\n"
                f"*Package ID*: {package_id}\n"
                f"*Share Destination:* {share_destination}"
            )

        else:
            text = (
                f":x: Push *{orcabus_id}* {status}.\n"
                f"*Package ID*: {package_id}\n"
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

    else:
        raise ValueError(f"Unexpected id format: {orcabus_id}")
