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

# --- Preprocess Data ---
df.columns = df.columns.str.strip()
df['Year Week'] = pd.to_datetime(df['Year Week'], errors='coerce')
df['Week Label'] = df['Year Week'].dt.strftime('%G Week %V')
df['Year'] = df['Year Week'].dt.isocalendar().year
df['Date'] = df['Year Week'].dt.date

if 'Store Name' in df.columns:
    df['Store Name'] = df['Store Name'].str.title()
if 'Store Number' in df.columns:
    df['Store Number'] = df['Store Number'].astype(str).str.strip()
if 'Baseline' in df.columns:
    df['Baseline'] = df['Baseline'].astype(str).str.strip()

# --- Current Week Display ---
today = datetime.date.today()
start_of_week = today - datetime.timedelta(days=today.weekday() + 1 if today.weekday() != 6 else 0)
start_of_week = start_of_week if today.weekday() != 6 else today
end_of_week = start_of_week + datetime.timedelta(days=6)

current_week_number = start_of_week.isocalendar()[1]
current_year = start_of_week.year

current_week_df = df[(df['Date'] >= start_of_week) & (df['Date'] <= end_of_week)]

st.markdown(
    f"""### 📋 <span style='color:red'>{len(current_week_df)}</span> Submissions for the week of {start_of_week.strftime('%B %d')}–{end_of_week.strftime('%B %d')} (week {current_week_number} of the year), {current_year}""",
    unsafe_allow_html=True
)

columns_to_show = ['Store Number', 'Store Name', 'CPM', 'Prototype', 'Week Label']
st.dataframe(current_week_df[columns_to_show].reset_index(drop=True), use_container_width=True)

# --- Password Protected Section ---
st.subheader("🔐 Generate Weekly Summary Report")
password = st.text_input("Enter Password", type="password")

if password == "1234":
    def generate_weekly_summary(df, summary_df, password):
        if password != "1234":
            return None, "❌ Incorrect password."

        trend_order = ["pulled in", "pushed", "held", "baseline", "no baseline dates"]
        trend_counts = summary_df['Trend'].value_counts().reindex(trend_order, fill_value=0)
        fig = create_trend_figure(trend_counts)
        img_base64 = fig_to_base64(fig)

        today = datetime.date.today()
        week_number = today.isocalendar()[1]
        year = today.year

        html = [
            "<html><head><style>",
            "body{font-family:Arial;padding:20px}",
            "h1{text-align:center}",
            "h2{background:#cce5ff;padding:10px;border-radius:4px}",
            ".entry{border:1px solid #ccc;padding:10px;margin:10px 0;border-radius:4px;background:#f9f9f9}",
            "ul{margin:0;padding-left:20px}",
            ".label{font-weight:bold}",
            "table {border-collapse: collapse; width: 100%; text-align: center;}",
            "th, td {border: 1px solid #ddd; padding: 8px; text-align: center;}",
            "th {background-color: #f2f2f2; text-decoration: underline;}",
            "</style></head><body>",
            f"<h1>{year} Week: {week_number} Weekly Summary Report</h1>",
            f'<img src="data:image/png;base64,{img_base64}" style="max-width:800px; display:block; margin:auto;">',
            "<h2>Trend Summary Table</h2>",
            trend_counts.rename_axis("Trend").reset_index().rename(columns={"index": "Trend", "Trend": "Count"}).to_html(index=False),
            "<h2>Executive Summary</h2>",
            summary_df.to_html(index=False, escape=False),
            "<hr>"
        ]

        group_col = "Subject" if "Subject" in df.columns else "Store Name"
        for group_name, group_df in df.groupby(group_col):
            html.append(f"<h2>{group_name}</h2>")
            for _, row in group_df.iterrows():
                store_number = row.get('Store Number', '')
                store_name = row.get('Store Name', '')
                prototype = row.get('Prototype', '')
                cpm = row.get('CPM', '')
                html.append(f"<div style='font-weight:bold; font-size:1.2em;'>{store_number} - {store_name}, {prototype} ({cpm})</div>")

                date_fields = ["TCO", "Ops Walk", "Turnover", "Open to Train", "Store Opening"]
                html.append("<li><span class='label'>Dates:</span><ul>")
                for field in date_fields:
                    val = row.get(field)
                    if isinstance(val, (datetime.datetime, datetime.date)):
                        val = val.strftime("%m/%d/%y")
                    else:
                        val = str(val) if val else "N/A"
                    html.append(f"<li style='margin-left: 40px;'><span style='text-decoration: underline;'>{field}</span>: {val}</li>")
                html.append("</ul></li>")

                notes = [re.sub(r"^[\s•\-–●]+", "", n) for n in str(row.get("Notes", "")).splitlines() if n.strip()]
                if notes:
                    html.append("<li><span class='label'>Notes:</span><ul>")
                    html += [f"<li style='margin-left: 40px;'>{n}</li>" for n in notes]
                    html.append("</ul></li>")

                html.append("</ul></div>")

        html.append("</body></html>")
        return df, "".join(html)

    if st.button("Generate Detailed Weekly Summary Report"):
        df_result, html = generate_weekly_summary(df, summary_df, password)
        if html is not None:
            st.markdown("### Weekly Summary")
            st.components.v1.html(html, height=1000, scrolling=True)
            st.download_button(
                label="📥 Download Summary as HTML",
                data=html.encode('utf-8'),
                file_name=f"Weekly_Summary_{datetime.datetime.now().strftime('%Y%m%d')}.html",
                mime="text/html",
                use_container_width=True
            )
        else:
            st.error(html)

elif password:
    st.error("❌ Incorrect password.")
else:
    st.info("Please enter the password to view the full report.")
