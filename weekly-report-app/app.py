import streamlit as st
import pandas as pd
from google.oauth2.service_account import Credentials
import gspread

# --- Google Sheets Auth ---
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

credentials = Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],
    scopes=SCOPES,
)

client = gspread.authorize(credentials)

# --- Config ---
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/edit#gid=0"
Sheet1 = "Sheet1"

# --- Load data from Google Sheet ---
@st.cache_data(ttl=600)
def load_data():
    try:
        sheet = client.open_by_url(SPREADSHEET_URL).worksheet(Sheet1)
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        df.columns = df.columns.str.strip()  # Ensure no leading/trailing spaces
        return df
    except Exception as e:
        st.error(f"❌ Failed to load data from Google Sheet: {e}")
        return pd.DataFrame()

df = load_data()

if df.empty:
    st.stop()

# --- Get store options ---
def get_store_names():
    if "Store Name" not in df.columns:
        st.error("❌ 'Store Name' column not found.")
        return []
    return sorted(df["Store Name"].dropna().astype(str).unique())

store_options = get_store_names()

# --- Streamlit App UI ---
st.title("Weekly Construction Update")

selected_store = st.selectbox("Select a Store", store_options)

filtered_df = df[df["Store Name"].astype(str) == selected_store]

st.dataframe(filtered_df)

# Optional: Render additional metrics or summaries here
