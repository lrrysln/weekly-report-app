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

# --- Streamlit Config ---
st.set_page_config(layout="wide", page_title="Store Opening Trend Analysis")
st.title("📊 Store Opening Trend Analysis")

SPREADSHEET_ID = "1cfr5rCRoRXuDJonarDbokznlaHHVpn1yUfTwo_ePL3w"
WORKSHEET_NAME = "Sheet1"

@st.cache_data(ttl=600)
def load_data():
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet(WORKSHEET_NAME)
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    return df

df = load_data()

if df.empty:
    st.warning("⚠️ No data loaded.")
    st.stop()

# --- Preprocess ---
df.columns = df.columns.str.strip()
df['Store Opening'] = pd.to_datetime(df['Store Opening'], errors='coerce')
df['Store Number'] = df['Store Number'].astype(str).str.strip()
df['Baseline'] = df['Baseline'].astype(str).str.strip()

# --- Separate baseline & non-baseline entries ---
baseline_df = df[df['Baseline'] == "/True"].copy()
update_df = df[df['Baseline'] != "/True"].copy()

# Index baseline data by Store Number for fast lookup
baseline_map = baseline_df.set_index('Store Number')['Store Opening'].to_dict()

# --- Trend Logic ---
def compute_trend(row):
    store_number = row['Store Number']
    current_open = row['Store Opening']
    
    if row['Baseline'] == "/True":
        return "baseline"
    
    baseline_open = baseline_map.get(store_number)
    
    if pd.isna(current_open) or pd.isna(baseline_open):
        return "No Baseline"
    
    if current_open > baseline_open:
        return "pushed"
    elif current_open < baseline_open:
        return "pulled in"
    else:
        return "held"

df['Trend'] = df.apply(compute_trend, axis=1)

# --- Summary Count ---
trend_counts = df['Trend'].value_counts().reindex(
    ["baseline", "pushed", "pulled in", "held", "No Baseline"], fill_value=0)

# --- Display Summary ---
st.subheader("Trend Summary")
st.table(trend_counts.rename_axis("Trend").reset_index().rename(columns={"index": "Trend", "Trend": "Count"}))

# --- Bar Chart ---
fig, ax = plt.subplots(figsize=(8, 5))
colors = {
    "baseline": "#6baed6",
    "pushed": "#de2d26",
    "pulled in": "#31a354",
    "held": "#ff7f00",
    "No Baseline": "#969696"
}
ax.bar(trend_counts.index, trend_counts.values, color=[colors.get(tr, "#999") for tr in trend_counts.index])
ax.set_title("📊 Trend Breakdown")
ax.set_ylabel("Store Count")
ax.set_xlabel("Trend")
ax.grid(axis='y', linestyle='--', alpha=0.7)
st.pyplot(fig)

# --- Optional: Show Table ---
st.subheader("Detailed Data with Trend")
st.dataframe(df[['Store Name', 'Store Number', 'Prototype', 'Project Manager', 'Store Opening', 'Baseline', 'Trend']])
