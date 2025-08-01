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

# Format store names
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

trend_map = {}
grouped = df.groupby('Store Name')
for store, group in grouped:
    group = group.sort_values('Year Week')
    prev_date = None
    for idx, row in group.iterrows():
        current_date = pd.to_datetime(row.get("Store Opening"), errors='coerce')
        Baseline_date = pd.to_datetime(row.get("⚪ Baseline Store Opening"), errors='coerce')
        if pd.isna(current_date):
            trend_map[idx] = "🟡 Held"
            continue
        if pd.notna(Baseline_date) and current_date == Baseline_date:
            trend_map[idx] = "⚪ Baseline"
            continue
        if prev_date is None:
            trend_map[idx] = "🟡 Held"
        else:
            if current_date < prev_date:
                trend_map[idx] = "🟢 Pulled In"
            elif current_date > prev_date:
                trend_map[idx] = "🔴 Pushed"
            else:
                trend_map[idx] = "🟡 Held"
        prev_date = current_date
df['Trend'] = df.index.map(trend_map)

# Filter notes
keywords = ["behind schedule", "lagging", "delay", "critical path", "cpm impact", "work on hold", "stop work order",
            "reschedule", "off track", "schedule drifting", "missed milestone", "budget overrun", "cost impact",
            "change order pending", "claim submitted", "dispute", "litigation risk", "schedule variance",
            "material escalation", "labor shortage", "equipment shortage", "low productivity", "rework required",
            "defects found", "qc failure", "weather delays", "permit delays", "regulatory hurdles",
            "site access issues", "awaiting sign-off", "conflict", "identified risk", "mitigation", "forecast revised"]

def check_notes(text):
    text_lower = str(text).lower()
    for kw in keywords:
        if kw in text_lower:
            return True
    return False

df['Notes'] = df['Notes'].fillna("")
df['Notes Filtered'] = df['Notes'].apply(lambda x: x if check_notes(x) else "see report below")

summary_cols = ['Store Name', 'Store Number', 'Prototype', 'CPM', 'Flag', 'Store Opening Delta', 'Trend', 'Notes Filtered']
summary_df = df[summary_cols].drop_duplicates(subset=['Store Name']).reset_index(drop=True)

# Submission summary BEFORE password
st.subheader("📋 Submitted Reports Overview")
submitted_count = len(summary_df)
st.markdown(f"<h4><span style='color:red;'><b>{submitted_count}</b></span> form responses have been submitted</h4>", unsafe_allow_html=True)
visible_df = summary_df[['Store Number', 'Store Name', 'CPM', 'Prototype']]
st.dataframe(visible_df)

# Password section
st.subheader("🔐 Generate Weekly Summary Report")
password = st.text_input("Enter Password", type="password")

# Weekly trend summary chart
trend_counts = summary_df['Trend'].value_counts().reindex(['🟢 Pulled In', '🔴 Pushed', '🟡 Held', '⚪ Baseline'], fill_value=0)
colors = {'🟢 Pulled In': 'green', '🔴 Pushed': 'red', '🟡 Held': 'yellow', '⚪ Baseline': 'grey'}
fig, ax = plt.subplots()
ax.bar(trend_counts.index, trend_counts.values, color=[colors.get(x, 'grey') for x in trend_counts.index])
ax.set_ylabel("Count")
ax.set_xlabel("Trend")
plt.tight_layout()

def fig_to_base64(fig):
    buf = BytesIO()
    fig.savefig(buf, format="png", bbox_inches='tight')
    buf.seek(0)
    return base64.b64encode(buf.read()).decode()

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
                    bullet_items.append(f"<li>{val}</li>")

            html.append(f"{header}<ul>{''.join(bullet_items)}</ul>")

    html.append("</body></html>")
    return df, "".join(html)

if st.button("Generate Report"):
    df_result, html = generate_weekly_summary(df, summary_df, fig, password)
    if html is not None:
        st.markdown("### Weekly Summary")
        st.components.v1.html(html, height=800, scrolling=True)
        st.download_button(
            "Download Summary as HTML",
            data=html,
            file_name=f"Weekly_Summary_{datetime.datetime.now().strftime('%Y%m%d')}.html",
            mime="text/html"
        )
    else:
        st.error(html)
