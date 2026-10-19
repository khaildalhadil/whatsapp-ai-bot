"""
WhatsApp AI Bot - main entry point.

Part 1: a minimal web server, just to confirm everything runs.
Part 2: the webhook. Meta verifies our server, then sends us every incoming message.
Part 3: the reply. We send a message back through the WhatsApp API.
Part 4: the AI. OpenAI writes the answer instead of repeating the user's message.
Part 5: bookings. The AI checks and books pitch hours in bookings.xlsx (see bookings.py).
"""
import json
import os
from datetime import timedelta

import requests
from dotenv import load_dotenv
from flask import Flask, request, send_from_directory

import bookings

# Load variables from the .env file (token, phone number ID, ...).
# On Azure there is no .env file: the same variables are set in the portal instead.
load_dotenv()

# Our WhatsApp credentials (from Meta dashboard > WhatsApp > API Setup).
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")

# Our OpenAI key (from platform.openai.com > API keys) and the model that answers.
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.4-mini")


def system_prompt():
    """The bot's instructions. Built again for every message so "today" is always right."""
    today = bookings.now().date()
    # Spell out the next 7 days, so the AI never miscalculates which date "Friday" is.
    next_days = ", ".join((today + timedelta(days=d)).strftime("%A %Y-%m-%d") for d in range(7))
    return (
        "You are the WhatsApp booking assistant of a tartan (artificial grass) football pitch. "
        f"The pitch is open every day from {bookings.OPEN_HOUR}:00 to midnight. Each booking is 1 hour. "
        f"Today is {today.strftime('%A %Y-%m-%d')}. The next 7 days are: {next_days}. "
        "When the customer asks about a day or time, call check_day to read the bookings table. Never guess. "
        "An hour without AM/PM, like 8, means 8 PM (20:00), because the pitch opens in the evening. "
        "To book: ask for the customer's name and phone number, then call book_slot. "
        "Only say the booking is done if book_slot returns ok; otherwise explain the reason. "
        "Never share other customers' names or phone numbers. "
        "Always reply in the same language the customer writes in, short and clear like a chat message, "
        "in plain text without Markdown headings or tables."
    )


# The tools the AI is allowed to use. OpenAI reads these descriptions to decide
# when to call them; our code (ask_ai below) actually runs them.
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "check_day",
            "description": "Get the booked and free hours of the pitch on one date.",
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": {"date": {"type": "string", "description": "The date, as YYYY-MM-DD"}},
                "required": ["date"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "book_slot",
            "description": "Book one hour of the pitch for a customer.",
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {"type": "string", "description": "The date, as YYYY-MM-DD"},
                    "hour": {"type": "integer", "description": "Start hour in 24h format, e.g. 20 for 8 PM"},
                    "name": {"type": "string", "description": "The customer's name"},
                    "phone": {"type": "string", "description": "The customer's phone number"},
                },
                "required": ["date", "hour", "name", "phone"],
                "additionalProperties": False,
            },
        },
    },
]
TOOL_FUNCTIONS = {"check_day": bookings.check_day, "book_slot": bookings.book_slot}

# Meta may send the same message twice (for example when the AI takes long to answer).
# We remember the IDs we already handled, so we never reply twice to one message.
# ponytail: kept in memory, so it resets on restart and isn't shared between Azure workers;
# move it to a database if duplicate replies show up there.
handled_message_ids = set()

# Each person's recent messages, so the AI understands follow-up questions
# like "and how much does it cost?". Key = phone number, value = list of messages.
# ponytail: kept in memory, so it resets on restart and isn't shared between Azure workers;
# move it to a database if conversations need to survive restarts.
conversations = {}
MAX_HISTORY = 10  # messages kept per person (5 questions + 5 answers)

# Azure (gunicorn) looks for a variable named "app" inside app.py to start the server.
app = Flask(__name__)


def ask_ai(history):
    """Send the conversation so far to OpenAI and return the AI's next answer.

    history is a list like [{"role": "user", "content": "hi"}, {"role": "assistant", ...}, ...]
    """
    # The instructions first, then the conversation, so the AI sees the whole context.
    messages = [{"role": "system", "content": system_prompt()}] + history

    try:
        # The AI may need a few rounds: check the table, then book, then write the answer.
        for _ in range(5):
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
                json={"model": OPENAI_MODEL, "messages": messages, "tools": TOOLS},
                timeout=60,
            )
            response.raise_for_status()  # turns an error answer (wrong key, no credit, ...) into an exception
            answer = response.json()["choices"][0]["message"]

            if not answer.get("tool_calls"):
                return answer["content"]  # a normal text answer: we're done

            # The AI asked to use one or more tools: run them and give it the results.
            messages.append(answer)
            for call in answer["tool_calls"]:
                name = call["function"]["name"]
                args = json.loads(call["function"]["arguments"])
                try:
                    result = TOOL_FUNCTIONS[name](**args)
                except Exception as error:  # e.g. a badly written date from the AI
                    result = {"ok": False, "reason": f"Error: {error}"}
                print(f"Tool {name}({args}) -> {result}", flush=True)
                messages.append({
                    "role": "tool",
                    "tool_call_id": call["id"],
                    "content": json.dumps(result, ensure_ascii=False),
                })
    except requests.RequestException as error:
        # Print the real reason for us, and send the user a polite message instead.
        reason = error.response.text if error.response is not None else error
        print(f"OpenAI error: {reason}", flush=True)

    return "Sorry, I can't answer right now. Please try again in a moment."


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


@app.get("/privacy")
def privacy():
    # Meta needs a public privacy policy link before the app can be published.
    # The page itself is the privacy.html file next to this one.
    return send_from_directory(app.root_path, "privacy.html")


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
                if message["id"] in handled_message_ids:
                    continue  # already answered this one
                handled_message_ids.add(message["id"])

                sender = message["from"]  # the sender's phone number, e.g. "9665xxxxxxxx"

                if message["type"] == "text":
                    text = message["text"]["body"]
                    # flush=True makes the line show up right away (also in Azure's log stream).
                    print(f"Message from {sender}: {text}", flush=True)

                    # Add the new message to this person's conversation, ask the AI,
                    # then save the answer too and forget the oldest messages.
                    history = conversations.setdefault(sender, [])
                    history.append({"role": "user", "content": text})
                    reply = ask_ai(history)
                    history.append({"role": "assistant", "content": reply})
                    del history[:-MAX_HISTORY]
                else:
                    # Images, voice notes, stickers, ... The AI only reads text for now.
                    print(f"Message from {sender}: <{message['type']} message>", flush=True)
                    reply = "Sorry, I can only read text messages for now."

                send_message(sender, reply)

    # Always answer 200 quickly. Otherwise Meta thinks we failed and keeps resending the event.
    return "OK", 200


if __name__ == "__main__":
    # This block only runs locally with "python app.py".
    # On Azure, gunicorn imports "app" directly, so this part is skipped.
    port = int(os.getenv("PORT", 8000))
    app.run(port=port, debug=True)
