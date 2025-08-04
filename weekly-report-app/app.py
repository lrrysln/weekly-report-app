import streamlit as st
import pandas as pd
import datetime
import gspread
from google.oauth2.service_account import Credentials
import matplotlib.pyplot as plt
from io import BytesIO
import base64
import re

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

# Clean column names
df.columns = df.columns.str.strip()

# --- Use 'Year Week' as timestamp ---
if 'Year Week' not in df.columns:
    st.error("❌ Column 'Year Week' not found in data. Cannot calculate week label.")
    st.stop()

df['Year Week'] = pd.to_datetime(df['Year Week'], errors='coerce')

# Use ISO week format (Monday start, standard business)
df['Week Label'] = df['Year Week'].dt.strftime('%G Week %V')
df['Year'] = df['Year Week'].dt.isocalendar().year

# Optional: Format store names and clean up strings
if 'Store Name' in df.columns:
    df['Store Name'] = df['Store Name'].str.title()

if 'Store Number' in df.columns:
    df['Store Number'] = df['Store Number'].astype(str).str.strip()

if 'Baseline' in df.columns:
    df['Baseline'] = df['Baseline'].astype(str).str.strip()

# Baseline mapping (for reference)
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

# --- Current Week's Data (Sunday to Saturday) ---
today = datetime.date.today()
start_of_week = today - datetime.timedelta(days=today.weekday() + 1 if today.weekday() != 6 else 0)
start_of_week = start_of_week if today.weekday() != 6 else today
end_of_week = start_of_week + datetime.timedelta(days=6)

# Format label as "2025 Week 32"
current_week_number = start_of_week.isocalendar()[1]
current_year = start_of_week.year
week_label = f"{current_year} Week {current_week_number:02d}"

# Filter using adjusted week range
df['Date'] = pd.to_datetime(df['Year Week'], errors='coerce').dt.date
current_week_df = df[(df['Date'] >= start_of_week) & (df['Date'] <= end_of_week)]

# 🔴 RED submission count in header using unsafe_allow_html
st.markdown(
    f"""### 📋 <span style='color:red'>{len(current_week_df)}</span> Submissions for the week of {start_of_week.strftime('%B %d')}–{end_of_week.strftime('%B %d')} (week {current_week_number} of the year), {current_year}""",
    unsafe_allow_html=True
)
st.dataframe(current_week_df.reset_index(drop=True))
