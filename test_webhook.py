"""
Quick check for the webhook, without Meta, OpenAI or the internet.
Run it with:  python test_webhook.py
"""
import io
from contextlib import redirect_stdout

import app as bot

# Replace the real send_message and ask_ai with fake ones.
# This way the test never sends a real WhatsApp message and never calls OpenAI.
sent = []
bot.send_message = lambda to, text: sent.append((to, text))
bot.ask_ai = lambda text: f"AI answer to: {text}"

client = bot.app.test_client()

# 1. Meta's verification (any verify token) -> we must echo the challenge.
r = client.get("/webhook?hub.mode=subscribe&hub.verify_token=anything&hub.challenge=12345")
assert r.status_code == 200 and r.get_data(as_text=True) == "12345"

# 2. Not a subscribe request -> refused.
r = client.get("/webhook?hub.challenge=12345")
assert r.status_code == 403

# 3. An incoming text message, shaped like the JSON Meta really sends -> printed and answered by the AI.
message_event = {
    "object": "whatsapp_business_account",
    "entry": [{"changes": [{"field": "messages", "value": {
        "messages": [{"id": "wamid.1", "from": "966500000000", "type": "text", "text": {"body": "hello"}}],
    }}]}],
}
output = io.StringIO()
with redirect_stdout(output):
    r = client.post("/webhook", json=message_event)
assert r.status_code == 200
assert "Message from 966500000000: hello" in output.getvalue()
assert sent == [("966500000000", "AI answer to: hello")]

# 4. Meta sends the same message again -> no second reply.
client.post("/webhook", json=message_event)
assert len(sent) == 1

# 5. A status update (no "messages" list) -> still 200, and no reply sent.
status_event = {"entry": [{"changes": [{"value": {"statuses": [{"status": "read"}]}}]}]}
assert client.post("/webhook", json=status_event).status_code == 200
assert len(sent) == 1

# 6. An image -> a polite "text only" reply, without calling the AI.
image_event = {"entry": [{"changes": [{"value": {
    "messages": [{"id": "wamid.2", "from": "966500000000", "type": "image", "image": {}}],
}}]}]}
client.post("/webhook", json=image_event)
assert sent[-1] == ("966500000000", "Sorry, I can only read text messages for now.")

# 7. The privacy policy page that Meta links to.
assert client.get("/privacy").status_code == 200

print("All webhook checks passed")
