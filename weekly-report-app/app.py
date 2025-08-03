import streamlit as st
import pandas as pd
import datetime
import re
import matplotlib.pyplot as plt
import gspread
from google.oauth2.service_account import Credentials
import base64
from io import BytesIO

# --- Auth & Google Sheets Setup ---
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=SCOPES)
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

# --- Clean column names ---
df.columns = df.columns.str.strip()

# --- Ensure datetime conversion for first column ---
first_column_name = df.columns[0]
df[first_column_name] = pd.to_datetime(df[first_column_name], errors='coerce')
df = df.dropna(subset=[first_column_name])

# --- Week Label (e.g., "2025 week 31") ---
df['Week Label'] = df[first_column_name].dt.strftime('%G week %V')

# --- Display Weekly Submission Counts ---
weekly_counts = df['Week Label'].value_counts().sort_index(ascending=False)
st.subheader("🗓️ Weekly Submission Volume")
st.dataframe(
    weekly_counts.reset_index().rename(columns={'index': 'Week of Submission', 'Week Label': 'Form Count'}),
    use_container_width=True
)

# Optional full data view
with st.expander("📄 Full Submission Table with Week Labels"):
    st.dataframe(df, use_container_width=True)

# --- Additional Cleaning ---
df['Store Name'] = df['Store Name'].str.title()
df['Store Opening'] = pd.to_datetime(df['Store Opening'], errors='coerce')
df['Baseline'] = df['Baseline'].astype(str).str.strip()
df['Store Number'] = df['Store Number'].astype(str).str.strip()

# --- Baseline Map ---
baseline_df = df[df['Baseline'] == "/True"].copy()
baseline_map = baseline_df.set_index('Store Number')['Store Opening'].to_dict()

def compute_trend(row):
    store_number = row['Store Number']
    current_open = row['Store Opening']
    if row['Baseline'] == "/True":
        return "baseline"
    baseline_open = baseline_map.get(store_number)
    if pd.isna(current_open) or pd.isna(baseline_open):
        return "no baseline dates"
    if current_open > baseline_open:
        return "pushed"
    elif current_open < baseline_open:
        return "pulled in"
    else:
        return "held"

df['Trend'] = df.apply(compute_trend, axis=1)

def compute_delta(row):
    baseline_open = baseline_map.get(row['Store Number'])
    if pd.isna(row['Store Opening']) or pd.isna(baseline_open):
        return 0
    return (row['Store Opening'] - baseline_open).days

df['Store Opening Delta'] = df.apply(compute_delta, axis=1)

def flag_delta(delta):
    if isinstance(delta, int) and abs(delta) > 5:
        return '<span style="color:red;font-weight:bold;">*</span>'
    return ""

df['Flag'] = df['Store Opening Delta'].apply(flag_delta)

# --- Notes Filtering (if present) ---
keywords = [ "behind schedule", "lagging", "delay", "critical path", "cpm impact", "work on hold", "stop work order",
    "reschedule", "off track", "schedule drifting", "missed milestone", "budget overrun", "cost impact",
    "change order pending", "claim submitted", "dispute", "litigation risk", "schedule variance",
    "material escalation", "labor shortage", "equipment shortage", "low productivity", "rework required",
    "defects found", "qc failure", "weather delays", "permit delays", "regulatory hurdles",
    "site access issues", "awaiting sign-off", "conflict", "identified risk", "mitigation", "forecast revised"
]

if 'Notes' in df.columns:
    def check_notes(text):
        text_lower = str(text).lower()
        return any(kw in text_lower for kw in keywords)

    df['Notes'] = df['Notes'].fillna("")
    df['Notes Filtered'] = df['Notes'].apply(lambda x: x if check_notes(x) else "see report below")
else:
    df['Notes'] = ""
    df['Notes Filtered'] = "see report below"

summary_cols = ['Store Name', 'Store Number', 'Prototype', 'CPM', 'Flag', 'Store Opening Delta', 'Trend', 'Notes Filtered']
summary_df = df[summary_cols].drop_duplicates(subset=['Store Number']).reset_index(drop=True)

# --- Report Table Output ---
st.subheader("📋 Submitted Reports Overview")
st.markdown(f"<h4><span style='color:red;'><b>{len(df)}</b></span> form responses have been submitted</h4>", unsafe_allow_html=True)
st.dataframe(df[['Store Number', 'Store Name', 'CPM', 'Prototype', 'Week Label']], use_container_width=True)

# --- Password-Protected Summary ---
st.subheader("🔐 Generate Weekly Summary Report")
password = st.text_input("Enter Password", type="password")

# The report generation logic from v5.5.2 can be reused here (omitted to save space)
