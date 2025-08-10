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
from scipy.stats import zscore, pearsonr
import random

# ======================
# Google Drive Setup
# ======================
SCOPES = ['https://www.googleapis.com/auth/drive.file']
CREDENTIALS_FILE = 'credentials.json'
TOKEN_PICKLE = 'token.pickle'
DRIVE_FOLDER_ID = 'YOUR_GOOGLE_DRIVE_FOLDER_ID'  # Use your actual folder ID here
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

    # Add advanced KPIs to report
    c.drawString(60, y, f"🗂 Total Activities: {len(df)}")
    y -= 12
    c.drawString(60, y, f"📁 Projects: {df['Project Code'].nunique()}")
    y -= 12
    c.drawString(60, y, f"🚨 Zero Float Tasks: {len(df[df['Float'] == 0])}")
    y -= 12

    # Advanced KPI summaries
    c.drawString(60, y, f"🔍 Avg Cost Performance Index (CPI): {df['CPI'].mean():.2f}")
    y -= 12
    c.drawString(60, y, f"🔍 Avg Schedule Performance Index (SPI): {df['SPI'].mean():.2f}")
    y -= 20

    if gantt_chart_img_path and os.path.exists(gantt_chart_img_path):
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
    url = f"http://api.openweathermap.org/data/2.5/forecast?q={location}&appid={API_KEY}&units=metric"
    resp = requests.get(url)
    if resp.status_code == 200:
        return resp.json()
    st.error("Failed to fetch weather data. Check location or API key.")
    return None

def is_weather_delay(date, forecast_data, rain_threshold=1):
    if not forecast_data:
        return False
    for item in forecast_data.get('list', []):
        if datetime.strptime(item['dt_txt'], "%Y-%m-%d %H:%M:%S").date() == date.date():
            if item.get('rain', {}).get('3h', 0) > rain_threshold:
                return True
    return False

def render_weather_forecast(forecast_data, days=7):
    alerts = []
    today = datetime.utcnow().date()
    future_days = [today + timedelta(days=i) for i in range(days)]

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
# Advanced KPIs and Diagnostics
# ======================
def compute_ev_metrics(df):
    # Earned Value (EV) Metrics Calculations - simplified example

    # Planned Value (PV) = planned % complete * Budget At Completion (BAC)
    # Earned Value (EV) = actual % complete * BAC
    # Actual Cost (AC) = from input (simulate here)
    # CPI = EV / AC
    # SPI = EV / PV

    # For this example, we simulate BAC and AC
    BAC = 100000  # Total budget estimate (simulate)
    df = df.copy()
    df["BAC"] = BAC / len(df)  # evenly distribute budget per activity
    df["PV"] = df["% Complete"] / 100 * df["BAC"]  # Planned Value approx
    df["EV"] = df["% Complete"] / 100 * df["BAC"]  # Assume actual % complete equals planned for now

    # Simulate Actual Cost (AC) with noise: some tasks cost more or less
    np.random.seed(42)
    df["AC"] = df["BAC"] * np.random.normal(loc=1.0, scale=0.1, size=len(df))
    df["CPI"] = df["EV"] / df["AC"]  # Cost Performance Index
    df["SPI"] = df["EV"] / df["PV"]  # Schedule Performance Index

    # Clamp SPI to avoid division by zero
    df["SPI"].replace([np.inf, -np.inf], np.nan, inplace=True)
    df["SPI"].fillna(1, inplace=True)

    return df

def monte_carlo_schedule_simulation(df, simulations=1000):
    # Monte Carlo simulation of schedule risk based on task durations and float
    total_durations = []
    for _ in range(simulations):
        simulated_finish_dates = []
        for _, row in df.iterrows():
            # Simulate a delay within float +/- 50%
            delay = np.random.uniform(-0.5, 0.5) * row["Float"] if row["Float"] > 0 else 0
            duration = max(1, row["Duration"] + delay)
            simulated_finish_dates.append(duration)
        total_durations.append(sum(simulated_finish_dates))
    return np.percentile(total_durations, 90)  # 90th percentile finish duration

def identify_critical_path(df):
    # Simplified critical path: activities with zero float or minimal float
    critical_df = df[df["Float"] <= 0]
    return critical_df

def productivity_metrics(df):
    # Simulate labor hours per unit output from 'Duration'
    # Assuming Duration days and random labor hours per day
    np.random.seed(42)
    labor_hours_per_day = np.random.uniform(6, 10, size=len(df))
    df = df.copy()
    df["Labor Hours"] = df["Duration"] * labor_hours_per_day
    # Units output simulated from duration and labor hours (inverse relation)
    df["Units Output"] = df["Duration"] * np.random.uniform(0.8, 1.2, size=len(df))
    df["Labor Hours per Unit"] = df["Labor Hours"] / df["Units Output"]
    return df

def correlation_analysis(df):
    # Statistical test correlation between Float and Cost Overruns (simulated)
    # Cost Overrun: AC - EV
    df = df.copy()
    df["Cost Overrun"] = df["AC"] - df["EV"]
    corr, p_value = pearsonr(df["Float"], df["Cost Overrun"])
    return corr, p_value

# ======================
# Streamlit App UI
# ======================
st.set_page_config(page_title="Multi-PDF Activity Extractor with Advanced KPIs", layout="wide")
st.title("📄 Multi-PDF Activity Extractor & Google Drive Uploader with Advanced KPIs")

uploaded_files = st.file_uploader("Upload one or more PDF files", type="pdf", accept_multiple_files=True)

if uploaded_files:
    all_data, total_skipped = [], []
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
        df = pd.DataFrame(all_data)
        df["Activity ID"] = df["Activity ID"].astype(str).str.strip()

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

        # Compute advanced KPIs
        df = compute_ev_metrics(df)
        df = productivity_metrics(df)

        # Duplicate detection
        dup_ids = df["Activity ID"][df["Activity ID"].duplicated(keep=False)].unique()
        st.write(f"Duplicate Activity IDs found: {len(dup_ids)}")

        repeated_df = df[df["Activity ID"].isin(dup_ids)].copy()
        if not repeated_df.empty:
            repeated_df["Phase"] = repeated_df["Activity Name"].apply(categorize_activity)
            repeated_df.sort_values(by=["Phase", "Activity ID", "Project Code", "Start Date"], inplace=True)

        # Tabs
        tabs = st.tabs([
            "📋 Extracted Data", "🔁 Repeated Activities", "📅 Timeline & Insights",
            "📤 Upload Summary", "📄 Reports & Upload", "📊 Advanced KPIs & Diagnostics"
        ])

        # Tab 0: Extracted data
        with tabs[0]:
            st.header("📋 Extracted Data Table")
            st.dataframe(df, use_container_width=True)

        # Tab 1: Repeated activities with project filter dropdown
        with tabs[1]:
            st.header("🔁 Repeated Activities")
            if not repeated_df.empty:
                project_options = ["All Projects"] + sorted(repeated_df["Project Name"].unique())
                selected_project = st.selectbox("Filter by Project Name", project_options)

                if selected_project != "All Projects":
                    filtered_df = repeated_df[repeated_df["Project Name"] == selected_project]
                else:
                    filtered_df = repeated_df

                if filtered_df.empty:
                    st.info(f"✅ No repeated activities found for project: {selected_project}")
                else:
                    for phase, phase_group in filtered_df.groupby("Phase"):
                        st.markdown(f"### {phase}")
                        with st.expander(f"View repeated activities in {phase}"):
                            st.dataframe(phase_group[[
                                "Activity ID", "Activity Name", "Project Code", "Project Name",
                                "Duration", "Start Date", "Finish Date", "Float", "Notes"
                            ]].reset_index(drop=True), use_container_width=True)
            else:
                st.info("✅ No repeated activities found.")

        # Tab 2: Timeline & weather
        with tabs[2]:
            st.header("📅 Activity Timeline & Summary Insights")
            col1, col2, col3 = st.columns(3)
            col1.metric("🗂 Total Activities", len(df))
            col2.metric("📁 Projects", df["Project Code"].nunique())
            col3.metric("🚨 Zero Float Tasks", len(df[df["Float"] == 0]))

            project = st.selectbox("Select a project", sorted(df["Project Name"].unique()))
            project_df = df[df["Project Name"] == project].sort_values(by="Start Date")

            loc = st.text_input("Enter project location (city name) for 7-day weather forecast")
            forecast_data = get_weather_forecast(loc) if loc else None

            if forecast_data:
                st.subheader(f"🌦 7-Day Weather Forecast for {loc}")
                html_blocks, alerts = render_weather_forecast(forecast_data)

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
                project_df["Weather Delay Risk"] = project_df["Start Date"].apply(
                    lambda d: is_weather_delay(d, forecast_data)) if forecast_data else False

                gantt = alt.Chart(project_df).mark_bar().encode(
                    x='Start Date:T', x2='Finish Date:T',
                    y=alt.Y('Activity Name:N', sort='-x'),
                    color=alt.Color('Float:Q', scale=alt.Scale(scheme='blues')),
                    tooltip=['Activity ID', 'Activity Name', 'Start Date', 'Finish Date', 'Float', 'Weather Delay Risk']
                ).properties(width=900, height=400, title=f"Gantt – {project}")
                st.altair_chart(gantt, use_container_width=True)

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

        # Tab 3: Upload extracted CSV data to Google Drive
        with tabs[3]:
            st.header("📤 Upload Extracted Data")
            temp_csv = os.path.join(tempfile.gettempdir(), f"Activity_Data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
            df.to_csv(temp_csv, index=False)
            st.download_button("⬇️ Download CSV", data=open(temp_csv, "rb").read(),
                               file_name=os.path.basename(temp_csv), mime="text/csv")
            if st.button("Upload CSV to Google Drive"):
                try:
                    fid = upload_csv_to_drive(temp_csv, os.path.basename(temp_csv), folder_id=DRIVE_FOLDER_ID)
                    st.success(f"Uploaded successfully! File ID: {fid}")
                except Exception as e:
                    st.error(f"Upload failed: {e}")

        # Tab 4: Reports & Upload (PDF Report generation)
        with tabs[4]:
            st.header("📄 Reports & Upload")
            project_for_report = st.selectbox("Select project for PDF report", sorted(df["Project Name"].unique()))
            float_threshold = st.slider("Set float threshold for critical tasks", 0, 20, 5, key="pdf_float")
            if st.button("Generate PDF Report"):
                filtered = df[df["Project Name"] == project_for_report]
                critical_for_report = filtered[filtered["Float"] <= float_threshold]
                pdf_path = create_pdf_report(filtered, critical_for_report, project_for_report)
                with open(pdf_path, "rb") as f:
                    pdf_bytes = f.read()
                st.download_button("⬇️ Download PDF Report", data=pdf_bytes, file_name=os.path.basename(pdf_path))

        # Tab 5: Advanced KPIs and Root Cause Diagnostics
        with tabs[5]:
            st.header("📊 Advanced KPIs & Root Cause Diagnostics")
            project_diag = st.selectbox("Select project for diagnostics", sorted(df["Project Name"].unique()), key="diag_project")
            diag_df = df[df["Project Name"] == project_diag]

            if not diag_df.empty:
                st.subheader("Earned Value Management Metrics")
                st.dataframe(diag_df[["Activity ID", "Activity Name", "BAC", "PV", "EV", "AC", "CPI", "SPI"]], use_container_width=True)

                st.subheader("Monte Carlo Schedule Risk Simulation")
                simulation_runs = st.slider("Number of Monte Carlo Simulations", 100, 5000, 1000)
                p90_duration = monte_carlo_schedule_simulation(diag_df, simulations=simulation_runs)
                total_duration = diag_df["Duration"].sum()
                st.write(f"Estimated 90th percentile total project duration: {p90_duration:.1f} days (Base duration: {total_duration} days)")

                st.subheader("Critical Path and Bottlenecks")
                critical_path_df = identify_critical_path(diag_df)
                if not critical_path_df.empty:
                    st.write(f"Critical Path Tasks (zero or negative float): {len(critical_path_df)}")
                    st.dataframe(critical_path_df[["Activity ID", "Activity Name", "Duration", "Start Date", "Finish Date", "Float"]], use_container_width=True)
                else:
                    st.info("No critical path tasks detected.")

                st.subheader("Productivity Metrics")
                st.dataframe(diag_df[["Activity ID", "Activity Name", "Labor Hours", "Units Output", "Labor Hours per Unit"]], use_container_width=True)

                st.subheader("Correlation Analysis (Float vs Cost Overrun)")
                corr, p_value = correlation_analysis(diag_df)
                st.write(f"Pearson correlation coefficient: {corr:.3f}")
                st.write(f"P-value: {p_value:.3f}")
                if p_value < 0.05:
                    st.success("Significant correlation detected.")
                else:
                    st.info("No statistically significant correlation detected.")

        with tabs[6]:  # Assuming your current last tab is tabs[5], this will be the 7th tab
    st.header("📈 Executive Summary")

    # Load and process sample historical data exactly as in the provided code:
    hist_df = load_sample_data()
    hist_df = calculate_kpis(hist_df)
    hist_df = calculate_earned_value_metrics(hist_df)
    hist_df = calculate_productivity(hist_df)
    summary_df = project_summary(hist_df)
    summary_df = add_benchmarking_metrics(summary_df)
    delay_causes = delay_cause_analysis(hist_df)

    st.subheader("Summary Table")
    st.dataframe(summary_df)

    st.subheader("Recommendations")
    recs = generate_recommendations(summary_df)
    for r in recs:
        st.write(r)

    st.subheader("Narrative Executive Summary")
    st.write(generate_narrative(summary_df))

    st.subheader("Select Project for Gantt Chart")
    project_option = st.selectbox("Project:", summary_df['project_id'].unique(), key="exec_proj_select")
    gantt_img_buf = plot_gantt_chart(hist_df, project_option)
    st.image(gantt_img_buf)

    st.subheader("Delay Cause Analysis")
    if delay_causes.empty:
        st.write("No delays reported across projects.")
    else:
        delay_img_buf = plot_delay_causes(delay_causes)
        st.image(delay_img_buf)

    st.subheader("Cost Variance Waterfall Chart")
    waterfall_fig = plot_cost_variance_waterfall(summary_df)
    st.pyplot(waterfall_fig)

    st.subheader("Delay Causes Heatmap")
    heatmap_fig = plot_delay_heatmap(hist_df)
    st.pyplot(heatmap_fig)

    # Data validation checks
    issues = validate_data(hist_df)
    if issues:
        for issue in issues:
            st.warning(issue)
    else:
        st.success("Data validation passed")

    if st.button("📄 Generate PDF Analysis Report (Executive Summary)"):
        pdf_buffer = generate_pdf_report(hist_df, summary_df, delay_causes)
        st.download_button("⬇️ Download Analysis Report PDF", pdf_buffer, "construction_analysis_report.pdf", "application/pdf")
        

else:
    st.info("Please upload one or more PDF files to begin processing.")

