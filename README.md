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

Run the webhook check (no internet needed):

```powershell
python test_webhook.py
```

## Connect the webhook to Meta (local testing)

Meta needs a public HTTPS URL, so we expose `localhost:8000` with a tunnel.

1. Install cloudflared once: `winget install --id Cloudflare.cloudflared`
   (no winget? download `cloudflared-windows-amd64.exe` from
   https://github.com/cloudflare/cloudflared/releases/latest and rename it to `cloudflared.exe`)
2. Keep `python app.py` running, then in a second terminal:
   `cloudflared tunnel --url http://localhost:8000`
   It prints a URL like `https://something.trycloudflare.com`.
3. Meta dashboard > WhatsApp > Configuration > Webhook > Edit:
   - Callback URL: `https://something.trycloudflare.com/webhook`
   - Verify token: type anything (Meta requires the field, our server doesn't check it)
   - Click **Verify and save**
4. Same page > Webhook fields > subscribe to **messages**.
5. Send a WhatsApp message to the test number. It shows up in the `python app.py` terminal.

The tunnel URL changes every time you restart cloudflared, so update it in Meta when it does.

## Project parts

1. **Project setup** (done): Flask server + health check
2. **Webhook** (done): Meta verifies our server and sends us incoming messages
3. Reply: send a message back through the WhatsApp API
4. AI: generate smart replies
5. Deploy to Azure
