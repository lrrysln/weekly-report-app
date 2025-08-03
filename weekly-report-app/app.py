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

# Clean column names
df.columns = df.columns.str.strip()

# Format store names
df['Store Name'] = df['Store Name'].str.title()

# Convert date columns to datetime
df['Store Opening'] = pd.to_datetime(df['Store Opening'], errors='coerce')
df['Baseline'] = df['Baseline'].astype(str).str.strip()
df['Store Number'] = df['Store Number'].astype(str).str.strip()

# Generate Week Label
df['Week Label'] = df['Store Opening'].dt.strftime('%Y week %U')
df['Year'] = df['Store Opening'].dt.year

# Separate baseline & non-baseline entries
baseline_df = df[df['Baseline'] == "/True"].copy()
baseline_map = baseline_df.set_index('Store Number')['Store Opening'].to_dict()

# Weekly counts
df_weekly_counts = df.groupby(['Year', 'Week Label']).size().reset_index(name='Count')

# Create expandable weekly details
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

# Show current week's data
current_date = datetime.datetime.now()
current_week_label = current_date.strftime('%Y week %U')
current_year = current_date.year
current_week_df = df[df['Week Label'] == current_week_label]

st.markdown(f"### 📋 {len(current_week_df)} Submissions for the week of {current_date.strftime('%B %d')} (week {current_date.strftime('%U')} of the year), {current_year}")
st.dataframe(current_week_df.reset_index(drop=True))
