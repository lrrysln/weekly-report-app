# --- Setup ---
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import streamlit as st

# --- Auth ---
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=SCOPES)
client = gspread.authorize(creds)

# --- Load Data from Google Sheet ---
SHEET_NAME = "Construction Weekly Updates"
WORKSHEET_NAME = "Sheet1"
worksheet = client.open(SHEET_NAME).worksheet(WORKSHEET_NAME)
data = worksheet.get_all_records()
df = pd.DataFrame(data)

# --- Format Dates to MM/DD/YY ---
date_columns = [col for col in df.columns if any(key in col for key in ["Baseline", "TCO", "Walk", "Turnover", "Open to Train", "Store Opening"])]
for col in date_columns:
    df[col] = pd.to_datetime(df[col], errors="coerce").dt.strftime('%m/%d/%y')

# --- Milestone Change Analysis ---
if "Store Opening" in df.columns and "Baseline Store Opening" in df.columns:
    df["Delta Days"] = (
        pd.to_datetime(df["Store Opening"], errors="coerce") -
        pd.to_datetime(df["Baseline Store Opening"], errors="coerce")
    ).dt.days

    df["Flag"] = df["Delta Days"].apply(
        lambda x: "🚩 Delay" if pd.notnull(x) and x > 7 else ("✅ On Track" if pd.notnull(x) and abs(x) <= 3 else "")
    )

    df["Trend"] = df["Delta Days"].apply(
        lambda x: "↗ Trending Later" if pd.notnull(x) and x > 0 else ("↘ Trending Earlier" if pd.notnull(x) and x < 0 else "→ Stable")
    )

# --- Note Quality Score ---
def score_note(note):
    if not isinstance(note, str) or len(note.strip()) < 10:
        return "❌ Missing"
    elif len(note) > 200:
        return "✅ Detailed"
    elif any(word in note.lower() for word in ["delay", "permit", "inspection", "crew", "weather"]):
        return "⚠️ Needs Attention"
    else:
        return "ℹ️ Okay"

if "Notes" in df.columns:
    df["Note Score"] = df["Notes"].apply(score_note)

# --- Streamlit Dashboard ---
st.title("🏗️ Construction Milestone Dashboard")

cols_to_show = ["Week of the Year", "Store Name", "Store Number", "Prototype", "Flag", "Delta Days", "Trend", "Note Score", "Notes"]
available_cols = [col for col in cols_to_show if col in df.columns]
st.dataframe(df[available_cols])

# --- Download Button ---
csv = df.to_csv(index=False).encode('utf-8')
st.download_button("Download CSV", data=csv, file_name="Weekly_Construction_Report.csv", mime="text/csv")
