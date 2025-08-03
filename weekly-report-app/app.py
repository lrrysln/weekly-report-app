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

# ✅ Clean column headers
df.columns = df.columns.str.strip()

# ✅ Convert first column to datetime
first_column_name = df.columns[0]
df[first_column_name] = pd.to_datetime(df[first_column_name], errors='coerce')

# ✅ Create new column for "Year Week"
df['Year Week'] = df[first_column_name].dt.strftime('%Y Week %U')  # %U = Week number, Sunday as first day
# OR use ISO calendar: df['Year Week'] = df[first_column_name].dt.isocalendar().apply(lambda x: f"{x['year']} Week {x['week']:02}", axis=1)

# ✅ Use Year Week as display label
df['Week of Submission'] = df['Year Week']

# ✅ Count submissions per week
weekly_counts = df['Week of Submission'].value_counts().sort_index(ascending=False)

# ✅ Display in Streamlit
st.subheader("🗓️ Weekly Submission Volume")
st.dataframe(
    weekly_counts.reset_index().rename(columns={'index': 'Week of Submission', 'Week of Submission': 'Form Count'}),
    use_container_width=True
)
