import os
import threading
from flask import Flask, jsonify, render_template_string

# Import the worker function from your renamed script
from bse_monitor_worker import start_bse_monitor_worker, log_message
import pandas as pd # Needed to load initial CSV for the worker
import json # Needed to load initial JSON for the worker

# --- Configuration ---
# File to list the scrip codes and names to monitor.
# This file is now defined directly in app.py
MONITORED_SCRIPTS_FILE = 'monitored_scripts.csv' 

app = Flask(__name__)

# --- Helper function to load initial scrip codes for the worker ---
def load_initial_scrip_codes(file_path):
    """
    Loads scrip codes from a local CSV/XLSX file for initial worker startup.
    This will be replaced by fetching from the admin panel in the next iteration.
    """
    scripts = {}
    if not os.path.exists(file_path):
        log_message(f"Warning: Initial monitored scripts file '{file_path}' not found for worker. Starting with empty list.")
        return scripts

    try:
        if file_path.endswith('.csv'):
            df = pd.read_csv(file_path)
        elif file_path.endswith('.xlsx'):
            df = pd.read_excel(file_path)
        else:
            log_message(f"Error: Unsupported file format for '{file_path}'. Use .csv or .xlsx for initial load.")
            return scripts

        if 'BSE Code' not in df.columns or 'Company Name' not in df.columns:
            log_message(f"Error: '{file_path}' must contain 'BSE Code' and 'Company Name' columns for initial load.")
            return scripts

        for index, row in df.iterrows():
            scrip_code = str(row['BSE Code']).strip()
            company_name = str(row['Company Name']).strip()
            if scrip_code and company_name:
                scripts[scrip_code] = company_name
        log_message(f"Successfully loaded initial {len(scripts)} scripts from {file_path} for worker.")
    except Exception as e:
        log_message(f"Error loading initial monitored scripts from {file_path} for worker: {e}")
    return scripts

# --- Flask Routes ---

@app.route('/')
def home():
    """Simple homepage to confirm the Flask app is running."""
    return render_template_string("""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>BSE Monitor Worker</title>
            <style>
                body { font-family: sans-serif; margin: 20px; text-align: center; background-color: #f4f4f4; color: #333; }
                .container { max-width: 600px; margin: auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
                h1 { color: #10486b; margin-bottom: 15px; }
                p { font-size: 1.1em; }
                .status-indicator {
                    display: inline-block; width: 15px; height: 15px; border-radius: 50%;
                    background-color: green; margin-left: 10px;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>BSE Announcement Monitor Worker</h1>
                <p>This service is running in the background.</p>
                <p>Status: <strong>Active</strong> <span class="status-indicator"></span></p>
                <p>Check the service logs on Render.com for detailed activity.</p>
            </div>
        </body>
        </html>
    """)

@app.route('/health')
def health_check():
    """Health check endpoint for Render.com."""
    return jsonify(status="ok", worker_running=worker_thread.is_alive()), 200

# --- Start the Worker in a separate thread ---
def start_worker_thread_target():
    """Function to start the BSE monitor worker in a thread."""
    log_message("Attempting to start BSE monitor worker thread...")
    # Load initial scrip codes from local CSV for the worker
    initial_scrip_codes = load_initial_scrip_codes(MONITORED_SCRIPTS_FILE)
    start_bse_monitor_worker(initial_scrip_codes)

# Create the worker thread
worker_thread = threading.Thread(target=start_worker_thread_target, daemon=True)

if __name__ == '__main__':
    # Start the worker thread explicitly when the Flask app is run
    if not worker_thread.is_alive():
        worker_thread.start()
        log_message("BSE monitor worker thread initiated.")
    else:
        log_message("BSE monitor worker thread already running.")

    # Render.com provides the port via an environment variable
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

