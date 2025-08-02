import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import json

# --- Page Config ---
st.set_page_config(page_title="Weekly Construction Report", layout="wide")

# --- Auth & Google Sheets Setup ---
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds = Credentials.from_service_account_info(
    st.secrets["gcp_service_account"], scopes=SCOPES
)
client = gspread.authorize(creds)

SPREADSHEET_ID = "1cfr5rCRoRXuDJonarDbokznlaHHVpn1yUfTwo_ePL3w"
WORKSHEET_NAME = "Sheet1"

@st.cache_data(ttl=600)
def load_data():
    try:
        sheet = client.open_by_key(SPREADSHEET_ID).worksheet(WORKSHEET_NAME)
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        return df
    except Exception as e:
        st.error(f"Failed to load data from Google Sheet: {e}")
        return pd.DataFrame()

df = load_data()

if df.empty:
    st.warning("⚠️ No data loaded from Google Sheet yet.")
    st.stop()

# --- Column Parsing and Cleaning ---
# Clean column names to avoid unicode issues
df.columns = df.columns.str.strip().str.replace("⚪", "", regex=False).str.replace(" ", "_")

# Handle date columns
date_columns = ["Baseline_Store_Opening", "Current_Store_Opening", "Turnover", "TCO"]
for col in date_columns:
    if col in df.columns:
        df[col + "_Parsed"] = pd.to_datetime(df[col], errors="coerce")

# --- Trend Detection Logic ---
if "Current_Store_Opening_Parsed" in df.columns and "Baseline_Store_Opening_Parsed" in df.columns:
    df["Opening_Trend"] = (df["Current_Store_Opening_Parsed"] - df["Baseline_Store_Opening_Parsed"]).dt.days

# --- Display Summary ---
st.title("📈 Weekly Construction Report")
st.markdown("Showing key trends between Baseline and Current milestones.")

with st.expander("📊 Raw Data Preview", expanded=False):
    st.dataframe(df)

# --- Highlight Key Trends ---
if "Opening_Trend" in df.columns:
    st.subheader("📅 Opening Date Variance (Days)")
    st.bar_chart(df[["Opening_Trend"]])
else:
    st.info("Trend columns not found — check column headers and date format.")

# --- Export or Save (Optional Placeholder) ---
# You can add exporting logic here if needed (Google Drive, Excel, etc.)
