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
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Failed to load data from Google Sheet: {e}")
        return pd.DataFrame()

df = load_data()

if df.empty:
    st.warning("⚠️ No data loaded from Google Sheet yet.")
    st.stop()

# Clean column names
df.columns = df.columns.str.strip()

# Show available columns for reference
st.write("🧪 Available Columns:", df.columns.tolist())

# --- Use 'Year Week' as timestamp ---
if 'Year Week' not in df.columns:
    st.error("❌ Column 'Year Week' not found in data. Cannot calculate week label.")
    st.stop()

df['Year Week'] = pd.to_datetime(df['Year Week'], errors='coerce')

# Use Sunday-starting week (U.S. style)
def get_us_week_label(date):
    if pd.isna(date):
        return None
    year = date.year
    first_day = datetime.datetime(year, 1, 1)
    # Shift first day to Sunday-start week
    delta_days = (date - first_day).days
    start_day_offset = (first_day.weekday() + 1) % 7  # 0 if Jan 1 is Sunday
    week_num = ((delta_days + start_day_offset) // 7) + 1
    return f"{year} Week {week_num:02d}"

df['Week Label'] = df['Year Week'].apply(get_us_week_label)
df['Year'] = df['Year Week'].dt.year

# Optional: Clean & Format
if 'Store Name' in df.columns:
    df['Store Name'] = df['Store Name'].str.title()

if 'Store Number' in df.columns:
    df['Store Number'] = df['Store Number'].astype(str).str.strip()

if 'Baseline' in df.columns:
    df['Baseline'] = df['Baseline'].astype(str).str.strip()

# Baseline mapping (optional reference)
baseline_df = df[df.get('Baseline') == "/True"].copy()
baseline_map = baseline_df.set_index('Store Number')['Week Label'].to_dict()

# --- Weekly Overview Section ---
st.markdown("## 🗓️ Weekly Submission Volume by Year")

years = sorted(df['Year'].dropna().unique(), reverse=True)
for year in years:
    with st.expander(f"📁 {year}"):
        year_data = df[df['Year'] == year]
        weekly_counts = year_data.groupby('Week Label').size().reset_index(name='Count')
        for _, row in weekly_counts.iterrows():
            week = row['Week Label']
            count = row['Count']
            with st.expander(f"📆 {week} — {count} submission(s)"):
                st.dataframe(year_data[year_data['Week Label'] == week].reset_index(drop=True))

# --- Current Week's Data (Sunday-based) ---
today = datetime.datetime.now()
year = today.year
first_day = datetime.datetime(year, 1, 1)
delta_days = (today - first_day).days
start_day_offset = (first_day.weekday() + 1) % 7
week_number = ((delta_days + start_day_offset) // 7) + 1
current_week_label = f"{year} Week {week_number:02d}"

current_week_df = df[df['Week Label'] == current_week_label]
submission_count = len(current_week_df)

# Format title with red count
title_html = f"""
### 📋 <span><span style='color:red; font-weight:bold;'>{submission_count}</span> Submissions for {year} Week of {week_number:02d}</span>
"""
st.markdown(title_html, unsafe_allow_html=True)

st.dataframe(current_week_df.reset_index(drop=True))
