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

# --- Google Sheets Auth ---
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
info = json.loads(secrets["GOOGLE_CREDENTIALS"])
creds = Credentials.from_service_account_info(info, scopes=SCOPES)
client = gspread.authorize(creds)

# --- Config ---
st.set_page_config(layout="wide", page_title="Weekly Construction Report")

# --- Get Data from Google Sheet ---
SPREADSHEET_NAME = "Construction Weekly Updates"
WORKSHEET_NAME = "Form Responses 1"

sheet = client.open(SPREADSHEET_NAME).worksheet(WORKSHEET_NAME)
data = pd.DataFrame(sheet.get_all_records())

# --- Clean Data ---
data["Timestamp"] = pd.to_datetime(data["Timestamp"])
data["Week"] = data["Timestamp"].dt.isocalendar().week
data["Year"] = data["Timestamp"].dt.year

# --- Auto-calculate Trend ---
data["Trend"] = data.groupby("Store Number")["Delta Days"].transform(lambda x: x.diff().fillna(0))

# --- Plotting ---
def create_summary_chart(df):
    chart_data = df.groupby("Store Name")["Delta Days"].mean().sort_values()
    fig, ax = plt.subplots(figsize=(10, 6))
    chart_data.plot(kind="barh", color=np.where(chart_data > 0, 'red', 'green'), ax=ax)
    ax.set_title("Average Delta Days per Store")
    ax.set_xlabel("Delta Days")
    plt.tight_layout()
    return fig

def fig_to_base64(fig):
    buf = BytesIO()
    fig.savefig(buf, format="png")
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode("utf-8")
    return img_base64

# --- HTML Generator ---
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
        "ul{margin:0;padding-left:20px}",
        "b.header{font-size:1.2em; display:block; margin-top:15px;}",
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
            store_number = row.get("Store Number", "")
            store_name = row.get("Store Name", "")
            prototype = row.get("Prototype", "")
            cpm = row.get("CPM", "")
            header = f"<b class='header'>{store_number} - {store_name}, {prototype} ({cpm})</b>"

            bullet_fields = ["Start", "TCO", "Turnover", " Notes"]
            bullet_items = []
            for field in bullet_fields:
                val = row.get(field, "")
                if pd.notna(val) and str(val).strip():
                    bullet_items.append(f"<li>{field}: {val}</li>")

            html.append(f"{header}<ul>{''.join(bullet_items)}</ul>")

    html.append("</body></html>")
    return df, "".join(html)

# --- Streamlit UI ---
st.title("📋 Weekly Construction Summary Generator")
password = st.text_input("Enter admin password to generate report", type="password")

if password:
    today = datetime.date.today()
    this_week = today.isocalendar()[1]
    this_year = today.year

    filtered_df = data[(data["Week"] == this_week) & (data["Year"] == this_year)]

    if filtered_df.empty:
        st.warning("⚠️ No data submitted yet for this week.")
    else:
        summary = filtered_df[["Store Name", "Store Number", "Prototype", "CPM", "Delta Days", "Trend"]].drop_duplicates()
        fig = create_summary_chart(filtered_df)
        df_out, html_report = generate_weekly_summary(filtered_df, summary, fig, password)

        if html_report:
            st.markdown(html_report, unsafe_allow_html=True)
