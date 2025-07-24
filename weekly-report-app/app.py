import streamlit as st
import pandas as pd
import datetime
import re
import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import tempfile

# --- CONFIG ---
SPREADSHEET_NAME = "Construction_Weekly_Updates"
FORM_SHEET_NAME = "Form_Entries"
FOLDER_NAME = "ConstructionReports"
PASSWORD = "1234"

# --- GOOGLE AUTH ---
@st.cache_resource
def get_gsheet_service():
    creds = service_account.Credentials.from_service_account_file(
        "credentials.json",
        scopes=["https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"]
    )
    sheet_service = build("sheets", "v4", credentials=creds)
    drive_service = build("drive", "v3", credentials=creds)
    return sheet_service, drive_service

sheet_service, drive_service = get_gsheet_service()

# --- FIND / CREATE SPREADSHEET ---
@st.cache_resource
def get_or_create_spreadsheet():
    results = drive_service.files().list(q=f"name='{SPREADSHEET_NAME}' and mimeType='application/vnd.google-apps.spreadsheet'", fields="files(id)").execute()
    files = results.get("files", [])
    if files:
        return files[0]["id"]
    file_metadata = {
        "name": SPREADSHEET_NAME,
        "mimeType": "application/vnd.google-apps.spreadsheet"
    }
    file = drive_service.files().create(body=file_metadata).execute()
    return file["id"]

spreadsheet_id = get_or_create_spreadsheet()

# --- FORM SECTION ---
st.title("📋 Construction Weekly Report Submission")

with st.form("weekly_form"):
    store = st.text_input("Store Name or Job #", "")
    pm = st.text_input("Project Manager", "")
    prototype = st.selectbox("Prototype", ["6K", "9K", "12K", "Other"])
    cpm = st.text_input("CPM", "")
    start = st.date_input("Start Date")
    tco = st.date_input("TCO Date")
    turnover = st.date_input("Turnover Date")
    notes_input = st.text_area("Weekly Notes (each line becomes a bullet point)")

    submitted = st.form_submit_button("Submit Report")

if submitted:
    # Format bullets
    notes_cleaned = "\n".join(
        f"- {re.sub(r'^[\s•\-–●]+', '', line)}"
        for line in notes_input.splitlines()
        if line.strip()
    )

    today = datetime.date.today()
    year_week = f"{today.year} Week {today.isocalendar()[1]}"
    submission = [year_week, store, pm, prototype, cpm,
                  start.strftime("%m/%d/%y"), tco.strftime("%m/%d/%y"),
                  turnover.strftime("%m/%d/%y"), notes_cleaned]

    # Save to Google Sheet (form tab)
    sheet_service.spreadsheets().values().append(
        spreadsheetId=spreadsheet_id,
        range=f"{FORM_SHEET_NAME}!A1",
        valueInputOption="USER_ENTERED",
        body={"values": [submission]}
    ).execute()

    st.success("✅ Submission saved successfully!")

    # Save HTML report to Drive
    html_report = f"""
    <h2>Weekly Report – {store}</h2>
    <ul>
        <li><strong>PM:</strong> {pm}</li>
        <li><strong>Prototype:</strong> {prototype}</li>
        <li><strong>CPM:</strong> {cpm}</li>
        <li><strong>Start:</strong> {start.strftime("%m/%d/%y")}</li>
        <li><strong>TCO:</strong> {tco.strftime("%m/%d/%y")}</li>
        <li><strong>Turnover:</strong> {turnover.strftime("%m/%d/%y")}</li>
    </ul>
    <p><strong>Notes:</strong></p>
    <ul>
        {''.join(f"<li>{line[2:]}</li>" for line in notes_cleaned.splitlines())}
    </ul>
    """

    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".html") as tmp:
        tmp.write(html_report)
        tmp_path = tmp.name

    media = MediaFileUpload(tmp_path, mimetype="text/html")
    drive_service.files().create(
        body={"name": f"{store}_Report_{year_week}.html"},
        media_body=media
    ).execute()

    os.unlink(tmp_path)

# --- VIEW REPORT (Password-Protected) ---
st.divider()
st.subheader("🔐 View Reports")

if st.button("View Report"):
    with st.expander("Enter Password"):
        pwd = st.text_input("Password", type="password")
        if pwd == PASSWORD:
            st.success("Access granted.")

            rows = sheet_service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=f"{FORM_SHEET_NAME}!A2:I"
            ).execute().get("values", [])

            if rows:
                df = pd.DataFrame(rows, columns=["YearWeek", "Store", "PM", "Prototype", "CPM", "Start", "TCO", "Turnover", "Notes"])
                st.dataframe(df)

                # Display latest HTML
                last = df.iloc[-1]
                last_html = f"""
                <h3>Latest Report – {last['Store']}</h3>
                <p><strong>PM:</strong> {last['PM']}</p>
                <p><strong>Notes:</strong></p>
                <ul>
                {''.join(f"<li>{line[2:]}</li>" for line in last['Notes'].splitlines())}
                </ul>
                """
                st.markdown(last_html, unsafe_allow_html=True)
                st.download_button("⬇️ Download Last Report (HTML)", last_html, file_name="Weekly_Report.html", mime="text/html")
            else:
                st.warning("No reports available.")
        else:
            st.error("Incorrect password.")
