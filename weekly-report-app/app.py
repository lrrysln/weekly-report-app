import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import plotly.express as px
from datetime import datetime

# --- Auth & Google Sheets Setup ---
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]
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

df = load_data()

if df.empty:
    st.warning("⚠️ No data loaded from Google Sheet yet.")
    st.stop()

# --- Password Protection ---
PASSWORD = "weeklyupdate"
entered_pw = st.text_input("🔒 Enter password to view report:", type="password")
if entered_pw != PASSWORD:
    st.stop()

# --- Data Cleaning ---
df['Store Opening'] = pd.to_datetime(df['Store Opening'], errors='coerce')
df['⚪ Baseline Store Opening'] = pd.to_datetime(df['⚪ Baseline Store Opening'], errors='coerce')

# --- Delta & Flag Calculation ---
def calculate_delta(row):
    if pd.isna(row['⚪ Baseline Store Opening']):
        return "no baseline dates"
    else:
        return (row['Store Opening'] - row['⚪ Baseline Store Opening']).days

df['Store Opening Delta'] = df.apply(calculate_delta, axis=1)

def flag(row):
    if isinstance(row['Store Opening Delta'], int) and row['Store Opening Delta'] > 5:
        return "<span style='color:red'>*</span>"
    else:
        return ""

df['Flag'] = df.apply(flag, axis=1)

# --- Trend Categorization ---
def categorize_trend(row):
    if isinstance(row['Store Opening Delta'], str):
        return row['Store Opening Delta']
    elif row['Store Opening Delta'] > 0:
        return "Pushed"
    elif row['Store Opening Delta'] < 0:
        return "Pulled In"
    else:
        return "Held"

df['Trend'] = df.apply(categorize_trend, axis=1)

# --- Trend Summary Table ---
summary_df = df['Trend'].value_counts().reset_index()
summary_df.columns = ['Trend', 'Count']

# --- Trend Breakdown Chart ---
fig = px.pie(summary_df, values='Count', names='Trend', title="Store Opening Trends Breakdown")

# --- HTML Report Generation ---
def generate_html_report(df, summary_df, fig_html):
    summary_html = summary_df.to_html(index=False)
    trend_table_html = df[['Store', 'Prototype', 'Store Opening', '⚪ Baseline Store Opening', 'Store Opening Delta', 'Trend', 'Flag']].to_html(index=False, escape=False)

    html_report = f"""
    <h2>📊 Store Opening Weekly Report</h2>
    <h3>Trend Summary</h3>
    {summary_html}
    <h3>Trend Breakdown Chart</h3>
    {fig_html}
    """
    return html_report

# Convert Plotly chart to HTML string
fig_html = fig.to_html(full_html=False, include_plotlyjs="cdn")

# --- Display Report ---
st.markdown("## 🧾 Executive Summary")
st.components.v1.html(generate_html_report(df, summary_df, fig_html), height=800, scrolling=True)
