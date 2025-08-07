# monitor4.py
import threading
import time
import schedule
import requests
from datetime import datetime, timedelta

# ── hard-coded config ────────────────────────────────────
TELEGRAM_BOT_TOKEN = '7527888676:AAEul4nktWJT2Bt7vciEsC9ukHfV1bTx-ck'
TELEGRAM_CHAT_ID = '453652457'
SCRIPT_CODES       = ["500325", "526861"]
LOOKBACK_DAYS      = 2
# ─────────────────────────────────────────────────────────

_seen = set()

def log(msg):
    print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}", flush=True)

def fetcher_get_announcements(code, num_announcements=50):
    # replace this with your fetcher import or logic
    from fetcher import get_bse_announcements
    return get_bse_announcements(code, num_announcements=num_announcements)

def send_to_telegram(chat_id, text):
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            data={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            timeout=10
        )
        r.raise_for_status()
        log(f"   ✓ Sent announcement to {chat_id}")
    except Exception as e:
        log(f"   ❌ Failed to send to {chat_id}: {e}")

def check_for_new_announcements_task():
    log("🔄 Worker: starting cycle")
    cutoff = datetime.now() - timedelta(days=LOOKBACK_DAYS)
    log(f"    cutoff = {cutoff.isoformat()}")

    for code in SCRIPT_CODES:
        log(f"→ [{code}] fetching up to 50 announcements…")
        try:
            anns = fetcher_get_announcements(code, num_announcements=50)
        except Exception as e:
            log(f"   ❌ Error fetching for {code}: {e}")
            continue

        log(f"   fetched {len(anns)} announcements")
        new_count = 0

        for ann in anns:
            raw_dt = ann["Date"]
            try:
                dt = datetime.fromisoformat(raw_dt)
            except:
                dt = datetime.strptime(raw_dt.split()[0], "%Y-%m-%d")

            log(f"     » date raw='{raw_dt}', parsed={dt.isoformat()}")
            if dt < cutoff:
                log("       ↳ too old, skipping")
                continue

            nid = ann.get("XBRL Link","").split("Bsenewid=")[-1].split("&")[0] or ann["Title"]
            key = (code, nid)
            if key in _seen:
                log("       ↳ already seen, skipping")
                continue

            log("       ↳ NEW announcement!")
            msg = (
                f"📢 <b>Scrip {code}</b>\n"
                f"🕒 {ann['Date']}\n"
                f"🔗 <a href='{ann['PDF Link']}'>PDF</a>\n"
                f"📰 {ann['Title']}"
            )
            for chat_id in TELEGRAM_CHAT_IDS:
                send_to_telegram(chat_id, msg)

            _seen.add(key)
            new_count += 1

        log(f"   ↳ {new_count} new announcement(s) for {code}")

    log("✅ Worker: cycle complete\n")

def worker_loop():
    # run immediately
    check_for_new_announcements_task()
    # then every 5 minutes
    schedule.every(5).minutes.do(check_for_new_announcements_task)
    while True:
        schedule.run_pending()
        time.sleep(1)
