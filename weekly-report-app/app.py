import streamlit as st
from datetime import datetime
import pandas as pd
from google.oauth2.service_account import Credentials
import gspread

# Streamlit setup
st.set_page_config(page_title="Weekly Construction Summary", layout="wide")
st.title("📅 Weekly Construction Report Summary")

# Google Sheets setup
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]
creds = Credentials.from_service_account_file("credentials.json", scopes=SCOPES)
client = gspread.authorize(creds)

# Connect to Google Sheet
SHEET_NAME = "Construction Weekly Updates"
WORKSHEET_NAME = "WeeklyData"  # <-- change if different
spreadsheet = client.open(SHEET_NAME)
worksheet = spreadsheet.worksheet(WORKSHEET_NAME)

# Load data into DataFrame
data = worksheet.get_all_records()
df = pd.DataFrame(data)

# Convert date columns
df['Store Opening'] = pd.to_datetime(df['Store Opening'], errors='coerce')
df['⚪ Baseline Store Opening'] = pd.to_datetime(df['⚪ Baseline Store Opening'], errors='coerce')

# Sort and calculate trends
df.sort_values(by=['Store Number', 'Year Week'], inplace=True)
trends = []
last_store_dates = {}

for _, row in df.iterrows():
    store = row['Store Number']
    curr_open = row['Store Opening']
    baseline = row['⚪ Baseline Store Opening']
    prev_open = last_store_dates.get(store)

    if pd.isna(curr_open):
        trend = "🟡 Held"
    elif pd.notna(baseline) and curr_open == baseline:
        trend = "⚪ Baseline"
    elif prev_open:
        if curr_open < prev_open:
            trend = "🟢 Pulled In"
        elif curr_open > prev_open:
            trend = "🔴 Pushed"
        else:
            trend = "🟡 Held"
    else:
        trend = "🟡 Held"

    trends.append(trend)
    last_store_dates[store] = curr_open

df['Trend'] = trends

# ---- Executive Summary ----
st.subheader("📝 Executive Summary")

for _, row in df.iterrows():
    header = f"<span style='font-size:18px'><strong>{row['Store Number']} - {row['Store Name']}, {row['Prototype']} ({row['CPM']})</strong></span>"
    st.markdown(header, unsafe_allow_html=True)

    for field in ['Notes', 'Milestone Risk', 'Support Needed', 'Schedule Risk']:
        content = row.get(field)
        if pd.notna(content) and str(content).strip():
            for line in str(content).split('\n'):
                line = line.strip()
                if line:
                    st.markdown(f"- **{line}**")

    st.markdown("---")

# ---- Bar Chart Summary ----
st.subheader("📊 Trend Summary")

trend_counts = df['Trend'].value_counts().reindex(
    ['🟢 Pulled In', '🔴 Pushed', '⚪ Baseline', '🟡 Held'], fill_value=0
)

st.bar_chart(trend_counts)
