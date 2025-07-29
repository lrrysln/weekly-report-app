# --- Setup ---
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import streamlit as st

# --- Auth ---
CREDENTIAL_PATH = "/content/drive/My Drive/gspread_credentials/creds.json"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

import streamlit as st
import json
from google.oauth2.service_account import Credentials
service_account_info = json.loads(st.secrets["gcp_service_account"].to_json())
creds = Credentials.from_service_account_info(service_account_info)
client = gspread.authorize(creds)

# --- Load Data from Google Sheet ---
SHEET_NAME = "Construction Weekly Updates"
WORKSHEET_NAME = "Sheet1"
spreadsheet = client.open(SHEET_NAME)
worksheet = spreadsheet.worksheet(WORKSHEET_NAME)
data = worksheet.get_all_records()
df = pd.DataFrame(data)

# --- Format Dates to MM/DD/YY ---
date_columns = [col for col in df.columns if "Baseline" in col or "TCO" in col or "Walk" in col or "Turnover" in col or "Open to Train" in col or "Store Opening" in col]
for col in date_columns:
    df[col] = pd.to_datetime(df[col], errors="coerce").dt.strftime('%m/%d/%y')

# --- Milestone Change Analysis ---
df["Delta Days"] = (
    pd.to_datetime(df["Store Opening"], errors="coerce") -
    pd.to_datetime(df["Baseline Store Opening"], errors="coerce")
).dt.days

df["Flag"] = df["Delta Days"].apply(
    lambda x: "🚩 Delay" if x and x > 7 else ("✅ On Track" if x and abs(x) <= 3 else "")
)

df["Trend"] = df["Delta Days"].apply(
    lambda x: "↗ Trending Later" if x and x > 0 else ("↘ Trending Earlier" if x and x < 0 else "→ Stable")
)

# --- Note Quality Score ---
def score_note(note):
    if not note or len(note.strip()) < 10:
        return "❌ Missing"
    elif len(note) > 200:
        return "✅ Detailed"
    elif any(word in note.lower() for word in ["delay", "permit", "inspection", "crew", "weather"]):
        return "⚠️ Needs Attention"
    else:
        return "ℹ️ Okay"

df["Note Score"] = df["Notes"].apply(score_note)

# --- Streamlit Dashboard ---
st.title("🏗️ Construction Milestone Dashboard")
st.dataframe(df[
    ["Week of the Year", "Store Name", "Store Number", "Prototype", "Flag", "Delta Days", "Trend", "Note Score", "Notes"]
])

# --- Download Button ---
csv = df.to_csv(index=False).encode('utf-8')
st.download_button("Download CSV", data=csv, file_name="Weekly_Construction_Report.csv", mime="text/csv")
