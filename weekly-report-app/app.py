import streamlit as st
import pandas as pd
import datetime
import re
import matplotlib.pyplot as plt
import gspread
from google.oauth2.service_account import Credentials

# --- Auth & Google Sheets Setup ---
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=SCOPES)
client = gspread.authorize(creds)

# Replace with your actual Spreadsheet ID (from your Google Sheets URL)
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
    st.stop()

# Clean column names (strip spaces)
df.columns = [c.strip() for c in df.columns]

# Format date columns to MM/DD/YY
date_cols = [col for col in df.columns if any(k in col for k in ["Baseline", "TCO", "Walk", "Turnover", "Open to Train", "Store Opening", "Start"])]
for col in date_cols:
    df[col] = pd.to_datetime(df[col], errors='coerce').dt.strftime('%m/%d/%y')

# Get Store Names for Dropdown
store_options = sorted(df["Store Name"].dropna().unique())

# Sidebar message about adding new projects manually
st.sidebar.title("Add New Project")
st.sidebar.write("Please update new projects manually in the Google Sheet.")

# Main Form
st.title("📝 Weekly Construction Update")

with st.form("weekly_update_form", clear_on_submit=True):
    st.subheader("Select Project")
    store_name = st.selectbox("Store Name", options=store_options)

    store_number = st.text_input("Store Number")
    subject = st.text_input("Subject")
    prototype = st.text_input("Prototype")
    cpm = st.text_input("CPM")
    start_date = st.date_input("Start Date")

    baseline_toggle = st.checkbox("Baseline Dates for All Milestones")

    # Date inputs
    tco_date = st.date_input("TCO Date")
    ops_walk_date = st.date_input("Ops Walk Date")
    turnover_date = st.date_input("Turnover Date")
    open_to_train_date = st.date_input("Open to Train Date")
    store_opening_date = st.date_input("Store Opening Date")

    notes = st.text_area("Notes (Press Enter for new bullet point)", value="• ", height=200)

    submitted = st.form_submit_button("Submit")

    if submitted:
        st.success("Submission received! (Note: Manual update to Google Sheet required)")

# Helper to parse dates
def parse_date(d):
    try:
        return pd.to_datetime(d, errors='coerce')
    except:
        return pd.NaT

df['Baseline Store Opening Date'] = df.apply(lambda r: parse_date(r.get("Baseline Store Opening")), axis=1)
df['Current Store Opening Date'] = df.apply(lambda r: parse_date(r.get("Store Opening")), axis=1)
df['Store Opening Delta'] = (df['Current Store Opening Date'] - df['Baseline Store Opening Date']).dt.days

# Flag: Critical if delta >= 5
df['Flag'] = df['Store Opening Delta'].apply(lambda x: "Critical" if pd.notna(x) and x >= 5 else "")

# Trend Calculation
df['Year Week'] = df['Week of the Year'].astype(str)
df = df.sort_values(by=['Store Name', 'Year Week'])

trend_map = {}
grouped = df.groupby('Store Name')

for store, group in grouped:
    group = group.sort_values('Year Week')
    prev_date = None
    for idx, row in group.iterrows():
        current_date = parse_date(row.get("Store Opening"))
        if prev_date is None:
            trend_map[idx] = "held"
        else:
            if current_date and prev_date:
                if current_date < prev_date:
                    trend_map[idx] = "pulled in"
                elif current_date > prev_date:
                    trend_map[idx] = "pushed"
                else:
                    trend_map[idx] = "held"
            else:
                trend_map[idx] = "held"
        prev_date = current_date

df['Trend'] = df.index.map(trend_map)

# Notes filter - keywords list
keywords = [
    "behind schedule", "lagging", "falling behind", "delay", "delayed", "unavoidable delay", "force majeure",
    "time extension request", "extended duration", "critical path", "cpm impact", "float erosion",
    "bottleneck identified", "resource bottleneck", "work on hold", "stop work order", "cease operations",
    "reschedule", "revised schedule", "re-baseline", "off track", "schedule drifting", "missed milestone",
    "missed completion date", "missed target", "schedule slip", "slippage", "budget overrun", "exceeding budget",
    "cost impact", "financial impact", "change order pending", "co requested", "unapproved co", "claim submitted",
    "dispute", "litigation risk", "cost variance", "schedule variance", "material escalation", "labor escalation",
    "potential penalties", "liquidated damages exposure", "unforeseen conditions", "unexpected costs",
    "cash flow issues", "payment delays", "labor shortage", "material shortage", "equipment shortage",
    "material not available", "equipment breakdown", "subcontractor availability", "low productivity",
    "inefficiency", "demobilization", "remobilization", "rework required", "rework identified", "defects found",
    "deficiencies", "non-conformance", "extensive punch list", "qc failure", "inspection hold",
    "adverse weather", "weather delays", "permit delays", "regulatory hurdles", "unforeseen ground conditions",
    "site access issues", "third-party interference", "utility conflicts", "lack of communication",
    "misunderstanding", "poor coordination", "approval pending", "awaiting sign-off", "disagreement",
    "conflict", "identified risk", "potential risk", "mitigation", "contingency utilized", "contingency running low",
    "forecast revised"
]

def check_notes(text):
    text_lower = str(text).lower()
    for kw in keywords:
        if kw in text_lower:
            return True
    return False

df['Notes Filtered'] = df['Notes'].apply(lambda x: x if check_notes(x) else "see report below")

# Executive Summary Table
summary_cols = [
    'Store Name',
    'Flag',
    'Store Opening Delta',
    'Trend',
    'Notes Filtered'
]

summary_df = df[summary_cols].drop_duplicates(subset=['Store Name']).reset_index(drop=True)

# Plot bar chart for trend counts
trend_counts = summary_df['Trend'].value_counts().reindex(['pulled in', 'pushed', 'held'], fill_value=0)

fig, ax = plt.subplots()
colors = {'pulled in': 'green', 'pushed': 'red', 'held': 'yellow'}
bars = ax.bar(trend_counts.index, trend_counts.values, color=[colors.get(x, 'grey') for x in trend_counts.index])
ax.set_title("Weekly Trend Summary")
ax.set_ylabel("Count")
ax.set_xlabel("Trend")
st.pyplot(fig)

# Display Executive Summary Table
st.subheader("Executive Summary Table")
st.dataframe(summary_df.style.format({"Store Opening Delta": "{:.0f}"}))

# Weekly Summary HTML Generator
def generate_weekly_summary(df, password):
    if password != "1234":
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
        "<h1>Weekly Summary Report</h1>",

        # Include Executive Summary Table in HTML
        "<h2>Executive Summary</h2>",
        summary_df.to_html(index=False),
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

            # Dates: show baseline date if exists else regular date
            date_fields = ["TCO", "Ops Walk", "Turnover", "Open to Train", "Store Opening"]
            html.append("<li><span class='label'>Dates:</span><ul>")
            for field in date_fields:
                baseline_field = f"Baseline {field}"
                val = row.get(baseline_field) if pd.notna(row.get(baseline_field)) and str(row.get(baseline_field)).strip() != "" else row.get(field)
                html.append(f"<li><span class='label'>{field}:</span> {val if val else ''}</li>")
            html.append("</ul></li>")

            # Notes bullets
            notes = [re.sub(r"^[\s•\-–●]+", "", n) for n in str(row.get("Notes", "")).splitlines() if n.strip()]
            if notes:
                html.append("<li><span class='label'>Notes:</span><ul>")
                html += [f"<li>{n}</li>" for n in notes]
                html.append("</ul></li>")

            html.append("</ul></div>")

    html.append("</body></html>")
    return df, "".join(html)

# Generate Weekly Summary Report
st.subheader("🔐 Generate Weekly Summary Report")
password = st.text_input("Enter Password", type="password")
if st.button("Generate Report"):
    df_result, html = generate_weekly_summary(df, password)
    if html:
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
