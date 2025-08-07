import tkinter as tk
from tkinter import ttk, messagebox
import requests
import pandas as pd
from datetime import datetime, timedelta
import webbrowser
from rapidfuzz import process

# Load BSE company list
bse_df = pd.read_csv("bse_company_list_cleaned.csv")
company_names = bse_df["Company Name"].tolist()

def get_suggestions(query, limit=5):
    return process.extract(query, company_names, limit=limit)

def get_bse_announcements(scrip_code, num_announcements=15):
    if not scrip_code.isdigit():
        messagebox.showerror("Input Error", "Scrip code must be a numeric string.")
        return []

    try:
        api_url = "https://api.bseindia.com/BseIndiaAPI/api/AnnGetData/w"
        to_date = datetime.now()
        from_date = to_date - timedelta(days=90)

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

            pdf_link = f"https://www.bseindia.com/xml-data/corpfiling/Attachlive/{pdf_link_filename}" if pdf_link_filename else "No PDF Available"
            xbrl_link = f"https://www.bseindia.com/Msource/90D/CorpXbrlGen.aspx?Bsenewid={news_id}&Scripcode={scrip_cd}" if news_id and scrip_cd else "No XBRL Available"

            announcements_list.append({
                "Date": date_time,
                "Title": title,
                "PDF Link": pdf_link,
                "XBRL Link": xbrl_link
            })

        return announcements_list

    except requests.exceptions.RequestException as e:
        messagebox.showerror("Request Error", f"An error occurred during the request:\n{e}")
        return []
    except Exception as e:
        messagebox.showerror("Error", f"An unexpected error occurred:\n{e}")
        return []

class AnnouncerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("BSE Corporate Announcements Tracker")
        self.geometry("1200x600")

        self.style = ttk.Style(self)
        self.style.theme_use("clam")
        self.style.configure("Treeview.Heading", font=("Helvetica", 10, "bold"))
        self.style.configure("Treeview", rowheight=25, font=("Helvetica", 9), wraplength=500)
        self.style.map("Treeview", background=[('selected', '#e0e0e0')], foreground=[('selected', 'black')])

        top_frame = ttk.Frame(self, padding="10")
        top_frame.pack(fill=tk.X)

        tree_frame = ttk.Frame(self, padding="10")
        tree_frame.pack(expand=True, fill=tk.BOTH)

        status_frame = ttk.Frame(self, padding="5")
        status_frame.pack(fill=tk.X)

        # --- Top Frame with autocomplete ---
        ttk.Label(top_frame, text="Company Name:").pack(side=tk.LEFT)
        self.company_var = tk.StringVar()
        self.company_entry = ttk.Entry(top_frame, textvariable=self.company_var, width=30)
        self.company_entry.pack(side=tk.LEFT, padx=5)
        self.company_entry.bind("<KeyRelease>", self.update_suggestions)

        self.suggestion_box = tk.Listbox(top_frame, height=4, width=30)
        self.suggestion_box.pack(side=tk.LEFT, padx=5)
        self.suggestion_box.bind("<<ListboxSelect>>", self.select_company)

        ttk.Label(top_frame, text="BSE Scrip Code:").pack(side=tk.LEFT)
        self.scrip_entry = ttk.Entry(top_frame, width=10)
        self.scrip_entry.pack(side=tk.LEFT, padx=5)
        self.scrip_entry.insert(0, "500325")

        self.fetch_button = ttk.Button(top_frame, text="Fetch Announcements", command=self.fetch_and_display)
        self.fetch_button.pack(side=tk.LEFT, padx=5)

        self.tree = ttk.Treeview(tree_frame, columns=("Date", "Title", "PDF Link", "XBRL Link"), show="headings")
        self.tree.heading("Date", text="Date & Time")
        self.tree.heading("Title", text="Announcement Title")
        self.tree.heading("PDF Link", text="PDF Link")
        self.tree.heading("XBRL Link", text="XBRL Link")

        self.tree.column("Date", width=150, anchor=tk.W)
        self.tree.column("Title", width=550, anchor=tk.W)
        self.tree.column("PDF Link", width=225, anchor=tk.W)
        self.tree.column("XBRL Link", width=225, anchor=tk.W)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)
        self.tree.pack(expand=True, fill=tk.BOTH)

        self.tree.bind("<Double-1>", self.on_double_click)

        self.status_label = ttk.Label(status_frame, text="Enter a company name or scrip code and click fetch.", anchor=tk.W)
        self.status_label.pack(fill=tk.X)

    def update_suggestions(self, event=None):
        query = self.company_var.get()
        self.suggestion_box.delete(0, tk.END)

        if query.strip():
            matches = get_suggestions(query, limit=5)
            for name, _, _ in matches:
                self.suggestion_box.insert(tk.END, name)

    def select_company(self, event=None):
        try:
            selection = self.suggestion_box.get(self.suggestion_box.curselection())
            self.company_var.set(selection)

            row = bse_df[bse_df["Company Name"] == selection]
            if not row.empty:
                code = row.iloc[0]["BSE Code"]
                self.scrip_entry.delete(0, tk.END)
                self.scrip_entry.insert(0, str(code))
                self.status_label.config(text=f"Selected {selection} with BSE Code {code}")
        except Exception as e:
            messagebox.showerror("Selection Error", f"Could not select company:\n{e}")

    def fetch_and_display(self):
        scrip_code = self.scrip_entry.get()
        if not scrip_code:
            messagebox.showwarning("Input Error", "Please enter a scrip code.")
            return

        self.status_label.config(text=f"Fetching announcements for scrip code {scrip_code}...")
        self.update_idletasks()

        for i in self.tree.get_children():
            self.tree.delete(i)

        announcements = get_bse_announcements(scrip_code)

        if announcements:
            self.status_label.config(text=f"Fetched {len(announcements)} announcements. Double-click to open a link.")
            for ann in announcements:
                self.tree.insert("", tk.END, values=(ann["Date"], ann["Title"], ann["PDF Link"], ann["XBRL Link"]))
        else:
            self.status_label.config(text=f"No announcements found for scrip code {scrip_code}.")

    def on_double_click(self, event):
        try:
            region = self.tree.identify_region(event.x, event.y)
            if region != "cell":
                return

            item_id = self.tree.selection()[0]
            item = self.tree.item(item_id)
            column_id = self.tree.identify_column(event.x)

            link = None
            if column_id == "#3":
                link = item['values'][2]
            elif column_id == "#4":
                link = item['values'][3]

            if link and link.startswith('http'):
                self.status_label.config(text=f"Opening link: {link}")
                webbrowser.open_new_tab(link)
            else:
                self.status_label.config(text="No valid link available.")
                messagebox.showinfo("No Link", "There is no valid link available for this item.")
        except IndexError:
            pass
        except Exception as e:
            messagebox.showerror("Error", f"Could not open the link:\n{e}")

if __name__ == "__main__":
    app = AnnouncerApp()
    app.mainloop()

