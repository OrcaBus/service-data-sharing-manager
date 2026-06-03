import json
import urllib.request
import boto3


from orcabus_api_tools.data_sharing import get_data_sharing_url
from orcabus_api_tools.utils.requests_helpers import get_request


# Flow overview
#
# ============================================================
# Auto-package flow
# ============================================================
#
# ┌──────────────────────┐
# │   Package is ready   │
# └──────────┬───────────┘
#            │
#            ▼
# ┌────────────────────────────────────────────────────────────┐
# │ Slack notify lambda: PACKAGE_READY                         │
# │                                                            │
# │ 1. Post main channel message                               │
# │    - "A new auto-package is ready"                         │
# │    - includes job name and status                          │
# │                                                            │
# │ 2. Save mainMessageTs                                      │
# │                                                            │
# │ 3. Post thread message under the main message              │
# │    - package details                                       │
# │    - report link                                           │
# │    - Push button                                           │
# │                                                            │
# └────────────────────────────────────────────────────────────┘
#
#
# ============================================================
# Transition: user action in Slack
# ============================================================
#
#                  ┌──────────────────────────────┐
#                  │ User clicks Push in Slack    │
#                  └──────────────┬───────────────┘
#                                 │
#                                 ▼
# ┌────────────────────────────────────────────────────────────┐
# │ Context extracted from Slack interaction payload:          │
# │   - userId                                                 │
# │   - channelId                                              │
# │   - packageReadyMessageTs  (The time stamp of the package  |
# |                 ready message, first messahe in thread)    |
# └────────────────────────────────────────────────────────────┘
#                                 │
#                                 ▼
# ┌────────────────────────────────────────────────────────────┐
# │ Context extracted from button value:                       │
# │   - packageId                                              │
# │   - packageName                                            │
# │   - shareDestination                                       │
# │   - jobName                                                │
# │   - mainMessageTs                                          │
# └────────────────────────────────────────────────────────────┘
#
# ============================================================
# Auto-push flow
# ============================================================
#
# ┌────────────────────────────────────────────────────────────┐
# │ Authorisation / validation step                            │
# └───────┬───────────────────────────────────────┬────────────┘
#         │                                       │
#         │ allowed                               │ not allowed
#         ▼                                       ▼
# ┌──────────────────────────────┐   ┌──────────────────────────────┐
# │ Continue workflow            │   │ Slack notify lambda:         │
# │                              │   │ PUSH_NOT_AUTHORISED          │
# │                              │   │                              │
# │                              │   │ - send ephemeral warning     │
# │                              │   │   to the user                │
# └──────────┬───────────────────┘   └──────────────────────────────┘
#            │
#            ▼
# ┌────────────────────────────────────────────────────────────┐
# │ Slack notify lambda: PUSH_TRIGGERED                        │
# │                                                            │
# │ 1. Update main channel message                             │
# │    - status => "Push in progress..."                       │
# │                                                            │
# │ 2. Update package-ready thread message                     │
# │    - remove Push button                                    │
# │    - keep package details text                             │
# │                                                            │
# │ 3. Post new thread reply                                   │
# │    - "Push triggered by <user>"                            │
# └──────────┬─────────────────────────────────────────────────┘
#            │
#            ▼
# ┌────────────────────────────────────────────────────────────┐
# │ Trigger backend push workflow                              │
# │ / state machine / push execution                           │
# └──────────┬─────────────────────────────────────────────────┘
#            │
#            ▼
# ┌────────────────────────────────────────────────────────────┐
# │ Slack notify lambda: PUSH_COMPLETED                        │
# └───────┬───────────────────────────────────────┬────────────┘
#         │                                       │
#         │ success                               │ failure
#         ▼                                       ▼
# ┌──────────────────────────────┐   ┌──────────────────────────────┐
# │ 1. Update main message       │   │ 1. Update main message       │
# │    - "Completed!"            │   │    - "Push not successful"   │
# │                              │   │                              │
# │ 2. Post thread reply         │   │ 2. Post thread reply         │
# │    - push status             │   │    - failed status           │
# │    - push id                 │   │    - push id                 │
# │    - share destination       │   │    - share destination       │
# └──────────────────────────────┘   │    - check SFN for details   │
#                                    └──────────────────────────────┘



def _get_slack_bot_token():
    _sm = boto3.client("secretsmanager")
    return _sm.get_secret_value(SecretId="auto-data-sharing-slack-bot-token")["SecretString"] # pragma: allowlist secret

def _get_slack_channel_id() -> str:
    resp = boto3.client("secretsmanager").get_secret_value(
        SecretId="auto-data-sharing-slack-config"  # pragma: allowlist secret
    )
    secret_str = resp["SecretString"]

    data = json.loads(secret_str)
    return data["channel_id"]


def _get_package_report(package_id):

    packaging_report_api_url = get_data_sharing_url(f"/api/v1/package/{package_id}:getSummaryReport")

    return get_request(
        url=packaging_report_api_url,
    )


def _slack_api_post(url: str, bot_token: str, payload: dict) -> dict:
    """
    Helper to POST to the Slack API.

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

def _post_message(
    bot_token: str,
    channel: str,
    text: str | None = None,
    blocks: list | None = None,
    ephemeral: bool = False,
    user: str | None = None,
    ts: str | None = None,
    thread_ts: str | None = None
):
    """
    Post a message to Slack via chat.postMessage or chat.postEphemeral (if ephemeral=True).
    """
    if ephemeral:
        url = "https://slack.com/api/chat.postEphemeral"
    else:
        url = "https://slack.com/api/chat.postMessage"

    # Base payload always has channel
    payload: dict = {"channel": channel}

    # Build payload depending on the case
    if ephemeral:
        payload["user"] = user
    if thread_ts:
        payload["thread_ts"] = thread_ts
    if text is not None:
        payload["text"] = text
    if blocks is not None:
        payload["blocks"] = blocks

    # Call the Slack API to update the message and return the response.
    response_data = _slack_api_post(
        url=url,
        bot_token=bot_token,
        payload=payload,
    )

    return {
        "ok": response_data.get("ok"),
        "error": response_data.get("error"),
        "ts": response_data.get("ts")
    }


def _update_message(
    bot_token: str,
    channel: str,
    ts: str,
    text: str,
) -> dict:
    """
    Update an existing Slack message via chat.update.
    """

    # Build payload has channel and ts of the message to update and the new text.
    payload: dict = {
        "channel": channel,
        "ts": ts,
        "text": text
    }

    # Call the Slack API to update the message and return the response.
    response_data = _slack_api_post(
        url="https://slack.com/api/chat.update",
        bot_token=bot_token,
        payload=payload,
    )

    return {
        "ok": response_data.get("ok"),
        "error": response_data.get("error"),
    }

# ----------------------------------------------------------------------

# Header text for the message. This is the main notification that appears in the channel,
# the rest of the info is in the thread under it.
def build_main_text(job_name, status):
    return (
    f"A new auto-package is ready.\n"
    f"*Job Name:* `{job_name}`\n"
    f"{status}"
    )

def handler(event, context):
    bot_token = _get_slack_bot_token()
    slack_notification_type = event.get("slackNotificationType")

    # ------------------------------------------------------------------
    # All fields pulled from the event up front
    # ------------------------------------------------------------------
    job_name = event.get("jobName")
    package_id = event.get("packageId")                             # PACKAGE_READY, PUSH_TRIGGERED, PUSH_COMPLETED
    package_name = event.get("packageName")                         # PACKAGE_READY, PUSH_TRIGGERED, PUSH_COMPLETED
    share_destination = event.get("shareDestination")               # PACKAGE_READY, PUSH_TRIGGERED, PUSH_COMPLETED

    channel_id = event.get("channelId")                             # PACKAGE_READY (overwritten), PUSH_NOT_AUTHORISED, PUSH_TRIGGERED, PUSH_COMPLETED
    user_id = event.get("userId")                                   # PUSH_NOT_AUTHORISED, PUSH_TRIGGERED, PUSH_COMPLETED
    package_ready_message_ts = event.get("packageReadyMessageTs")   # PUSH_TRIGGERED, PUSH_COMPLETED
    main_message_ts = event.get("mainMessageTs")

    status = event.get("status")                                    # PUSH_COMPLETED
    push_id = event.get("pushId")                                   # PUSH_COMPLETED

    package_report_presigned_url = None
    if package_id is not None:
        package_report_presigned_url = _get_package_report(package_id).strip('"')  # PACKAGE_READY, PUSH_TRIGGERED, PUSH_COMPLETED



    package_ready_text = (
        f"*Package Name:* `{package_name}`\n"
        f"*Package ID:* `{package_id}`\n"
        f"*Share Destination:* `{share_destination}`\n"
        f"Review the packaging report <{package_report_presigned_url}|here>.\n"
    )


    # ----------------------------------------------------
    # Package notifications
    # ----------------------------------------------------
    if slack_notification_type == "PACKAGE_READY":

        # When a package is ready, the channel ID is pulled from the secret
        #  as is empty in the event
        channel_id = _get_slack_channel_id()

        main_text = build_main_text(job_name, ':package: Awaiting review')

        post_header_response = _post_message(
            bot_token=bot_token,
            channel=channel_id,
            text=main_text,
        )

        # Read the main message time stamp from the response, in the following notifications both
        # for update status or post in a thread under it.
        main_message_ts = post_header_response.get("ts")


        # First message in the thread with package details, report link and push button.
        button_value = json.dumps(
            {
                "packageId": package_id,
                "jobName": job_name,
                "packageName": package_name,
                "shareDestination": share_destination,
                "mainMessageTs": main_message_ts
            }
        )

        # Needs a block for set the button.
        thread_blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": package_ready_text,
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

        # Post the message in the thread with the button to trigger the push and package details.
        thread_response = _post_message(
            bot_token=bot_token,
            channel=channel_id,
            thread_ts=main_message_ts,
            text=package_ready_text,
            blocks=thread_blocks,
        )

        return {
            "ok": thread_response.get("ok"),
            "error": thread_response.get("error"),
        }


    # ----------------------------------------------------
    # Push notifications
    # ----------------------------------------------------

    elif slack_notification_type == "PUSH_NOT_AUTHORISED":
        text = ":warning: You’re not authorised to trigger push."

        return _post_message(
            bot_token=bot_token,
            channel=channel_id,
            user=user_id,
            text=text,
            ephemeral=True
        )

    elif slack_notification_type == "PUSH_TRIGGERED":

        # Update Status in header messege to "In progress".
        updated_main_text = build_main_text(job_name, ':outbox_tray: Push in progress...')

        _update_message(
            bot_token=bot_token,
            channel=channel_id,
            ts=main_message_ts,
            text=updated_main_text,
        )

        # Update package ready message in thread JUST to remove the button and prevent double push.

        _update_message(
            bot_token=bot_token,
            channel=channel_id,
            ts=package_ready_message_ts,
            text=package_ready_text,
        )

        # Post message in thread to show the push is in progress and who triggered it.
        push_in_progress_text = (
            f"*Push triggered* by <@{user_id}>."
        )

        _post_message(
            bot_token=bot_token,
            channel=channel_id,
            thread_ts=main_message_ts,
            text=push_in_progress_text,
        )


    elif slack_notification_type == "PUSH_COMPLETED":
        # Push succeded
        if status == "SUCCEEDED":

            # Update Status in header messege to "Completed!".
            succeeded_updated_main_text = build_main_text(job_name, ':white_check_mark: Completed!')

            _update_message(
                bot_token=bot_token,
                channel=channel_id,
                ts=main_message_ts,
                text=succeeded_updated_main_text,
            )

            # Post message in thread to show the push result and details.
            push_succeeded_text = (
                f"*Push Completed:* {status}.\n"
                f"*Push ID:* {push_id}\n"
                f"*Share Destination:* `{share_destination}`"
            )

            _post_message(
                bot_token=bot_token,
                channel=channel_id,
                thread_ts=main_message_ts,
                text=push_succeeded_text,
            )


        # Push NOT succeded; catch and show the issue
        else:
            # Update status in header message to "Failed".
            failed_updated_main_text = build_main_text(job_name, ':warning: Push not successful.')

            _update_message(
                bot_token=bot_token,
                channel=channel_id,
                ts=main_message_ts,
                text=failed_updated_main_text,
            )
            # Post message in thread to show the push result and details.
            push_failed_text = (
                f"*Push completed, but was NOT successful:* {status}\n"
                f"*Push ID:* {push_id}\n"
                f"*Share Destination:* `{share_destination}`\n"
                f"Please check `data-sharing--autoPush` state machine for more details."
            )

            _post_message(
                bot_token=bot_token,
                channel=channel_id,
                thread_ts=main_message_ts,
                text=push_failed_text
            )
