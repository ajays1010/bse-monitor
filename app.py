# app.py
import threading
import time
import schedule
from flask import Flask
from monitor4 import check_for_new_announcements_task  # your existing logic

app = Flask(__name__)

# ─── Worker loop ────────────────────────────────────────────────────────────────
def worker_loop():
    """Run once immediately, then every 5 minutes."""
    check_for_new_announcements_task()
    schedule.every(5).minutes.do(check_for_new_announcements_task)
    while True:
        schedule.run_pending()
        time.sleep(1)

# ─── Kick off the thread at import time ─────────────────────────────────────────
threading.Thread(target=worker_loop, daemon=True).start()
app.logger.info("🧵 Background worker thread started")

# ─── Keep-alive endpoint for UptimeRobot ────────────────────────────────────────
@app.route("/ping")
def ping():
    return "pong", 200

# ─── Optional homepage so “/” doesn’t 404 ───────────────────────────────────────
@app.route("/")
def index():
    return "BSE Monitor is alive. Use /ping to keep it awake.", 200

# ─── Entrypoint ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(__import__("os").environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
