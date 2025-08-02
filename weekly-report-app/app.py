import streamlit as st
import pandas as pd
import datetime
import json
import gspread
from google.oauth2.service_account import Credentials

# --- Setup Page ---
st.set_page_config(page_title="Weekly Construction Report", layout="wide")
st.title("📋 Weekly Construction Report")

# --- Load Google Credentials ---
info = json.loads(st.secrets["GOOGLE_CREDENTIALS"])

scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_info(info, scopes=scope)
client = gspread.authorize(creds)

# --- Config ---
SPREADSHEET_ID = "your_google_sheet_id_here"   # Replace with actual Sheet ID
SHEET_NAME = "Sheet1"  # Replace with your actual sheet name

# --- Load Sheet ---
sheet = client.open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME)

# --- Get Data from Sheet ---
data = sheet.get_all_records()
df = pd.DataFrame(data)

# --- Report Generator Form ---
st.header("Submit Update")

with st.form("update_form"):
    store_name = st.text_input("Store Name")
    store_number = st.text_input("Store Number")
    prototype = st.selectbox("Prototype", ["EFC Traditional", "RaceWay EDO", "Travel Center", "Prototype A", "Prototype B"])
    pm = st.text_input("Project Manager")
    notes = st.text_area("Notes (one per line)", height=150)

    submitted = st.form_submit_button("Submit")

    if submitted:
        today = datetime.datetime.now().strftime("%m/%d/%Y")
        notes_list = [f"- {line.strip()}" for line in notes.strip().split("\n") if line.strip()]
        html_report = f"""
        <div style="font-family:Arial">
            <h3>{store_name} ({store_number})</h3>
            <p><b>Prototype:</b> {prototype}<br>
            <b>Project Manager:</b> {pm}<br>
            <b>Date:</b> {today}</p>
            <ul>
                {''.join(f'<li>{line[2:]}</li>' for line in notes_list)}
            </ul>
        </div>
        """

        st.markdown("### Live Preview")
        st.components.v1.html(html_report, height=300, scrolling=True)

        # Save to Google Sheet
        sheet.append_row([store_name, store_number, prototype, pm, today, "\n".join(notes_list)])
        st.success("✅ Update submitted successfully!")

# --- Display Current Sheet Data ---
st.header("📊 Submitted Reports")
st.dataframe(df)
