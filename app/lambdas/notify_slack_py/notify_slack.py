import json
import logging
import urllib.request
from datetime import datetime, timezone
import boto3

logger = logging.getLogger()
logger.setLevel("INFO")

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
# │    - package report link                                   │
# │    - Push button                                           │
# │    - Deprecate button                                      │
# │                                                            │
# │ 4. The auto package SFN also schedules a one-shot          │
# │    EventBridge Scheduler that, after PACKAGE_EXPIRY_DAYS,   │
# │    invokes this lambda with PACKAGE_EXPIRED (see the        │
# │    expiry flow below).                                      │
# │                                                            │
# └────────────────────────────────────────────────────────────┘
#
# ============================================================
# Transition: user action in Slack
# ============================================================
#
#                  ┌──────────────────────────────┐
#                  │ User clicks Push or Deprecate │
#                  │ in Slack                      │
#                  └──────────────┬───────────────┘
#                                 │
#                                 ▼
# ┌────────────────────────────────────────────────────────────┐
# │ Context extracted from Slack interaction payload:          │
# │   - userId                                                 │
# │   - channelId                                              │
# │   - packageReadyMessageTs  (The time stamp of the package  |
# |                 ready message, first message in thread)    |
# └────────────────────────────────────────────────────────────┘
#                                 │
#                                 ▼
# ┌────────────────────────────────────────────────────────────┐
# │ Context extracted from button value:                       │
# │   - actionId (push_package | decline_push_package |         │
# │     deprecate_package,                                     │
# │     used to branch to the push or deprecate flow)          │
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
# │    - package report link     │   │    - package report link     │
# └──────────────────────────────┘   └──────────────────────────────┘
#
# ============================================================
# Deprecate flow (user clicks Deprecate; authorised like push)
# ============================================================
#
# ┌────────────────────────────────────────────────────────────┐
# │ Deprecate the package via the data sharing API             │
# └───────┬───────────────────────────────────────┬────────────┘
#         │                                       │
#         │ success / already deprecated          │ failure
#         ▼                                       ▼
# ┌──────────────────────────────┐   ┌──────────────────────────────┐
# │ Slack notify lambda:         │   │ Slack notify lambda:         │
# │ PACKAGE_DEPRECATED           │   │ DEPRECATE_NOT_SUCCESSFUL     │
# │                              │   │                              │
# │ 1. Update main message       │   │ - send ephemeral warning     │
# │    - "Package deprecated"    │   │   to the user (buttons kept  │
# │                              │   │   so they can retry / push)  │
# │ 2. Update package-ready msg  │   │                              │
# │    - remove Push + Deprecate │   │                              │
# │      buttons                 │   │                              │
# │                              │   │                              │
# │ 3. Post thread reply         │   │                              │
# │    - "Deprecated by <user>"  │   │                              │
# │      (or "already            │   │                              │
# │      deprecated")            │   │                              │
# └──────────────────────────────┘   └──────────────────────────────┘
#
# ============================================================
# Expiry flow (scheduled, no user action)
# ============================================================
#
# ┌──────────────────────────────────────────────────────────┐
# │ One-shot EventBridge Scheduler fires PACKAGE_EXPIRY_DAYS  │
# │ after the package was ready and invokes this lambda with │
# │ PACKAGE_EXPIRED (then the schedule deletes itself).      │
# └──────────────────────────┬───────────────────────────────┘
#                            │
#                            ▼
# ┌────────────────────────────────────────────────────────────┐
# │ Slack notify lambda: PACKAGE_EXPIRED                       │
# │                                                            │
# │ 1. Update main message                                     │
# │    - "Package expired"                                     │
# │                                                            │
# │ 2. Update package-ready thread message                     │
# │    - remove Push + Deprecate buttons                       │
# │    - drop the report link (expired reports are rejected)   │
# │                                                            │
# │ 3. Post thread reply                                       │
# │    - "Package expired on <date>"                           │
# └────────────────────────────────────────────────────────────┘
#



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

def _find_copy_report_key(
    bucket: str,
    base_prefix: str,
    push_id: str,
) -> str | None:
    """
    Discover the copy report object under base_prefix, matching the deterministic
    filename COPY_REPORT__<push_id>.html, wherever the copier placed it.
    Returns the object key, or None if not found.
    """
    s3_client = boto3.client("s3")
    target_suffix = f"COPY_REPORT__{push_id}.html"

    paginator = s3_client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=base_prefix):
        for obj in page.get("Contents", []):
            if obj["Key"].endswith(target_suffix):
                return obj["Key"]
    return None

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

def _main_message_was_updated(bot_token: str, channel: str, ts: str) -> bool:
    """
    Return True if the main message has already been edited (i.e. its status moved on from
    "Awaiting review" to push/completed/deprecated). Slack adds an `edited` field to any
    message updated via chat.update; an untouched original has none.

    Best-effort: on any error we return True so the expiry flow does NOT overwrite a card
    whose state we couldn't confirm. Requires the bot's channel history scope.
    """
    try:
        # Values are a channel id and a numeric ts, so no URL-encoding is needed.
        url = (
            "https://slack.com/api/conversations.history"
            f"?channel={channel}&latest={ts}&limit=1&inclusive=true"
        )
        req = urllib.request.Request(
            url,
            headers={"Authorization": f"Bearer {bot_token}"},
            method="GET",
        )
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        # Slack returns HTTP 200 even on API errors (e.g. missing_scope), so check `ok`.
        if not data.get("ok"):
            logger.warning(
                "conversations.history failed for %s: %s; assuming already updated.",
                ts, data.get("error"),
            )
            return True

        messages = data.get("messages") or []
        if not messages:
            logger.warning(
                "conversations.history returned no message for %s; assuming already updated.", ts
            )
            return True

        was_edited = "edited" in messages[0]
        logger.info("Main message %s edited=%s", ts, was_edited)
        return was_edited
    except Exception:
        logger.warning(
            "Could not read main message %s; assuming already updated.", ts, exc_info=True
        )
        return True

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
    steps_s3_copy_bucket = event.get("stepsS3CopyBucket")
    steps_s3_copy_base_prefix = event.get("stepsS3CopyBasePrefix")
    error_cause = event.get("errorCause")





    # Report link
    # Only fetched for the notifications that render it (PACKAGE_READY, PUSH_TRIGGERED).
    # The getSummaryReport endpoint rejects deprecated packages (409), so we must not
    # fetch it for PACKAGE_DEPRECATED. Kept best-effort: a failure here should not sink
    # the whole notification.
    package_report_presigned_url = None
    if package_id is not None and slack_notification_type in ("PACKAGE_READY", "PUSH_TRIGGERED"):
        try:
            package_report_presigned_url = _get_package_report(package_id).strip('"')
        except Exception:
            logger.warning(
                "Failed to fetch package report for %s; continuing without a report link.",
                package_id,
                exc_info=True,
            )

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
                        "action_id": "push_package",
                        "value": button_value,
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Don't Push",
                            "emoji": True,
                        },
                        "action_id": "decline_push_package",
                        "value": button_value,
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Deprecate Package",
                            "emoji": True,
                        },
                        "action_id": "deprecate_package",
                        "value": button_value,
                    },
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

        # Return the response from both API calls for observability. The ts values and
        # channel id are also used by the auto package SFN to schedule the expiry
        # notification (PACKAGE_EXPIRED).
        return {
            "mainMessageOk": main_message_response.get("ok"),
            "mainMessageError": main_message_response.get("error"),
            "mainMessageTs": main_message_ts,
            "pushButtonMessageOk": push_button_message_response.get("ok"),
            "pushButtonMessageError": push_button_message_response.get("error"),
            "packageReadyMessageTs": push_button_message_response.get("ts"),
            "channelId": channel_id,
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
        # the blocks (and thus the button) will be removed to prevent multiple push
        # triggers. The text remains the same with package details and report link.

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

        # Generate the presigned URL for the copy report in the Steps-S3-Copy working bucket.
        # We need the bucket, the prefix and the report key to generate the full key for the report.
        # otherwise, the copy report URL will be None and the message will not include a link to it.
        # Build the copy report link on a best-effort basis: if it can't be
        # resolved, log a warning and post the notification without the link
        # rather than failing the whole push-completed notification.
        copy_report_url = None
        if steps_s3_copy_bucket and steps_s3_copy_base_prefix and push_id:
            try:
                copy_report_key = _find_copy_report_key(
                    bucket=steps_s3_copy_bucket,
                    base_prefix=steps_s3_copy_base_prefix,
                    push_id=push_id,
                )
                if copy_report_key:
                    copy_report_url = _generate_presigned_url(
                        bucket=steps_s3_copy_bucket,
                        key=copy_report_key,
                    )
                else:
                    logger.warning(
                        "Copy report not found for push %s under s3://%s/%s",
                        push_id, steps_s3_copy_bucket, steps_s3_copy_base_prefix,
                    )
            except Exception:
                logger.warning(
                    "Failed to generate presigned URL for copy report of push %s under s3://%s/%s",
                    push_id, steps_s3_copy_bucket, steps_s3_copy_base_prefix,
                    exc_info=True,
                )


        # Push succeeded
        if push_status == "SUCCEEDED":

            # Update status in main message to "Completed!".
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


        # Push NOT succeeded; catch and show the issue
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
                f"*Push was NOT successful:* {push_status}\n"
                f"*Share Destination:* `{share_destination}`\n"
                f"*Cause:* `{error_cause}`\n"
                f"Please check `data-sharing--slackPackageAction` state machine for more details."
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

    # ----------------------------------------------------
    # Deprecate notifications
    # ----------------------------------------------------

    elif slack_notification_type == "PACKAGE_DEPRECATED":

        # Update the main message status to "Package deprecated".
        deprecated_card_blocks = _build_main_message_blocks(
            job_name, package_name, ':heavy_multiplication_x: Package deprecated'
        )

        main_message_update_response = _update_message(
            bot_token=bot_token,
            channel=channel_id,
            ts=main_message_ts,
            blocks=deprecated_card_blocks,
        )

        # Update the package-ready message without a blocks payload, which removes
        # both the Push and Deprecate buttons. A deprecated package's report is no
        # longer accessible, so we drop the report link and keep the core details.
        deprecated_details_text = (
            f"*Package ID:* `{package_id}`\n"
            f"*Share Destination:* `{share_destination}`\n"
        )

        package_ready_message_update_response = _update_message(
            bot_token=bot_token,
            channel=channel_id,
            ts=package_ready_message_ts,
            text=deprecated_details_text,
        )

        # Post a thread reply showing who deprecated the package. If it was already
        # deprecated, note that instead of implying this click deprecated it.
        already_deprecated = event.get("alreadyDeprecated") is True
        if already_deprecated:
            deprecated_text = (
                f"<@{user_id}> requested deprecation, but this package was *already deprecated*."
            )
        else:
            deprecated_text = (
                f"*Package deprecated* by <@{user_id}>."
            )

        deprecated_message_response = _post_message(
            bot_token=bot_token,
            channel=channel_id,
            thread_ts=main_message_ts,
            text=deprecated_text,
        )

        return {
            "mainMessageOk": main_message_update_response.get("ok"),
            "mainMessageError": main_message_update_response.get("error"),
            "packageReadyMessageOk": package_ready_message_update_response.get("ok"),
            "packageReadyMessageError": package_ready_message_update_response.get("error"),
            "deprecatedMessageOk": deprecated_message_response.get("ok"),
            "deprecatedMessageError": deprecated_message_response.get("error"),
        }

    elif slack_notification_type == "DEPRECATE_NOT_SUCCESSFUL":

        # Deprecation failed. Leave the main message and the buttons untouched so the
        # user can retry or push, and send an ephemeral warning to whoever clicked.
        deprecate_failed_text = (
            f":warning: Deprecation was not successful.\n"
            f"*Cause:* `{error_cause}`\n"
            f"You can retry, or push the package instead."
        )

        return _post_message(
            bot_token=bot_token,
            channel=channel_id,
            user=user_id,
            text=deprecate_failed_text,
            thread_ts=main_message_ts,
            ephemeral=True,
        )

    # ----------------------------------------------------
    # Decline push notifications
    # ----------------------------------------------------

    elif slack_notification_type == "PUSH_DECLINED":

        # The user chose not to push and not to deprecate: the package stays active.
        # Update the main card to a declined state and strip the buttons from the
        # package-ready message so no further push/deprecate can be triggered from it.
        declined_card_blocks = _build_main_message_blocks(
            job_name, package_name, ':heavy_multiplication_x: Push declined'
        )

        main_message_update_response = _update_message(
            bot_token=bot_token,
            channel=channel_id,
            ts=main_message_ts,
            blocks=declined_card_blocks,
        )

        # Update the package-ready message without a blocks payload, which removes the
        # Push, Don't Push and Deprecate buttons.
        declined_details_text = (
            f"*Package ID:* `{package_id}`\n"
            f"*Share Destination:* `{share_destination}`\n"
        )

        package_ready_message_update_response = _update_message(
            bot_token=bot_token,
            channel=channel_id,
            ts=package_ready_message_ts,
            text=declined_details_text,
        )

        # Post a thread reply showing who declined the push.
        declined_text = (
            f"*Push declined* by <@{user_id}>."
        )

        declined_message_response = _post_message(
            bot_token=bot_token,
            channel=channel_id,
            thread_ts=main_message_ts,
            text=declined_text,
        )

        return {
            "mainMessageOk": main_message_update_response.get("ok"),
            "mainMessageError": main_message_update_response.get("error"),
            "packageReadyMessageOk": package_ready_message_update_response.get("ok"),
            "packageReadyMessageError": package_ready_message_update_response.get("error"),
            "declinedMessageOk": declined_message_response.get("ok"),
            "declinedMessageError": declined_message_response.get("error"),
        }

    # ----------------------------------------------------
    # Expiry notifications
    # ----------------------------------------------------

    elif slack_notification_type == "PACKAGE_EXPIRED":

        # Only overwrite the main card if it is still the original "Awaiting review"
        # message. If it was already updated (push / completed / deprecated), leave it
        # and just add the expiry note in the thread.
        main_message_update_response = {}
        package_ready_message_update_response = {}
        if not _main_message_was_updated(bot_token, channel_id, main_message_ts):
            # Update the main message status to "Package expired".
            expired_card_blocks = _build_main_message_blocks(
                job_name, package_name, ':heavy_multiplication_x: Package expired'
            )

            main_message_update_response = _update_message(
                bot_token=bot_token,
                channel=channel_id,
                ts=main_message_ts,
                blocks=expired_card_blocks,
            )

            # Update the package-ready message without a blocks payload, which removes
            # both the Push and Deprecate buttons. An expired package's report is no
            # longer accessible, so we drop the report link and keep the core details.
            expired_details_text = (
                f"*Package ID:* `{package_id}`\n"
                f"*Share Destination:* `{share_destination}`\n"
            )

            package_ready_message_update_response = _update_message(
                bot_token=bot_token,
                channel=channel_id,
                ts=package_ready_message_ts,
                text=expired_details_text,
            )

        # Post a thread reply noting the expiry. Use Slack's <!date> token so the
        # timestamp renders in each viewer's own local timezone; the text after the
        # pipe is the fallback shown if Slack can't format it.
        expiry_epoch = int(datetime.now(timezone.utc).timestamp())
        expiry_when = (
            f"<!date^{expiry_epoch}^{{date_short_pretty}} at {{time}}"
            f"|{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}>"
        )
        expired_text = (
            f"*Package expired* ({expiry_when})."
        )

        expired_message_response = _post_message(
            bot_token=bot_token,
            channel=channel_id,
            thread_ts=main_message_ts,
            text=expired_text,
        )

        return {
            "mainMessageOk": main_message_update_response.get("ok"),
            "mainMessageError": main_message_update_response.get("error"),
            "packageReadyMessageOk": package_ready_message_update_response.get("ok"),
            "packageReadyMessageError": package_ready_message_update_response.get("error"),
            "expiredMessageOk": expired_message_response.get("ok"),
            "expiredMessageError": expired_message_response.get("error"),
        }

    # ----------------------------------------------------
    # Unknown action: the action id didn't match any known button.
    # Nothing is triggered; just tell the user.
    # ----------------------------------------------------

    elif slack_notification_type == "UNKNOWN_ACTION":
        unknown_action_text = ":warning: Unrecognised action."

        return _post_message(
            bot_token=bot_token,
            channel=channel_id,
            user=user_id,
            text=unknown_action_text,
            thread_ts=main_message_ts,
            ephemeral=True,
        )

    else:
        return {
            "ok": False,
            "error": f"Unknown slackNotificationType: {slack_notification_type}",
        }
