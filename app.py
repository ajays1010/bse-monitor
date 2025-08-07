import os, threading, time, schedule, requests
from datetime import datetime, timedelta
import pandas as pd
from rapidfuzz import process
from flask import Flask, request, jsonify, render_template_string
from supabase import create_client
from fetcher import get_bse_announcements as fetcher_get_announcements

# ──────────────────────────────────────────────────────────────────────────────
# Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_IDS  = os.getenv("TELEGRAM_CHAT_IDS","").split(",")  # comma-separated

# Load company list
DF = pd.read_csv("bse_company_list_cleaned.csv")
# ──────────────────────────────────────────────────────────────────────────────

app = Flask(__name__)

def log(msg):
    print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}", flush=True)

def get_suggestions(q, limit=5):
    matches = process.extract(q, DF["Company Name"], limit=limit)
    return [
      {"company_name": m, "bse_code": str(DF.iloc[i]["BSE Code"])}
      for m, score, i in matches if score > 70
    ]

def list_monitored():
    data = supabase.table("monitored_scrips").select("*").execute().data
    return {r["bse_code"]: r["company_name"] for r in data}

def add_scrip(bse_code, company_name):
    return supabase.table("monitored_scrips")\
      .insert({"bse_code": bse_code, "company_name": company_name})\
      .execute()

def remove_scrip(bse_code):
    return supabase.table("monitored_scrips")\
      .delete().eq("bse_code", bse_code)\
      .execute()

# ─── Admin UI ────────────────────────────────────────────────────────────────

@app.route("/")
def admin_panel():
    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
  <title>BSE Monitor Admin</title>
  <style>
    body { font-family:sans-serif; max-width:800px; margin:auto; }
    input, button { padding:8px; font-size:1em; }
    #suggestions { border:1px solid #ccc; max-height:150px; overflow:auto; }
    #suggestions div{ padding:5px; cursor:pointer; }
    #suggestions div:hover{ background:#eef; }
  </style>
</head>
<body>
  <h1>Manage Monitored Scripts</h1>
  <p>Type a company name:</p>
  <input id="search" autocomplete="off"/>
  <div id="suggestions"></div>
  <button onclick="add()">Add Selected</button>
  <h2>Currently Monitored</h2>
  <ul id="current"></ul>
  <script>
    let selected={};
    async function refresh(){
      let r=await fetch("/api/scripts");
      let j=await r.json();
      let ul=document.getElementById("current");
      ul.innerHTML="";
      for(let c in j){
        let li=document.createElement("li");
        li.innerHTML=`${c}: ${j[c]} <button onclick="del('${c}')">✕</button>`;
        ul.appendChild(li);
      }
      selected={};
    }
    document.getElementById("search").oninput=async e=>{
      let q=e.target.value;
      if(q.length<2){ document.getElementById("suggestions").innerHTML=""; return; }
      let r=await fetch("/api/suggest?q="+encodeURIComponent(q));
      let j=await r.json();
      let out="";
      j.forEach(x=>{
        out+=`<div onclick="pick('${x.bse_code}','${x.company_name}')">${x.company_name} (${x.bse_code})</div>`;
      });
      document.getElementById("suggestions").innerHTML=out;
    };
    function pick(code,name){
      selected={code,name};
      document.getElementById("search").value=`${name} (${code})`;
      document.getElementById("suggestions").innerHTML="";
    }
    async function add(){
      if(!selected.code) return alert("Pick a suggestion first");
      let r=await fetch("/api/scripts", {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({bse_code:selected.code,company_name:selected.name})
      });
      if(r.ok) refresh();
      else alert(await r.text());
    }
    async function del(code){
      await fetch("/api/scripts", {
        method:"DELETE",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({bse_code:code})
      });
      refresh();
    }
    refresh();
  </script>
</body>
</html>
    """)

@app.route("/api/suggest")
def api_suggest():
    q = request.args.get("q","")
    return jsonify(get_suggestions(q))

@app.route("/api/scripts", methods=["GET","POST","DELETE"])
def api_scripts():
    if request.method=="GET":
        return jsonify(list_monitored())
    data = request.get_json()
    if request.method=="POST":
        add_scrip(data["bse_code"], data["company_name"])
        return "OK",200
    else:
        remove_scrip(data["bse_code"])
        return "OK",200

# ─── Keep-alive ────────────────────────────────────────────────────────────────

@app.route("/ping")
def ping():
    return "pong",200

# ─── Monitoring loop ──────────────────────────────────────────────────────────

_seen = set()
def check_and_send():
    log("🔄 cycle start")
    cfg = list_monitored()
    cutoff = datetime.now()-timedelta(days=2)
    for code, name in cfg.items():
        anns = fetcher_get_announcements(code,50)  # import appropriately
        for ann in anns:
            dt = datetime.fromisoformat(ann["Date"])
            if dt<cutoff: continue
            nid = ann["XBRL Link"].split("Bsenewid=")[-1]
            key=(code,nid)
            if key in _seen: continue
            msg = f"📢 <b>{name}</b>\n🕒{ann['Date']}\n🔗<a href='{ann['PDF Link']}'>PDF</a>"
            for cid in TELEGRAM_CHAT_IDS:
                requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                              data={"chat_id":cid,"text":msg,"parse_mode":"HTML"})
            _seen.add(key)
    log("✅ cycle done")

def worker():
    check_and_send()
    schedule.every(5).minutes.do(check_and_send)
    while True:
        schedule.run_pending()
        time.sleep(1)

threading.Thread(target=worker,daemon=True).start()
log("🧵 background worker started")

# ─── Launch ───────────────────────────────────────────────────────────────────

if __name__=="__main__":
    port=int(os.getenv("PORT",5000))
    app.run("0.0.0.0",port)

