"""
Quick check for the webhook, without Meta or the internet.
Run it with:  python test_webhook.py
"""
import io
from contextlib import redirect_stdout

from app import app

client = app.test_client()

# 1. Meta's verification (any verify token) -> we must echo the challenge.
r = client.get("/webhook?hub.mode=subscribe&hub.verify_token=anything&hub.challenge=12345")
assert r.status_code == 200 and r.get_data(as_text=True) == "12345"

# 2. Not a subscribe request -> refused.
r = client.get("/webhook?hub.challenge=12345")
assert r.status_code == 403

# 3. An incoming text message, shaped like the JSON Meta really sends.
message_event = {
    "object": "whatsapp_business_account",
    "entry": [{"changes": [{"field": "messages", "value": {
        "messages": [{"from": "966500000000", "type": "text", "text": {"body": "hello"}}],
    }}]}],
}
output = io.StringIO()
with redirect_stdout(output):
    r = client.post("/webhook", json=message_event)
assert r.status_code == 200
assert "Message from 966500000000: hello" in output.getvalue()

# 4. A status update (no "messages" list) -> still 200, nothing printed.
status_event = {"entry": [{"changes": [{"value": {"statuses": [{"status": "read"}]}}]}]}
assert client.post("/webhook", json=status_event).status_code == 200

print("All webhook checks passed")
