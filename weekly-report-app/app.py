import streamlit as st
import pandas as pd
from datetime import datetime
from google.oauth2.service_account import Credentials
import gspread

# --- Google Sheets Auth ---
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]
creds = Credentials.from_service_account_file("credentials.json", scopes=SCOPES)
client = gspread.authorize(creds)
sheet = client.open("Construction Weekly Updates").sheet1  # <-- Make sure this name is EXACT

# --- Streamlit Setup ---
st.set_page_config(page_title="Weekly Construction Update", layout="wide")
st.title("Weekly Construction Update")

# --- Load Sheet as DataFrame ---
try:
    df = pd.DataFrame(sheet.get_all_records())
    df.columns = df.columns.str.strip()  # Remove extra spaces in column names
except Exception as e:
    st.error(f"❌ Failed to load data from Google Sheet: {e}")
    st.stop()

# --- Helper Functions ---
def get_store_names():
    if "Store Name" not in df.columns:
        st.warning(f"⚠️ 'Store Name' column not found. Available columns: {list(df.columns)}")
        return []
    return sorted(df["Store Name"].dropna().unique())

def get_subjects():
    if "Subject" not in df.columns:
        st.warning(f"⚠️ 'Subject' column not found. Available columns: {list(df.columns)}")
        return []
    return sorted(df["Subject"].dropna().unique())

def generate_html_summary(grouped_df):
    html = "<h3>Weekly Summary</h3>"
    for subject, group in grouped_df:
        html += f"<h4>{subject}</h4><ul>"
        for _, row in group.iterrows():
            notes = str(row.get("Notes", "")).strip().replace("\n", "<br>• ")
            html += f"<li><strong>{row.get('Store Name', 'N/A')}:</strong> • {notes}</li>"
        html += "</ul>"
    return html

# --- Password Protection ---
password = st.text_input("Enter password to generate summary:", type="password")
if password != "1234":
    st.stop()

# --- Filters ---
store_options = get_store_names()
subject_options = get_subjects()

selected_week = st.selectbox("Select Week of the Year", sorted(df["Week of the Year"].dropna().unique(), reverse=True))
filtered_df = df[df["Week of the Year"] == selected_week]

# --- Grouping ---
grouped = filtered_df.groupby("Subject")

# --- Display Summary ---
st.subheader("📋 Summary Report")
try:
    summary_html = generate_html_summary(grouped)
    st.markdown(summary_html, unsafe_allow_html=True)
except Exception as e:
    st.error(f"❌ Error generating summary: {e}")

# --- Raw Table View ---
with st.expander("📄 View Raw Table"):
    st.dataframe(filtered_df)
