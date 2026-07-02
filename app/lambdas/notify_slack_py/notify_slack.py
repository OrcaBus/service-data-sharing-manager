import json
import os
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



def _generate_presigned_url(
    bucket: str,
    key: str,
    expiration: int = 604800,
) -> str:
    s3_client = boto3.client("s3")
    return s3_client.generate_presigned_url(
        ClientMethod="get_object",
        Params={
            "Bucket": bucket,
            "Key": key,
        },
        ExpiresIn=expiration,
    )


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
    thread_ts: str | None = None,
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
    text: str | None = None,
    blocks: list | None = None,
) -> dict:
    """
    Update an existing Slack message via chat.update.
    """

    # Base payload always has channel and ts
    payload: dict = {
        "channel": channel,
        "ts": ts,
    }
    # Build payload depending on the case
    if text is not None:
        payload["text"] = text
    if blocks is not None:
        payload["blocks"] = blocks


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



def _build_main_message_blocks(job_name, package_name, status):
    return [
        {
            "type": "card",
            "title": {
                "type": "mrkdwn",
                "text": "New auto-package ready.",
            },
            "body": {
                "type": "mrkdwn",
                "text": f"Job Name: `{job_name}`\nPackage Name: `{package_name}`",
            },
            "subtext": {
                "type": "mrkdwn",
                "text": status,
            }
        }
    ]

def handler(event, context):
    bot_token = _get_slack_bot_token()
    slack_notification_type = event.get("slackNotificationType")

    # ------------------------------------------------------------------
    # All fields pulled from the event up front. Will be None if not
    # present, but it's easier to read up front instead of pulling them
    # from the event in the middle of the code.
    # ------------------------------------------------------------------

    # Package context
    # Used in: PACKAGE_READY, PUSH_TRIGGERED, PUSH_COMPLETED
    job_name = event.get("jobName")
    package_id = event.get("packageId")
    package_name = event.get("packageName")
    share_destination = event.get("shareDestination")

    # Slack message context
    # Used in: PUSH_NOT_AUTHORISED, PUSH_TRIGGERED, PUSH_COMPLETED
    channel_id = event.get("channelId")
    main_message_ts = event.get("mainMessageTs")

    # Slack interaction context
    # Used in: PUSH_NOT_AUTHORISED, PUSH_TRIGGERED
    user_id = event.get("userId")
    package_ready_message_ts = event.get("packageReadyMessageTs")  # Used in: PUSH_TRIGGERED

    # Push result context
    # Used in: PUSH_COMPLETED
    push_status = event.get("pushStatus")
    push_id = event.get("pushId")
    push_date = event.get("pushDate")

    # Report link
    # Used in: PACKAGE_READY, PUSH_TRIGGERED
    package_report_presigned_url = None
    if package_id is not None:
        package_report_presigned_url = _get_package_report(package_id).strip('"')

    # Text for the first message in the thread, with package details and report link.
    #  Used in: PACKAGE_READY, PUSH_TRIGGERED (to update the message and remove the button).
    package_ready_text = (
        f"*Package ID:* `{package_id}`\n"
        f"*Share Destination:* `{share_destination}`\n"
        f"Review the *package report* <{package_report_presigned_url}|here>.\n"
    )

    # ----------------------------------------------------
    # Package notifications
    # ----------------------------------------------------
    if slack_notification_type == "PACKAGE_READY":

        # When a package is ready, the channel ID is pulled from the secret
        #  as is empty in the event
        channel_id = _get_slack_channel_id()

        # The first message posted in the channel when the package is ready, with the job name and status.
        # The rest of the details are in the thread under it.
        card_blocks = _build_main_message_blocks(job_name, package_name, ':package: Awaiting review')

        main_message_response = _post_message(
            bot_token=bot_token,
            channel=channel_id,
            blocks=card_blocks,
        )

        # Read the main message time stamp from the response, in the following notifications both
        # for update status or post in a thread under it.
        main_message_ts = main_message_response.get("ts")


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

        # Use blocks here so the message can include the Push button.
        push_button_blocks = [
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
                            "text": "Push",
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
        push_button_message_response = _post_message(
            bot_token=bot_token,
            channel=channel_id,
            thread_ts=main_message_ts,
            text=package_ready_text,
            blocks=push_button_blocks,
        )

        # Return the response from both API calls for observability.
        return {
            "mainMessageOk": main_message_response.get("ok"),
            "mainMessageError": main_message_response.get("error"),
            "mainMessageTs": main_message_ts,
            "pushButtonMessageOk": push_button_message_response.get("ok"),
            "pushButtonMessageError": push_button_message_response.get("error"),
        }

    # ----------------------------------------------------
    # Push notifications
    # ----------------------------------------------------

    elif slack_notification_type == "PUSH_NOT_AUTHORISED":
        unauthorized_text = ":no_entry: You’re not authorised to trigger push."

        return _post_message(
            bot_token=bot_token,
            channel=channel_id,
            user=user_id,
            text=unauthorized_text,
            thread_ts=main_message_ts,
            ephemeral=True
        )

    elif slack_notification_type == "PUSH_TRIGGERED":

        # Update the main message status to "Push in progress..."
        in_progress_card_blocks = _build_main_message_blocks(job_name, package_name, ':outbox_tray: Push in progress...')

        main_message_update_response =_update_message(
            bot_token=bot_token,
            channel=channel_id,
            ts=main_message_ts,
            blocks=in_progress_card_blocks,
        )

        # Update push_button_message. We are not passing a blocks payload which means
        # the blocks (and thus the button) will be removed for preventing multiple push
        # triggers .The text will remain the same with package details and report link.

        package_ready_message_update_response = _update_message(
            bot_token=bot_token,
            channel=channel_id,
            ts=package_ready_message_ts,
            text=package_ready_text,
        )

        # Post a thread reply showing who triggered the push.
        push_in_progress_text = (
            f"*Push triggered* by <@{user_id}>."
        )

        push_triggered_message_response = _post_message(
            bot_token=bot_token,
            channel=channel_id,
            thread_ts=main_message_ts,
            text=push_in_progress_text,
        )


        return {
            "mainMessageOk": main_message_update_response.get("ok"),
            "mainMessageError": main_message_update_response.get("error"),
            "packageReadyMessageOk": package_ready_message_update_response.get("ok"),
            "packageReadyMessageError": package_ready_message_update_response.get("error"),
            "pushTriggeredMessageOk": push_triggered_message_response.get("ok"),
            "pushTriggeredMessageError": push_triggered_message_response.get("error"),
        }


    elif slack_notification_type == "PUSH_COMPLETED":

        # Generate the presigned URL for the copy report in the Stepes-S3-Copy working bucket.
        steps_s3_copy_bucket_name = os.environ["STEPS_S3_COPY_BUCKET_NAME"]
        steps_s3_copy_midfix = os.environ["STEPS_S3_COPY_MIDFIX"]
        steps_s3_copy_prefix = os.environ["STEPS_S3_COPY_PREFIX"]
        copy_report_key = f"{steps_s3_copy_prefix}{steps_s3_copy_midfix}{push_date}/{push_id}/COPY_REPORT__{push_date.replace('__','_')}__{push_id}.html"

        copy_report_url = _generate_presigned_url(
            bucket=steps_s3_copy_bucket_name,
            key=copy_report_key
        )


        # Push succeded
        if push_status == "SUCCEEDED":

            # Update Status in main messege to "Completed!".
            succeeded_card_blocks = _build_main_message_blocks(job_name, package_name, ':white_check_mark: Completed!')

            main_message_update_response = _update_message(
                bot_token=bot_token,
                channel=channel_id,
                ts=main_message_ts,
                blocks=succeeded_card_blocks,
            )

            # Post message in thread to show the push result and details.
            push_succeeded_text = (
                f"*Push Completed:* {push_status}.\n"
                f"*Push ID:* {push_id}\n"
                f"*Share Destination:* `{share_destination}`\n"
                f"Review the *copy report* <{copy_report_url}|here>.\n"
            )

            push_result_message_response = _post_message(
                bot_token=bot_token,
                channel=channel_id,
                thread_ts=main_message_ts,
                text=push_succeeded_text,
            )


        # Push NOT succeded; catch and show the issue
        else:
            # Update status in main message to "Failed".
            failed_card_blocks = _build_main_message_blocks(job_name, package_name, ':warning: Push not successful.')

            main_message_update_response = _update_message(
                bot_token=bot_token,
                channel=channel_id,
                ts=main_message_ts,
                blocks=failed_card_blocks,
            )
            # Post message in thread to show the push result and details.
            push_failed_text = (
                f"*Push completed, but was NOT successful:* {push_status}\n"
                f"*Push ID:* {push_id}\n"
                f"*Share Destination:* `{share_destination}`\n"
                f"Review the *copy report* <{copy_report_url}|here>."
            )

            push_result_message_response = _post_message(
                bot_token=bot_token,
                channel=channel_id,
                thread_ts=main_message_ts,
                text=push_failed_text
            )

        return {
            "mainMessageOk": main_message_update_response.get("ok"),
            "mainMessageError": main_message_update_response.get("error"),
            "pushResultMessageOk": push_result_message_response.get("ok"),
            "pushResultMessageError": push_result_message_response.get("error"),
        }
    else:
        return {
            "ok": False,
            "error": f"Unknown slackNotificationType: {slack_notification_type}",
        }
