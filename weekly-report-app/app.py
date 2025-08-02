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
df.columns = [c.strip() for c in df.columns]
df['Store Name'] = df['Store Name'].str.title()

# Convert and format date columns
date_cols = [col for col in df.columns if any(k in col for k in ["⚪ Baseline", "TCO", "Walk", "Turnover", "Open to Train", "Store Opening", "Start"])]
for col in date_cols:
    df[col] = pd.to_datetime(df[col], errors='coerce').dt.strftime('%m/%d/%y')

# Calculate deltas and flags
try:
    df['Store Opening Delta'] = (
        pd.to_datetime(df['Store Opening'], errors='coerce') - pd.to_datetime(df['⚪ Baseline Store Opening'], errors='coerce')
    ).dt.days
    df['Flag'] = df['Store Opening Delta'].apply(lambda x: "Critical" if pd.notna(x) and x >= 5 else "")
except:
    df['Store Opening Delta'] = None
    df['Flag'] = ""

# Week info
df['Year Week'] = df['Year Week'].astype(str)
df = df.sort_values(by=['Store Name', 'Year Week'])

# Compute Trend based on Baseline comparison
df['Store Opening Parsed'] = pd.to_datetime(df['Store Opening'], errors='coerce')
df['Baseline Parsed'] = pd.to_datetime(df['⚪ Baseline Store Opening'], errors='coerce')

def compute_trend(row):
    current = row['Store Opening Parsed']
    baseline = row['Baseline Parsed']
    if pd.isna(current):
        return "Held"
    if pd.isna(baseline):
        return "No Baseline"
    if current > baseline:
        return "Pushed"
    elif current < baseline:
        return "Pulled In"
    else:
        return "Held"

df['Trend'] = df.apply(compute_trend, axis=1)

# Clean Trend DataFrame
summary_cols = ['Store Name', 'Store Number', 'Prototype', 'CPM', 'Flag', 'Store Opening Delta', 'Trend', 'Notes']
summary_df = df[summary_cols].drop_duplicates(subset=['Store Name']).reset_index(drop=True)

# Submitted Report Overview
st.subheader("📋 Submitted Reports Overview")
st.markdown(f"<h4><span style='color:red;'><b>{len(summary_df)}</b></span> form responses have been submitted</h4>", unsafe_allow_html=True)
visible_df = summary_df[['Store Number', 'Store Name', 'CPM', 'Prototype']]
st.dataframe(visible_df)

# Password section
st.subheader("🔐 Generate Weekly Summary Report")
password = st.text_input("Enter Password", type="password")

# Trend Breakdown Chart
st.subheader("Trend Breakdown")
trend_counts = summary_df['Trend'].value_counts().reindex(['Pulled In', 'Pushed', 'Held', 'No Baseline'], fill_value=0)
colors = {'Pulled In': 'green', 'Pushed': 'red', 'Held': 'yellow', 'No Baseline': 'grey'}
fig, ax = plt.subplots()
ax.bar(trend_counts.index, trend_counts.values, color=[colors.get(x, 'grey') for x in trend_counts.index])
ax.set_ylabel("Count")
ax.set_xlabel("Trend")
plt.tight_layout()
st.pyplot(fig)

# Trend Summary Table (moved here)
st.subheader("Trend Summary Table")
st.table(trend_counts.rename_axis("Trend").reset_index().rename(columns={"index": "Trend", "Trend": "Count"}))

# Weekly Report HTML generation omitted here for brevity.
