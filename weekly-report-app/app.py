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

if "gcp_service_account" not in st.secrets:
    st.error("Service account credentials not found in secrets.")
    st.stop()

creds = Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],
    scopes=SCOPES
)
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

# --- Load and Clean Data ---
df = load_data()

if df.empty:
    st.warning("⚠️ No data loaded from Google Sheet yet.")
    st.stop()
else:
    st.success("✅ Data loaded successfully.")

df.columns = [c.strip() for c in df.columns]

# --- Date Columns ---
if 'Baseline' not in df.columns:
    st.warning("'Baseline' column is missing from dataset. Creating empty.")
    df['Baseline'] = pd.NaT
else:
    df['Baseline'] = pd.to_datetime(df['Baseline'], errors='coerce')

date_cols = [col for col in df.columns if any(k in col for k in ["TCO", "Ops Walk", "Turnover", "Open to Train", "Store Opening", "Start"])]
for col in date_cols:
    df[col] = pd.to_datetime(df[col], errors='coerce')

# --- Calculate Delta & Flag ---
df['Store Opening Delta'] = df.apply(
    lambda row: (row['Store Opening'] - row['Baseline']).days
    if pd.notna(row['Store Opening']) and pd.notna(row['Baseline']) else None,
    axis=1
)

df['Flag'] = df['Store Opening Delta'].apply(lambda x: "Critical" if pd.notna(x) and x >= 5 else "")

# --- Calculate Trends ---
trend_map = {}
if 'Year Week' not in df.columns:
    st.warning("'Year Week' column is missing. Adding based on current date.")
    df['Year Week'] = pd.to_datetime('today').isocalendar().week

grouped = df.groupby('Store Name')
for store, group in grouped:
    group = group.sort_values('Year Week')
    prev_date = None
    for idx, row in group.iterrows():
        current_date = row['Store Opening']
        baseline_date = row['Baseline']
        if pd.isna(current_date):
            trend_map[idx] = "🟡 Held"
        elif pd.notna(baseline_date) and current_date == baseline_date:
            trend_map[idx] = "⚪ Baseline"
        elif prev_date is None:
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

# --- Notes Filtering ---
keywords = ["behind schedule", "lagging", "delay", "critical path", "cpm impact", "work on hold", "stop work order",
            "reschedule", "off track", "schedule drifting", "missed milestone", "budget overrun", "cost impact",
            "change order pending", "claim submitted", "dispute", "litigation risk", "schedule variance",
            "material escalation", "labor shortage", "equipment shortage", "low productivity", "rework required",
            "defects found", "qc failure", "weather delays", "permit delays", "regulatory hurdles",
            "site access issues", "awaiting sign-off", "conflict", "identified risk", "mitigation", "forecast revised"]

def check_notes(text):
    text_lower = str(text).lower()
    return any(kw in text_lower for kw in keywords)

df['Notes'] = df['Notes'].fillna("")
df['Notes Filtered'] = df['Notes'].apply(lambda x: x if check_notes(x) else "see report below")

# --- Summary ---
summary_cols = ['Store Name', 'Store Number', 'Prototype', 'CPM', 'Store Opening Delta', 'Trend', 'Flag', 'Notes Filtered']
summary_df = df[summary_cols].drop_duplicates(subset=['Store Name']).reset_index(drop=True)
summary_df.rename(columns={'Notes Filtered': 'Notes'}, inplace=True)

# --- Trend Plot ---
def plot_trends(df):
    trend_counts = df['Trend'].value_counts()
    if trend_counts.empty:
        st.warning("No trend data to plot.")
        return None

    colors = {
        "🟢 Pulled In": "green",
        "🔴 Pushed": "red",
        "🟡 Held": "yellow",
        "⚪ Baseline": "gray"
    }

    fig, ax = plt.subplots()
    bars = ax.bar(trend_counts.index, trend_counts.values, color=[colors.get(x, 'grey') for x in trend_counts.index])
    for bar in bars:
        height = bar.get_height()
        ax.annotate(f"{int(height)}", (bar.get_x() + bar.get_width() / 2, height), ha="center", va="bottom")
    ax.set_ylabel("Count")
    ax.set_xlabel("Trend")
    plt.tight_layout()
    return fig

# --- Convert Figure to Base64 ---
def fig_to_base64(fig):
    buf = BytesIO()
    fig.savefig(buf, format="png", bbox_inches='tight')
    buf.seek(0)
    return base64.b64encode(buf.read()).decode()

# --- Generate Report ---
def generate_report(df, summary_df, fig):
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
        "th, td {border: 1px solid #ddd; padding: 8px;}",
        "th {background-color: #f2f2f2;}",
        "</style></head><body>",
        f"<h1>{year} Week: {week_number} Weekly Summary Report</h1>",
        f'<img src="data:image/png;base64,{img_base64}" style="max-width:600px; display:block; margin:auto;">',
        "<h2>Executive Summary</h2>",
        summary_df.to_html(index=False, escape=False),
        "<hr>"
    ]

    group_col = "Subject" if "Subject" in df.columns else "Store Name"
    for group_name, group_df in df.groupby(group_col):
        html.append(f"<h2>{group_name}</h2>")
        html.append(group_df.to_html(index=False))

    html.append("</body></html>")
    return "".join(html)

# --- Password Input ---
st.subheader("🔐 Generate Weekly Summary Report")
password = st.text_input("Enter Password", type="password")

# --- Button Logic ---
if password:
    if password == "1234":
        st.success("✅ Password accepted.")
        fig = plot_trends(summary_df)
        if fig:
            if st.button("Generate Report"):
                report_html = generate_report(df, summary_df, fig)
                st.markdown("### 📄 Weekly Summary")
                st.components.v1.html(report_html, height=800, scrolling=True)
                st.download_button(
                    "Download Summary as HTML",
                    data=report_html,
                    file_name=f"Weekly_Summary_{datetime.datetime.now().strftime('%Y%m%d')}.html",
                    mime="text/html"
                )
    else:
        st.error("❌ Incorrect password.")

# Optional: Display submitted overview table
st.subheader("📋 Submitted Reports Overview")
st.dataframe(summary_df[['Store Number', 'Store Name', 'CPM', 'Prototype']])
