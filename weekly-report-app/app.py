import streamlit as st
import pandas as pd
import numpy as np
import json
import datetime
import gspread

# ========== GOOGLE SHEETS SETUP ========== #
info = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
client = gspread.service_account_from_dict(info)

spreadsheet_url = st.secrets["SHEET_URL"]
spreadsheet = client.open_by_url(spreadsheet_url)
worksheet = spreadsheet.get_worksheet(0)
data = worksheet.get_all_records()

# ========== DATAFRAME SETUP ========== #
df = pd.DataFrame(data)
df.columns = df.columns.str.strip()  # Clean up whitespace

# ========== DATE PARSING ========== #
df["Store Opening"] = pd.to_datetime(df.get("Store Opening"), errors="coerce")
df["TCO"] = pd.to_datetime(df.get("TCO"), errors="coerce")
df["Turnover"] = pd.to_datetime(df.get("Turnover"), errors="coerce")
df["Baseline Parsed"] = pd.to_datetime(df.get("Baseline Store Opening"), errors="coerce")

# ========== TREND ANALYSIS ========== #
def detect_trend(group):
    group = group.sort_values("Week", ascending=True)
    trends = []

    for i in range(1, len(group)):
        prev = group.iloc[i - 1]["Baseline Parsed"]
        curr = group.iloc[i]["Baseline Parsed"]

        if pd.isnull(prev) or pd.isnull(curr):
            trends.append("↔️")
        elif curr > prev:
            trends.append("🔺 Delayed")
        elif curr < prev:
            trends.append("🔻 Pull Ahead")
        else:
            trends.append("↔️ No Change")

    trends.insert(0, "–")  # First row has no previous week to compare
    group["Trend"] = trends
    return group

if "Week" in df.columns and "Baseline Parsed" in df.columns:
    df = df.groupby("Job #", group_keys=False).apply(detect_trend)

# ========== DISPLAY ========== #
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
