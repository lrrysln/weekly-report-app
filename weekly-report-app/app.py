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

SPREADSHEET_ID = "1cfr5rCRoRXuDJonarDbokznlaHHVpn1yUfTwo_ePL3w"
WORKSHEET_NAME = "Sheet1"

# --- Load Sheet ---
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

# --- Load and Prepare Data ---
df = load_data()

if df.empty:
    st.warning("⚠️ No data loaded from Google Sheet yet.")
    st.stop()

df.columns = df.columns.str.strip()
df["Flag"] = df["Flag"].astype(str).str.strip()
df["Store Number"] = df["Store Number"].astype(str).str.strip()

# --- Convert Store Opening Dates ---
df["Store Opening"] = pd.to_datetime(df["Store Opening"], errors="coerce")

# --- Split Data: Baseline vs Current ---
baseline_df = df[df["Flag"] == "/True"].copy()
current_df = df[df["Flag"] != "/True"].copy()

# --- Latest Baseline per Store ---
latest_baseline = (
    baseline_df.sort_values("Year Week", ascending=False)
    .drop_duplicates(subset=["Store Number"], keep="first")
    .set_index("Store Number")[["Store Opening"]]
    .rename(columns={"Store Opening": "Baseline Opening"})
)

# --- Merge Current Data with Baseline Dates ---
current_df = current_df.merge(
    latest_baseline,
    how="left",
    left_on="Store Number",
    right_index=True
)

# --- Trend Logic ---
def calculate_trend(row):
    current_date = row["Store Opening"]
    baseline_date = row["Baseline Opening"]
    
    if pd.isna(current_date) or pd.isna(baseline_date):
        return pd.Series(["⚫ No Data", None])
    
    delta = (current_date - baseline_date).days
    
    if delta > 0:
        return pd.Series(["🔴 Pushed", delta])
    elif delta < 0:
        return pd.Series(["🟢 Pulled In", delta])
    else:
        return pd.Series(["🟡 Held", 0])

current_df[["Trend", "Delta Days"]] = current_df.apply(calculate_trend, axis=1)

# --- Add Baseline Tags ---
baseline_df["Trend"] = "🟤 Baseline"
baseline_df["Delta Days"] = 0

# --- Combine Data ---
combined = pd.concat([baseline_df, current_df], ignore_index=True)

# --- Display Table ---
st.subheader("📋 Store Opening Trend Table")
st.dataframe(combined[[
    "Store Name", "Store Number", "Prototype", "CPM", "Delta Days", "Trend"
]])

# --- Plot Trend Counts ---
st.subheader("📊 Store Opening Trend Summary")
trend_counts = combined["Trend"].value_counts()

fig, ax = plt.subplots()
trend_counts.plot(
    kind='bar',
    ax=ax,
    color=["#DA3E52", "#3CBA54", "#F4C300", "#A9A9A9", "#808080"]
)
ax.set_title("Store Opening Trend Count")
ax.set_xlabel("Trend")
ax.set_ylabel("Number of Stores")
st.pyplot(fig)
