# app.py
import os, threading, time, requests, schedule
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, render_template_string, url_for
from supabase import create_client

from fetcher import get_bse_announcements  # your existing fetcher

# ─── Config ───────────────────────────────────────────────────────────────────
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Worker settings
DAYS_TO_FETCH     = 2
INTERVAL_MINUTES  = 5

# Initialize
app = Flask(__name__)
sb  = create_client(SUPABASE_URL, SUPABASE_KEY)

def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)

# ─── Supabase Helpers ──────────────────────────────────────────────────────────
def load_config():
    """Return (scrips: dict, chats: list)."""
    r1 = sb.table("monitored_scrips").select("bse_code,company_name").execute()
    scrips = {row["bse_code"]: row["company_name"] for row in (r1.data or [])}
    r2 = sb.table("telegram_recipients").select("chat_id").execute()
    chats  = [row["chat_id"] for row in (r2.data or [])]
    return scrips, chats

def load_seen_ids(code):
    r = sb.table("seen_announcements").select("news_id") \
           .eq("scrip_code", code).execute()
    return {row["news_id"] for row in (r.data or [])}

def mark_seen(code, news_id):
    try:
        sb.table("seen_announcements").insert({
            "scrip_code": code, "news_id": news_id
        }).execute()
    except Exception:
        pass

# ─── Telegram ──────────────────────────────────────────────────────────────────
def send_telegram(chat_id, text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    resp = requests.post(url, data={
        "chat_id": chat_id, "text": text, "parse_mode": "HTML"
    }, timeout=10)
    resp.raise_for_status()

# ─── Background Worker ─────────────────────────────────────────────────────────
def check_announcements():
    log("🔄 Worker cycle start")
    scrips, chats = load_config()
    cutoff = datetime.now() - timedelta(days=DAYS_TO_FETCH)
    log(f"Using cutoff = {cutoff.isoformat()}")

    for code, name in scrips.items():
        log(f"→ [{code}] {name}: fetching up to 50 announcements…")
        try:
            anns = get_bse_announcements(code, num_announcements=50)
            log(f"   fetched {len(anns)} total announcements")
        except Exception as e:
            log(f"   ❌ fetch error: {e}")
            continue

        seen = load_seen_ids(code)
        new_items = []

        for ann in anns:
            raw_dt = ann["Date"]
            # log the raw date string
            log(f"     » announcement date raw: {raw_dt}")
            try:
                dt = datetime.fromisoformat(raw_dt)
            except Exception:
                dt = datetime.strptime(raw_dt.split(" ")[0], "%Y-%m-%d")
            log(f"       parsed as {dt.isoformat()}")
            if dt < cutoff:
                log("       ↳ too old, skipping")
                continue

            nid = ann["XBRL Link"].split("Bsenewid=")[-1].split("&")[0]
            if nid in seen:
                log("       ↳ already seen, skipping")
                continue

            log("       ↳ NEW announcement!")
            new_items.append((nid, ann))

        log(f"   ↳ {len(new_items)} new announcement(s) found for {code}")

        for nid, ann in new_items:
            msg = (
                f"📢 <b>{name}</b> ({code})\n"
                f"🕒 {ann['Date']}\n"
                f"🔗 <a href='{ann['PDF Link']}'>PDF</a>"
            )
            for chat in chats:
                try:
                    send_telegram(chat, msg)
                    log(f"       ✓ sent to {chat}")
                except Exception as e:
                    log(f"       ❌ telegram error to {chat}: {e}")
            mark_seen(code, nid)

    log("✅ Worker cycle complete\n")

def start_worker():
    check_announcements()
    schedule.every(INTERVAL_MINUTES).minutes.do(check_announcements)
    while True:
        schedule.run_pending()
        time.sleep(1)

# ─── Flask Admin & UI Routes ──────────────────────────────────────────────────

# 1) Admin Panel (/) — manage scrips & chat IDs
@app.route('/', methods=['GET'])
def index():
    scrips, chats = load_config()
    return render_template_string("""
<!doctype html>
<html>
<head><title>BSE Monitor Admin</title></head>
<body>
  <h1>Admin Panel</h1>
  <h2>Monitored Scrips</h2>
  <ul>
    {% for code, name in scrips.items() %}
      <li>{{code}}: {{name}} 
        <form style="display:inline" method="POST" action="/remove_scrip">
          <input type="hidden" name="code" value="{{code}}">
          <button>Delete</button>
        </form>
      </li>
    {% endfor %}
  </ul>
  <form method="POST" action="/add_scrip">
    <input name="bse_code" placeholder="BSE code">
    <input name="company_name" placeholder="Company">
    <button>Add</button>
  </form>

  <h2>Telegram Recipients</h2>
  <ul>
    {% for chat in chats %}
      <li>{{chat}}
        <form style="display:inline" method="POST" action="/remove_chat">
          <input type="hidden" name="chat_id" value="{{chat}}">
          <button>Delete</button>
        </form>
      </li>
    {% endfor %}
  </ul>
  <form method="POST" action="/add_chat">
    <input name="chat_id" placeholder="Chat ID">
    <button>Add</button>
  </form>

  <p><a href="{{url_for('view_announcements')}}">View Announcements</a></p>
</body>
</html>
    """, scrips=scrips, chats=chats)

@app.route('/add_scrip', methods=['POST'])
def add_scrip():
    code = request.form['bse_code'].strip()
    name = request.form['company_name'].strip()
    sb.table("monitored_scrips").insert({"bse_code": code, "company_name": name}).execute()
    return ('', 302, {'Location': '/'})

@app.route('/remove_scrip', methods=['POST'])
def remove_scrip():
    code = request.form['code']
    sb.table("monitored_scrips").delete().eq("bse_code", code).execute()
    return ('', 302, {'Location': '/'})

@app.route('/add_chat', methods=['POST'])
def add_chat():
    cid = request.form['chat_id'].strip()
    sb.table("telegram_recipients").insert({"chat_id": cid}).execute()
    return ('', 302, {'Location': '/'})

@app.route('/remove_chat', methods=['POST'])
def remove_chat():
    cid = request.form['chat_id']
    sb.table("telegram_recipients").delete().eq("chat_id", cid).execute()
    return ('', 302, {'Location': '/'})

# 2) Announcement Viewer
@app.route('/announcements', methods=['GET'])
def view_announcements():
    scrips, _ = load_config()
    selected = request.args.get('scrip_code','').strip()
    announcements = []
    if selected:
        announcements = get_bse_announcements(selected, num_announcements=20)

    return render_template_string("""
<!doctype html>
<html>
<head><title>View Announcements</title></head>
<body>
  <h1>Announcements</h1>
  <form method="GET">
    <select name="scrip_code" onchange="this.form.submit()">
      <option value="">-- Select Company --</option>
      {% for c,n in scrips.items() %}
        <option value="{{c}}" {{'selected' if c==selected else ''}}>
          {{n}} ({{c}})
        </option>
      {% endfor %}
    </select>
  </form>

  {% if announcements %}
    <table border=1 cellpadding=5>
      <tr><th>Date</th><th>Title</th><th>PDF</th></tr>
      {% for ann in announcements %}
        <tr>
          <td>{{ann['Date']}}</td>
          <td>{{ann['Title']}}</td>
          <td><a href="{{ann['PDF Link']}}" target="_blank">PDF</a></td>
        </tr>
      {% endfor %}
    </table>
  {% else %}
    <p>No announcements</p>
  {% endif %}
</body>
</html>
    """, scrips=scrips, selected=selected, announcements=announcements)

# 3) Ping (for UptimeRobot)
@app.route('/ping', methods=['GET'])
def ping():
    return "pong", 200

# ─── Startup ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # start background worker
    t = threading.Thread(target=start_worker, daemon=True)
    t.start()

    # run Flask
    port = int(os.getenv("PORT", 8000))
    app.run(host="0.0.0.0", port=port)

