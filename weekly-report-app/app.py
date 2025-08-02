import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import matplotlib.pyplot as plt

# --- Auth & Google Sheets Setup ---
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]
creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=SCOPES)
client = gspread.authorize(creds)

# --- Config ---
st.set_page_config(layout="wide", page_title="Store Opening Trend Tracker")

# --- Load Sheet ---
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

# --- Clean Columns ---
df.columns = df.columns.str.strip()
df["Store Number"] = df["Store Number"].astype(str)

# --- Split Baseline and Current Week ---
baseline_df = df[df["Flag"].astype(str).str.strip() == "/True"].copy()
current_df = df[df["Flag"].astype(str).str.strip() != "/True"].copy()

# Convert dates
baseline_df["Store Opening"] = pd.to_datetime(baseline_df["Store Opening"], errors='coerce')
current_df["Store Opening"] = pd.to_datetime(current_df["Store Opening"], errors='coerce')

# Create lookup of baseline opening dates
baseline_lookup = baseline_df.set_index("Store Number")["Store Opening"].to_dict()

# --- Compare Dates and Assign Trend ---
def get_trend(store_num, current_open_date):
    baseline_date = baseline_lookup.get(store_num)
    if baseline_date is None or pd.isna(current_open_date):
        return "⚫ No Baseline"
    if current_open_date > baseline_date:
        return "🔴 Pushed"
    elif current_open_date < baseline_date:
        return "🟢 Pulled In"
    else:
        return "🟡 Held"

current_df["Trend"] = current_df.apply(
    lambda row: get_trend(row["Store Number"], row["Store Opening"]), axis=1
)

# Add Baseline trend rows too
baseline_df["Trend"] = "🟤 Baseline"

# Combine all for output
final_df = pd.concat([baseline_df, current_df], ignore_index=True)

# --- Display Table ---
st.subheader("📋 Store Opening Trend Table")
st.dataframe(final_df[[
    "Store Name", "Store Number", "Prototype", "CPM", "Trend", "Store Opening", "Notes"
]])

# --- Chart: Trend Counts ---
st.subheader("📊 Store Opening Trend Summary")
trend_counts = final_df["Trend"].value_counts()

fig, ax = plt.subplots()
trend_counts.plot(kind='bar', color=["#DA3E52", "#3CBA54", "#F4C300", "#A9A9A9", "#8E8E8E"], ax=ax)
ax.set_title("Store Opening Trend Count")
ax.set_xlabel("Trend")
ax.set_ylabel("Number of Stores")
st.pyplot(fig)
