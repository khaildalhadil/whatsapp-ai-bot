"""
WhatsApp AI Bot - main entry point.

Part 1: a minimal web server, just to confirm everything runs.
Part 2: the webhook. Meta verifies our server, then sends us every incoming message.
Next parts will add the replies.
"""
import os

from dotenv import load_dotenv
from flask import Flask, request

# Load variables from the .env file (token, phone number ID, ...).
# On Azure there is no .env file: the same variables are set in the portal instead.
load_dotenv()

# The secret word we also type in Meta's webhook settings.
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")

# Azure (gunicorn) looks for a variable named "app" inside app.py to start the server.
app = Flask(__name__)


@app.get("/")
def health():
    # Health check: open http://localhost:8000 in the browser and you should see this text.
    return "WhatsApp bot is running"


@app.get("/webhook")
def verify_webhook():
    # Meta calls this once, when you click "Verify and save" in the dashboard.
    # It sends 3 values in the URL. If the token matches ours, we send back the challenge
    # and Meta knows this server is really ours.
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    # "VERIFY_TOKEN and" stops an empty token from matching an empty .env value.
    if mode == "subscribe" and VERIFY_TOKEN and token == VERIFY_TOKEN:
        return challenge, 200
    return "Verification failed", 403


@app.post("/webhook")
def receive_message():
    # Meta calls this every time something happens on our number:
    # a new message, or a status update (sent / delivered / read).
    # TODO before deploying: check the X-Hub-Signature-256 header so only Meta can call this.
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

    # Always answer 200 quickly. Otherwise Meta thinks we failed and keeps resending the event.
    return "OK", 200


if __name__ == "__main__":
    # This block only runs locally with "python app.py".
    # On Azure, gunicorn imports "app" directly, so this part is skipped.
    port = int(os.getenv("PORT", 8000))
    app.run(port=port, debug=True)
