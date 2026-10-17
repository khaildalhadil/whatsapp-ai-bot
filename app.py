"""
WhatsApp AI Bot - main entry point.

Part 1: a minimal web server, just to confirm everything runs.
Next parts will add the WhatsApp webhook and the replies.
"""
import os

from dotenv import load_dotenv
from flask import Flask

# Load variables from the .env file (token, phone number ID, ...).
# On Azure there is no .env file: the same variables are set in the portal instead.
load_dotenv()

# Azure (gunicorn) looks for a variable named "app" inside app.py to start the server.
app = Flask(__name__)


@app.get("/")
def health():
    # Health check: open http://localhost:8000 in the browser and you should see this text.
    return "WhatsApp bot is running"


if __name__ == "__main__":
    # This block only runs locally with "python app.py".
    # On Azure, gunicorn imports "app" directly, so this part is skipped.
    port = int(os.getenv("PORT", 8000))
    app.run(port=port, debug=True)
