import time
import hmac
import hashlib
import boto3



def _extract_value_from_headers(h: str, key: str) -> str | None:
    needle = f"{key}="
    i = h.find(needle)
    if i == -1:
        return None
    start = i + len(needle)
    end = h.find(", ", start)
    if end == -1:
        end = h.rfind("}")
        if end == -1:
            end = len(h)
    return h[start:end]


def _get_signing_secret():
    _sm = boto3.client("secretsmanager")
    return _sm.get_secret_value(SecretId="auto-data-sharing-slack-signing-secret")["SecretString"] # pragma: allowlist secret


def _constant_time_equals(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))


def _verify_slack_signature(signing_secret: str, timestamp: str, body: str, slack_signature: str) -> bool:
    # Slack basestring: "v0:{timestamp}:{raw_body}"
    basestring = f"v0:{timestamp}:{body}".encode("utf-8")
    digest = hmac.new(signing_secret.encode("utf-8"), basestring, hashlib.sha256).hexdigest()
    expected = f"v0={digest}"
    return _constant_time_equals(expected, slack_signature)



def handler(event, context):
    """
    Verifies that a Slack request is valid using signing secret.
    Implements replay protection by checking timestamp is recent.
    Expects event to have:
      - headers: stringified dict of headers
      - slackBody: raw body of the Slack request
      Returns dict with:
      - verified: bool
      - slackBody: raw body of the Slack request (if verified)

    """

    headers_str = event.get("headers")
    timestamp = _extract_value_from_headers(headers_str, "X-Slack-Request-Timestamp")
    sig = _extract_value_from_headers(headers_str, "X-Slack-Signature")
    slack_body = event.get("slackBody")

    # Check is signature valid
    signing_secret = _get_signing_secret()
    if not _verify_slack_signature(signing_secret, timestamp, slack_body, sig):
        print ("Invalid Slack signature")
        return {"verified": False, "slackBody": None}

    # Replay protection: max age of request
    MAX_AGE_SECONDS = 60 * 5  # 5 minutes
    try:
        timestamp_int = int(timestamp)
    except ValueError:
        print ("Invalid timestamp")
        return {"verified": False, "slackBody": None}

    now = int(time.time())
    if abs(now - timestamp_int) > MAX_AGE_SECONDS:
        print ("Request timestamp too old")
        return {"verified": False, "slackBody": None}



    # Success: pass slack_body through
    return {"verified": True, "slackBody": slack_body}
