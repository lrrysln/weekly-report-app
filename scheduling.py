import streamlit as st
import pdfplumber
import pandas as pd
import re
import os
import tempfile
import pickle
import numpy as np
from datetime import datetime, timedelta
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
    """Authenticate with Google Drive using OAuth credentials."""
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
    """Upload a CSV file to Google Drive in the specified folder."""
    service = authenticate_google_drive()
    file_metadata = {'name': file_name, 'mimeType': 'text/csv'}
    if folder_id:
        file_metadata['parents'] = [folder_id]
    media = MediaFileUpload(csv_path, mimetype='text/csv')
    file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    return file.get('id')

# ======================
# PDF Report Generation
# ======================
def create_pdf_report(df, critical_df, selected_project, gantt_chart_img_path=None):
    """Create a PDF report summarizing project activities and critical tasks."""
    output_path = os.path.join(tempfile.gettempdir(),
                               f"Activity_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")
    c = canvas.Canvas(output_path, pagesize=letter)
    width, height = letter
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height - 50, "📄 Project Activity Summary Report")
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
    for m in metrics:
        c.drawString(60, y, m)
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
    for _, row in critical_df.head(10).iterrows():
        if y < 50:
            c.showPage()
            y = height - 50
        c.drawString(50, y,
                     f"{row['Activity ID']} - {row['Activity Name']}, Float: {row['Float']}, Project: {row['Project Name']}")
        y -= 10
    c.save()
    return output_path

# ======================
# Activity Categorization
# ======================
def categorize_activity(name):
    """Categorize an activity based on keywords in its name."""
    name = name.lower()
    categories = {
        "🏗 Site Work & Earthwork": ["clear", "grade", "trench", "backfill", "earthwork", "site"],
        "🧱 Foundation & Structural": ["foundation", "slab", "footing", "structural"],
        "⚙️ Fuel System Installation": ["tank", "dispenser", "piping", "fuel", "gas"],
        "🛠️ Building Construction": ["building", "framing", "roof", "wall", "interior"],
        "🌿 Landscaping & Finishing": ["landscape", "sidewalk", "curb", "paving", "striping"],
        "📋 Final Inspection & Handover": ["inspection", "punchlist", "handover", "final"]
    }
    for label, words in categories.items():
        if any(w in name for w in words):
            return label
    return "❓ Uncategorized"

# ======================
# Weather API Integration
# ======================
def get_weather_forecast(location):
    """Fetch 7-day weather forecast data for a location from OpenWeatherMap."""
    url = f"http://api.openweathermap.org/data/2.5/forecast?q={location}&appid={API_KEY}&units=metric"
    resp = requests.get(url)
    if resp.status_code == 200:
        return resp.json()
    st.error("Failed to fetch weather data. Check location or API key.")
    return None

def is_weather_delay(date, forecast_data, rain_threshold=1):
    """Determine if weather delays are expected on a given date based on rain threshold."""
    for item in forecast_data.get('list', []):
        if datetime.strptime(item['dt_txt'], "%Y-%m-%d %H:%M:%S").date() == date.date():
            if item.get('rain', {}).get('3h', 0) > rain_threshold:
                return True
    return False

# ======================
# Weather Forecast Rendering (with improved dark mode visibility)
# ======================
def render_weather_forecast(forecast_data, days=7):
    """
    Render 7-day weather forecast as HTML blocks with icons and color alerts.
    Weather descriptions use a light color (#ccc) for better visibility on dark mode.
    """
    alerts = []
    today = datetime.utcnow().date()
    future_days = [today + timedelta(days=i) for i in range(days)]

    # Group forecasts by date
    daily_forecast = {str(day): [] for day in future_days}
    for entry in forecast_data.get('list', []):
        date_str = entry['dt_txt'].split()[0]
        if datetime.strptime(date_str, '%Y-%m-%d').date() in future_days:
            daily_forecast[date_str].append(entry)

    html_blocks = []
    for date, entries in daily_forecast.items():
        if not entries:
            continue

        temps = [e['main']['temp'] for e in entries]
        weather_descs = [e['weather'][0]['description'] for e in entries]
        icons = []
        color = "black"
        bold = False

        if any("rain" in desc for desc in weather_descs):
            icons.append("🌧")
            alerts.append(f"🌧 Rain expected on {date}")
        if any("snow" in desc for desc in weather_descs):
            icons.append("❄️")
            alerts.append(f"❄️ Snow expected on {date}")

        max_temp = max(temps)
        min_temp = min(temps)

        if max_temp >= 35:
            bold = True
            color = "red"
            alerts.append(f"🔥 Extreme heat expected on {date} (up to {max_temp}°C)")
        elif min_temp <= -5:
            bold = True
            color = "blue"
            alerts.append(f"🧊 Extreme cold expected on {date} (low of {min_temp}°C)")

        font_style = f"color:{color}; font-weight:{'bold' if bold else 'normal'}"

        # NOTE: Here we add inline style color:#ccc for weather description for visibility on dark mode
        html_blocks.append(f"""
            <div style="padding:5px 10px; margin:5px; border:1px solid #ccc; border-radius:5px;">
                <div><strong>{date}</strong> — <span style="{font_style}">{', '.join(set(weather_descs))}</span> {''.join(set(icons))}</div>
                <div style="font-size: 0.9em;">
                    Temp: {min_temp:.1f}°C to {max_temp:.1f}°C<br>
                    <span style="color:#ccc;">{', '.join(set(weather_descs))}</span>
                </div>
            </div>
        """)

    return html_blocks, alerts

# ======================
# Streamlit App UI
# ======================
st.set_page_config(page_title="Multi-PDF Activity Extractor", layout="wide")
st.title("📄 Multi-PDF Activity Extractor & Google Drive Uploader")

# File uploader: multiple PDF files allowed
uploaded_files = st.file_uploader("Upload one or more PDF files", type="pdf", accept_multiple_files=True)

if uploaded_files:
    all_data, total_skipped = [], []
    # Loop over each uploaded PDF
    for uploaded_file in uploaded_files:
        pdf_name = os.path.splitext(uploaded_file.name)[0]
        st.info(f"📄 Processing: `{uploaded_file.name}`")
        title_parts = pdf_name.split(" - ")
        project_code = title_parts[0].strip() if title_parts else "Unknown"
        project_name = title_parts[1].strip().title() if len(title_parts) > 1 else "Unknown Project"
        text = ""
        with pdfplumber.open(uploaded_file) as pdf:
            for page in pdf.pages:
                txt = page.extract_text()
                if txt:
                    text += txt + "\n"
        # Regex pattern to parse activity lines from the PDF text
        pattern = re.compile(r"^(\S+)\s+(.+?)\s+(\d+)\s+(\d{2}-\d{2}-\d{2})\s+(\d{2}-\d{2}-\d{2})\s+(\d+)\s+(.*)$")
        for line in text.strip().split('\n'):
            m = pattern.match(line.strip())
            if m:
                all_data.append({
                    "Project Code": project_code,
                    "Project Name": project_name,
                    "Activity ID": m.group(1),
                    "Activity Name": m.group(2),
                    "Duration": int(m.group(3)),
                    "Start Date": m.group(4),
                    "Finish Date": m.group(5),
                    "Float": int(m.group(6)),
                    "Notes": m.group(7)
                })
            else:
                total_skipped.append({"PDF": uploaded_file.name, "Line": line})

    if all_data:
        # Create dataframe and preprocess dates and flags
        df = pd.DataFrame(all_data)
        df["Start Date"] = pd.to_datetime(df["Start Date"], format="%m-%d-%y", errors="coerce")
        df["Finish Date"] = pd.to_datetime(df["Finish Date"], format="%m-%d-%y", errors="coerce")
        invalid = df[df["Start Date"].isna() | df["Finish Date"].isna()]
        if not invalid.empty:
            st.warning(f"⚠️ {len(invalid)} rows with invalid date format detected:")
            st.dataframe(invalid)
        df.dropna(subset=["Start Date", "Finish Date"], inplace=True)
        np.random.seed(42)
        df["% Complete"] = np.random.randint(30, 100, size=len(df))
        df.sort_values(by=["Project Code", "Start Date"], inplace=True)
        df["Prev Finish"] = df.groupby("Project Code")["Finish Date"].shift(1)
        df["Out of Sequence"] = df["Start Date"] < df["Prev Finish"]

        # Detect repeated activity IDs
        dup = df["Activity ID"][df["Activity ID"].duplicated(keep=False)]
        repeated_df = df[df["Activity ID"].isin(dup)]
        if not repeated_df.empty:
            repeated_df["Phase"] = repeated_df["Activity Name"].apply(categorize_activity)
            repeated_df.sort_values(by=["Phase", "Activity ID", "Project Code", "Start Date"], inplace=True)

        # Create app tabs
        tabs = st.tabs([
            "📋 Extracted Data", "🔁 Repeated Activities", "📅 Timeline & Insights",
            "📤 Upload Summary", "📄 Reports & Upload"
        ])

        # Tab 1: Raw extracted data
        with tabs[0]:
            st.header("📋 Extracted Data Table")
            st.dataframe(df, use_container_width=True)

        # Tab 2: Repeated activities
        with tabs[1]:
            st.header("🔁 Repeated Activities")
            if not repeated_df.empty:
                for (phase, act_id, act_name), group in repeated_df.groupby(["Phase", "Activity ID", "Activity Name"]):
                    st.markdown(f"### {phase}" if phase else "")
                    with st.expander(f"{act_id} — {act_name}"):
                        st.dataframe(group[[
                            "Project Code", "Project Name", "Duration", "Start Date", "Finish Date", "Float", "Notes"
                        ]].reset_index(drop=True), use_container_width=True)
            else:
                st.info("✅ No repeated activities found.")

        # Tab 3: Timeline, weather forecast, and insights
        with tabs[2]:
            st.header("📅 Activity Timeline & Summary Insights")

            col1, col2, col3 = st.columns(3)
            col1.metric("🗂 Total Activities", len(df))
            col2.metric("📁 Projects", df["Project Code"].nunique())
            col3.metric("🚨 Zero Float Tasks", len(df[df["Float"] == 0]))

            project = st.selectbox("Select a project", sorted(df["Project Name"].unique()))
            project_df = df[df["Project Name"] == project].sort_values(by="Start Date")

            # Weather forecast input and display
            loc = st.text_input("Enter project location (city name) for 7-day weather forecast")
            forecast_data = get_weather_forecast(loc) if loc else None

            if forecast_data:
                st.subheader(f"🌦 7-Day Weather Forecast for {loc}")
                html_blocks, alerts = render_weather_forecast(forecast_data)

                # Inject CSS style for weather-description class (optional)
                st.markdown("""
                <style>
                    .weather-description {
                        color: #ccc;
                    }
                </style>
                """, unsafe_allow_html=True)

                for block in html_blocks:
                    st.markdown(block, unsafe_allow_html=True)

                if alerts:
                    st.error("🚨 Upcoming Weather Alerts:")
                    for alert in alerts:
                        st.markdown(f"- {alert}")
                else:
                    st.success("✅ No severe weather expected.")

            if not project_df.empty:
                # Flag weather delay risk per activity start date
                project_df["Weather Delay Risk"] = project_df["Start Date"].apply(
                    lambda d: is_weather_delay(d, forecast_data)) if forecast_data else False

                # Render Gantt chart with Altair
                gantt = alt.Chart(project_df).mark_bar().encode(
                    x='Start Date:T', x2='Finish Date:T',
                    y=alt.Y('Activity Name:N', sort='-x'),
                    color=alt.Color('Float:Q', scale=alt.Scale(scheme='blues')),
                    tooltip=['Activity ID', 'Activity Name', 'Start Date', 'Finish Date', 'Float', 'Weather Delay Risk']
                ).properties(width=900, height=400, title=f"Gantt – {project}")
                st.altair_chart(gantt, use_container_width=True)

                # Float threshold slider to highlight critical tasks
                float_threshold = st.slider("Highlight tasks with float ≤", 0, 20, 5)
                critical_df = project_df[project_df["Float"] <= float_threshold]

                if not critical_df.empty:
                    st.warning(f"⚠️ {len(critical_df)} task(s) have float ≤ {float_threshold} days.")

                    def highlight_weather_delay(row):
                        return ['background-color: yellow'] * len(row) if row["Weather Delay Risk"] else [''] * len(row)

                    st.dataframe(
                        critical_df[[
                            "Project Code", "Project Name", "Activity ID",
                            "Activity Name", "Duration", "Start Date", "Finish Date",
                            "Float", "Notes", "Weather Delay Risk"
                        ]].style.apply(highlight_weather_delay, axis=1),
                        use_container_width=True
                    )
                else:
                    st.success("✅ No critical tasks found with the selected float threshold.")

        # Tab 4: Upload extracted CSV data to Google Drive
        with tabs[3]:
            st.header("📤 Upload Extracted Data")
            temp_csv = os.path.join(tempfile.gettempdir(), f"Activity_Data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
            df.to_csv(temp_csv, index=False)
            st.download_button("⬇️ Download CSV", data=open(temp_csv, "rb").read(),
                               file_name=os.path.basename(temp_csv), mime="text/csv")
            if st.button("Upload CSV to Google Drive"):
                try:
                    fid = upload_csv_to_drive(temp_csv, os.path.basename(temp_csv), folder_id=DRIVE_FOLDER_ID)
                    st.success(f"Uploaded successfully! File ID:
