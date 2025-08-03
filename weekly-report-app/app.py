import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import plotly.express as px

# --- Page Config ---
st.set_page_config(page_title="Weekly Construction Trends", layout="wide")

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

# --- Password Protection ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    with st.form("password_form"):
        password = st.text_input("Enter password to view report", type="password")
        submitted = st.form_submit_button("Submit")
        if submitted:
            if password == "1234":
                st.session_state.authenticated = True
            else:
                st.error("Incorrect password")
    st.stop()

# --- Load Data After Auth ---
df = load_data()

if df.empty:
    st.warning("⚠️ No data loaded from Google Sheet yet.")
    st.stop()

# --- Clean & Format ---
df["Week Ending"] = pd.to_datetime(df["Week Ending"], errors="coerce")
df["Store Opening"] = pd.to_datetime(df["Store Opening"], errors="coerce")
df["Baseline Store Opening"] = pd.to_datetime(df["Baseline Store Opening"], errors="coerce")

# --- Trend Logic ---
def calculate_trend(row):
    baseline = row["Baseline Store Opening"]
    current = row["Store Opening"]
    if pd.isna(baseline):
        return "no baseline dates"
    elif current > baseline:
        return "pushed"
    elif current < baseline:
        return "pulled in"
    else:
        return "held"

def calculate_delta(row):
    baseline = row["Baseline Store Opening"]
    current = row["Store Opening"]
    if pd.isna(baseline):
        return None
    return (current - baseline).days

df["Store Opening Trend"] = df.apply(calculate_trend, axis=1)
df["Store Opening Δ"] = df.apply(calculate_delta, axis=1)

def flag_delta(delta, trend):
    if trend == "no baseline dates":
        return "no baseline dates"
    elif delta is not None and abs(delta) > 5:
        return '<span style="color:red;font-weight:bold;">*</span>'
    else:
        return ""

df["⚑"] = df.apply(lambda row: flag_delta(row["Store Opening Δ"], row["Store Opening Trend"]), axis=1)

# --- Trend Summary Table ---
summary = df["Store Opening Trend"].value_counts().reset_index()
summary.columns = ["Trend", "Count"]
summary = summary[summary["Trend"] != "no baseline dates"]

# --- Display Trend Summary Table ---
st.subheader("📊 Store Opening Trend Summary")
st.dataframe(summary, use_container_width=True)

# --- Trend Breakdown Chart ---
fig = px.bar(summary, x="Trend", y="Count", color="Trend", title="Store Opening Trend Breakdown")
st.plotly_chart(fig, use_container_width=True)

# --- Export HTML Report (Optional) ---
with st.expander("📄 HTML Summary (Optional)"):
    html_table = df[["Prototype", "Store #", "Store Name", "Store Opening", "Baseline Store Opening", "Store Opening Δ", "Store Opening Trend", "⚑"]].copy()
    html_table["Store Opening"] = html_table["Store Opening"].dt.strftime("%m/%d/%y")
    html_table["Baseline Store Opening"] = html_table["Baseline Store Opening"].dt.strftime("%m/%d/%y")
    html_html = html_table.to_html(escape=False, index=False)
    st.markdown(html_html, unsafe_allow_html=True)
