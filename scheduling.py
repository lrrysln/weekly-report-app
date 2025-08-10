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

# ... [your other functions unchanged: authenticate_google_drive, upload_csv_to_drive, create_pdf_report, categorize_activity, get_weather_forecast, is_weather_delay, render_weather_forecast]

st.set_page_config(page_title="Multi-PDF Activity Extractor", layout="wide")
st.title("📄 Multi-PDF Activity Extractor & Google Drive Uploader")

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

        dup_ids = df["Activity ID"][df["Activity ID"].duplicated(keep=False)].unique()
        st.write(f"Duplicate Activity IDs found: {len(dup_ids)}")

        repeated_df = df[df["Activity ID"].isin(dup_ids)].copy()
        if not repeated_df.empty:
            repeated_df["Phase"] = repeated_df["Activity Name"].apply(categorize_activity)
            repeated_df.sort_values(by=["Phase", "Activity ID", "Project Code", "Start Date"], inplace=True)

        tabs = st.tabs([
            "📋 Extracted Data", "🔁 Repeated Activities", "📅 Timeline & Insights",
            "📤 Upload Summary", "📄 Reports & Upload"
        ])

        # Tab 1: Extracted data
        with tabs[0]:
            st.header("📋 Extracted Data Table")
            st.dataframe(df, use_container_width=True)

        # Tab 2: Repeated activities with project filter
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

        # Tab 3: Timeline & weather
        with tabs[2]:
            # ... your existing Tab 3 code unchanged ...

        # Tab 4: Upload extracted CSV data to Google Drive
        with tabs[3]:
            # ... your existing Tab 4 code unchanged ...

        # Tab 5: Reports and Upload
        with tabs[4]:
            # ... your existing Tab 5 code unchanged ...
