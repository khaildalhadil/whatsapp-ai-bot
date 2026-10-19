"""
WhatsApp AI Bot - main entry point.

Part 1: a minimal web server, just to confirm everything runs.
Part 2: the webhook. Meta verifies our server, then sends us every incoming message.
Part 3: the reply. We send a message back through the WhatsApp API (echo for now).
"""
import os

import requests
from dotenv import load_dotenv
from flask import Flask, request

# Load variables from the .env file (token, phone number ID, ...).
# On Azure there is no .env file: the same variables are set in the portal instead.
load_dotenv()

# Our WhatsApp credentials (from Meta dashboard > WhatsApp > API Setup).
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")

# Azure (gunicorn) looks for a variable named "app" inside app.py to start the server.
app = Flask(__name__)


def send_message(to, text):
    """Send a WhatsApp text message to the phone number "to"."""
    url = f"https://graph.facebook.com/v23.0/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}"}
    body = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text},
    }

    try:
        response = requests.post(url, headers=headers, json=body, timeout=10)
    except requests.RequestException as error:
        # No internet, timeout, ... We print it instead of crashing the webhook.
        print(f"Could not reach WhatsApp: {error}", flush=True)
        return

    if not response.ok:
        # Common reasons: the token expired, or (test number) the recipient
        # is not in the allowed list in Meta's API Setup page.
        print(f"WhatsApp refused the message: {response.text}", flush=True)


@app.get("/")
def health():
    # Health check: open http://localhost:8000 in the browser and you should see this text.
    return "WhatsApp bot is running"


@app.get("/webhook")
def verify_webhook():
    # Meta calls this once, when you click "Verify and save" in the dashboard.
    # It sends a "challenge" number; we send it back and Meta saves the webhook.
    # We don't check the "Verify token" field, so you can type anything there.
    mode = request.args.get("hub.mode")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe":
        return challenge, 200
    return "Verification failed", 403


@app.post("/webhook")
def receive_message():
    # Meta calls this every time something happens on our number:
    # a new message, or a status update (sent / delivered / read).
    data = request.get_json(silent=True) or {}

    # The JSON is nested: entry -> changes -> value -> messages.
    # Status updates have no "messages" list, so the loop simply skips them.
    for entry in data.get("entry", []):
        for change in entry.get("changes", []):
            for message in change.get("value", {}).get("messages", []):
                sender = message["from"]  # the sender's phone number, e.g. "9665xxxxxxxx"

                if message["type"] == "text":
                    text = message["text"]["body"]
                else:
                    text = f"<{message['type']} message>"  # image, audio, sticker, ...

                # flush=True makes the line show up right away (also in Azure's log stream).
                print(f"Message from {sender}: {text}", flush=True)

                # Reply with the same text (echo). Part 4 will replace this with an AI answer.
                send_message(sender, f"You said: {text}")

    # Always answer 200 quickly. Otherwise Meta thinks we failed and keeps resending the event.
    return "OK", 200


if __name__ == "__main__":
    # This block only runs locally with "python app.py".
    # On Azure, gunicorn imports "app" directly, so this part is skipped.
    port = int(os.getenv("PORT", 8000))
    app.run(port=port, debug=True)
