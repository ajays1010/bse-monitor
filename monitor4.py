import time
import json
import os
import requests
from datetime import datetime, timedelta
import schedule # Re-introduced for scheduling
from fetcher import get_bse_announcements # Assuming fetcher.py is in the same directory

# --- Configuration ---
SCRIP_CODES = ['533104', '530669']  # Example: Reliance, Tata Motors
CACHE_FILE = "seen_announcements.json"
LOG_FILE = "telegram_log.txt" # File to log Telegram messages
MAX_RETRIES = 3
DAYS_TO_FETCH = 1 # Set to 2 to include today and the previous 2 full days (total 3 days)

# Telegram settings
TELEGRAM_BOT_TOKEN = '7527888676:AAEul4nktWJT2Bt7vciEsC9ukHfV1bTx-ck'
TELEGRAM_CHAT_ID = '453652457'

# --- Helper Functions ---

def load_seen_ids():
    """Loads previously seen announcement IDs from a JSON cache file."""
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            print(f"Warning: Could not decode JSON from {CACHE_FILE}. Starting with empty cache.")
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
    """Sends a message to Telegram and logs it."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        response = requests.post(url, data=payload, timeout=10)
        response.raise_for_status()
        log_message(f"Telegram message sent successfully: {message}")
    except Exception as e:
        log_message(f"Telegram error: {e} for message: {message}")
        print(f"Telegram error: {e}") # Print error to console
        # Optionally, re-raise if you want the main loop to handle retries for Telegram failures
        # raise

def check_for_new_announcements_task():
    """
    The main task function that will be scheduled to run periodically.
    It fetches, filters, and sends new announcements.
    """
    seen = load_seen_ids()
    
    current_time = datetime.now()
    # Calculate the cutoff date.
    # DAYS_TO_FETCH = 2 means today (day 0), yesterday (day 1), and the day before yesterday (day 2).
    cutoff_date = current_time - timedelta(days=DAYS_TO_FETCH)
    log_message(f"Checking for new announcements since {cutoff_date.strftime('%Y-%m-%d %H:%M:%S')}")

    new_announcements_found_this_cycle = False

    for code in SCRIP_CODES:
        # Fetch announcements, explicitly setting num_announcements to a higher value
        # to ensure we get enough recent ones for filtering.
        anns = get_bse_announcements(code, num_announcements=50) 

        if not anns:
            log_message(f"No announcements fetched for scrip code {code}.")
            continue

        if code not in seen:
            seen[code] = {} # Initialize as dictionary for news_id tracking

        new_items_for_scrip = []
        for ann in anns:
            ann_full_date_str = ann.get('Date', '')
            ann_date = None
            
            try:
                # Attempt to parse ISO 8601 format directly (e.g., "YYYY-MM-DDTHH:MM:SS.ms")
                ann_date = datetime.fromisoformat(ann_full_date_str)
            except ValueError:
                # Fallback if fromisoformat fails (e.g., non-standard fractional seconds or other issues)
                try:
                    # Try parsing by splitting at 'T' or space and then parsing the date part
                    date_only_str = ann_full_date_str.split('T')[0].split(' ')[0]
                    ann_date = datetime.strptime(date_only_str, '%Y-%m-%d')
                except ValueError:
                    log_message(f"Warning: Failed to parse date '{ann_full_date_str}' for announcement. Skipping date filter for this item.")
                    ann_date = None

            # Proceed only if date was successfully parsed
            if ann_date:
                # Compare only the date part for filtering (ignore time of day for cutoff)
                if ann_date.date() >= cutoff_date.date():
                    # Use a unique identifier for the announcement to prevent re-sending
                    news_id = ann['XBRL Link'].split("Bsenewid=")[-1].split("&")[0] if "Bsenewid=" in ann['XBRL Link'] else ann['Title'] + ann['Date']

                    if news_id not in seen[code]:
                        seen[code][news_id] = True # Mark as seen
                        new_items_for_scrip.append(ann)
                        log_message(f"Found new announcement for {code}: {ann['Title']}")
                        new_announcements_found_this_cycle = True
                else:
                    log_message(f"Announcement for {code} on {ann_date.strftime('%Y-%m-%d')} is older than {DAYS_TO_FETCH} days. Skipping.")
            else:
                log_message(f"Announcement for {code} has unparsable date format '{ann_full_date_str}'. Skipping this announcement.")

        for ann in new_items_for_scrip:
            msg_text = f"� {ann['Title']}\n🕒 {ann['Date']}\n🔗 {ann['PDF Link']}"
            send_telegram_message(msg_text)

    save_seen_ids(seen)
    if not new_announcements_found_this_cycle:
        log_message("No new announcements found in this cycle.")
    log_message(f"Monitoring cycle completed.")


def main():
    """Sets up the scheduler and runs the continuous monitoring loop."""
    # Ensure log file exists
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            f.write(f"--- Telegram Log started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---\n")

    log_message("Monitoring script started.")
    log_message(f"Scheduled to check every 5 minutes for scrips: {', '.join(SCRIP_CODES)}")

    # Run the task immediately on startup
    check_for_new_announcements_task()

    # Schedule the task to run every 5 minutes
    schedule.every(5).minutes.do(check_for_new_announcements_task)

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
        log_message("Monitoring script finished.")

if __name__ == "__main__":
    main()

