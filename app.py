# app.py
import os
import threading
import time
import requests
import schedule
from datetime import datetime, timedelta
from flask import Flask, jsonify
from supabase import create_client
from fetcher import get_bse_announcements  # your existing fetcher

# ─── Configuration ──────────────────────────────────────────────────────────────
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not all([SUPABASE_URL, SUPABASE_KEY, TELEGRAM_BOT_TOKEN]):
    raise RuntimeError("Set SUPABASE_URL, SUPABASE_KEY & TELEGRAM_BOT_TOKEN env vars")

# Worker settings
DAYS_TO_FETCH = 2     # today + past 2 days
INTERVAL_MINUTES = 5  # run every 5 minutes

# ─── Initialize ────────────────────────────────────────────────────────────────
app = Flask(__name__)
sb  = create_client(SUPABASE_URL, SUPABASE_KEY)

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)

# ─── Supabase helpers ───────────────────────────────────────────────────────────
def load_config():
    """Returns ({code:company}, [chat_id,…])."""
    # monitored_scrips
    r1 = sb.table("monitored_scrips").select("bse_code,company_name").execute()
    scrips = {row["bse_code"]: row["company_name"] for row in (r1.data or [])}
    # telegram_recipients
    r2 = sb.table("telegram_recipients").select("chat_id").execute()
    chats = [row["chat_id"] for row in (r2.data or [])]
    log(f"Loaded {len(scrips)} scripts, {len(chats)} chat IDs")
    return scrips, chats

def load_seen_ids(code):
    """Returns set of news_id already sent for this scrip."""
    res = sb.table("seen_announcements") \
            .select("news_id") \
            .eq("scrip_code", code) \
            .execute()
    return {row["news_id"] for row in (res.data or [])}

def mark_seen_id(code, news_id):
    """Inserts (code,news_id), ignores duplicates."""
    try:
        sb.table("seen_announcements") \
          .insert({"scrip_code": code, "news_id": news_id}) \
          .execute()
    except Exception as e:
        # duplicate key, etc
        log(f"❗ Could not mark seen ({code},{news_id}): {e}")

# ─── Telegram ──────────────────────────────────────────────────────────────────
def send_telegram(chat_id, text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    resp = requests.post(url, data={"chat_id": chat_id, "text": text, "parse_mode": "HTML"}, timeout=10)
    resp.raise_for_status()

# ─── Worker task ────────────────────────────────────────────────────────────────
def check_announcements():
    log("🔄 Worker cycle start")
    scrips, chats = load_config()
    cutoff = datetime.now() - timedelta(days=DAYS_TO_FETCH)
    for code, name in scrips.items():
        log(f"→ {code} ({name}): fetching announcements…")
        try:
            anns = get_bse_announcements(code, num_announcements=50)
        except Exception as e:
            log(f"⚠️ Fetch error for {code}: {e}")
            continue

        seen = load_seen_ids(code)
        newly = []
        for ann in anns:
            # parse date
            try:
                dt = datetime.fromisoformat(ann["Date"])
            except Exception:
                # fallback: assume "YYYY-MM-DD ..." prefix
                dt = datetime.strptime(ann["Date"].split(" ")[0], "%Y-%m-%d")
            if dt < cutoff:  
                continue
            # identify
            news_id = ann["XBRL Link"].split("Bsenewid=")[-1].split("&")[0]
            if news_id in seen:
                continue
            newly.append((news_id, ann))

        log(f"  ↳ {len(newly)} new announcements")
        for nid, ann in newly:
            msg = (
                f"📢 <b>{name}</b> ({code})\n"
                f"🕒 {ann['Date']}\n"
                f"🔗 <a href='{ann['PDF Link']}'>PDF</a>"
            )
            for chat in chats:
                try:
                    send_telegram(chat, msg)
                    log(f"    ✔️ Sent to {chat}: {ann['Title']}")
                except Exception as e:
                    log(f"    ❌ Telegram error for {chat}: {e}")
            mark_seen_id(code, nid)

    log("✅ Worker cycle complete")

def start_worker():
    # run once immediately
    check_announcements()
    schedule.every(INTERVAL_MINUTES).minutes.do(check_announcements)
    while True:
        schedule.run_pending()
        time.sleep(1)

# ─── Ping endpoint (for UptimeRobot) ────────────────────────────────────────────
@app.route("/ping")
def ping():
    return "pong", 200

# ─── Entrypoint ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    t = threading.Thread(target=start_worker, daemon=True)
    t.start()
    # Flask app on arbitrary port—Render will route it but we won't use it for HTTP
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
