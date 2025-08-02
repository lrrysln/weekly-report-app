import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import plotly.express as px
from datetime import datetime

st.set_page_config(page_title="Weekly Construction Trend Report", layout="wide")

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

# --- Password Protection ---
PASSWORD = st.secrets.get("password", "admin123")
entered_password = st.text_input("Enter password to view the report", type="password")

if entered_password != PASSWORD:
    st.stop()

# --- Date Parsing ---
df['Store Opening Parsed'] = pd.to_datetime(df['Store Opening'], errors='coerce')
df['Baseline Parsed'] = pd.to_datetime(df['⚪ Baseline Store Opening'], errors='coerce')

# --- Delta and Trend Categorization ---
def get_trend(row):
    if pd.isnull(row['Baseline Parsed']):
        return "no baseline dates", "", ""
    delta = (row['Store Opening Parsed'] - row['Baseline Parsed']).days
    if delta > 0:
        trend = "Pushed"
    elif delta < 0:
        trend = "Pulled In"
    else:
        trend = "Held"
    flag = f"<span style='color:red'>*</span>" if abs(delta) > 5 else ""
    return trend, delta, flag

df[['Trend Type', 'Store Opening Delta', 'Flag']] = df.apply(
    lambda row: pd.Series(get_trend(row)), axis=1
)

# --- Trend Summary Table ---
trend_summary = df['Trend Type'].value_counts().reset_index()
trend_summary.columns = ['Trend', 'Count']

# --- Trend Breakdown Chart ---
fig = px.pie(trend_summary, names='Trend', values='Count', title="📊 Trend Breakdown")

# --- Final HTML Report ---
def generate_report(df, fig, trend_summary):
    st.markdown("### 📋 Executive Summary")

    # Pie chart
    st.plotly_chart(fig, use_container_width=True)

    # Summary table
    st.markdown("#### 🧮 Trend Summary Table")
    st.dataframe(trend_summary)

    # Simplified detailed view
    st.markdown("#### 🏗️ Store-Level Weekly Trend")
    styled_df = df[['Store #', 'Store Name', '⚪ Baseline Store Opening', 'Store Opening', 'Trend Type', 'Store Opening Delta', 'Flag']].copy()
    styled_df['Flag'] = styled_df['Flag'].astype(str)
    styled_df['Flag'] = styled_df['Flag'].apply(lambda x: x if x else "")
    
    def highlight_flag(val):
        return "color: red;" if "*" in val else ""

    st.dataframe(
        styled_df.style.set_properties(**{
            'Flag': 'text-align: center;'
        }).applymap(highlight_flag, subset=['Flag']),
        use_container_width=True
    )

# --- Generate Report ---
generate_report(df, fig, trend_summary)
