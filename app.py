import os
import json
import time
import threading
from flask import Flask, request, jsonify
from supabase import create_client, Client
import requests

app = Flask(__name__)

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
supabase: Client = None

CONFIG_FILE = "monitored_scripts_config.json"
SEEN_FILE = "seen_announcements.json"
LOG_FILE = "telegram_log.txt"

GLOBAL_MONITORED_SCRIPS = {}
GLOBAL_TELEGRAM_CHAT_IDS = []
worker_thread = None


def log_message(msg):
    print(f"[LOG] {msg}")
    with open(LOG_FILE, "a") as f:
        f.write(f"[LOG] {msg}\n")


def get_supabase_client():
    global supabase
    if supabase is None:
        if not SUPABASE_URL or not SUPABASE_KEY:
            log_message("❌ Supabase URL or Key missing.")
            return None
        try:
            supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
            log_message("✅ Supabase client initialized.")
        except Exception as e:
            log_message(f"❌ Supabase client error: {e}")
            supabase = None
    return supabase


def load_config_from_db():
    sb = get_supabase_client()
    if sb is None:
        return

    try:
        log_message("🔄 Loading monitored scrips and chat IDs from Supabase...")
        response_scrips = sb.table("monitored_scrips").select("*").execute()
        response_chats = sb.table("telegram_recipients").select("*").execute()

        scrips = {item["bse_code"]: item["company_name"] for item in response_scrips.data}
        chats = [item["chat_id"] for item in response_chats.data]

        log_message(f"✅ Loaded {len(scrips)} scrips and {len(chats)} chat IDs from Supabase.")

        global GLOBAL_MONITORED_SCRIPS, GLOBAL_TELEGRAM_CHAT_IDS
        GLOBAL_MONITORED_SCRIPS = scrips
        GLOBAL_TELEGRAM_CHAT_IDS = chats

        with open(CONFIG_FILE, "w") as f:
            json.dump(GLOBAL_MONITORED_SCRIPS, f)
    except Exception as e:
        log_message(f"❌ Failed to load config from Supabase: {e}")


def check_for_new_announcements_task():
    log_message("🔥 Worker loop running...")
    while True:
        try:
            load_config_from_db()

            for code, name in GLOBAL_MONITORED_SCRIPS.items():
                log_message(f"👁️ Checking {code} - {name}")
                # Simulate an announcement
                alert_message = f"📢 New test announcement for {name} ({code})"
                for chat_id in GLOBAL_TELEGRAM_CHAT_IDS:
                    send_telegram_message(chat_id, alert_message)
                time.sleep(2)

            time.sleep(300)
        except Exception as e:
            log_message(f"❌ Error in worker loop: {e}")
            time.sleep(60)


def send_telegram_message(chat_id, message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {"chat_id": chat_id, "text": message}
        res = requests.post(url, data=data)
        if res.status_code != 200:
            raise Exception(res.text)
        log_message(f"✅ Sent message to {chat_id}")
    except Exception as e:
        log_message(f"❌ Failed to send message to {chat_id}: {e}")


@app.route("/")
def home():
    return "✅ BSE Monitor Flask App is running!"


@app.route("/debug")
def debug():
    return jsonify({
        "loaded_scrips": list(GLOBAL_MONITORED_SCRIPS.keys()),
        "chat_ids": GLOBAL_TELEGRAM_CHAT_IDS,
        "thread_alive": worker_thread.is_alive() if worker_thread else False
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    log_message("🚀 Flask app starting.")
    worker_thread = threading.Thread(target=check_for_new_announcements_task, daemon=True)
    worker_thread.start()
    log_message("🧵 Background worker thread started.")
    app.run(host="0.0.0.0", port=port)
