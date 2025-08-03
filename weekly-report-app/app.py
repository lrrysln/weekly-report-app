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

# Convert 'Year Week' (which we assume contains a date) into datetime, then extract year/week
df['Year Week'] = pd.to_datetime(df['Year Week'], errors='coerce')

# Create new column 'Week Label' like "2025 week 31"
df['Week Label'] = df['Year Week'].dt.strftime('%G week %V')  # ISO year and ISO week

# Show submission count per week label
weekly_counts = df['Week Label'].value_counts().sort_index(ascending=False)

st.subheader("🗓️ Weekly Submission Volume")
st.dataframe(
    weekly_counts.reset_index().rename(columns={
        'index': 'Week of Submission',
        'Week Label': 'Form Count'
    }),
    use_container_width=True
)

# Optional: show the full table with each row's "Week Label"
with st.expander("📋 View All Submissions with Week Labels"):
    st.dataframe(df[['Store Name', 'Store Number', 'Year Week', 'Week Label']], use_container_width=True)
