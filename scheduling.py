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
import requests

# ======================
# Google Drive Setup
# ======================
SCOPES = ['https://www.googleapis.com/auth/drive.file']
CREDENTIALS_FILE = 'credentials.json'
TOKEN_PICKLE = 'token.pickle'
DRIVE_FOLDER_ID = 'YOUR_GOOGLE_DRIVE_FOLDER_ID'  # Replace with your folder ID

API_KEY = "3f5a9ae8a3c7d5c8438e0f4cf4b0b610"  # OpenWeatherMap API Key

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

def get_weather_forecast(location):
    url = f"http://api.openweathermap.org/data/2.5/forecast?q={location}&appid={API_KEY}&units=metric"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        st.error("Failed to fetch weather data. Check location or API key.")
        return None

def is_weather_delay(date, forecast_data, rain_threshold=1):
    # date is a datetime.date or pd.Timestamp object
    for item in forecast_data['list']:
        forecast_date = datetime.strptime(item['dt_txt'], "%Y-%m-%d %H:%M:%S").date()
        if forecast_date == date.date():
            rain = item.get('rain', {}).get('3h', 0)
            if rain > rain_threshold:
                return True
    return False

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

        df = df.dropna(subset=["Start Date", "Finish Date"])

        np.random.seed(42)
        df["% Complete"] = np.random.randint(30, 100, size=len(df))

        df = df.sort_values(by=["Project Code", "Start Date"])
        df["Prev Finish"] = df.groupby("Project Code")["Finish Date"].shift(1)
        df["Out of Sequence"] = df["Start Date"] < df["Prev Finish"]

        # Prepare repeated activities DataFrame
        dup_ids = df["Activity ID"][df["Activity ID"].duplicated(keep=False)]
        repeated_df = df[df["Activity ID"].isin(dup_ids)]
        if not repeated_df.empty:
            repeated_df["Phase"] = repeated_df["Activity Name"].apply(categorize_activity)
            repeated_df = repeated_df.sort_values(by=["Phase", "Activity ID", "Project Code", "Start Date"])

        # Tabs for navigation
        tabs = st.tabs([
            "📋 Extracted Data",
            "🔁 Repeated Activities",
            "📅 Timeline & Insights",
            "📤 Upload Summary",
            "📄 Reports & Upload"
        ])

        # Tab 1: Extracted Data Table
        with tabs[0]:
            st.header("📋 Extracted Data Table")
            st.dataframe(df, use_container_width=True)

        # Tab 2: Repeated Activities
        with tabs[1]:
            st.header("🔁 Repeated Activities Comparison")
            if not repeated_df.empty:
                phase_grouped = repeated_df.groupby(["Phase", "Activity ID", "Activity Name"])
                current_phase = None
                for (phase, act_id, act_name), group in phase_grouped:
                    if current_phase != phase:
                        st.markdown(f"### {phase}")
                        current_phase = phase
                    with st.expander(f"🔁 {act_id} — {act_name}"):
                        display_df = group[[
                            "Project Code", "Project Name", "Duration",
                            "Start Date", "Finish Date", "Float", "Notes"
                        ]].reset_index(drop=True)
                        st.dataframe(display_df, use_container_width=True)
            else:
                st.info("✅ No repeated activities found.")

        # Tab 3: Timeline & Insights (with Weather Integration)
        with tabs[2]:
            st.header("📅 Activity Timeline & Summary Insights")

            col1, col2, col3 = st.columns(3)
            col1.metric("🗂 Total Activities", len(df))
            col2.metric("📁 Projects", df["Project Code"].nunique())
            col3.metric("🚨 Zero Float Tasks", len(df[df["Float"] == 0]))

            selected_project = st.selectbox("Select a project to view timeline", sorted(df["Project Name"].unique()))
            project_df = df[df["Project Name"] == selected_project].sort_values(by="Start Date")

            # New input for location
            project_location = st.text_input("Enter project location (city name) for weather forecast")

            forecast_data = None
            if project_location:
                forecast_data = get_weather_forecast(project_location)
                if forecast_data:
                    st.subheader(f"🌦 5-Day Weather Forecast for {project_location}")
                    for item in forecast_data['list'][:10]:
                        dt_txt = item['dt_txt']
                        desc = item['weather'][0]['description']
                        rain = item.get('rain', {}).get('3h', 0)
                        st.write(f"{dt_txt}: {desc.capitalize()}, Rain (last 3h): {rain} mm")

            if not project_df.empty:
                if forecast_data:
                    project_df['Weather Delay Risk'] = project_df['Start Date'].apply(lambda d: is_weather_delay(d, forecast_data))
                else:
                    project_df['Weather Delay Risk'] = False

                gantt_chart = alt.Chart(project_df).mark_bar().encode(
                    x='Start Date:T',
                    x2='Finish Date:T',
                    y=alt.Y('Activity Name:N', sort='-x'),
                    color=alt.Color('Float:Q', scale=alt.Scale(scheme='blues')),
                    tooltip=[
                        'Activity ID', 'Activity Name', 'Duration',
                        'Start Date', 'Finish Date', 'Float', 'Weather Delay Risk'
                    ]
                ).properties(
                    height=400,
                    width=800,
                    title=f"Gantt Chart for {selected_project}"
                )
                st.altair_chart(gantt_chart, use_container_width=True)

                st.subheader("🚨 Critical Tasks with Low Float")
                float_threshold = st.slider("Set max float days to flag", min_value=0, max_value=30, value=2)
                critical_df = project_df[project_df["Float"] <= float_threshold].sort_values(by="Float")
                if not critical_df.empty:
                    st.warning(f"⚠️ {len(critical_df)} task(s) have float ≤ {float_threshold} days.")
                    st.dataframe(critical_df[[
                        "Project Code", "Project Name", "Activity ID", "Activity Name",
                        "Duration", "Start Date", "Finish Date", "Float", "Notes", "Weather Delay Risk"
                    ]].style.apply(
                        lambda x: ['background-color: yellow' if v else '' for v in x['Weather Delay Risk']], axis=1
                    ), use_container_width=True)
                else:
                    st.success("✅ No critical tasks found with the selected float threshold.")

                st.subheader("🚦 Out of Sequence Activities")
                out_seq_df = project_df[project_df["Out of Sequence"]]
                if not out_seq_df.empty:
                    st.error(f"❗ Found {len(out_seq_df)} out-of-sequence activities.")
                    st.dataframe(out_seq_df[[
                        "Project Code", "Project Name", "Activity ID", "Activity Name",
                        "Duration", "Start Date", "Finish Date", "Float", "Notes", "Weather Delay Risk"
                    ]], use_container_width=True)
                else:
                    st.success("✅ No out-of-sequence activities detected.")

        # Tab 4: Upload Summary
        with tabs[3]:
            st.header("📤 Upload Summary to Google Drive")
            if st.button("Upload extracted CSV to Google Drive"):
                with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as temp_csv:
                    df.to_csv(temp_csv.name, index=False)
                    file_id = upload_csv_to_drive(temp_csv.name, f"Extracted_Activities_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv", DRIVE_FOLDER_ID)
                    st.success(f"✅ CSV uploaded successfully! File ID: {file_id}")

            if total_skipped:
                st.warning(f"⚠️ Some lines could not be parsed ({len(total_skipped)}):")
                st.dataframe(pd.DataFrame(total_skipped), use_container_width=True)

        # Tab 5: Reports & Upload
        with tabs[4]:
            st.header("📄 Generate Reports and Upload")

            selected_project_report = st.selectbox("Select project for report", sorted(df["Project Name"].unique()))

            # Filter critical tasks for report
            critical_df_report = df[(df["Project Name"] == selected_project_report) & (df["Float"] <= 2)]

            # Generate gantt chart image (saving chart as PNG requires altair_saver or similar; simplified here)
            gantt_chart_report = alt.Chart(df[df["Project Name"] == selected_project_report]).mark_bar().encode(
                x='Start Date:T',
                x2='Finish Date:T',
                y=alt.Y('Activity Name:N', sort='-x'),
                color='Float:Q',
                tooltip=['Activity Name', 'Start Date', 'Finish Date', 'Float']
            ).properties(width=500, height=300)

            st.altair_chart(gantt_chart_report, use_container_width=True)

            if st.button("Generate and Upload PDF Report"):
                pdf_path = create_pdf_report(df[df["Project Name"] == selected_project_report], critical_df_report, selected_project_report)
                st.success(f"✅ PDF report generated: {pdf_path}")

                uploaded_pdf_id = upload_csv_to_drive(pdf_path, f"Activity_Report_{selected_project_report}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf", DRIVE_FOLDER_ID)
                st.success(f"📤 PDF uploaded to Google Drive! File ID: {uploaded_pdf_id}")

else:
    st.info("Upload one or more PDFs to begin extraction.")
