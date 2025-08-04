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
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    password = st.text_input("Enter Password", type="password")
    if st.button("Submit"):
        if password == "1234":
            st.session_state.authenticated = True
        else:
            st.error("❌ Incorrect password.")
    st.stop()

st.subheader("🔐 Generate Weekly Summary Report")

st.markdown("## 🗓️ Weekly Submission Volume by Year")
years = sorted(df['Year'].dropna().unique(), reverse=True)
for year in years:
    with st.expander(f"📁 {year}"):
        year_data = df[df['Year'] == year]
        weekly_counts = year_data.groupby('Week Label').size().reset_index(name='Count')
        for _, row in weekly_counts.iterrows():
            week = row['Week Label']
            count = row['Count']
            with st.expander(f"📆 {week} — {count} submission(s)"):
                st.dataframe(year_data[year_data['Week Label'] == week].reset_index(drop=True))

# --- Data for Summary ---
df['Baseline'] = df['Baseline'].astype(str).str.strip()
baseline_df = df[df['Baseline'] == "/True"].copy()
baseline_df['Store Opening'] = pd.to_datetime(baseline_df['Store Opening'], errors='coerce')
baseline_map = baseline_df.set_index('Store Number')['Store Opening'].to_dict()

df['Store Opening'] = pd.to_datetime(df['Store Opening'], errors='coerce').dt.normalize()
baseline_df['Store Opening'] = pd.to_datetime(baseline_df['Store Opening'], errors='coerce').dt.normalize()

def compute_trend(row):
    store_number = row['Store Number']
    current_open = row['Store Opening']
    if row['Baseline'] == "/True":
        return "baseline"
    baseline_open = baseline_map.get(store_number)
    if pd.isna(current_open) or pd.isna(baseline_open):
        return "no baseline dates"
    if current_open > baseline_open:
        return "pushed"
    elif current_open < baseline_open:
        return "pulled in"
    else:
        return "held"

df['Trend'] = df.apply(compute_trend, axis=1)

def compute_delta(row):
    baseline_open = baseline_map.get(row['Store Number'])
    if pd.isna(row['Store Opening']) or pd.isna(baseline_open):
        return 0
    return (row['Store Opening'] - baseline_open).days

df['Store Opening Delta'] = df.apply(compute_delta, axis=1)

def flag_delta(delta):
    if isinstance(delta, int) and abs(delta) > 5:
        return '<span style="color:red;font-weight:bold;">*</span>'
    return ""

df['Flag'] = df['Store Opening Delta'].apply(flag_delta)

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
    return any(kw in text_lower for kw in keywords)

df['Notes'] = df['Notes'].fillna("")
df['Notes Filtered'] = df['Notes'].apply(lambda x: x if check_notes(x) else "see report below")

summary_cols = ['Store Name', 'Store Number', 'Prototype', 'CPM', 'Flag', 'Store Opening Delta', 'Trend', 'Notes Filtered']
df_sorted = df.sort_values(['Store Number', 'Year Week'], ascending=[True, False])
summary_df = df_sorted.groupby('Store Number').first().reset_index()
summary_df = summary_df[summary_cols]

def format_date(value):
    if pd.isna(value):
        return "N/A"
    try:
        return pd.to_datetime(value).strftime("%m/%d/%y")
    except:
        return str(value)

def generate_weekly_summary(df, summary_df):
    html = []
    html.append("<div style='font-family: Arial, sans-serif;'>")
    html.append("<h2 style='text-align: center;'>🗓️ Detailed Weekly Summary</h2>")

    for _, row in summary_df.iterrows():
        store_num = row['Store Number']
        store_df = df[df['Store Number'] == store_num]

        html.append(f"<h3 style='margin-bottom: 0;'>{row['Store Name']} ({store_num}) - {row['Prototype']}</h3>")
        html.append(f"<p><strong>CPM:</strong> {row['CPM']} | <strong>Flag:</strong> {row['Flag']}</p>")
        html.append(f"<p><strong>Store Opening Delta:</strong> {row['Store Opening Delta']} | <strong>Trend:</strong> {row['Trend']}</p>")

        notes = row['Notes Filtered']
        notes_html = "<ul style='margin-top: 0;'>"
        for note in str(notes).split("\n"):
            if note.strip():
                notes_html += f"<li>{note.strip()}</li>"
        notes_html += "</ul>"

        html.append(f"<p><strong>📝 Notes:</strong>{notes_html}</p>")

        milestone_headers = ['TCO', 'Ops Walk', 'Turnover', 'Open to Train', 'Store Opening']
        date_section = "<p><strong>📅 Dates:</strong></p><ul style='margin-top: 0;'>"
        for header in milestone_headers:
            milestone_dates = store_df[header].dropna().unique()
            milestone_dates_formatted = [format_date(d) for d in milestone_dates]
            milestone_html = "<ul style='margin-top: 0; margin-left: 20px;'>"
            for date in milestone_dates_formatted:
                milestone_html += f"<li>{date}</li>"
            milestone_html += "</ul>"
            date_section += f"<li><u>{header}</u>: {milestone_html}</li>"
        date_section += "</ul>"

        html.append(date_section)
        html.append("<hr style='margin: 30px 0;'>")

    html.append("</div>")
    return "".join(html)

if st.button("Generate Detailed Weekly Summary Report"):
    html_report = generate_weekly_summary(df, summary_df)
    st.subheader("📄 Weekly Report (Preview)")
    st.components.v1.html(html_report, height=1000, scrolling=True)

    b64 = base64.b64encode(html_report.encode()).decode()
    href = f'<a href="data:text/html;base64,{b64}" download="weekly_summary.html">📥 Download Full Report as HTML</a>'
    st.markdown(href, unsafe_allow_html=True)
