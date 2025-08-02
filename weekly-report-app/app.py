import streamlit as st
import pandas as pd
import numpy as np
import json
import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ========== SETUP GOOGLE SHEETS ========== #
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
info = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
credentials = ServiceAccountCredentials.from_json_keyfile_dict(info, scope)
client = gspread.authorize(credentials)

spreadsheet_url = st.secrets["SHEET_URL"]
spreadsheet = client.open_by_url(spreadsheet_url)
worksheet = spreadsheet.get_worksheet(0)
data = worksheet.get_all_records()

# ========== DATAFRAME SETUP ========== #
df = pd.DataFrame(data)

# Clean column names
df.columns = df.columns.str.strip()

# ========== DATE PARSING ========== #
df["Store Opening"] = pd.to_datetime(df["Store Opening"], errors="coerce")
df["TCO"] = pd.to_datetime(df["TCO"], errors="coerce")
df["Turnover"] = pd.to_datetime(df["Turnover"], errors="coerce")
df["Baseline Parsed"] = pd.to_datetime(df["Baseline Store Opening"], errors='coerce')

# ========== TREND LOGIC ========== #
def detect_trend(group):
    group = group.sort_values("Week", ascending=True)
    trends = []

    for i in range(1, len(group)):
        prev_date = group.iloc[i - 1]["Baseline Parsed"]
        curr_date = group.iloc[i]["Baseline Parsed"]

        if pd.isnull(prev_date) or pd.isnull(curr_date):
            trend = "↔️"
        elif curr_date > prev_date:
            trend = "🔺 Delayed"
        elif curr_date < prev_date:
            trend = "🔻 Pull Ahead"
        else:
            trend = "↔️ No Change"

        trends.append(trend)

    trends.insert(0, "–")  # First row has no prior data to compare
    group["Trend"] = trends
    return group

if "Week" in df.columns and "Baseline Parsed" in df.columns:
    df = df.groupby("Job #").apply(detect_trend).reset_index(drop=True)

# ========== DISPLAY REPORT ========== #
st.title("📊 Construction Weekly Report Summary")
st.write(f"Last updated: {datetime.datetime.now().strftime('%B %d, %Y %I:%M %p')}")

if df.empty:
    st.warning("No data found in the Google Sheet.")
else:
    selected_week = st.selectbox("Select Week", sorted(df["Week"].unique(), reverse=True))
    filtered_df = df[df["Week"] == selected_week]

    st.dataframe(filtered_df[[
        "Week", "Prototype", "Job #", "Store Name", 
        "Baseline Store Opening", "Store Opening", "Trend", 
        "TCO", "Turnover", "PM Notes"
    ]].sort_values("Prototype"))

