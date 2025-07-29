import streamlit as st
import pandas as pd
import datetime
import re
import gspread
from google.oauth2.service_account import Credentials

# --- Auth ---
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]
creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=SCOPES)
client = gspread.authorize(creds)

# --- Load Data from Google Sheets ---
SHEET_NAME = "Construction Weekly Updates"
WORKSHEET_NAME = "Sheet1"
spreadsheet = client.open(SHEET_NAME)
worksheet = spreadsheet.worksheet(WORKSHEET_NAME)
data = worksheet.get_all_records()
df = pd.DataFrame(data)

# --- Format date columns to MM/DD/YY ---
date_cols = [col for col in df.columns if any(keyword in col for keyword in [
    "Baseline", "TCO", "Walk", "Turnover", "Open to Train", "Store Opening", "Start"
])]
for col in date_cols:
    df[col] = pd.to_datetime(df[col], errors='coerce').dt.strftime('%m/%d/%y')

# --- Weekly Summary HTML Generator ---
def generate_weekly_summary(df, password):
    if password != "1234":  # your password
        return None, "❌ Incorrect password."

    if df.empty:
        return None, "🚫 No data available to summarize."

    html = [
        "<html><head><style>",
        "body{font-family:Arial;padding:20px}",
        "h1{text-align:center}",
        "h2{background:#cce5ff;padding:10px;border-radius:4px}",
        ".entry{border:1px solid #ccc;padding:10px;margin:10px 0;border-radius:4px;background:#f9f9f9}",
        "ul{margin:0;padding-left:20px}",
        ".label{font-weight:bold}",
        "</style></head><body>",
        "<h1>Weekly Summary Report</h1>"
    ]

    # Group by Subject (your new column)
    group_col = "Subject"
    for group_name, group_df in df.groupby(group_col):
        html.append(f"<h2>{group_name}</h2>")
        for _, row in group_df.iterrows():
            html.append('<div class="entry"><ul>')
            html.append(f"<li><span class='label'>Store Name:</span> {row.get('Store Name', '')}</li>")
            html.append(f"<li><span class='label'>Store Number:</span> {row.get('Store Number', '')}</li>")
            html.append(f"<li><span class='label'>Prototype:</span> {row.get('Prototype', '')}</li>")

            # Dates section
            html.append("<li><span class='label'>Dates:</span><ul>")
            for label in ["Start", "Baseline TCO", "TCO", "Baseline Ops Walk", "Ops Walk", "Baseline Turnover", "Turnover", "Baseline Open to Train", "Open to Train", "Baseline Store Opening", "Store Opening"]:
                val = row.get(label, "")
                html.append(f"<li><span class='label'>{label}:</span> {val}</li>")
            html.append("</ul></li>")

            # Notes with bullets, removing any leading bullet chars
            notes = [re.sub(r"^[\s•\-–●]+", "", n) for n in str(row.get("Notes", "")).splitlines() if n.strip()]
            if notes:
                html.append("<li><span class='label'>Notes:</span><ul>")
                html += [f"<li>{n}</li>" for n in notes]
                html.append("</ul></li>")

            html.append("</ul></div>")

    html.append("</body></html>")
    return df, "".join(html)

# --- Streamlit UI ---
st.title("🏗️ Construction Weekly Report")

st.subheader("Current Data Table")
st.dataframe(df)

st.subheader("🔐 Generate Weekly Summary Report")
password = st.text_input("Enter Password", type="password")
if st.button("Generate Report"):
    df_result, html = generate_weekly_summary(df, password)
    if html:
        st.markdown("### Weekly Summary")
        st.components.v1.html(html, height=700, scrolling=True)
        st.download_button(
            "Download Summary as HTML",
            data=html,
            file_name=f"Weekly_Summary_{datetime.datetime.now().strftime('%Y%m%d')}.html",
            mime="text/html"
        )
    else:
        st.error(html)
