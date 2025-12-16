import json
import urllib.request
import boto3


from orcabus_api_tools.data_sharing import get_data_sharing_url
from orcabus_api_tools.utils.requests_helpers import get_request


def _get_slack_bot_token():
    _sm = boto3.client("secretsmanager")
    return _sm.get_secret_value(SecretId="auto-data-sharing-slack-bot-token")["SecretString"] # pragma: allowlist secret


def _post_message(bot_token: str, channel: str, text: str, blocks = None, ephemeral = False, user = None):

    if ephemeral:
        url = "https://slack.com/api/chat.postEphemeral"

        payload = {
            "channel": channel,
            "user": user,
            "text": text,
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "Authorization": f"Bearer {bot_token}",
            },
            method="POST",
        )

        with urllib.request.urlopen(req) as resp:
            body = resp.read().decode()
            print("Ephemeral response raw:", body)
            data = json.loads(body)


    else:
        url = "https://slack.com/api/chat.postMessage"

        payload: dict = {
            "channel": channel,
            "text": text,
        }
        if blocks is not None:
            payload["blocks"] = blocks

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "Authorization": f"Bearer {bot_token}",
            },
            method="POST",
        )

        with urllib.request.urlopen(req) as resp:
            body = resp.read().decode()
            print("chat.postMessage response:", body)





def _update_slack_message(bot_token: str, channel: str, ts: str, blocks: list):
    """
    Update the original Slack message, replacing only the blocks.
    We do NOT change the 'text' field, so Slack won't show 'edited'.
    """
    url = "https://slack.com/api/chat.update"

    payload = {
        "channel": channel,
        "ts": ts,
        "blocks": blocks,
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "Authorization": f"Bearer {bot_token}",
        },
        method="POST",
    )

    with urllib.request.urlopen(req) as resp:
        body = resp.read().decode()
        print("chat.update response:", body)


def _get_package_report(package_id):

    packaging_report_api_url = get_data_sharing_url(f"/api/v1/package/{package_id}:getSummaryReport")

    return get_request(
        url=packaging_report_api_url,
    )

# ----------------------------------------------------------------------


def handler(event, context):
    bot_token = _get_slack_bot_token()
    slack_notification_type = event.get("slackNotificationType")
    package_id = event.get("packageId")
    package_name = event.get("packageName")
    share_destination = event.get("shareDestination")

    package_report_presigned_url = _get_package_report(package_id).strip('"')

    # ----------------------------------------------------
    # Package notifications
    # ----------------------------------------------------
    if slack_notification_type == "PACKAGE_READY":
        channel_id = "C09KQ32MXAS" # Should live in a better places....




        text = f"Auto Package for {package_name} is ready."

        button_value = json.dumps(
            {
                "packageId": package_id,
                "packageName": package_name,
                "shareDestination": share_destination,
            }
        )

        body_text = (
            f":package: *Auto Package*\n"
            f"*{package_name}* is ready.\n"
            f"*Package ID:* `{package_id}`\n"
            f"Destination: `{share_destination}`\n"
            f"Review the packaging report <{package_report_presigned_url}|here>."
        )


        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": body_text,
                },
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": f"Push",
                            "emoji": True,
                        },
                        "style": "primary",
                        "action_id": "auto_push_package",
                        "value": button_value,
                    }
                ],
            },
        ]



        _post_message(
            bot_token=bot_token,
            channel=channel_id,
            text= text,
            blocks=blocks,
        )

        return {"status": "ok"}



    # ----------------------------------------------------
    # Push notifications
    # ----------------------------------------------------

    elif slack_notification_type == "PUSH_NOT_AUTHORISED":
        channel_id = event.get("channelId")
        user_id = event.get("userId")
        text = ":warning: You’re not authorised to trigger push."

        _post_message(
            bot_token=bot_token,
            channel=channel_id,
            user=user_id,
            text=text,
            ephemeral=True
        )

        return {"ok": True}

    elif slack_notification_type == "PUSH_TRIGGERED":
        channel_id = event.get("channelId")
        user_id = event.get("userId")
        message_ts = event.get("messageTs")


        body_text = (
            f":package: *Auto Package*\n"
            f"*{package_name}* is ready.\n"
            f"*Package ID:* `{package_id}`\n"
            f"Destination: `{share_destination}`\n"
            f"Review the packaging report <{package_report_presigned_url}|here>.\n"
            f":outbox_tray: Push in progress… triggered by <@{user_id}>."
        )

        updated_blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": body_text,
                },
            },
        ]


        # Remove button for everyone by updating only the blocks
        _update_slack_message(
            bot_token=bot_token,
            channel=channel_id,
            ts=message_ts,
            blocks=updated_blocks,
        )
        return {"ok": True}

    elif slack_notification_type == "PUSH_COMPLETED":
        status = event["status"]
        push_id = event.get("pushId")
        user_id = event.get("userId")
        channel_id = event.get("channelId")
        message_ts = event.get("messageTs")


        # Push succeded
        if status == "SUCCEEDED":

            body_text = (
                f":package: *Auto Package*\n"
                f"      *{package_name}* is ready.\n"
                f"      *Package ID:* `{package_id}`\n"
                f"      Destination: `{share_destination}`\n"
                f"      Review the packaging report <{package_report_presigned_url}|here>.\n"
                f"      Pushed by <@{user_id}>.\n"
                f"\n"
                f"\n"
                f":white_check_mark: *Push Completed*\n"
                f"      *Push ID:* {push_id} *{status}*\n"
                f"      *Package ID*: {push_id}\n"
                f"      *Share Destination:* {share_destination}"
            )

        # Push NOT succeded; catch and show the issue
        else:
            body_text = (
                f":package: *Auto Package*\n"
                f"*     {package_name}* is ready.\n"
                f"      *Package ID:* `{package_id}`\n"
                f"      Destination: `{share_destination}`\n"
                f"      Review the packaging report <{package_report_presigned_url}|here>.\n"
                f"      Pushed by <@{user_id}>.\n"
                f"\n"
                f"\n"
                f":x: Push *{push_id}* {status}.\n"
                f"      *Package ID*: {push_id}\n"
            )

        # Update
        updated_blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": body_text,
                },
            },
        ]

        # Post updated message
        _update_slack_message(
            bot_token=bot_token,
            channel=channel_id,
            ts=message_ts,
            blocks=updated_blocks,
        )
        return {"ok": True}
