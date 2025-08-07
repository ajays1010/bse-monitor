# app.py
import threading
from flask import Flask
import monitor4  # contains check_for_new_announcements_task and worker_loop

app = Flask(__name__)

# start worker as soon as the module loads
threading.Thread(target=monitor4.worker_loop, daemon=True).start()
app.logger.info("🧵 Background worker thread started")

@app.route("/ping")
def ping():
    return "pong", 200

@app.route("/")
def index():
    return "BSE Monitor is running. /ping to keep alive.", 200

if __name__ == "__main__":
    port = int(__import__("os").environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
