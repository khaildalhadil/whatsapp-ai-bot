# WhatsApp AI Bot

A WhatsApp bot built with Python + Flask, using the WhatsApp Cloud API (Meta).
It will be deployed to Azure App Service.

## Run locally (Windows PowerShell)

```powershell
# 1. Create and activate the virtual environment (first time only)
python -m venv .venv
.venv\Scripts\Activate.ps1

# 2. Install the packages
pip install -r requirements.txt

# 3. Create your secrets file and fill it in
copy .env.example .env

# 4. Start the server
python app.py
```

Then open http://localhost:8000. You should see `WhatsApp bot is running`.

## Project parts

1. **Project setup** (done): Flask server + health check
2. Webhook: Meta verifies our server and sends us incoming messages
3. Reply: send a message back through the WhatsApp API
4. AI: generate smart replies
5. Deploy to Azure
