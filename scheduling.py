import streamlit as st
import pdfplumber
import pandas as pd
import re
import os
import tempfile
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.service_account import Credentials

# ======================
# Google Drive Setup
# ======================

SCOPES = ['https://www.googleapis.com/auth/drive']
DRIVE_FOLDER_NAME = 'Scheduling'  # This must match the folder name in Google Drive

@st.cache_resource
def authenticate_google_drive():
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=SCOPES
    )
    return build('drive', 'v3', credentials=creds)

def get_drive_folder_id(service, folder_name):
    query = f"name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    results = service.files().list(q=query, spaces='drive', fields='files(id, name)', pageSize=1).execute()
    folders = results.get('files', [])
    if not folders:
        raise Exception(f"Folder named '{folder_name}' not found in your Google Drive.")
    return folders[0]['id']

def upload_csv_to_drive(service, csv_path, file_name, folder_id):
    file_metadata = {
        'name': file_name,
        'mimeType': 'text/csv',
        'parents': [folder_id]
    }
    media = MediaFileUpload(csv_path, mimetype='text/csv')
    file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    return file.get('id')

# ======================
# Streamlit App
# ======================

st.set_page_config(page_title="PDF Data Extractor", layout="wide")
st.title("📄 Multi-PDF Activity Extractor & Uploader")

uploaded_files = st.file_uploader("Upload one or more PDF files", type="pdf", accept_multiple_files=True)

if uploaded_files:
    service = authenticate_google_drive()
    folder_id = get_drive_folder_id(service, DRIVE_FOLDER_NAME)

    all_dataframes = []

    for uploaded_file in uploaded_files:
        pdf_name = os.path.splitext(uploaded_file.name)[0]
        file_prefix = pdf_name.split(" - ")[0] if " - " in pdf_name else pdf_name

        # Extract text from uploaded PDF
        all_text = ""
        with pdfplumber.open(uploaded_file) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    all_text += page_text + "\n"

        # Regex to extract structured data
        pattern = re.compile(r"(\S+)\s+(.+?)\s+(\d+)\s+(\d{2}-\d{2}-\d{2})\s+(\d{2}-\d{2}-\d{2})\s+(\d+)\s+(.*)")

        rows = []
        for line in all_text.strip().split('\n'):
            match = pattern.match(line)
            if match:
                rows.append({
                    "File Prefix": file_prefix,
                    "Activity ID": match.group(1),
                    "Activity Name": match.group(2),
                    "Duration": int(match.group(3)),
                    "Start Date": match.group(4),
                    "Finish Date": match.group(5),
                    "Float": int(match.group(6)),
                    "Notes": match.group(7)
                })

        if rows:
            df = pd.DataFrame(rows)
            all_dataframes.append(df)

            st.success(f"✅ Extracted {len(df)} activities from `{uploaded_file.name}`")
            st.dataframe(df, use_container_width=True)

            # Save individual CSV and upload
            with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp_csv:
                df.to_csv(tmp_csv.name, index=False)
                csv_path = tmp_csv.name

            csv_filename = f"{file_prefix}.csv"

            if st.button(f"📤 Upload `{csv_filename}` to Google Drive", key=csv_filename):
                try:
                    file_id = upload_csv_to_drive(service, csv_path, csv_filename, folder_id)
                    st.success(f"✅ Uploaded! [View File](https://drive.google.com/file/d/{file_id})")
                except Exception as e:
                    st.error(f"❌ Upload failed for `{csv_filename}`: {str(e)}")

    # Optional: Combine and download all
    if all_dataframes:
        combined_df = pd.concat(all_dataframes, ignore_index=True)
        st.markdown("### 📦 Download All Extracted Data")
        st.download_button("⬇️ Download Combined CSV", combined_df.to_csv(index=False), file_name="combined_activities.csv", mime="text/csv")

else:
    st.info("👆 Upload one or more PDF files to begin.")
