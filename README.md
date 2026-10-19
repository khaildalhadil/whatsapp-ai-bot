# WhatsApp AI Bot

A WhatsApp booking bot for a tartan football pitch, built with Python + Flask and the
WhatsApp Cloud API (Meta). OpenAI writes the replies, and reads/writes the bookings table
in `bookings.xlsx`. It will be deployed to Azure App Service.

## The bookings table

`bookings.xlsx` has one row per booked hour: `Date | Day | Time | Name | Phone`.
It is created with sample data the first time the bot runs. To reset it to sample data:

```powershell
python bookings.py
```

Close the file in Excel before people book: Excel locks it while it's open.

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

Run the checks (no internet needed):

```powershell
python test_webhook.py
python test_bookings.py
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
3. **Reply** (done): send a message back through the WhatsApp API
4. **AI** (done): OpenAI writes the replies and remembers each person's last 10 messages
   (needs `OPENAI_API_KEY` in `.env`)
5. **Bookings** (done): the AI checks free hours and books them in `bookings.xlsx`
6. Deploy to Azure
