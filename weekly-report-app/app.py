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

# --- Date Conversion ---
first_column_name = df.columns[0]
try:
    df[first_column_name] = pd.to_datetime(df[first_column_name], errors='coerce')
except Exception as e:
    st.error(f"Date conversion failed: {e}")

# --- Create "Week Label" ---
df = df.dropna(subset=[first_column_name])
df['Week Label'] = df[first_column_name].dt.strftime('%G week %V')

# --- Group by Week ---
weekly_groups = df.groupby('Week Label')

st.subheader("🗓️ Weekly Submission Volume")

# --- Render Table with Expanders ---
for week_label, group_df in weekly_groups:
    with st.expander(f"{week_label} — {len(group_df)} submissions"):
        st.dataframe(group_df.reset_index(drop=True), use_container_width=True)
