import streamlit as st
import pdfplumber
import pandas as pd
import re
import os
import tempfile
import pickle
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# ======================
# Google Drive Setup
# ======================

SCOPES = ['https://www.googleapis.com/auth/drive.file']
CREDENTIALS_FILE = 'credentials.json'  # Your OAuth 2.0 credentials file
TOKEN_PICKLE = 'token.pickle'
DRIVE_FOLDER_ID = 'YOUR_GOOGLE_DRIVE_FOLDER_ID'  # Replace this with your folder ID

@st.cache_resource
def authenticate_google_drive():
    creds = None
    if os.path.exists(TOKEN_PICKLE):
        with open(TOKEN_PICKLE, 'rb') as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_PICKLE, 'wb') as token:
            pickle.dump(creds, token)

    return build('drive', 'v3', credentials=creds)

def upload_csv_to_drive(csv_path, file_name, folder_id=None):
    service = authenticate_google_drive()
    file_metadata = {
        'name': file_name,
        'mimeType': 'text/csv',
    }
    if folder_id:
        file_metadata['parents'] = [folder_id]

    media = MediaFileUpload(csv_path, mimetype='text/csv')
    file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id'
    ).execute()
    return file.get('id')


# ======================
# Streamlit App
# ======================

st.set_page_config(page_title="Multi-PDF Activity Extractor", layout="wide")
st.title("📄 Multi-PDF Activity Extractor & Google Drive Uploader")

uploaded_files = st.file_uploader("Upload one or more PDF files", type="pdf", accept_multiple_files=True)

if uploaded_files:
    all_data = []

    for uploaded_file in uploaded_files:
        pdf_name = os.path.splitext(uploaded_file.name)[0]
        st.info(f"Processing: `{uploaded_file.name}`")

        # --- Extract project metadata ---
        title_parts = pdf_name.split(" - ")
        project_code = title_parts[0].strip() if len(title_parts) > 0 else "Unknown"
        project_name = title_parts[1].strip().title() if len(title_parts) > 1 else "Unknown Project"

        # Extract text
        all_text = ""
        with pdfplumber.open(uploaded_file) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    all_text += page_text + "\n"

        # Regex pattern
        pattern = re.compile(r"(\S+)\s+(.+?)\s+(\d+)\s+(\d{2}-\d{2}-\d{2})\s+(\d{2}-\d{2}-\d{2})\s+(\d+)\s+(.*)")

        for line in all_text.strip().split('\n'):
            match = pattern.match(line)
            if match:
                all_data.append({
                    "Project Code": project_code,
                    "Project Name": project_name,
                    "Activity ID": match.group(1),
                    "Activity Name": match.group(2),
                    "Duration": int(match.group(3)),
                    "Start Date": match.group(4),
                    "Finish Date": match.group(5),
                    "Float": int(match.group(6)),
                    "Notes": match.group(7)
                })

    # If we found data
    if all_data:
        df = pd.DataFrame(all_data)

        st.success(f"✅ Extracted {len(df)} rows from {len(uploaded_files)} file(s).")
        st.dataframe(df, use_container_width=True)

        # Save to CSV
        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp_csv:
            df.to_csv(tmp_csv.name, index=False)
            csv_path = tmp_csv.name

        csv_filename = "combined_activity_data.csv"

        if st.button("📤 Upload Combined Table to Google Drive"):
            try:
                file_id = upload_csv_to_drive(csv_path, csv_filename, folder_id=DRIVE_FOLDER_ID)
                st.success(f"✅ Uploaded! [View File](https://drive.google.com/file/d/{file_id})")
            except Exception as e:
                st.error(f"❌ Upload failed: {str(e)}")
    else:
        st.warning("⚠️ No valid activity data found in the uploaded PDFs.")
else:
    st.info("📂 Upload one or more PDF files to begin.")
