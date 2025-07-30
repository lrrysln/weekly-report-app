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

# Clean column names (strip spaces)
df.columns = [c.strip() for c in df.columns]

# Convert date columns to datetime (do not format as string here)
date_cols = [col for col in df.columns if any(k in col for k in ["Baseline", "TCO", "Walk", "Turnover", "Open to Train", "Store Opening", "Start"])]
for col in date_cols:
    df[col] = pd.to_datetime(df[col], errors='coerce')

# Calculate deltas and flags
df['Baseline Store Opening Date'] = df['Baseline Store Opening']
df['Current Store Opening Date'] = df['Store Opening']
df['Store Opening Delta'] = (df['Current Store Opening Date'] - df['Baseline Store Opening Date']).dt.days

df['Flag'] = df['Store Opening Delta'].apply(lambda x: "Critical" if pd.notna(x) and x >= 5 else "")

df['Year Week'] = df['Week of the Year'].astype(str)
df = df.sort_values(by=['Store Name', 'Year Week'])

trend_map = {}
grouped = df.groupby('Store Name')
for store, group in grouped:
    group = group.sort_values('Year Week')
    prev_date = None
    for idx, row in group.iterrows():
        current_date = row.get("Store Opening")
        if pd.isna(current_date):
            trend_map[idx] = "held"
            continue
        if prev_date is None:
            trend_map[idx] = "held"
        else:
            if current_date < prev_date:
                trend_map[idx] = "pulled in"
            elif current_date > prev_date:
                trend_map[idx] = "pushed"
            else:
                trend_map[idx] = "held"
        prev_date = current_date
df['Trend'] = df.index.map(trend_map)

keywords = [
    "behind schedule", "lagging", "delay", "critical path", "cpm impact", "work on hold", "stop work order",
    "reschedule", "off track", "schedule drifting", "missed milestone", "budget overrun", "cost impact",
    "change order pending", "claim submitted", "dispute", "litigation risk", "schedule variance",
    "material escalation", "labor shortage", "equipment shortage", "low productivity", "rework required",
    "defects found", "qc failure", "weather delays", "permit delays", "regulatory hurdles",
    "site access issues", "awaiting sign-off", "conflict", "identified risk", "mitigation", "forecast revised"
]

def check_notes(text):
    text_lower = str(text).lower()
    for kw in keywords:
        if kw in text_lower:
            return True
    return False

df['Notes'] = df['Notes'].fillna("")
df['Notes Filtered'] = df['Notes'].apply(lambda x: x if check_notes(x) else "see report below")

summary_cols = ['Store Name', 'Flag', 'Store Opening Delta', 'Trend', 'Notes Filtered']
summary_df = df[summary_cols].drop_duplicates(subset=['Store Name']).reset_index(drop=True)

# Plot bar chart for trend counts
trend_counts = summary_df['Trend'].value_counts().reindex(['pulled in', 'pushed', 'held'], fill_value=0)
colors = {'pulled in': 'green', 'pushed': 'red', 'held': 'yellow'}

fig, ax = plt.subplots()
bars = ax.bar(trend_counts.index, trend_counts.values, color=[colors.get(x, 'grey') for x in trend_counts.index])
ax.set_title("Weekly Trend Summary")
ax.set_ylabel("Count")
ax.set_xlabel("Trend")

# Show plot on main page
st.pyplot(fig)

# Show Executive Summary Table on main page
st.subheader("Executive Summary Table")
st.dataframe(summary_df.style.format({"Store Opening Delta": "{:.0f}"}))

# Function to convert matplotlib fig to PNG base64 for embedding in HTML
def fig_to_base64(fig):
    buf = BytesIO()
    fig.savefig(buf, format="png", bbox_inches='tight')
    buf.seek(0)
    img_bytes = buf.read()
    encoded = base64.b64encode(img_bytes).decode()
    return encoded

def generate_weekly_summary(df, summary_df, fig, password):
    if password != "1234":
        return None, "❌ Incorrect password."
    if df.empty:
        return None, "🚫 No data available to summarize."

    # Convert plot to base64 string
    img_base64 = fig_to_base64(fig)

    html = [
        "<html><head><style>",
        "body{font-family:Arial;padding:20px}",
        "h1{text-align:center}",
        "h2{background:#cce5ff;padding:10px;border-radius:4px}",
        ".entry{border:1px solid #ccc;padding:10px;margin:10px 0;border-radius:4px;background:#f9f9f9}",
        "ul{margin:0;padding-left:20px}",
        ".label{font-weight:bold}",
        "table {border-collapse: collapse; width: 100%;}",
        "th, td {border: 1px solid #ddd; padding: 8px;}",
        "th {background-color: #f2f2f2;}",
        "</style></head><body>",
        "<h1>Weekly Summary Report</h1>",
        "<h2>Executive Summary</h2>",
        summary_df.to_html(index=False, escape=False),
        "<h2>Weekly Trend Summary</h2>",
        f'<img src="data:image/png;base64,{img_base64}" style="max-width:600px; width:100%;">',
        "<hr>"
    ]

    group_col = "Subject"
    for group_name, group_df in df.groupby(group_col):
        html.append(f"<h2>{group_name}</h2>")
        for _, row in group_df.iterrows():
            html.append('<div class="entry"><ul>')
            html.append(f"<li><span class='label'>Store Name:</span> {row.get('Store Name', '')}</li>")
            html.append(f"<li><span class='label'>Store Number:</span> {row.get('Store Number', '')}</li>")
            html.append(f"<li><span class='label'>Prototype:</span> {row.get('Prototype', '')}</li>")

            date_fields = ["TCO", "Ops Walk", "Turnover", "Open to Train", "Store Opening"]
            html.append("<li><span class='label'>Dates:</span><ul>")
            for field in date_fields:
                baseline_field = f"Baseline {field}"
                val = row.get(baseline_field) if pd.notna(row.get(baseline_field)) and str(row.get(baseline_field)).strip() != "" else row.get(field)
                html.append(f"<li><span class='label'>{field}:</span> {val if val else ''}</li>")
            html.append("</ul></li>")

            notes = [re.sub(r"^[\s•\-–●]+", "", n) for n in str(row.get("Notes", "")).splitlines() if n.strip()]
            if notes:
                html.append("<li><span class='label'>Notes:</span><ul>")
                html += [f"<li>{n}</li>" for n in notes]
                html.append("</ul></li>")

            html.append("</ul></div>")

    html.append("</body></html>")
    return df, "".join(html)

st.subheader("🔐 Generate Weekly Summary Report")
password = st.text_input("Enter Password", type="password")
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
