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
CREDENTIALS_FILE = 'credentials.json'
TOKEN_PICKLE = 'token.pickle'
DRIVE_FOLDER_ID = 'YOUR_GOOGLE_DRIVE_FOLDER_ID'  # Replace this

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

# ======================
# Sidebar Navigation
# ======================
page = st.sidebar.radio(
    "Navigation",
    ["🏠 Home", "📋 View Extracted Data", "🔁 View Repeated Activities", "📤 Upload Summary"]
)

uploaded_files = st.file_uploader("Upload one or more PDF files", type="pdf", accept_multiple_files=True)

if uploaded_files:
    all_data = []
    total_skipped = []

    for uploaded_file in uploaded_files:
        pdf_name = os.path.splitext(uploaded_file.name)[0]
        st.info(f"📄 Processing: `{uploaded_file.name}`")

        title_parts = pdf_name.split(" - ")
        project_code = title_parts[0].strip() if len(title_parts) > 0 else "Unknown"
        project_name = title_parts[1].strip().title() if len(title_parts) > 1 else "Unknown Project"

        all_text = ""
        with pdfplumber.open(uploaded_file) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    all_text += page_text + "\n"

        pattern = re.compile(r"^(\S+)\s+(.+?)\s+(\d+)\s+(\d{2}-\d{2}-\d{2})\s+(\d{2}-\d{2}-\d{2})\s+(\d+)\s+(.*)$")
        skipped_lines = []

        for line in all_text.strip().split('\n'):
            line = line.strip()
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
            else:
                skipped_lines.append({"PDF": uploaded_file.name, "Line": line})

        if skipped_lines:
            total_skipped.extend(skipped_lines)

    if all_data:
        df = pd.DataFrame(all_data)

        # Categorization function
        def categorize_activity(name):
            name = name.lower()
            if any(word in name for word in ["clear", "grade", "trench", "backfill", "earthwork", "site"]):
                return "🏗 Site Work & Earthwork"
            elif any(word in name for word in ["foundation", "slab", "footing", "structural"]):
                return "🧱 Foundation & Structural"
            elif any(word in name for word in ["tank", "dispenser", "piping", "fuel", "gas"]):
                return "⚙️ Fuel System Installation"
            elif any(word in name for word in ["building", "framing", "roof", "wall", "interior"]):
                return "🛠️ Building Construction"
            elif any(word in name for word in ["landscape", "sidewalk", "curb", "paving", "striping"]):
                return "🌿 Landscaping & Finishing"
            elif any(word in name for word in ["inspection", "punchlist", "handover", "final"]):
                return "📋 Final Inspection & Handover"
            else:
                return "❓ Uncategorized"

        # ======================
        # 🏠 HOME PAGE
        # ======================
        if page == "🏠 Home":
            st.success(f"✅ Extracted {len(df)} valid activities from {len(uploaded_files)} file(s).")
            st.info("Use the sidebar to view extracted data, repeated activities, or upload summary.")

        # ======================
        # 📋 VIEW EXTRACTED DATA
        # ======================
        elif page == "📋 View Extracted Data":
            st.subheader("📋 Extracted Activity Data")
            st.dataframe(df, use_container_width=True)

        # ======================
        # 🔁 VIEW REPEATED ACTIVITIES
        # ======================
        elif page == "🔁 View Repeated Activities":
            st.subheader("🔁 Repeated Activities Comparison by Construction Phase")
            dup_ids = df["Activity ID"][df["Activity ID"].duplicated(keep=False)]
            repeated_df = df[df["Activity ID"].isin(dup_ids)]

            if not repeated_df.empty:
                repeated_df["Phase"] = repeated_df["Activity Name"].apply(categorize_activity)
                repeated_df = repeated_df.sort_values(by=["Phase", "Activity ID", "Project Code", "Start Date"])
                phase_grouped = repeated_df.groupby(["Phase", "Activity ID", "Activity Name"])

                for (phase, act_id, act_name), group in phase_grouped:
                    st.markdown(f"### {phase}")
                    with st.expander(f"🔁 {act_id} — {act_name}"):
                        display_df = group.copy().reset_index(drop=True)

                        def highlight_diff(df_block):
                            styles = []
                            for col in ["Duration", "Start Date", "Finish Date", "Float"]:
                                unique_vals = df_block[col].nunique()
                                if unique_vals > 1:
                                    styles.append(f'background-color: #ffe6e6')  # Light red
                                else:
                                    styles.append('')
                            return pd.DataFrame([styles] * len(df_block), columns=["Duration", "Start Date", "Finish Date", "Float"])

                        styled = display_df[[
                            "Project Code", "Project Name", "Duration",
                            "Start Date", "Finish Date", "Float", "Notes"
                        ]].style.apply(highlight_diff, axis=0, subset=["Duration", "Start Date", "Finish Date", "Float"])
                        st.dataframe(styled, use_container_width=True)
            else:
                st.info("✅ No repeated activities found across files.")

        # ======================
        # 📤 UPLOAD SUMMARY
        # ======================
        elif page == "📤 Upload Summary":
            if total_skipped:
                st.subheader("📤 Upload Summary (Skipped Lines)")
                st.warning(f"⚠️ Skipped {len(total_skipped)} line(s) due to format issues.")
                skipped_df = pd.DataFrame(total_skipped)
                skipped_csv_path = os.path.join(tempfile.gettempdir(), "skipped_lines.csv")
                skipped_df.to_csv(skipped_csv_path, index=False)
                st.download_button(
                    "⬇️ Download Skipped Lines CSV",
                    data=open(skipped_csv_path, "rb"),
                    file_name="skipped_lines.csv",
                    mime="text/csv"
                )
            else:
                st.success("✅ No skipped lines! All activities were parsed successfully.")

        # ======================
        # 📤 Upload to Google Drive (always show at bottom)
        # ======================
        st.markdown("---")
        with st.expander("📤 Upload Extracted Data to Google Drive"):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp_csv:
                df.to_csv(tmp_csv.name, index=False)
                csv_path = tmp_csv.name

            if st.button("📤 Upload Combined Table to Google Drive"):
                try:
                    file_id = upload_csv_to_drive(csv_path, "combined_activity_data.csv", folder_id=DRIVE_FOLDER_ID)
                    st.success(f"✅ Uploaded! [View File](https://drive.google.com/file/d/{file_id})")
                except Exception as e:
                    st.error(f"❌ Upload failed: {str(e)}")
    else:
        st.warning("⚠️ No valid activity data found in uploaded files.")
else:
    st.info("📂 Upload one or more PDF files to begin.")
