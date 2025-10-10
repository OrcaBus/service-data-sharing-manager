import json, urllib.request

WEBHOOK_URL = "A_WEBHOOK_URL_SHOULD_BE_HERE"

def handler(event, _ctx):
    text = event.get("message")
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
