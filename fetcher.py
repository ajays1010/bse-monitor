import requests
import pandas as pd
from datetime import datetime, timedelta
import webbrowser
from rapidfuzz import process
import os # Import os for file existence check

# Load BSE company list
# Ensure bse_company_list_cleaned.csv is available in the deployment environment
# If not, this line will cause an error. For a worker, this might not be strictly needed
# unless you plan to use get_suggestions in the worker itself.
# For now, we'll keep it but be aware it needs the CSV.
try:
    # Check if the CSV exists before trying to read it
    if os.path.exists("bse_company_list_cleaned.csv"):
        bse_df = pd.read_csv("bse_company_list_cleaned.csv")
        company_names = bse_df["Company Name"].tolist()
    else:
        print("Warning: bse_company_list_cleaned.csv not found. Autocomplete/suggestions will not work.")
        bse_df = pd.DataFrame(columns=["BSE Code", "Company Name"])
        company_names = []
except Exception as e:
    print(f"Error loading bse_company_list_cleaned.csv: {e}")
    bse_df = pd.DataFrame(columns=["BSE Code", "Company Name"])
    company_names = []


def get_suggestions(query, limit=5):
    # This function is primarily for the Tkinter GUI.
    # It might not be used by the worker script.
    return process.extract(query, company_names, limit=limit)

def get_bse_announcements(scrip_code, num_announcements=15):
    if not scrip_code.isdigit():
        # Changed from messagebox.showerror to print for headless environment
        print(f"Input Error: Scrip code '{scrip_code}' must be a numeric string. Skipping.")
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
        # Limiting to num_announcements as per original logic, but fetching all from API first
        for announcement in announcements_data[:num_announcements]:
            title = announcement.get('HEADLINE', 'N/A')
            pdf_link_filename = announcement.get('ATTACHMENTNAME')
            date_time = announcement.get('DissemDT', 'N/A')
            news_id = announcement.get('NEWSID')
            scrip_cd = announcement.get('SCRIP_CD')

            # Construct full PDF link
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
        # Changed from messagebox.showerror to print for headless environment
        print(f"Request Error in get_bse_announcements for {scrip_code}: {e}")
        return []
    except Exception as e:
        # Changed from messagebox.showerror to print for headless environment
        print(f"An unexpected error occurred in get_bse_announcements for {scrip_code}:\n{e}")
        return []

# The Tkinter GUI application part is commented out or removed if not needed for the worker.
# If you still use fetcher.py as a standalone GUI, keep this part.
# For Render deployment, this part is not executed by app.py.
# class AnnouncerApp(tk.Tk):
#     def __init__(self):
#         super().__init__()
#         self.title("BSE Corporate Announcements Tracker")
#         # ... (rest of Tkinter GUI code)
#
# if __name__ == "__main__":
#     # This block will only run if fetcher.py is executed directly, not when imported by app.py
#     # You can keep it for local GUI testing if desired.
#     app = AnnouncerApp()
#     app.mainloop()

