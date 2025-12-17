import json
import urllib.request
import boto3


from orcabus_api_tools.data_sharing import get_data_sharing_url
from orcabus_api_tools.utils.requests_helpers import get_request


def _get_slack_bot_token():
    _sm = boto3.client("secretsmanager")
    return _sm.get_secret_value(SecretId="auto-data-sharing-slack-bot-token")["SecretString"] # pragma: allowlist secret


def _slack_api_post(url: str, bot_token: str, payload: dict) -> dict:
    """
    Helper to POST JSON payloads to the Slack Web API.

    - Encodes the payload as JSON
    - Adds the Authorization header
    - Returns the parsed JSON response as a dict
    """
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
        body = resp.read().decode("utf-8")

    data = json.loads(body)

    return data


def _post_message(bot_token: str,
                  channel: str,
                  text= None,
                  blocks = None,
                  update = False,
                  ts=None,
                  ephemeral = False,
                  user = None
):

    if update:
        url = "https://slack.com/api/chat.update"

        payload = {
            "channel": channel,
            "ts": ts,
            "blocks": blocks,
        }



    elif ephemeral:
        url = "https://slack.com/api/chat.postEphemeral"

        payload = {
            "channel": channel,
            "user": user,
            "text": text,
        }


    else:
        url = "https://slack.com/api/chat.postMessage"

        payload: dict = {
            "channel": channel,
            "text": text,
        }
        if blocks is not None:
            payload["blocks"] = blocks


    response_data = _slack_api_post(
        url=url,
        bot_token=bot_token,
        payload=payload
    )

    return {
        "ok": response_data.get('ok'),
        "error": response_data.get('error')
    }



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



    text = f"Auto Package for {package_name} is ready."
    body_text = (
        f":package: *Auto Package*\n"
        f"*{package_name}* is ready.\n"
        f"*Package ID:* `{package_id}`\n"
        f"Destination: `{share_destination}`\n"
        f"Review the packaging report <{package_report_presigned_url}|here>.\n"
    )




    # ----------------------------------------------------
    # Package notifications
    # ----------------------------------------------------
    if slack_notification_type == "PACKAGE_READY":
        # auto-data-sharing
        channel_id = "C09KQ32MXAS" # Should live in a better places....

        # alert-dev
        channel_id = "C06T9S6DZKK"

        button_value = json.dumps(
            {
                "packageId": package_id,
                "packageName": package_name,
                "shareDestination": share_destination,
            }
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



        result = _post_message(
            bot_token=bot_token,
            channel=channel_id,
            text= text,
            blocks=blocks,
        )

        return result



    # ----------------------------------------------------
    # Push notifications
    # ----------------------------------------------------

    elif slack_notification_type == "PUSH_NOT_AUTHORISED":
        channel_id = event.get("channelId")
        user_id = event.get("userId")
        text = ":warning: You’re not authorised to trigger push."

        result = _post_message(
            bot_token=bot_token,
            channel=channel_id,
            user=user_id,
            text=text,
            ephemeral=True
        )

        return result

    elif slack_notification_type == "PUSH_TRIGGERED":
        channel_id = event.get("channelId")
        user_id = event.get("userId")
        message_ts = event.get("messageTs")


        push_in_progress_update = (
            f":outbox_tray: Push in progress… triggered by <@{user_id}>."
        )

        block_text = body_text + push_in_progress_update

        updated_blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": block_text,
                },
            },
        ]


        # Remove button for everyone by updating only the blocks
        result = _post_message(
            bot_token=bot_token,
            channel=channel_id,
            ts=message_ts,
            blocks=updated_blocks,
            update=True,
        )
        return result

    elif slack_notification_type == "PUSH_COMPLETED":
        status = event["status"]
        push_id = event.get("pushId")
        user_id = event.get("userId")
        channel_id = event.get("channelId")
        message_ts = event.get("messageTs")


        # Push succeded
        if status == "SUCCEEDED":

            push_succeeded_update = (
                f"Pushed by <@{user_id}>.\n"
                f"\n"
                f"\n"
                f":white_check_mark: *Push Completed*\n"
                f"*Push ID:* {push_id} *{status}*\n"
                f"*Package ID*: {push_id}\n"
                f"*Share Destination:* {share_destination}"
            )

            block_text = body_text + push_succeeded_update


        # Push NOT succeded; catch and show the issue
        else:
            push_failed_update = (
                f"Pushed by <@{user_id}>.\n"
                f"\n"
                f"\n"
                f":x: Push *{push_id}* {status}.\n"
                f"*Package ID*: {push_id}\n"
            )

            block_text = body_text + push_failed_update

        # Update
        updated_blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": block_text,
                },
            },
        ]

        # Post updated message
        result = _post_message(
            bot_token=bot_token,
            channel=channel_id,
            ts=message_ts,
            blocks=updated_blocks,
            update=True,
        )
        return result
