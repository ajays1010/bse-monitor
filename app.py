import os
import threading
import time
import requests
import schedule
from datetime import datetime, timedelta
from flask import Flask

from fetcher import get_bse_announcements  # your existing fetcher function

# ─── Configuration ─────────────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "<YOUR_TOKEN_HERE>")
TELEGRAM_CHAT_IDS = [
    "<CHAT_ID_1>",
    # "<CHAT_ID_2>",
]
SCRIPT_CODES = [
    "500325",  # Reliance
    "526861",  # Example
    # add more here…
]

FETCH_INTERVAL_MINUTES = 5
DAYS_LOOKBACK = 2  # include today + previous 2 days

# ─── Flask + App Setup ──────────────────────────────────────────────────────────
app = Flask(__name__)

def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)

# ─── Telegram helper ────────────────────────────────────────────────────────────
def send_telegram(chat_id, text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    resp = requests.post(url, data={
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }, timeout=10)
    resp.raise_for_status()
    log(f"Sent to {chat_id}")

# ─── In-memory seen cache ───────────────────────────────────────────────────────
# (resets on deploy; for prod you'd persist this)
_seen = set()  # holds tuples (scrip_code, news_id)

# ─── Worker function ────────────────────────────────────────────────────────────
def check_announcements():
    log("🔄 Worker: starting cycle")
    cutoff = datetime.now() - timedelta(days=DAYS_LOOKBACK)

    for code in SCRIPT_CODES:
        log(f"→ fetching announcements for {code}")
        anns = get_bse_announcements(code, num_announcements=50)
        log(f"   fetched {len(anns)} announcements")

        for ann in anns:
            raw_dt = ann["Date"]
            # parse ISO or fallback to date-only
            try:
                dt = datetime.fromisoformat(raw_dt)
            except Exception:
                dt = datetime.strptime(raw_dt.split(" ")[0], "%Y-%m-%d")

            if dt < cutoff:
                log(f"   ↳ {raw_dt} too old, skipping")
                continue

            # use NEWSID or XBRL link param as unique ID
            nid = ann.get("XBRL Link", "").split("Bsenewid=")[-1].split("&")[0]
            key = (code, nid)
            if key in _seen:
                log(f"   ↳ already sent {nid}, skipping")
                continue

            # New announcement! send it
            msg = (
                f"📢 <b>Scrip {code}</b>\n"
                f"🕒 {ann['Date']}\n"
                f"🔗 <a href='{ann['PDF Link']}'>PDF</a>\n"
                f"📰 {ann['Title']}"
            )
            for chat in TELEGRAM_CHAT_IDS:
                try:
                    send_telegram(chat, msg)
                except Exception as e:
                    log(f"   ❌ Telegram error for {chat}: {e}")

            _seen.add(key)

    log("✅ Worker: cycle complete\n")

def start_worker():
    # run once immediately
    check_announcements()
    # schedule every FETCH_INTERVAL_MINUTES
    schedule.every(FETCH_INTERVAL_MINUTES).minutes.do(check_announcements)
    while True:
        schedule.run_pending()
        time.sleep(1)

# ─── Ping endpoint for UptimeRobot ──────────────────────────────────────────────
@app.route("/ping", methods=["GET"])
def ping():
    return "pong", 200

# ─── Kick off worker on first request ──────────────────────────────────────────
@app.before_first_request
def launch_worker():
    t = threading.Thread(target=start_worker, daemon=True)
    t.start()
    log("🧵 Background worker launched")

# ─── Run Flask ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # local dev
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
