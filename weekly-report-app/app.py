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

# Show the available columns for debugging
st.write("🧪 Available Columns:", df.columns.tolist())

# Clean column names
df.columns = df.columns.str.strip()

# Try to use an appropriate timestamp column
timestamp_col = None
for col in df.columns:
    if "timestamp" in col.lower() or "submission" in col.lower():
        timestamp_col = col
        break

if timestamp_col is None:
    st.error("❌ No submission date or timestamp column found. Please check your Google Sheet.")
    st.stop()

# Convert that column to datetime and calculate Week Label
df[timestamp_col] = pd.to_datetime(df[timestamp_col], errors='coerce')
df['Week Label'] = df[timestamp_col].dt.strftime('%Y week %U')
df['Year'] = df[timestamp_col].dt.year

# Format store names
if 'Store Name' in df.columns:
    df['Store Name'] = df['Store Name'].str.title()

# Clean up data
if 'Store Number' in df.columns:
    df['Store Number'] = df['Store Number'].astype(str).str.strip()

if 'Baseline' in df.columns:
    df['Baseline'] = df['Baseline'].astype(str).str.strip()

# Separate baseline entries
baseline_df = df[df.get('Baseline') == "/True"].copy()
baseline_map = baseline_df.set_index('Store Number')['Week Label'].to_dict()

# Weekly counts
df_weekly_counts = df.groupby(['Year', 'Week Label']).size().reset_index(name='Count')

# Expand by Year > Week
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

# Current week
current_date = datetime.datetime.now()
current_week_label = current_date.strftime('%Y week %U')
current_year = current_date.year
current_week_df = df[df['Week Label'] == current_week_label]

st.markdown(f"### 📋 {len(current_week_df)} Submissions for the week of {current_date.strftime('%B %d')} (week {current_date.strftime('%U')} of the year), {current_year}")
st.dataframe(current_week_df.reset_index(drop=True))
