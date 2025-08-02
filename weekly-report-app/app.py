import streamlit as st
import pandas as pd
import numpy as np
import datetime
import matplotlib.pyplot as plt
from google.oauth2.service_account import Credentials
import gspread
import base64
from io import BytesIO
import json
import re

# --- Auth & Google Sheets Setup ---
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=SCOPES)
client = gspread.authorize(creds)

# --- Config ---
st.set_page_config(layout="wide", page_title="Weekly Construction Report")

# --- Load Sheet ---
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

# --- Clean & Process Data ---
data["Timestamp"] = pd.to_datetime(data["Timestamp"])
data["Week"] = data["Timestamp"].dt.isocalendar().week
data["Year"] = data["Timestamp"].dt.year

# Fix column names if needed
data.columns = [col.strip() for col in data.columns]

# Ensure Delta Days is numeric
data["Delta Days"] = pd.to_numeric(data["Delta Days"], errors="coerce").fillna(0)

# Calculate Trend properly
data["Trend"] = data.sort_values("Timestamp").groupby("Store Number")["Delta Days"].diff().fillna(0)

# --- Plotting ---
def create_summary_chart(df):
    chart_data = df.groupby("Store Name")["Delta Days"].mean().sort_values()
    fig, ax = plt.subplots(figsize=(10, 6))
    colors = ['red' if val > 0 else 'green' for val in chart_data]
    chart_data.plot(kind="barh", color=colors, ax=ax)
    ax.set_title("Average Delta Days per Store")
    ax.set_xlabel("Delta Days")
    plt.tight_layout()
    return fig

def fig_to_base64(fig):
    buf = BytesIO()
    fig.savefig(buf, format="png")
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")

# --- HTML Report ---
def generate_weekly_summary(df, summary_df, fig, password):
    if password != "1234":
        return None, "❌ Incorrect password."

    img_base64 = fig_to_base64(fig)
    today = datetime.date.today()
    week_number = today.isocalendar()[1]
    year = today.year

    html = [
        "<html><head><style>",
        "body{font-family:Arial;padding:20px}",
        "h1{text-align:center}",
        "h2{background:#cce5ff;padding:10px;border-radius:4px}",
        "ul{margin:0 0 20px;padding-left:20px}",
        "b.header{font-size:1.4em; display:block; margin-top:20px; margin-bottom:8px;}",
        "</style></head><body>",
        f"<h1>{year} Week: {week_number} Weekly Summary Report</h1>",
        f'<img src="data:image/png;base64,{img_base64}" style="max-width:600px; display:block; margin:auto;">',
        "<h2>Executive Summary</h2>",
        summary_df.to_html(index=False, escape=False),
        "<hr><h2>Site Notes</h2>"
    ]

    group_col = "Subject" if "Subject" in df.columns else "Store Name"
    for group_name, group_df in df.groupby(group_col):
        html.append(f"<h2>{group_name}</h2>")
        for _, row in group_df.iterrows():
            # First line: Bold, larger font, not a bullet
            store_info = f"{row.get('Store Number', '')} - {row.get('Store Name', '')}, {row.get('Prototype', '')} ({row.get('CPM', '')})"
            html.append(f"<b class='header'>{store_info}</b>")

            # Remaining bullets
            bullet_fields = ["Start", "TCO", "Turnover", "Notes"]
            bullets = []
            for field in bullet_fields:
                val = row.get(field, "")
                if pd.notna(val) and str(val).strip():
                    if field == "Notes":
                        # Split multiple lines into bullets
                        note_lines = re.split(r"\n|\r", str(val))
                        for line in note_lines:
                            line = line.strip("•-–● ").strip()
                            if line:
                                bullets.append(f"<li>{line}</li>")
                    else:
                        bullets.append(f"<li>{field}: {val}</li>")

            if bullets:
                html.append("<ul>")
                html.extend(bullets)
                html.append("</ul>")

    html.append("</body></html>")
    return df, "".join(html)

# --- Streamlit UI ---
st.title("📋 Weekly Construction Summary Generator")
password = st.text_input("Enter admin password to generate report", type="password")

if password:
    today = datetime.date.today()
    current_week = today.isocalendar()[1]
    current_year = today.year
    filtered_df = data[(data["Week"] == current_week) & (data["Year"] == current_year)]

    if filtered_df.empty:
        st.warning("⚠️ No data submitted yet for this week.")
    else:
        summary_df = filtered_df[["Store Name", "Store Number", "Prototype", "CPM", "Delta Days", "Trend"]].drop_duplicates()
        fig = create_summary_chart(filtered_df)
        df_out, html_report = generate_weekly_summary(filtered_df, summary_df, fig, password)

        if html_report:
            st.markdown(html_report, unsafe_allow_html=True)
