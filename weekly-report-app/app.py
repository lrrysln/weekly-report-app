import streamlit as st
from datetime import datetime
from google.oauth2.service_account import Credentials
import gspread
import streamlit as st
from datetime import datetime
from google.oauth2.service_account import Credentials
import json

# --- Google Sheets Auth ---
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
service_account_info = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
# Authorize using dictionary directly from secrets.toml
creds = Credentials.from_service_account_info(st.secrets["GOOGLE_CREDENTIALS"], scopes=SCOPES)
client = gspread.authorize(creds)

# Open the Google Sheet
sheet = client.open("My Weekly Report Sheet").worksheet("Form Submissions")


# Open the Google Sheet
sheet = client.open("My Weekly Report Sheet").worksheet("Form Submissions")

# --- Streamlit App ---
st.set_page_config(page_title="Weekly Report", layout="centered")
st.title("📋 Weekly Construction Report")

# --- Password Gate ---
password = st.text_input("Enter password to unlock form", type="password")
if password != "yourpassword":  # <-- Replace with your actual password
    st.warning("Enter valid password to continue.")
    st.stop()

# --- Form Inputs ---
with st.form("weekly_report_form"):
    name = st.text_input("Your Name")
    date = st.date_input("Date", value=datetime.today())
    notes = st.text_area("Weekly Notes (Each bullet on a new line)", height=200)

    submitted = st.form_submit_button("Submit Report")

# --- On Submit ---
if submitted:
    # Auto-bullet format
    bullet_notes = "\n".join([f"- {line.strip()}" for line in notes.split("\n") if line.strip()])

    # Append to Google Sheet
    sheet.append_row([
        name,
        date.strftime("%m/%d/%y"),
        bullet_notes
    ])

    # --- HTML Preview ---
    html_report = f"""
    <div style="font-family:Arial;padding:10px">
        <h2>Weekly Report</h2>
        <p><strong>Name:</strong> {name}</p>
        <p><strong>Date:</strong> {date.strftime("%m/%d/%y")}</p>
        <p><strong>Notes:</strong></p>
        <ul>
            {''.join([f'<li>{line.strip()}</li>' for line in notes.splitlines() if line.strip()])}
        </ul>
    </div>
    """

    st.success("✅ Report submitted successfully!")
    st.markdown("---")
    st.markdown("### 📄 HTML Preview")
    st.components.v1.html(html_report, height=400, scrolling=True)
    
    # Clear form inputs (Streamlit doesn't support full reset yet)
    st.experimental_rerun()
