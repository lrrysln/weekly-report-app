# Combined Script: Submission Viewer + Weekly Summary + Trend Report

import streamlit as st
import pandas as pd
import datetime
import gspread
from google.oauth2.service_account import Credentials

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

# --- Preprocessing ---
df.columns = df.columns.str.strip()
df['Year Week'] = pd.to_datetime(df['Year Week'], errors='coerce')
df['Week Label'] = df['Year Week'].dt.strftime('%G Week %V')
df['Year'] = df['Year Week'].dt.isocalendar().year

if 'Store Name' in df.columns:
    df['Store Name'] = df['Store Name'].str.title()
if 'Store Number' in df.columns:
    df['Store Number'] = df['Store Number'].astype(str).str.strip()
if 'Baseline' in df.columns:
    df['Baseline'] = df['Baseline'].astype(str).str.strip()

# --- Current Week Display ---
today = datetime.date.today()
iso_info = today.isocalendar()
current_week_number = iso_info.week
current_year = iso_info.year
week_label = f"{current_year} Week {current_week_number:02d}"

st.markdown(
    f"### 📋 Submissions Summary for <span style='color:red'>{week_label}</span>",
    unsafe_allow_html=True
)

# --- Weekly Expander View ---
df['Date'] = df['Year Week'].dt.date
current_week_df = df[df['Week Label'] == week_label]
columns_to_show = ['Store Number', 'Store Name', 'CPM', 'Prototype', 'Week Label']
st.dataframe(current_week_df[columns_to_show].reset_index(drop=True), use_container_width=True)

st.subheader("🔐 Generate Weekly Submission Report")
with st.form("password_form"):
    password_input = st.text_input("Enter Password", type="password")
    submitted = st.form_submit_button("Submit")

if submitted and password_input == "1234":
    st.markdown("## 🗓️ Weekly Submission Volume")
    years = sorted(df['Year'].dropna().unique(), reverse=True)
    for year in years:
        year_data = df[df['Year'] == year]
        weekly_counts = year_data.groupby('Week Label').size().reset_index(name='Count')
        for _, row in weekly_counts.iterrows():
            week = row['Week Label']
            count = row['Count']
            with st.expander(f"📆 {week} — {count} submission(s)"):
                st.dataframe(year_data[year_data['Week Label'] == week].reset_index(drop=True))
else:
    if submitted:
        st.error("❌ Incorrect password.")
    else:
        st.info("Please enter the password and click Submit to view full submission breakdown.")

# --- Store Opening Analysis ---
df['Store Opening'] = pd.to_datetime(df['Store Opening'], errors='coerce')
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

keywords = [
    "behind schedule", "lagging", "delay", "critical path", "cpm impact", "work on hold",
    "stop work order", "reschedule", "off track", "schedule drifting", "missed milestone",
    "budget overrun", "cost impact", "change order pending", "claim submitted", "dispute",
    "litigation risk", "schedule variance", "material escalation", "labor shortage",
    "equipment shortage", "low productivity", "rework required", "defects found", "qc failure",
    "weather delays", "permit delays", "regulatory hurdles", "site access issues", "awaiting sign-off",
    "conflict", "identified risk", "mitigation", "forecast revised"
]

def check_notes(text):
    text_lower = str(text).lower()
    return any(kw in text_lower for kw in keywords)

df['Notes'] = df['Notes'].fillna("")
df['Notes Filtered'] = df['Notes'].apply(lambda x: x if check_notes(x) else "see report below")

summary_cols = ['Store Name', 'Store Number', 'Prototype', 'CPM', 'Flag', 'Store Opening Delta', 'Trend', 'Notes Filtered']
summary_df = df[summary_cols].drop_duplicates(subset=['Store Number']).reset_index(drop=True)

# You may include additional logic or export here if needed.
