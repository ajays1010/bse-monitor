import os
import json
import threading
import time
import requests
from datetime import datetime, timedelta
import schedule
import random # For exponential backoff jitter
import pandas as pd
import logging

from supabase import create_client, Client

from flask import Flask, request, jsonify, render_template_string, url_for, redirect
from rapidfuzz import process # Import rapidfuzz for fuzzy matching

# --- Global Configuration ---
# File to store the monitored scrip codes and Telegram chat IDs
CONFIG_FILE = 'monitored_scripts_config.json' 
# File to track seen announcements (used by the background worker)
CACHE_FILE = "seen_announcements.json"
# File to log all activity
LOG_FILE = "telegram_log.txt" 
#Set all logs to stdout
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(message)s"
)

# Worker settings
MAX_RETRIES_MAIN_LOOP = 3 # Max retries for the main scheduling loop
DAYS_TO_FETCH = 2 # Set to 2 to include today and the previous 2 full days (total 3 days)

# Telegram settings
TELEGRAM_BOT_TOKEN = '7527888676:AAEul4nktWJT2Bt7vciEsC9ukHfV1bTx-ck'
TELEGRAM_TIMEOUT = 15 # Increased timeout for Telegram requests (from 10 to 15 seconds)
TELEGRAM_MAX_RETRIES = 5 # Max retries for sending a single Telegram message
TELEGRAM_RETRY_DELAY_BASE = 5 # Base delay in seconds for exponential backoff

# Global variables for application state
GLOBAL_MONITORED_SCRIPS = {} # Stores scrip_code: company_name from config file
GLOBAL_TELEGRAM_CHAT_IDS = []

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase: Client = None
 # Stores a list of Telegram chat IDs
GLOBAL_BSE_COMPANY_NAMES = [] # Stores all company names for suggestions (from bse_company_list_cleaned.csv)
GLOBAL_BSE_DF = pd.DataFrame() # Stores the full BSE company list DataFrame

app = Flask(__name__)

# --- Core Helper Functions (consolidated from previous scripts) ---

# def app.logger.info(message):
#     """Logs messages to a local file with a timestamp."""
#     timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
#     with open(LOG_FILE, "a", encoding="utf-8") as f:
#         f.write(f"[{timestamp}] {message}\n")
#     print(f"[LOG] {message}") # Also print to console for testing

def send_telegram_message(chat_id, message): # Modified to accept chat_id
    """Sends a message to a specific Telegram chat ID with retry logic and logs it."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "HTML"}

    for attempt in range(TELEGRAM_MAX_RETRIES):
        try:
            response = requests.post(url, data=payload, timeout=TELEGRAM_TIMEOUT)
            response.raise_for_status() # Raises HTTPError for bad responses (4xx or 5xx)
            app.logger.info(f"Telegram message sent successfully to {chat_id} (Attempt {attempt + 1}/{TELEGRAM_MAX_RETRIES}): {message}")
            return True # Message sent successfully
        except requests.exceptions.Timeout as e:
            delay = (TELEGRAM_RETRY_DELAY_BASE * (2 ** attempt)) + random.uniform(0, 1) # Exponential backoff with jitter
            app.logger.info(f"Telegram send timeout to {chat_id} (Attempt {attempt + 1}/{TELEGRAM_MAX_RETRIES}): {e}. Retrying in {delay:.2f} seconds.")
            time.sleep(delay)
        except requests.exceptions.RequestException as e:
            delay = (TELEGRAM_RETRY_DELAY_BASE * (2 ** attempt)) + random.uniform(0, 1)
            app.logger.info(f"Telegram request error to {chat_id} (Attempt {attempt + 1}/{TELEGRAM_MAX_RETRIES}): {e}. Retrying in {delay:.2f} seconds.")
            time.sleep(delay)
        except Exception as e:
            app.logger.info(f"Unexpected error sending Telegram message to {chat_id} (Attempt {attempt + 1}/{TELEGRAM_MAX_RETRIES}): {e}. No further retries for this attempt.")
            break # Break on unexpected errors not related to requests

    app.logger.info(f"Failed to send Telegram message to {chat_id} after {TELEGRAM_MAX_RETRIES} attempts: {message}")
    return False # Message failed after all retries


def get_supabase_client():
    global supabase
    if supabase is None:
        if not SUPABASE_URL or not SUPABASE_KEY:
            app.logger.info("❌ Supabase URL or Key missing.")
            return None
        try:
            supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
            app.logger.info("✅ Supabase client initialized.")
        except Exception as e:
            app.logger.info(f"❌ Supabase client error: {e}")
            supabase = None
    return supabase


def load_config_from_supabase():
    """Fetches monitored_scrips & telegram_recipients from Supabase and returns as dict."""
    sb = get_supabase_client()
    if sb is None:
        app.logger.info("❌ load_config: Supabase client is not initialized.")
        return {"scrip_codes": {}, "telegram_chat_ids": []}

    try:
        scrips_res = sb.table("monitored_scrips").select("bse_code,company_name").execute()
        chats_res = sb.table("telegram_recipients").select("chat_id").execute()

        scrips = {item["bse_code"]: item["company_name"] for item in scrips_res.data}
        chats = [item["chat_id"] for item in chats_res.data]

        # update globals for background worker
        global GLOBAL_MONITORED_SCRIPS, GLOBAL_TELEGRAM_CHAT_IDS
        GLOBAL_MONITORED_SCRIPS = scrips
        GLOBAL_TELEGRAM_CHAT_IDS = chats

        app.logger.info(f"✅ load_config: Loaded {len(scrips)} scrips and {len(chats)} chat IDs from Supabase.")
        return {"scrip_codes": scrips, "telegram_chat_ids": chats}

    except Exception as e:
        app.logger.info(f"❌ load_config: Supabase query failed: {e}")
        return {"scrip_codes": {}, "telegram_chat_ids": []}

def save_config(config_data):
    """Saves scrip codes and chat IDs to the JSON config file."""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config_data, f, indent=4)
        app.logger.info(f"Config saved to {CONFIG_FILE}.")
    except Exception as e:
        app.logger.info(f"Error saving config to {CONFIG_FILE}: {e}")

def load_seen_ids():
    """Loads previously seen announcement IDs from a JSON cache file."""
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            app.logger.info(f"Warning: Could not decode JSON from {CACHE_FILE}. Starting with empty cache.")
            return {}
    return {}

def save_seen_ids(data):
    """Saves current seen announcement IDs to a JSON cache file."""
    try:
        with open(CACHE_FILE, "w") as f:
            json.dump(data, f)
        app.logger.info(f"Seen IDs saved to {CACHE_FILE}.")
    except Exception as e:
        app.logger.info(f"Error saving seen IDs to {CACHE_FILE}: {e}")

def get_bse_announcements(scrip_code, num_announcements=15):
    """
    Fetches recent announcements for a given scrip code from the BSE API.
    """
    if not scrip_code.isdigit():
        app.logger.info(f"Input Error: Scrip code '{scrip_code}' must be a numeric string. Skipping.")
        return []

    try:
        api_url = "https://api.bseindia.com/BseIndiaAPI/api/AnnGetData/w"
        to_date = datetime.now()
        from_date = to_date - timedelta(days=90) # Fetches for the last 90 days by default

        to_date_str = to_date.strftime('%Y%m%d')
        from_date_str = from_date.strftime('%Y%m%d')

        params = {
            'strCat': '-1',
            'strPrevDate': from_date_str,
            'strToDate': to_date_str,
            'strScrip': scrip_code,
            'strSearch': 'P',
            'strType': 'C'
        }

        headers = {
            'User-Agent': 'Mozilla/5.0',
            'Referer': 'https://www.bseindia.com/'
        }

        response = requests.get(api_url, headers=headers, params=params, timeout=30)
        response.raise_for_status()

        data = response.json()
        announcements_data = data.get('Table', [])

        if not announcements_data:
            return []

        announcements_list = []
        for announcement in announcements_data[:num_announcements]:
            title = announcement.get('HEADLINE', 'N/A')
            pdf_link_filename = announcement.get('ATTACHMENTNAME')
            date_time = announcement.get('DissemDT', 'N/A')
            news_id = announcement.get('NEWSID')
            scrip_cd = announcement.get('SCRIP_CD')

            pdf_link = f"https://www.bseindia.com/xml-data/corpfiling/AttachLive/{pdf_link_filename}" if pdf_link_filename else "No PDF Available"
            xbrl_link = f"https://www.bseindia.com/Msource/90D/CorpXbrlGen.aspx?Bsenewid={news_id}&Scripcode={scrip_cd}" if news_id and scrip_cd else "No XBRL Available"

            announcements_list.append({
                "Date": date_time,
                "Title": title,
                "PDF Link": pdf_link,
                "XBRL Link": xbrl_link
            })

        return announcements_list

    except requests.exceptions.RequestException as e:
        app.logger.info(f"Request Error in get_bse_announcements for {scrip_code}: {e}")
        return []
    except Exception as e:
        app.logger.info(f"An unexpected error occurred in get_bse_announcements for {scrip_code}:\n{e}")
        return []

def get_suggestions_from_list(query, limit=5): # Renamed to avoid conflict with Flask route
    """
    Provides company name suggestions based on a query using loaded data.
    """
    if not GLOBAL_BSE_DF.empty and 'Company Name' in GLOBAL_BSE_DF.columns:
        # Use rapidfuzz's process.extract to get fuzzy matches
        # extract returns (match, score, index)
        matches = process.extract(query, GLOBAL_BSE_DF["Company Name"].tolist(), limit=limit)
        
        results = []
        for match_name, score, index in matches:
            # Ensure score is above a certain threshold to avoid irrelevant suggestions
            if score > 75: # Adjust threshold as needed (0-100)
                bse_code = str(GLOBAL_BSE_DF.iloc[index]["BSE Code"])
                results.append({"bse_code": bse_code, "company_name": match_name})
        return results
    return []

def load_bse_company_list():
    """
    Loads the BSE company list for suggestions.
    """
    global GLOBAL_BSE_DF, GLOBAL_BSE_COMPANY_NAMES
    bse_company_list_file = "bse_company_list_cleaned.csv" # Assuming this file is present in deployment

    try:
        if os.path.exists(bse_company_list_file):
            GLOBAL_BSE_DF = pd.read_csv(bse_company_list_file)
            GLOBAL_BSE_COMPANY_NAMES = GLOBAL_BSE_DF["Company Name"].tolist()
            app.logger.info(f"Loaded {len(GLOBAL_BSE_COMPANY_NAMES)} companies for suggestions.")
        else:
            app.logger.info(f"Warning: {bse_company_list_file} not found. Company name suggestions will not work.")
            GLOBAL_BSE_DF = pd.DataFrame(columns=["BSE Code", "Company Name"])
            GLOBAL_BSE_COMPANY_NAMES = []
    except Exception as e:
        app.logger.info(f"Error loading {bse_company_list_file}: {e}")
        GLOBAL_BSE_DF = pd.DataFrame(columns=["BSE Code", "Company Name"])
        GLOBAL_BSE_COMPANY_NAMES = []

# --- Background Worker Logic ---

def reload_monitored_scrip_codes_from_config_file():
    """Task to periodically reload the monitored scrip codes and chat IDs from the local JSON config."""
    global GLOBAL_MONITORED_SCRIPS, GLOBAL_TELEGRAM_CHAT_IDS
    app.logger.info("DEBUG: reload task triggered")
    new_config = load_config_from_supabase()
    if new_config:
        GLOBAL_MONITORED_SCRIPS = new_config.get("scrip_codes", {})
        GLOBAL_TELEGRAM_CHAT_IDS = new_config.get("telegram_chat_ids", [])
        app.logger.info(f"Successfully reloaded {len(GLOBAL_MONITORED_SCRIPS)} scrip codes and {len(GLOBAL_TELEGRAM_CHAT_IDS)} chat IDs from local config.")
    else:
        app.logger.info("Warning: Failed to reload config. Keeping previous lists.")

def check_for_new_announcements_task():
    """
    The main task function that will be scheduled to run periodically.
    It fetches, filters, and sends new announcements.
    """
    seen = load_seen_ids()
    
    current_time = datetime.now()
    cutoff_date = current_time - timedelta(days=DAYS_TO_FETCH)
    app.logger.info(f"Worker: Checking for new announcements since {cutoff_date.strftime('%Y-%m-%d %H:%M:%S')}")

    new_announcements_found_this_cycle = False

    if not GLOBAL_MONITORED_SCRIPS:
        app.logger.info("Worker: No scrip codes loaded. Skipping announcement check in this cycle.")
        return

    for scrip_code, company_name in GLOBAL_MONITORED_SCRIPS.items():
        app.logger.info(f"Worker: Processing {company_name} (Scrip Code: {scrip_code})...")
        anns = get_bse_announcements(scrip_code, num_announcements=50) 

        if not anns:
            app.logger.info(f"Worker: No announcements fetched for scrip code {scrip_code}.")
            continue

        if scrip_code not in seen:
            seen[scrip_code] = {} # Initialize as dictionary for news_id tracking

        new_items_for_scrip = []
        for ann in anns:
            ann_full_date_str = ann.get('Date', '')
            ann_date = None
            
            try:
                ann_date = datetime.fromisoformat(ann_full_date_str)
            except ValueError:
                try:
                    date_only_str = ann_full_date_str.split('T')[0].split(' ')[0]
                    ann_date = datetime.strptime(date_only_str, '%Y-%m-%d')
                except ValueError:
                    app.logger.info(f"Worker: Warning: Failed to parse date '{ann_full_date_str}' for announcement. Skipping date filter for this item.")
                    ann_date = None

            if ann_date:
                if ann_date.date() >= cutoff_date.date():
                    news_id = ann['XBRL Link'].split("Bsenewid=")[-1].split("&")[0] if "Bsenewid=" in ann['XBRL Link'] else ann['Title'] + ann['Date']

                    if news_id not in seen.get(scrip_code, {}): # Use .get() to safely check nested dict
                        seen.setdefault(scrip_code, {})[news_id] = True # Set default and mark as seen
                        new_items_for_scrip.append(ann)
                        app.logger.info(f"Worker: Found new announcement for {scrip_code} ({company_name}): {ann['Title']}")
                        new_announcements_found_this_cycle = True
            else:
                app.logger.info(f"Worker: Announcement for {scrip_code} has unparsable date format '{ann_full_date_str}'. Skipping this announcement.")

        # Send messages to all configured Telegram chat IDs
        if new_items_for_scrip and GLOBAL_TELEGRAM_CHAT_IDS:
            for chat_id in GLOBAL_TELEGRAM_CHAT_IDS:
                for ann in new_items_for_scrip:
                    msg_text = f"📢 {ann['Title']}\n🕒 {ann['Date']}\n🔗 {ann['PDF Link']}"
                    send_telegram_message(chat_id, msg_text) # Pass chat_id here
        elif new_items_for_scrip and not GLOBAL_TELEGRAM_CHAT_IDS:
            app.logger.info("Worker: New announcements found, but no Telegram chat IDs configured.")

    save_seen_ids(seen)
    if not new_announcements_found_this_cycle:
        app.logger.info("Worker: No new announcements found in this cycle.")
    app.logger.info(f"Worker: Monitoring cycle completed.")

def start_background_worker():
    """
    Initializes and starts the BSE monitoring worker's scheduling loop.
    This function runs in a separate thread.
    """
    app.logger.info("Background worker thread started.")

    # Initial load of scrip codes and chat IDs for the worker
    reload_monitored_scrip_codes_from_config_file()
    
    # Run the task immediately on startup
    check_for_new_announcements_task()

    # Schedule the main announcement checking task
    schedule.every(5).minutes.do(check_for_new_announcements_task)
    
    # Schedule the config reloading task (e.g., every 1 minute for quick updates)
    schedule.every(1).minutes.do(reload_monitored_scrip_codes_from_config_file) 

    retries = 0
    while True:
        try:
            schedule.run_pending()
            time.sleep(1) # Sleep for 1 second to avoid high CPU usage
            retries = 0 # Reset retries on successful loop iteration
        except Exception as e:
            app.logger.info(f"Background Worker: Error in scheduling loop: {e}")
            retries += 1
            if retries >= MAX_RETRIES_MAIN_LOOP:
                app.logger.info(f"Background Worker: Max retries ({MAX_RETRIES_MAIN_LOOP}) reached. Exiting worker thread.")
                break
            app.logger.info(f"Background Worker: Retrying scheduling loop in 60 seconds (retry {retries}/{MAX_RETRIES_MAIN_LOOP}).")
            time.sleep(60)

# --- Flask Routes ---

@app.route('/')
def index():
    """Admin panel homepage with scrip management and links to manage chat IDs and view announcements."""
    current_config = load_config_from_supabase()
    scrip_codes = current_config.get("scrip_codes", {})
    telegram_chat_ids = current_config.get("telegram_chat_ids", [])
    
    # Simple HTML template for the admin panel
    return render_template_string("""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>BSE Scrip Monitor Admin</title>
            <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap" rel="stylesheet">
            <style>
                body { font-family: 'Inter', sans-serif; margin: 0; padding: 20px; background-color: #f0f2f5; color: #333; }
                .container { max-width: 900px; margin: 20px auto; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }
                h1, h2, h3 { color: #10486b; text-align: center; margin-bottom: 25px; border-bottom: 2px solid #e0e0e0; padding-bottom: 10px; }
                h2, h3 { margin-top: 30px; }
                form { display: flex; flex-direction: column; gap: 15px; margin-bottom: 30px; padding: 15px; border: 1px solid #e0e0e0; border-radius: 8px; background-color: #f9f9f9; }
                input[type="text"], input[type="submit"], button {
                    padding: 12px; border-radius: 8px; border: 1px solid #ccc; font-size: 1em;
                }
                input[type="submit"], button {
                    background-color: #007bff; color: white; cursor: pointer; border: none; font-weight: bold; transition: background-color 0.3s ease;
                }
                input[type="submit"]:hover, button:hover { background-color: #0056b3; }
                .button-group { display: flex; justify-content: center; gap: 15px; margin-top: 20px; }
                .button-group a {
                    text-decoration: none; padding: 12px 25px; border-radius: 8px; background-color: #28a745; color: white; font-weight: bold; transition: background-color 0.3s ease;
                }
                .button-group a:hover { background-color: #218838; }
                ul { list-style: none; padding: 0; margin-top: 20px; }
                li { background: #e9ecef; margin-bottom: 10px; padding: 15px; border-radius: 8px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
                .delete-btn { background-color: #dc3545; color: white; border: none; padding: 8px 15px; border-radius: 5px; cursor: pointer; font-size: 0.9em; transition: background-color 0.3s ease; }
                .delete-btn:hover { background-color: #c82333; }
                .message { text-align: center; margin-top: 15px; padding: 12px; border-radius: 8px; font-weight: bold; display: none; }
                .success { background-color: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
                .error { background-color: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
                .info-box { background-color: #e0f2f7; border-left: 5px solid #007bff; padding: 15px; margin-bottom: 20px; border-radius: 8px; font-size: 0.95em; }
                #suggestionsList {
                    border: 1px solid #ddd;
                    max-height: 150px;
                    overflow-y: auto;
                    background-color: white;
                    position: absolute; /* Position relative to the form or container */
                    width: calc(100% - 30px); /* Adjust width to match input field */
                    z-index: 1000; /* Ensure it appears above other elements */
                    box-shadow: 0 4px 8px rgba(0,0,0,0.1);
                    border-top: none;
                    border-radius: 0 0 8px 8px;
                }
                #suggestionsList div {
                    padding: 10px;
                    cursor: pointer;
                    border-bottom: 1px solid #eee;
                }
                #suggestionsList div:hover {
                    background-color: #f0f0f0;
                }
                #suggestionsList div:last-child {
                    border-bottom: none;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>BSE Monitor Admin Panel</h1>
                <div id="message" class="message" style="display:none;"></div>

                <h2>Manage Monitored Scrips</h2>
                <form id="addScripForm">
                    <input type="text" id="bseCode" name="bse_code" placeholder="BSE Code (e.g., 500325)" readonly>
                    <input type="text" id="companyName" name="company_name" placeholder="Type Company Name (e.g., Reliance Industries)" oninput="getCompanySuggestions(this.value)" required>
                    <div id="suggestionsList"></div> <!-- For suggestions -->
                    <input type="submit" value="Add Scrip">
                </form>

                <h3>Currently Monitored Scrips:</h3>
                <ul id="scripList"></ul>

                <h2>Manage Telegram Recipients</h2>
                <div class="info-box">
                    <p>To get your Chat ID:</p>
                    <ol>
                        <li>Open Telegram.</li>
                        <li>Search for the bot <code>@RawDataBot</code>.</li>
                        <li>Send it any message. It will reply with your Chat ID.</li>
                        <li>Copy that numeric ID and paste it below.</li>
                    </ol>
                </div>
                <form id="addChatIdForm">
                    <input type="text" id="chatId" name="chat_id" placeholder="Telegram Chat ID (e.g., 123456789)" required>
                    <input type="submit" value="Add Chat ID">
                </form>

                <h3>Current Telegram Recipients:</h3>
                <ul id="chatIdList"></ul>

                <div class="button-group">
                    <a href="/announcements">View Announcements</a>
                </div>
            </div>

            <script>
                const scripList = document.getElementById('scripList');
                const addScripForm = document.getElementById('addScripForm');
                const chatIdList = document.getElementById('chatIdList');
                const addChatIdForm = document.getElementById('addChatIdForm');
                const messageDiv = document.getElementById('message');
                const companyNameInput = document.getElementById('companyName');
                const bseCodeInput = document.getElementById('bseCode');
                const suggestionsList = document.getElementById('suggestionsList');

                async function fetchAndDisplayScrips() {
                    try {
                        const response = await fetch('/api/config');
                        const data = await response.json();
                        
                        // Display Scrips
                        scripList.innerHTML = '';
                        if (Object.keys(data.scrip_codes).length === 0) {
                            scripList.innerHTML = '<li>No scrips currently monitored.</li>';
                        } else {
                            for (const code in data.scrip_codes) {
                                const li = document.createElement('li');
                                li.innerHTML = `
                                    <span>${code}: ${data.scrip_codes[code]}</span>
                                    <button class="delete-btn" data-type="scrip" data-code="${code}">Delete</button>
                                `;
                                scripList.appendChild(li);
                            }
                        }

                        // Display Chat IDs
                        chatIdList.innerHTML = '';
                        if (data.telegram_chat_ids.length === 0) {
                            chatIdList.innerHTML = '<li>No Telegram recipients added.</li>';
                        } else {
                            data.telegram_chat_ids.forEach(id => {
                                const li = document.createElement('li');
                                li.innerHTML = `
                                    <span>${id}</span>
                                    <button class="delete-btn" data-type="chat_id" data-id="${id}">Delete</button>
                                `;
                                chatIdList.appendChild(li);
                            });
                        }

                    } catch (error) {
                        showMessage('error', 'Failed to load configuration: ' + error.message);
                    }
                }

                async function getCompanySuggestions(query) {
                    suggestionsList.innerHTML = '';
                    if (query.length < 2) { // Start suggesting after 2 characters
                        suggestionsList.style.display = 'none';
                        return;
                    }

                    try {
                        const response = await fetch(`/api/suggest_company?query=${encodeURIComponent(query)}`);
                        const suggestions = await response.json();

                        if (suggestions.length > 0) {
                            suggestionsList.style.display = 'block';
                            suggestions.forEach(item => {
                                const div = document.createElement('div');
                                div.textContent = `${item.company_name} (${item.bse_code})`;
                                div.dataset.bseCode = item.bse_code;
                                div.dataset.companyName = item.company_name;
                                div.addEventListener('click', () => {
                                    companyNameInput.value = item.company_name;
                                    bseCodeInput.value = item.bse_code;
                                    suggestionsList.style.display = 'none';
                                });
                                suggestionsList.appendChild(div);
                            });
                        } else {
                            suggestionsList.style.display = 'none';
                        }
                    } catch (error) {
                        console.error('Error fetching suggestions:', error);
                        suggestionsList.style.display = 'none';
                    }
                }


                async function manageConfig(action, type, value1, value2 = null) {
                    let body = { action: action, type: type };
                    if (type === 'scrip') {
                        body.bse_code = value1;
                        if (action === 'add') body.company_name = value2;
                    } else if (type === 'chat_id') {
                        body.chat_id = value1;
                    }

                    try {
                        const response = await fetch('/api/config', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify(body)
                        });
                        const result = await response.json();
                        if (response.ok) {
                            showMessage('success', result.message);
                            if (type === 'scrip') {
                                addScripForm.reset();
                                suggestionsList.innerHTML = ''; // Clear suggestions
                                suggestionsList.style.display = 'none';
                            }
                            if (type === 'chat_id') addChatIdForm.reset();
                            fetchAndDisplayScrips();
                        } else {
                            showMessage('error', result.message || `Failed to ${action} ${type}.`);
                        }
                    } catch (error) {
                        showMessage('error', 'Network error: ' + error.message);
                    }
                }

                function showMessage(type, text) {
                    messageDiv.className = `message ${type}`;
                    messageDiv.textContent = text;
                    messageDiv.style.display = 'block';
                    setTimeout(() => { messageDiv.style.display = 'none'; }, 5000);
                }

                addScripForm.addEventListener('submit', (event) => {
                    event.preventDefault();
                    const bseCode = document.getElementById('bseCode').value.trim();
                    const companyName = document.getElementById('companyName').value.trim();
                    manageConfig('add', 'scrip', bseCode, companyName);
                });

                addChatIdForm.addEventListener('submit', (event) => {
                    event.preventDefault();
                    const chatId = document.getElementById('chatId').value.trim();
                    manageConfig('add', 'chat_id', chatId);
                });

                scripList.addEventListener('click', (event) => {
                    if (event.target.classList.contains('delete-btn') && event.target.dataset.type === 'scrip') {
                        if (confirm(`Are you sure you want to delete scrip code ${event.target.dataset.code}?`)) {
                            manageConfig('remove', 'scrip', event.target.dataset.code);
                        }
                    }
                });

                chatIdList.addEventListener('click', (event) => {
                    if (event.target.classList.contains('delete-btn') && event.target.dataset.type === 'chat_id') {
                        if (confirm(`Are you sure you want to delete chat ID ${event.target.dataset.id}?`)) {
                            manageConfig('remove', 'chat_id', event.target.dataset.id);
                        }
                    }
                });

                fetchAndDisplayScrips(); // Initial load
            </script>
        </body>
        </html>
    """)

@app.route('/api/config', methods=['GET'])
def get_config_api():
    """API endpoint to get the current configuration (scrip codes and chat IDs) from Supabase."""
    sb = get_supabase_client()
    if sb is None:
        return jsonify({"status": "error", "message": "Supabase not initialized"}), 500

    try:
        scrips_res = sb.table("monitored_scrips").select("*").execute()
        chats_res = sb.table("telegram_recipients").select("*").execute()
        app.logger.info("SUCCESS: Supabase Tables Loaded")
        
        return jsonify({
            "scrip_codes": {item["bse_code"]: item["company_name"] for item in scrips_res.data},
            "telegram_chat_ids": [item["chat_id"] for item in chats_res.data]
        })
    except Exception as e:
        app.logger.info("ERROR: Not able to load Supabase Tables!")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/config', methods=['POST'])
def manage_config_api():
    """API endpoint to add or remove scrip codes or Telegram chat IDs using Supabase."""
    data = request.get_json()
    action = data.get('action')  # 'add' or 'remove'
    item_type = data.get('type')  # 'scrip' or 'chat_id'

    sb = get_supabase_client()
    if sb is None:
        return jsonify({"message": "Supabase not initialized."}), 500

    try:
        if item_type == 'scrip':
            bse_code = data.get('bse_code')
            company_name = data.get('company_name')

            if action == 'add':
                if not bse_code or not company_name:
                    return jsonify({"message": "BSE Code and Company Name are required."}), 400

                sb.table("monitored_scrips").insert({
                    "bse_code": bse_code,
                    "company_name": company_name
                }).execute()
                return jsonify({"message": f"Scrip code {bse_code} ({company_name}) added to Supabase."}), 200

            elif action == 'remove':
                if not bse_code:
                    return jsonify({"message": "BSE Code is required for removal."}), 400

                sb.table("monitored_scrips").delete().eq("bse_code", bse_code).execute()
                return jsonify({"message": f"Scrip code {bse_code} removed from Supabase."}), 200

        elif item_type == 'chat_id':
            chat_id = data.get('chat_id')

            if action == 'add':
                if not chat_id:
                    return jsonify({"message": "Chat ID is required."}), 400

                sb.table("telegram_recipients").insert({"chat_id": chat_id}).execute()
                return jsonify({"message": f"Chat ID {chat_id} added to Supabase."}), 200

            elif action == 'remove':
                if not chat_id:
                    return jsonify({"message": "Chat ID is required for removal."}), 400

                sb.table("telegram_recipients").delete().eq("chat_id", chat_id).execute()
                return jsonify({"message": f"Chat ID {chat_id} removed from Supabase."}), 200

        return jsonify({"message": "Invalid item type. Use 'scrip' or 'chat_id'."}), 400

    except Exception as e:
        return jsonify({"message": f"Supabase error: {e}"}), 500


@app.route('/api/suggest_company', methods=['GET'])
def suggest_company_api():
    """API endpoint for fuzzy company name suggestions."""
    query = request.args.get('query', '').strip()
    if not query:
        return jsonify([])
    
    suggestions = get_suggestions_from_list(query, limit=10) # Get up to 10 suggestions
    return jsonify(suggestions)
  @app.route('/announcements', methods=['GET'])
def view_announcements():
    """
    Displays announcements for a selected scrip code in an HTML table.
    Allows selection of scrip code via a dropdown.
    """
    # 1️⃣ Get the query param
    selected_scrip_code = request.args.get('scrip_code', "").strip()
    app.logger.info(f"/announcements called with scrip_code={selected_scrip_code!r}")

    # 2️⃣ Reload config from Supabase
    cfg = load_config_from_supabase()
    app.logger.info(f"/announcements config loaded: {cfg}")

    # 3️⃣ Build dropdown options
    scrip_options_html = ""
    for code, name in cfg['scrip_codes'].items():
        is_sel = "selected" if code == selected_scrip_code else ""
        scrip_options_html += (
            f"<option value='{code}' {is_sel}>{name} ({code})</option>"
        )

    # 4️⃣ If a code is selected, fetch its announcements
    announcements_to_display = []
    company_name_for_display = "Select a Company"
    if selected_scrip_code:
        company_name_for_display = cfg['scrip_codes'].get(
            selected_scrip_code, f"Unknown ({selected_scrip_code})"
        )
        app.logger.info(f"/announcements fetching for {selected_scrip_code}")
        announcements_to_display = get_bse_announcements(
            selected_scrip_code, num_announcements=20
        )
        app.logger.info(
            f"/announcements found {len(announcements_to_display)} announcements"
        )

    @@ def view_announcements():
-    # 5️⃣ Render
-    return render_template_string(f"""
-    <!DOCTYPE html>
-    <html lang="en">
-      <head>… your existing head …</head>
-      <body>
-        <h1>Announcements for {company_name_for_display}</h1>
-        <form method="GET" action="/announcements">
-          <select name="scrip_code" onchange="this.form.submit()">
-            <option value="">-- Select a Company --</option>
-            {scrip_options_html}
-          </select>
-        </form>
-
-        {"<table><tr><th>Date</th><th>Title</th><th>PDF</th></tr>" if announcements_to_display else ""}
-        {"".join([
-            f"<tr>"
-            f"<td>{ann['Date']}</td>"
-            f"<td>{ann['Title']}</td>"
-            f"<td><a href='{ann['PDF Link']}' target='_blank'>PDF</a></td>"
-            f"</tr>"
-            for ann in announcements_to_display
-        ]) if announcements_to_display else ""}
-        {"</table>" if announcements_to_display else ""}
-        {"" if announcements_to_display else "<p>No announcements found.</p>"}
-      </body>
-    </html>
-    """)
+    # 5️⃣ Build the announcements table HTML
+    if announcements_to_display:
+        rows = ""
+        for ann in announcements_to_display:
+            rows += (
+                "<tr>"
+                f"<td>{ann['Date']}</td>"
+                f"<td>{ann['Title']}</td>"
+                f"<td><a href='{ann['PDF Link']}' target='_blank'>PDF</a></td>"
+                "</tr>"
+            )
+        table_html = (
+            "<table>"
+            "<tr><th>Date</th><th>Title</th><th>PDF</th></tr>"
+            f"{rows}"
+            "</table>"
+        )
+    else:
+        table_html = "<p>No announcements found.</p>"
+
+    # 6️⃣ Render the final page
+    return render_template_string(f"""
+    <!DOCTYPE html>
+    <html lang="en">
+      <head>
+        <meta charset="UTF-8">
+        <title>Announcements</title>
+      </head>
+      <body>
+        <h1>Announcements for {company_name_for_display}</h1>
+        <form method="GET" action="/announcements">
+          <select name="scrip_code" onchange="this.form.submit()">
+            <option value="">-- Select a Company --</option>
+            {scrip_options_html}
+          </select>
+        </form>
+
+        {table_html}
+      </body>
+    </html>
+    """)


@app.route('/health')
def health_check():
    """Health check endpoint for Render.com."""
    # Check if the background worker thread is alive
    return jsonify(status="ok", worker_running=worker_thread.is_alive()), 200

# --- Worker Thread Setup ---
worker_thread = threading.Thread(target=start_background_worker, daemon=True)

# --- Initial Setup and App Run ---
if __name__ == '__main__':
    # Ensure log file exists
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            f.write(f"--- Application Log started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---\n")

    app.logger.info("Flask app starting.")

    # Create empty config/cache files if they don't exist on first run
    if not os.path.exists(CONFIG_FILE):
        save_config({"scrip_codes": {}, "telegram_chat_ids": []}) # Initialize with empty chat_ids list
    if not os.path.exists(CACHE_FILE):
        save_seen_ids({})

    # Load initial BSE company list for suggestions (only once at startup)
    load_bse_company_list()

    # Start the background worker thread
    if not worker_thread.is_alive():
        worker_thread.start()
        app.logger.info("Background worker thread initiated.")
    else:
        app.logger.info("Background worker thread already running.")

    # Render.com provides the port via an environment variable
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)




