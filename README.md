# WhatsApp AI Bot

A WhatsApp booking bot for a tartan football pitch, built with Python + Flask and the
WhatsApp Cloud API (Meta). OpenAI writes the replies and books hours in a SQLite database,
and a web dashboard shows the bookings. It will be deployed to Azure App Service.

## The bookings dashboard

Open http://localhost:8000/dashboard (or the tunnel/Azure URL + `/dashboard`).
The browser asks for a login: user `admin`, password = `DASHBOARD_PASSWORD` from `.env`.

It shows today's numbers, a weekly grid (days x hours) and the list of upcoming bookings
with the customers' numbers. It reloads by itself every minute.

The bookings are saved in `bookings.db` (SQLite, one file, comes with Python). One row per
booked hour: date, hour, name, phone (8-digit Omani number, without 968). The database is
created with sample bookings the first time the bot runs. To reset it to sample bookings:

```powershell
python bookings.py
```

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
5. **Bookings** (done): the AI checks free hours and books them in the database
6. **Dashboard** (done): a password-protected page that shows the bookings
7. Deploy to Azure
