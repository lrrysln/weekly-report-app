import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from google.oauth2.service_account import Credentials
import gspread

# --- Auth & Google Sheets Setup ---
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=SCOPES)
client = gspread.authorize(creds)

# --- Config ---
st.set_page_config(layout="wide", page_title="Weekly Construction Trend Report")
st.title("📊 Weekly Store Opening Trend Report")

SPREADSHEET_ID = "1cfr5rCRoRXuDJonarDbokznlaHHVpn1yUfTwo_ePL3w"
WORKSHEET_NAME = "Sheet1"

# --- Load data ---
@st.cache_data(ttl=600)
def load_data():
    try:
        sheet = client.open_by_key(SPREADSHEET_ID).worksheet(WORKSHEET_NAME)
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        return df
    except Exception as e:
        st.error(f"Failed to load data: {e}")
        return pd.DataFrame()

df = load_data()

if df.empty:
    st.warning("⚠️ No data loaded from Google Sheet.")
    st.stop()

# --- Preprocess date columns ---
for col in ["Baseline", "Store Opening"]:
    if col in df.columns:
        df[col] = pd.to_datetime(df[col], errors='coerce')

# --- Define trend calculation function ---
def calculate_trend(row):
    baseline_flag = str(row.get("Baseline", "")).strip()
    baseline_date = row.get("Baseline")
    current_date = row.get("Store Opening")

    # Check baseline flag field, you mentioned "/True" means baseline
    baseline_flag_raw = str(row.get("Flag") or "").strip()  # or change to your actual baseline flag column name

    # Use "Flag" or "Baseline" column depending on your sheet; adjust accordingly
    if baseline_flag_raw == "/True":
        return "baseline"
    
    if pd.isna(baseline_date) or pd.isna(current_date):
        return "No Data"

    if current_date > baseline_date:
        return "pushed"
    elif current_date < baseline_date:
        return "pulled in"
    else:
        return "held"

# --- Compute trend ---
df["Trend"] = df.apply(calculate_trend, axis=1)

# --- Summary counts ---
trend_counts = df["Trend"].value_counts().reindex(["baseline", "pushed", "pulled in", "held", "No Data"], fill_value=0)

# --- Display summary table ---
st.subheader("Trend Counts Summary")
st.table(trend_counts.rename_axis("Trend").reset_index().rename(columns={"index": "Trend", "Trend": "Count"}))

# --- Plot bar chart ---
fig, ax = plt.subplots(figsize=(8, 5))
colors = {
    "baseline": "#6baed6",
    "pushed": "#de2d26",
    "pulled in": "#31a354",
    "held": "#ff7f00",
    "No Data": "#969696"
}
bars = ax.bar(trend_counts.index, trend_counts.values, color=[colors.get(trend, "#636363") for trend in trend_counts.index])
ax.set_title("Store Opening Trend Counts")
ax.set_ylabel("Number of Stores")
ax.set_xlabel("Trend")
ax.grid(axis="y", linestyle="--", alpha=0.7)
st.pyplot(fig)

# --- Optional: Show full data table with trend ---
st.subheader("Detailed Store Data with Trend")
st.dataframe(df)

