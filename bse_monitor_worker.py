import time
import json
import os
import requests
from datetime import datetime, timedelta
import schedule
import random # For exponential backoff jitter
# We'll assume fetcher.py is available in the same environment
# from fetcher import get_bse_announcements # This import will happen in the main function now

# --- Configuration ---
# File to list the scrip codes and names to monitor.
# This file will be loaded by the worker itself, or by the admin panel if you integrate that.
MONITORED_SCRIPTS_FILE = 'monitored_scripts.csv' 

# Path to the JSON file where announcements will be stored (for tracking new ones)
CACHE_FILE = "seen_announcements.json"

# File to log Telegram messages and script activity
LOG_FILE = "telegram_log.txt" 

MAX_RETRIES = 3 # Max retries for the main scheduling loop
DAYS_TO_FETCH = 2 # Set to 2 to include today and the previous 2 full days (total 3 days)

# Telegram settings
TELEGRAM_BOT_TOKEN = '7527888676:AAEul4nktWJT2Bt7vciEsC9ukHfV1bTx-ck'
TELEGRAM_CHAT_ID = '453652457'
TELEGRAM_TIMEOUT = 15 # Increased timeout for Telegram requests (from 10 to 15 seconds)
TELEGRAM_MAX_RETRIES = 5 # Max retries for sending a single Telegram message
TELEGRAM_RETRY_DELAY_BASE = 5 # Base delay in seconds for exponential backoff

# Global variable to store currently monitored scrip codes, reloaded periodically
# This will be managed by the worker itself, or by fetching from the admin panel later
GLOBAL_SCRIP_CODES = {} 

# --- Helper Functions ---

# Note: load_monitored_scripts is not directly used here anymore if fetching from admin panel.
# If you decide to keep local CSV loading for the worker, re-add it here.
# For now, we'll assume GLOBAL_SCRIP_CODES is populated externally or by a specific load function.

def load_seen_ids():
    """Loads previously seen announcement IDs from a JSON cache file."""
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            log_message(f"Warning: Could not decode JSON from {CACHE_FILE}. Starting with empty cache.")
            return {}
    return {}

def save_seen_ids(data):
    """Saves current seen announcement IDs to a JSON cache file."""
    with open(CACHE_FILE, "w") as f:
        json.dump(data, f)

def log_message(message):
    """Logs messages to a local file with a timestamp."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {message}\n")
    print(f"[LOG] {message}") # Also print to console for testing

def send_telegram_message(message):
    """Sends a message to Telegram with retry logic and logs it."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}

    for attempt in range(TELEGRAM_MAX_RETRIES):
        try:
            response = requests.post(url, data=payload, timeout=TELEGRAM_TIMEOUT)
            response.raise_for_status() # Raises HTTPError for bad responses (4xx or 5xx)
            log_message(f"Telegram message sent successfully (Attempt {attempt + 1}/{TELEGRAM_MAX_RETRIES}): {message}")
            return True # Message sent successfully
        except requests.exceptions.Timeout as e:
            delay = (TELEGRAM_RETRY_DELAY_BASE * (2 ** attempt)) + random.uniform(0, 1) # Exponential backoff with jitter
            log_message(f"Telegram send timeout (Attempt {attempt + 1}/{TELEGRAM_MAX_RETRIES}): {e}. Retrying in {delay:.2f} seconds.")
            time.sleep(delay)
        except requests.exceptions.RequestException as e:
            delay = (TELEGRAM_RETRY_DELAY_BASE * (2 ** attempt)) + random.uniform(0, 1)
            log_message(f"Telegram request error (Attempt {attempt + 1}/{TELEGRAM_MAX_RETRIES}): {e}. Retrying in {delay:.2f} seconds.")
            time.sleep(delay)
        except Exception as e:
            log_message(f"Unexpected error sending Telegram message (Attempt {attempt + 1}/{TELEGRAM_MAX_RETRIES}): {e}. No further retries for this attempt.")
            break # Break on unexpected errors not related to requests

    log_message(f"Failed to send Telegram message after {TELEGRAM_MAX_RETRIES} attempts: {message}")
    return False # Message failed after all retries

def check_for_new_announcements_task():
    """
    The main task function that will be scheduled to run periodically.
    It fetches, filters, and sends new announcements.
    """
    # Import get_bse_announcements here to avoid circular import if fetcher.py imports this file
    from fetcher import get_bse_announcements 

    seen = load_seen_ids()
    
    current_time = datetime.now()
    cutoff_date = current_time - timedelta(days=DAYS_TO_FETCH)
    log_message(f"Checking for new announcements since {cutoff_date.strftime('%Y-%m-%d %H:%M:%S')}")

    new_announcements_found_this_cycle = False

    # Use the globally loaded scrip codes (populated by start_bse_monitor_worker)
    if not GLOBAL_SCRIP_CODES:
        log_message("No scrip codes loaded. Skipping announcement check in this cycle.")
        return # Exit if no scrip codes to monitor

    for scrip_code, company_name in GLOBAL_SCRIP_CODES.items():
        log_message(f"Processing {company_name} (Scrip Code: {scrip_code})...")
        anns = get_bse_announcements(scrip_code, num_announcements=50) 

        if not anns:
            log_message(f"No announcements fetched for scrip code {scrip_code}.")
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
                    log_message(f"Warning: Failed to parse date '{ann_full_date_str}' for announcement. Skipping date filter for this item.")
                    ann_date = None

            if ann_date:
                if ann_date.date() >= cutoff_date.date():
                    news_id = ann['XBRL Link'].split("Bsenewid=")[-1].split("&")[0] if "Bsenewid=" in ann['XBRL Link'] else ann['Title'] + ann['Date']

                    if news_id not in seen[code]:
                        seen[code][news_id] = True # Mark as seen
                        new_items_for_scrip.append(ann)
                        log_message(f"Found new announcement for {scrip_code} ({company_name}): {ann['Title']}")
                        new_announcements_found_this_cycle = True
            else:
                log_message(f"Announcement for {scrip_code} has unparsable date format '{ann_full_date_str}'. Skipping this announcement.")

        for ann in new_items_for_scrip:
            msg_text = f"📢 {ann['Title']}\n🕒 {ann['Date']}\n🔗 {ann['PDF Link']}"
            send_telegram_message(msg_text)

    save_seen_ids(seen)
    if not new_announcements_found_this_cycle:
        log_message("No new announcements found in this cycle.")
    log_message(f"Monitoring cycle completed.")

def start_bse_monitor_worker(initial_scrip_codes_dict):
    """
    Initializes and starts the BSE monitoring worker.
    This function will be called from the Flask app in a separate thread.
    """
    global GLOBAL_SCRIP_CODES
    GLOBAL_SCRIP_CODES = initial_scrip_codes_dict # Set initial scrip codes from Flask app

    # Ensure log file exists
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            f.write(f"--- Telegram Log started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---\n")

    log_message("BSE Monitor Worker started.")
    log_message(f"Initial scrips loaded: {', '.join(GLOBAL_SCRIP_CODES.keys()) if GLOBAL_SCRIP_CODES else 'None'}")

    # Run the task immediately on startup
    check_for_new_announcements_task()

    # Schedule the main announcement checking task
    schedule.every(5).minutes.do(check_for_new_announcements_task)
    
    # Schedule the scrip code reloading task (e.g., every 15 minutes)
    # This will fetch from the admin panel URL once integrated.
    # For now, it will just reload the local CSV.
    # You'll replace this with a call to fetch from ADMIN_PANEL_URL later.
    schedule.every(15).minutes.do(lambda: log_message("Scheduled reload of scrip codes (placeholder for external fetch)."))


    retries = 0
    try:
        while True:
            try:
                schedule.run_pending()
                time.sleep(1) # Sleep for 1 second to avoid high CPU usage
                retries = 0 # Reset retries on successful loop iteration
            except Exception as e:
                log_message(f"Error in main scheduling loop: {e}")
                print(f"Error in main scheduling loop: {e}")
                retries += 1
                if retries >= MAX_RETRIES:
                    log_message(f"Max retries ({MAX_RETRIES}) reached for scheduling loop. Exiting.")
                    print("Max retries reached. Exiting.")
                    break
                log_message(f"Retrying scheduling loop in 60 seconds (retry {retries}/{MAX_RETRIES}).")
                time.sleep(60)

    except KeyboardInterrupt:
        log_message("Monitoring manually stopped by user (KeyboardInterrupt).")
        print("Monitoring manually stopped.")
    finally:
        log_message("BSE Monitor Worker finished.")

# Removed the if __name__ == "__main__": block so it can be imported as a module
