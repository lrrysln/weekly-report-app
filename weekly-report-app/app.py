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



# --- Google Sheets Auth ---
secrets = st.secrets
info = json.loads(secrets["GOOGLE_CREDENTIALS"])
creds = service_account.Credentials.from_service_account_info(
    info,
    scopes=["https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"]
)
client = gspread.authorize(creds)

# --- Sheet Info ---
SPREADSHEET_NAME = "Construction Weekly Updates"
worksheet = client.open(SPREADSHEET_NAME).sheet1

# --- Load Data from Google Sheet ---
data = worksheet.get_all_records()
df = pd.DataFrame(data)

# --- Convert "Year Week" to datetime, then extract Year/Week ---
if "Year Week" in df.columns:
    df["Year Week"] = pd.to_datetime(df["Year Week"], errors='coerce')
    df["Year"] = df["Year Week"].dt.isocalendar().year
    df["Week"] = df["Year Week"].dt.isocalendar().week
else:
    st.error("'Year Week' column not found.")
    st.stop()

# --- Handle date columns ---
date_columns = ["Baseline", "Start", "TCO", "Ops Walk", "Turnover", "Open to Train", "Store Opening"]
for col in date_columns:
    if col in df.columns:
        df[col] = pd.to_datetime(df[col], errors="coerce")

# --- Sort and calculate Delta Days and Trend ---
df.sort_values(["Store Name", "Year", "Week"], inplace=True)
df["Delta Days"] = 0.0
df["Trend"] = 0.0

for store in df["Store Name"].unique():
    store_df = df[df["Store Name"] == store]
    prev_row = None

    for idx, row in store_df.iterrows():
        if pd.notnull(row["Store Opening"]) and prev_row is not None and pd.notnull(prev_row["Store Opening"]):
            delta = (row["Store Opening"] - prev_row["Store Opening"]).days
            df.at[idx, "Delta Days"] = delta
            if delta > 0:
                df.at[idx, "Trend"] = 1
            elif delta < 0:
                df.at[idx, "Trend"] = -1
        prev_row = row

# --- Show preview ---
st.title("Weekly Construction Report Dashboard")
st.dataframe(df)

# --- Optional: Save cleaned data to a CSV or Excel ---
# df.to_csv("cleaned_updates.csv", index=False)


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
    filtered_df = df[(df["Week"] == current_week) & (df["Year"] == current_year)]

    if filtered_df.empty:
        st.warning("⚠️ No data submitted yet for this week.")
    else:
        summary_df = filtered_df[["Store Name", "Store Number", "Prototype", "CPM", "Delta Days", "Trend"]].drop_duplicates()
        fig = create_summary_chart(filtered_df)
        df_out, html_report = generate_weekly_summary(filtered_df, summary_df, fig, password)

        if html_report:
            st.markdown(html_report, unsafe_allow_html=True)

