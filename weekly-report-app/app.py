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

# Ensure credentials are present in st.secrets
if "gcp_service_account" not in st.secrets:
    st.error("Service account credentials not found in secrets.")
    st.stop()

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

# Clean column names by removing spaces and special characters
df.columns = [c.strip() for c in df.columns]

# --- Data Preparation ---
# Ensure 'Baseline' column exists in the data
if 'Baseline' in df.columns:
    df['Baseline'] = pd.to_datetime(df['Baseline'], errors='coerce')
else:
    st.warning("'Baseline' column is missing from the dataset.")
    df['Baseline'] = pd.NaT  # If missing, set the column to NaT (Not a Time)

# Convert other date columns
date_cols = [col for col in df.columns if any(k in col for k in ["TCO", "Ops Walk", "Turnover", "Open to Train", "Store Opening", "Start"])]
for col in date_cols:
    df[col] = pd.to_datetime(df[col], errors='coerce')

# --- Calculate Store Opening Delta and Flag ---
df['Store Opening Delta'] = df.apply(
    lambda row: (row['Store Opening'] - row['Baseline']).days
    if pd.notna(row['Baseline']) and pd.notna(row['Store Opening'])
    else None,
    axis=1
)

df['Flag'] = df['Store Opening Delta'].apply(lambda x: "Critical" if pd.notna(x) and x >= 5 else "")

# --- Trend Calculation ---
trend_map = {}
grouped = df.groupby('Store Name')
for store, group in grouped:
    group = group.sort_values('Year Week')
    prev_date = None
    for idx, row in group.iterrows():
        current_date = row['Store Opening']
        baseline_date = row['Baseline']

        if pd.isna(current_date):
            trend_map[idx] = "🟡 Held"
            continue

        if pd.notna(baseline_date) and current_date == baseline_date:
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

# Week info
df['Year Week'] = df['Year Week'].astype(str)
df = df.sort_values(by=['Store Name', 'Year Week'])

# --- Notes Filtering ---
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
def highlight_keyword(x):
    return f"{x} <span style='color:red;'>*</span>" if check_notes(x) else "see report below"

df['Notes Filtered'] = df['Notes'].apply(highlight_keyword)

# --- Report Overview ---
summary_cols = ['Store Name', 'Store Number', 'Prototype', 'CPM', 'Store Opening Delta', 'Trend', 'Flag', 'Notes Filtered']
summary_df = df[summary_cols].drop_duplicates(subset=['Store Name']).reset_index(drop=True)
summary_df.rename(columns={'Notes Filtered': 'Notes'}, inplace=True)

# --- Submission Overview BEFORE password ---
st.subheader("📋 Submitted Reports Overview")
submitted_count = len(summary_df)
st.markdown(f"<h4><span style='color:red;'><b>{submitted_count}</b></span> form responses have been submitted</h4>", unsafe_allow_html=True)
visible_df = summary_df[['Store Number', 'Store Name', 'CPM', 'Prototype']]
st.dataframe(visible_df)

# --- Password Section ---
st.subheader("🔐 Generate Weekly Summary Report")

# Password input field
password = st.text_input("Enter Password", type="password")

# Show submit button only after correct password
if password == "1234":
    st.session_state.password_valid = True  # Save password status in session state
else:
    st.session_state.password_valid = False

# Show button only if password is correct
if st.session_state.password_valid:
    if st.button("Generate Report"):
        fig = plot_trends(df)
        df, report_html = generate_report(df, summary_df, fig)
        if df is not None:
            st.markdown(report_html, unsafe_allow_html=True)
else:
    if password:
        st.error("❌ Incorrect password.")

# --- Plot Trends Function ---
def plot_trends(df):
    # Count the occurrences of each trend
    trend_counts = df['Trend'].value_counts()

    # Define a color palette for the trends
    colors = {
        "🟡 Held": "yellow",
        "⚪ Baseline": "gray",
        "🟢 Pulled In": "green",
        "🔴 Pushed": "red"
    }

    # Plotting the bar chart
    fig, ax = plt.subplots()
    bars = ax.bar(trend_counts.index, trend_counts.values, color=[colors.get(x, 'grey') for x in trend_counts.index])
    ax.set_ylabel("Count")
    ax.set_xlabel("Trend")

    # Annotate the bars with values (whole numbers)
    for bar in bars:
        height = bar.get_height()
        ax.annotate(f'{int(height)}', xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3), textcoords="offset points",
                    ha='center', va='bottom')

    plt.tight_layout()

    return fig

# --- Function to Generate Report ---
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
        "th, td {border: 1px solid #ddd; padding: 8px; text-align: center;}",
        "th {background-color: #f2f2f2;}",
        "</style></head><body>",
        f"<h1>{year} Week: {week_number} Weekly Summary Report</h1>",
        f'<img src="data:image/png;base64,{img_base64}" style="max-width:600px; display:block; margin:auto;">',
        "<h2>Executive Summary</h2>",
        summary_df.to_html(index=False, escape=False),
        "<hr>"
    ]

    # Group by store name or subject
    group_col = "Subject" if "Subject" in df.columns else "Store Name"
    for group_name, group_df in df.groupby(group_col):
        html.append(f"<h2>{group_name}</h2>")
        html.append(group_df.to_html(index=False))

    html.append("</body></html>")
    return df, "".join(html)

def fig_to_base64(fig):
    """Convert matplotlib figure to base64 string."""
    img_buffer = BytesIO()
    fig.savefig(img_buffer, format='png')
    img_buffer.seek(0)
    img_base64 = base64.b64encode(img_buffer.read()).decode('utf-8')
    return img_base64


