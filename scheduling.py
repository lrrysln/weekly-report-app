import streamlit as st
import pdfplumber
import pandas as pd
import re
import os
import tempfile
import pickle
import numpy as np
from datetime import datetime
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import altair as alt
from altair_saver import save as altair_save
import altair as alt
from altair_saver import save as altair_save

# ======================
# Google Drive Setup
# ======================
SCOPES = ['https://www.googleapis.com/auth/drive.file']
CREDENTIALS_FILE = 'credentials.json'
TOKEN_PICKLE = 'token.pickle'
DRIVE_FOLDER_ID = 'YOUR_GOOGLE_DRIVE_FOLDER_ID'  # Replace with your actual folder ID

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


def create_pdf_report(df, critical_df, selected_project, gantt_chart_img_path=None):
    output_path = os.path.join(tempfile.gettempdir(), f"Activity_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")
    c = canvas.Canvas(output_path, pagesize=letter)
    width, height = letter

    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height - 50, f"📄 Project Activity Summary Report")
    c.setFont("Helvetica", 10)
    c.drawString(50, height - 70, f"Project: {selected_project}")
    c.drawString(50, height - 85, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    y = height - 110
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "📊 Key Metrics:")
    y -= 15
    c.setFont("Helvetica", 10)
    metrics = [
        f"🗂 Total Activities: {len(df)}",
        f"📁 Projects: {df['Project Code'].nunique()}",
        f"🚨 Zero Float Tasks: {len(df[df['Float'] == 0])}"
    ]
    for metric in metrics:
        c.drawString(60, y, metric)
        y -= 12

    if gantt_chart_img_path and os.path.exists(gantt_chart_img_path):
        y -= 20
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, y, "📅 Gantt Chart:")
        y -= 300
        c.drawImage(gantt_chart_img_path, 50, y, width=500, height=250)
        y -= 20

    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "🚨 Critical Tasks:")
    y -= 15
    c.setFont("Helvetica", 8)

    for idx, row in critical_df.head(10).iterrows():
        if y < 50:
            c.showPage()
            y = height - 50
        c.drawString(50, y, f"{row['Activity ID']} - {row['Activity Name']}, Float: {row['Float']}, Project: {row['Project Name']}")
        y -= 10

    c.save()
    return output_path


# ======================
# Streamlit App
# ======================
st.set_page_config(page_title="Multi-PDF Activity Extractor", layout="wide")
st.title("📄 Multi-PDF Activity Extractor & Google Drive Uploader")

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

        pattern = re.compile(
            r"^(\S+)\s+(.+?)\s+(\d+)\s+(\d{2}-\d{2}-\d{2})\s+(\d{2}-\d{2}-\d{2})\s+(\d+)\s+(.*)$"
        )
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

        # Convert date columns
        df["Start Date"] = pd.to_datetime(df["Start Date"], format="%m-%d-%y", errors="coerce")
        df["Finish Date"] = pd.to_datetime(df["Finish Date"], format="%m-%d-%y", errors="coerce")

        invalid_dates = df[df["Start Date"].isna() | df["Finish Date"].isna()]
        if not invalid_dates.empty:
            st.warning(f"⚠️ Found {len(invalid_dates)} rows with invalid date format:")
            st.dataframe(invalid_dates)

        # Optionally drop those rows so they don’t break downstream logic
        df = df.dropna(subset=["Start Date", "Finish Date"])

        # Simulate % complete
        np.random.seed(42)
        df["% Complete"] = np.random.randint(30, 100, size=len(df))

        # Detect out-of-sequence activities
        df = df.sort_values(by=["Project Code", "Start Date"])
        df["Prev Finish"] = df.groupby("Project Code")["Finish Date"].shift(1)
        df["Out of Sequence"] = df["Start Date"] < df["Prev Finish"]

        st.header("🔍 Step 2: Summary Insights")

        col1, col2, col3 = st.columns(3)
        col1.metric("🗂 Total Activities", len(df))
        col2.metric("📁 Projects", df["Project Code"].nunique())
        col3.metric("🚨 Zero Float Tasks", len(df[df["Float"] == 0]))

        # 📅 Gantt Chart
        st.subheader("📅 Activity Timeline by Project")
        selected_project = st.selectbox("Select a project to view timeline", sorted(df["Project Name"].unique()))
        project_df = df[df["Project Name"] == selected_project].sort_values(by="Start Date")

        if not project_df.empty:
            gantt_chart = alt.Chart(project_df).mark_bar().encode(
                x='Start Date:T',
                x2='Finish Date:T',
                y=alt.Y('Activity Name:N', sort='-x'),
                color=alt.Color('Float:Q', scale=alt.Scale(scheme='blues')),
                tooltip=[
                    'Activity ID', 'Activity Name', 'Duration',
                    'Start Date', 'Finish Date', 'Float'
                ]
            ).properties(
                height=400,
                width=800,
                title=f"Gantt Chart for {selected_project}"
            )
            st.altair_chart(gantt_chart, use_container_width=True)
            
            # Save Gantt chart
            # Save as HTML
            gantt_path = os.path.join(tempfile.gettempdir(), "gantt_chart.html")
            gantt_chart.save(gantt_path)

        # 🚨 Critical Tasks
        st.subheader("🚨 Critical Tasks with Zero or Low Float")
        float_threshold = st.slider("Set max float days to flag", min_value=0, max_value=30, value=2)
        critical_df = df[df["Float"] <= float_threshold].sort_values(by="Float")
        if not critical_df.empty:
            st.warning(f"⚠️ {len(critical_df)} task(s) have float ≤ {float_threshold} days.")
            st.dataframe(critical_df[[
                "Project Code", "Project Name", "Activity ID", "Activity Name",
                "Duration", "Start Date", "Finish Date", "Float", "Notes"
            ]], use_container_width=True)
        else:
            st.success("✅ No critical tasks found.")

        # 🔀 Out-of-sequence
        violations = df[df["Out of Sequence"] == True]
        if not violations.empty:
            st.subheader("🔀 Out-of-Sequence Activities")
            st.dataframe(violations[[
                "Project Code", "Activity ID", "Activity Name", "Start Date", "Prev Finish"
            ]], use_container_width=True)

        # PDF report
        if st.button("📄 Generate PDF Report"):
            try:
                pdf_path = create_pdf_report(df, critical_df, selected_project, gantt_chart_img_path=gantt_path)
                with open(pdf_path, "rb") as f:
                    st.download_button("⬇️ Download PDF Report", f, file_name="Activity_Report.pdf", mime="application/pdf")
            except Exception as e:
                st.error(f"Error generating PDF: {e}")

        # Upload to Google Drive
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
        st.warning("⚠️ No valid activity data found.")
else:
    st.info("📂 Upload one or more PDF files to begin.")



