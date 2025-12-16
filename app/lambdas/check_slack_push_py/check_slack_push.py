import json
import boto3
from urllib.parse import parse_qs

def _event_from_slack_body(slack_body: str) -> dict:
    """
    Convert the raw Slack body (application/x-www-form-urlencoded;
    Example slack_body: "payload=%7B%22type%22%3A%22block_actions%22,...%7D")
    into:
      {
        "id": "pkg.xxx",
        "packageName": "...",
        "shareDestination": "s3://...",
        "user_id": "U…",
        "channel_id": "C…",
        "message_ts": "17-digit-ts"
      }
    """
    #
    params = parse_qs(slack_body)
    payload_str = params.get("payload", ["{}"])[0]
    slack_payload = json.loads(payload_str)

    user = slack_payload.get("user")
    user_id = user.get("id")

    container = slack_payload.get("container")
    channel_id = container.get("channel_id")
    message_ts = container.get("message_ts")

    action = slack_payload.get("actions")[0]
    raw_value = action.get("value")

    value = json.loads(raw_value)

    package_id = value.get("packageId")
    package_name = value.get("packageName")
    share_destination = value.get("shareDestination")

    return {
      "packageId": package_id,
      "packageName": package_name,
      "shareDestination": share_destination,
      "userId": user_id,
      "channelId": channel_id,
      "messageTs": message_ts
    }



def _get_allowed_users() -> list[str]:
    """
    Read the Slack allowed users secret and return a list of user IDs.

    Secret format (JSON string):
      [
        {"username": "<some-username>", "id": "<SLACK_USER_ID>"},
        ...
      ]
    """
    resp = boto3.client("secretsmanager").get_secret_value(SecretId="auto-data-sharing-slack-allowed-users") # pragma: allowlist secret
    secret_str = resp["SecretString"]

    data = json.loads(secret_str)

    # Extract just the IDs from any dict entries that have an "id" string
    ids: list[str] = []
    for entry in data:
        if isinstance(entry, dict):
            user_id = entry.get("id")
            if isinstance(user_id, str):
                ids.append(user_id)

    return ids





def handler(event, context):

  """
  Lambda handler to trigger the push step in the data sharing auto_push workflow.
  """
  event_data = _event_from_slack_body(event["slackBody"])
  allowed_users = _get_allowed_users()

  package_id = event_data.get("packageId")
  package_name = event_data.get("packageName")
  share_destination = event_data.get("shareDestination")
  user_id = event_data.get("userId")
  channel_id = event_data.get("channelId")
  message_ts = event_data.get("messageTs")
  userAllowed = user_id in allowed_users


  return {
      "userAllowed": userAllowed,
      "packageId": package_id,
      "packageName": package_name,
      "shareDestination": share_destination,
      "userId": user_id,
      "channelId": channel_id,
      "messageTs": message_ts,
  }
