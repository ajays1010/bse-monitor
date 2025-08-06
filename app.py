
import os
import time
import threading
import requests
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from supabase import create_client, Client

# Constants
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHECK_INTERVAL = 300  # 5 minutes

app = Flask(__name__)
GLOBAL_MONITORED_SCRIPS = {}
GLOBAL_TELEGRAM_CHAT_IDS = []

# Supabase connection
def get_supabase_client() -> Client:
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("[ERROR] Supabase URL or Key missing.")
        return None
    return create_client(SUPABASE_URL, SUPABASE_KEY)

# Load config
def load_config_from_supabase():
    global GLOBAL_MONITORED_SCRIPS, GLOBAL_TELEGRAM_CHAT_IDS
    sb = get_supabase_client()
    if sb is None:
        print("[ERROR] Supabase not initialized.")
        return

    try:
        scrips_res = sb.table("monitored_scrips").select("*").execute()
        chats_res = sb.table("telegram_recipients").select("*").execute()

        GLOBAL_MONITORED_SCRIPS = {
            item["bse_code"]: item["company_name"] for item in scrips_res.data
        }
        GLOBAL_TELEGRAM_CHAT_IDS = [item["chat_id"] for item in chats_res.data]

        print(f"[LOG] ✅ Loaded {len(GLOBAL_MONITORED_SCRIPS)} scrip codes and {len(GLOBAL_TELEGRAM_CHAT_IDS)} chat IDs from Supabase.")
    except Exception as e:
        print(f"[ERROR] Failed to load config from Supabase: {e}")

# Send alert to Telegram
def send_telegram_alert(message: str):
    for chat_id in GLOBAL_TELEGRAM_CHAT_IDS:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            requests.post(url, data={"chat_id": chat_id, "text": message})
        except Exception as e:
            print(f"[ERROR] Failed to send Telegram message to {chat_id}: {e}")

# Check for new announcements
def check_bse_announcements():
    print(f"[LOG] Worker: Checking BSE announcements at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    sb = get_supabase_client()
    if not sb:
        return

    try:
        for bse_code, company_name in GLOBAL_MONITORED_SCRIPS.items():
            url = f"https://api.bseindia.com/corporates/api/AnnSubCategory/GetData/{bse_code}?strCat=-1&strPrevDate={datetime.today().strftime('%Y-%m-%d')}&strScrip=&strSearch=P"
            res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})

            if res.status_code != 200:
                print(f"[WARN] Could not fetch data for {bse_code}")
                continue

            data = res.json()
            for ann in data.get("Table", []):
                news_id = ann.get("NewsId")
                title = ann.get("Title")
                date_str = ann.get("News_dt")
                pdf_link = f"https://www.bseindia.com/xml-data/corpfiling/AttachLive/{ann.get('Attachment_Name')}" if ann.get("Attachment_Name") else "N/A"

                # Check if already seen
                exists = sb.table("seen_announcements").select("news_id").eq("news_id", news_id).execute()
                if exists.data:
                    continue

                # Save seen
                sb.table("seen_announcements").insert({"news_id": news_id}).execute()

                # Send alert
                msg = (
    f"📢 *{company_name}* ({bse_code})\\n"
    f"📝 {title}\\n"
    f"📅 {date_str}\\n"
    f"📎 {pdf_link}"
)
                send_telegram_alert(msg)

    except Exception as e:
        print(f"[ERROR] Exception while checking BSE announcements: {e}")

# Background worker
def background_worker():
    print("[LOG] 🧵 Background worker thread started.")
    while True:
        load_config_from_supabase()
        if not GLOBAL_MONITORED_SCRIPS:
            print("[LOG] No scrip codes loaded. Skipping announcement check in this cycle.")
        else:
            check_bse_announcements()
        time.sleep(CHECK_INTERVAL)

# UptimeRobot ping
@app.route("/ping", methods=["GET"])
def ping():
    return "pong", 200

# Config APIs
@app.route("/api/config", methods=["GET"])
def get_config_api():
    sb = get_supabase_client()
    if sb is None:
        return jsonify({"status": "error", "message": "Supabase not initialized"}), 500

    try:
        scrips = sb.table("monitored_scrips").select("*").execute().data
        chats = sb.table("telegram_recipients").select("*").execute().data
        return jsonify({
            "scrip_codes": {s["bse_code"]: s["company_name"] for s in scrips},
            "telegram_chat_ids": [c["chat_id"] for c in chats]
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/config", methods=["POST"])
def manage_config_api():
    data = request.get_json()
    action = data.get('action')
    item_type = data.get('type')
    sb = get_supabase_client()
    if sb is None:
        return jsonify({"message": "Supabase not initialized."}), 500

    try:
        if item_type == 'scrip':
            bse_code = data.get('bse_code')
            company_name = data.get('company_name')
            if action == 'add':
                sb.table("monitored_scrips").insert({"bse_code": bse_code, "company_name": company_name}).execute()
            elif action == 'remove':
                sb.table("monitored_scrips").delete().eq("bse_code", bse_code).execute()
        elif item_type == 'chat_id':
            chat_id = data.get('chat_id')
            if action == 'add':
                sb.table("telegram_recipients").insert({"chat_id": chat_id}).execute()
            elif action == 'remove':
                sb.table("telegram_recipients").delete().eq("chat_id", chat_id).execute()
        return jsonify({"message": f"{item_type} {action} action completed."})
    except Exception as e:
        return jsonify({"message": f"Supabase error: {e}"}), 500

if __name__ == "__main__":
    threading.Thread(target=background_worker, daemon=True).start()
    print("[LOG] 🚀 Flask app starting.")
    app.run(host="0.0.0.0", port=10000)

