import streamlit as st
import pandas as pd
import datetime
import gspread
from google.oauth2.service_account import Credentials
import matplotlib.pyplot as plt
from io import BytesIO
import base64
import re

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

# --- Current Week Display (shown to all users) ---
today = datetime.date.today()
start_of_week = today - datetime.timedelta(days=today.weekday() + 1 if today.weekday() != 6 else 0)
start_of_week = start_of_week if today.weekday() != 6 else today
end_of_week = start_of_week + datetime.timedelta(days=6)

current_week_number = start_of_week.isocalendar()[1]
current_year = start_of_week.year
week_label = f"{current_year} Week {current_week_number:02d}"

current_week_df = df[(df['Date'] >= start_of_week) & (df['Date'] <= end_of_week)]

st.markdown(
    f"""### 📋 <span style='color:red'>{len(current_week_df)}</span> Submissions for the week of {start_of_week.strftime('%B %d')}–{end_of_week.strftime('%B %d')} (week {current_week_number} of the year), {current_year}""",
    unsafe_allow_html=True
)
columns_to_show = ['Store Number', 'Store Name', 'CPM', 'Prototype', 'Week Label']
st.dataframe(current_week_df[columns_to_show].reset_index(drop=True), use_container_width=True)

# --- Password-Protected Report ---
st.subheader("🔐 Generate Weekly Summary Report")

with st.form("password_form"):
    password_input = st.text_input("Enter Password", type="password")
    submitted = st.form_submit_button("Submit")

if submitted and password_input == "1234":

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

    # --- Detailed Weekly Summary Report ---

    # First, strip spaces on Baseline column to be safe
    df['Baseline'] = df['Baseline'].astype(str).str.strip()

    # Filter baseline entries and convert their Store Opening to datetime BEFORE creating the mapping
    baseline_df = df[df['Baseline'] == "/True"].copy()
    baseline_df['Store Opening'] = pd.to_datetime(baseline_df['Store Opening'], errors='coerce')

    # Create mapping from Store Number to baseline Store Opening date (datetime)
    baseline_map = baseline_df.set_index('Store Number')['Store Opening'].to_dict()

    # Convert entire df Store Opening column to datetime
    df['Store Opening'] = pd.to_datetime(df['Store Opening'], errors='coerce')

    # Define trend calculation function with safe checks
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

    # Apply trend computation to the dataframe
    df['Trend'] = df.apply(compute_trend, axis=1)

    # Calculate delta
    def compute_delta(row):
        baseline_open = baseline_map.get(row['Store Number'])
        if pd.isna(row['Store Opening']) or pd.isna(baseline_open):
            return 0
        return (row['Store Opening'] - baseline_open).days

    df['Store Opening Delta'] = df.apply(compute_delta, axis=1)

    # Flag logic with red asterisk
    def flag_delta(delta):
        if isinstance(delta, int) and abs(delta) > 5:
            return '<span style="color:red;font-weight:bold;">*</span>'
        return ""

    df['Flag'] = df['Store Opening Delta'].apply(flag_delta)

    # Filter notes for keywords
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
    summary_df = df[summary_cols].drop_duplicates(subset=['Store Number']).reset_index(drop=True)

    # ✅ Generate and display the HTML report
    html_report = generate_weekly_summary(df, summary_df)
    st.subheader("📄 Weekly Report (Preview)")
    st.components.v1.html(html_report, height=1000, scrolling=True)

    for _, row in summary_df.iterrows():
    store_name = row['Store Name']
    store_number = row['Store Number']
    prototype = row['Prototype']
    cpm = row['CPM']
    flag = row['Flag']
    delta = row['Store Opening Delta']
    trend = row['Trend']
    notes = row['Notes Filtered'].replace('\n', '<br>')

    card = f"""
    <div style="border:1px solid #ccc;padding:15px;margin-bottom:10px;border-radius:10px;">
        <h3 style="margin:0;">🏪 {store_name} ({store_number})</h3>
        <p><strong>🧬 Prototype:</strong> {prototype} | <strong>👷 CPM:</strong> {cpm} | <strong>🚩 Flag:</strong> {flag}</p>
        <p><strong>📅 Store Opening Delta:</strong> {delta} days | <strong>📈 Trend:</strong> {trend}</p>
        <p><strong>📝 Notes:</strong><br>{notes}</p>
    </div>
    """
    html.append(card)

    b64 = base64.b64encode(html_report.encode()).decode()
    href = f'<a href="data:text/html;base64,{b64}" download="weekly_summary.html">📥 Download Full Report as HTML</a>'
    st.markdown(href, unsafe_allow_html=True)

    # Custom Bar Colors
    def create_trend_figure(trend_counts):
        hex_colors = {
            "held": "#FDC01A",
            "baseline": "#0E2D72",
            "pushed": "#E2231A",
            "pulled in": "#40C4F3",
            "no baseline dates": "#999999"
        }
        fig, ax = plt.subplots(figsize=(10, 5))
        bars = ax.bar(trend_counts.index, trend_counts.values,
                      color=[hex_colors.get(x, "#999") for x in trend_counts.index])
        ax.set_ylabel("Count")
        ax.set_xlabel("Trend")
        ax.set_title("📊 Store Opening Trend Breakdown")
        ax.grid(axis='y', linestyle='--', alpha=0.7)
        plt.tight_layout()
        return fig

    def fig_to_base64(fig):
        buf = BytesIO()
        fig.savefig(buf, format="png", bbox_inches='tight')
        buf.seek(0)
        return base64.b64encode(buf.read()).decode()

def generate_weekly_summary(df, summary_df):
    html = []
    html.append("<html><head><style>")
    html.append("""
        body { font-family: Arial, sans-serif; line-height: 1.6; padding: 20px; }
        h2 { color: #2e6c80; }
        .store-card {
            border: 1px solid #ccc;
            padding: 15px;
            margin-bottom: 10px;
            border-radius: 10px;
            background-color: #f9f9f9;
        }
        .store-header {
            font-size: 18px;
            font-weight: bold;
        }
        .store-info, .store-notes {
            margin: 5px 0;
        }
    """)
    html.append("</style></head><body>")
    html.append("<h2>🏗️ Weekly Construction Report</h2>")
    html.append("<p>This report includes a summary of the latest updates on active construction sites.</p>")

    for _, row in summary_df.iterrows():
        store_name = row['Store Name']
        store_number = row['Store Number']
        prototype = row['Prototype']
        cpm = row['CPM']
        flag = row['Flag']
        delta = row['Store Opening Delta']
        trend = row['Trend']
        notes = row['Notes Filtered'].replace('\n', '<br>')

        card = f"""
        <div class="store-card">
            <div class="store-header">🏪 {store_name} ({store_number})</div>
            <div class="store-info"><strong>🧬 Prototype:</strong> {prototype} | <strong>👷 CPM:</strong> {cpm} | <strong>🚩 Flag:</strong> {flag}</div>
            <div class="store-info"><strong>📅 Store Opening Delta:</strong> {delta} days | <strong>📈 Trend:</strong> {trend}</div>
            <div class="store-notes"><strong>📝 Notes:</strong><br>{notes}</div>
        </div>
        """
        html.append(card)

    html.append("</body></html>")
    return "".join(html)
