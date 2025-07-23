import streamlit as st
import pandas as pd
import datetime
import re
from pathlib import Path

# Paths
DOWNLOADS = Path.home() / "Downloads"

# Utility functions
def get_current_week_folder():
    today = datetime.datetime.now()
    week_num = today.isocalendar().week
    return DOWNLOADS / f"Week {week_num} {today.year}"

def get_weekly_filename():
    today = datetime.datetime.now()
    week_num = today.isocalendar().week
    return f"Week {week_num} {today.year} Report.html"

def save_to_excel(entry_data):
    week_folder = get_current_week_folder()
    week_folder.mkdir(parents=True, exist_ok=True)
    existing = list(week_folder.glob("file*.xlsx"))
    index = len(existing) + 1
    path = week_folder / f"file{index}.xlsx"
    pd.DataFrame([entry_data]).to_excel(path, index=False, engine="openpyxl")

def generate_weekly_summary(password):
    if password != "1234":
        return None, "\n❌ Incorrect password."
    week_folder = get_current_week_folder()
    if not week_folder.exists():
        return None, "⚠️ There have been no entries submitted this week."

    files = sorted(week_folder.glob("file*.xlsx"))
    if not files:
        return None, "⚠️ There have been no entries submitted this week."

    df = pd.concat((pd.read_excel(f, engine="openpyxl") for f in files), ignore_index=True)
    if df.empty:
        return None, "🚫 No data to summarize."

    df.sort_values("Subject", inplace=True)

    html = ["<html><head><style>",
            "body{font-family:Arial;padding:20px}",
            "h1{text-align:center}",
            "h2{background:#cce5ff;padding:10px;border-radius:4px}",
            ".entry{border:1px solid #ccc;padding:10px;margin:10px 0;border-radius:4px;background:#f9f9f9}",
            "ul{margin:0;padding-left:20px}",
            ".label{font-weight:bold}",
            "</style></head><body>",
            "<h1>Weekly Summary Report</h1>"]

    for subject, group in df.groupby("Subject"):
        html.append(f"<h2>{subject}</h2>")
        for _, row in group.iterrows():
            html.append('<div class="entry"><ul>')
            html.append(f"<li><span class='label'>Store Name:</span> {row.get('Store Name', '')}</li>")
            html.append(f"<li><span class='label'>Store Number:</span> {row.get('Store Number', '')}</li>")

            types = [col for col in
                     ["RaceWay EDO Stores", "RT EFC - Traditional", "RT 5.5k EDO Stores", "RT EFC EDO Stores",
                      "RT Travel Centers"] if row.get(col)]
            if types:
                html.append("<li><span class='label'>Types:</span><ul>")
                html += [f"<li>{t}</li>" for t in types]
                html.append("</ul></li>")

            html.append("<li><span class='label'>Dates:</span><ul>")
            for label in ["TCO Date", "Ops Walk Date", "Turnover Date", "Open to Train Date", "Store Opening"]:
                html.append(f"<li><span class='label'>{label}:</span> {row.get(label, '')}</li>")
            html.append("</ul></li>")

            notes = [
                re.sub(r"^[\s•\-–●]+", "", n)
                for n in str(row.get("Notes", "")).splitlines()
                if n.strip()
            ]
            if notes:
                html.append("<li><span class='label'>Notes:</span><ul>")
                html += [f"<li>{n}</li>" for n in notes]
                html.append("</ul></li>")

            html.append("</ul></div>")

    html.append("</body></html>")
    return df, "".join(html)

def save_html_report(html_content):
    week_folder = get_current_week_folder()
    week_folder.mkdir(parents=True, exist_ok=True)
    filename = get_weekly_filename()
    path = week_folder / filename
    with open(path, "w", encoding="utf-8") as f:
        f.write(html_content)
    return path

# Streamlit UI
st.title("📝 Weekly Store Report Form")

with st.form("entry_form"):
    st.subheader("Store Info")
    store_name = st.text_input("Store Name")
    store_number = st.text_input("Store Number")

    st.subheader("Project Details")
    subject = st.selectbox("Subject", [
        "New Construction", "EDO Additions", "Phase 1/ Demo - New Construction Sites",
        "Remodels", "6k Remodels", "EV Project", "Traditional Special Project",
        "Miscellaneous Items of Note", "Potential Projects",
        "Complete - Awaiting Post Completion Site Visit", "2025 Completed Projects"
    ])

    st.subheader("Store Types")
    types = {
        "RaceWay EDO Stores": st.checkbox("RaceWay EDO Stores"),
        "RT EFC - Traditional": st.checkbox("RT EFC - Traditional"),
        "RT 5.5k EDO Stores": st.checkbox("RT 5.5k EDO Stores"),
        "RT EFC EDO Stores": st.checkbox("RT EFC EDO Stores"),
        "RT Travel Centers": st.checkbox("RT Travel Centers")
    }

    st.subheader("Important Dates")
    tco_date = st.date_input("TCO Date")
    ops_walk_date = st.date_input("Ops Walk Date")
    turnover_date = st.date_input("Turnover Date")
    open_to_train_date = st.date_input("Open to Train Date")
    store_opening = st.date_input("Store Opening")

    notes = st.text_area("Notes (Use bullets or dashes)", value="• ", height=200)

    submitted = st.form_submit_button("Submit")
    if submitted:
        data = {
            "Store Name": store_name,
            "Store Number": store_number,
            "Subject": subject,
            "TCO Date": tco_date,
            "Ops Walk Date": ops_walk_date,
            "Turnover Date": turnover_date,
            "Open to Train Date": open_to_train_date,
            "Store Opening": store_opening,
            "Notes": notes
        }
        data.update(types)
        save_to_excel(data)
        st.success("✅ Entry saved successfully!")

st.subheader("🔐 Generate Weekly Report")
report_pw = st.text_input("Enter Password to Generate Report", type="password")
if st.button("Generate Report"):
    df, html = generate_weekly_summary(report_pw)
    if df is not None:
        path = save_html_report(html)
        st.success(f"✅ Report generated and saved to: {path}")
        st.download_button("Download Report", html, file_name=get_weekly_filename(), mime="text/html")
    else:
        st.error(html)

" and leave it the same aside from the following changes: update all date formats to be "MM/DD/YY", make sure that on the form in the notes section that there is a bullet point and when you click enter to go to a new line a new bullet point appears. use the below to help display the report on the screen after the password for the generate report is successfully compelted, in addition to the options to download. ensure that new reports start with no entries and the form is cleared when a form is submitted. use to help "import streamlit as st 
from datetime import datetime

# Page config
st.set_page_config(page_title="Weekly Construction Report", layout="centered")
st.title("Weekly Site Update Submission")

# Form Start
with st.form("weekly_report_form"):
    submitted_by = st.text_input("Your Name")
    project_name = st.text_input("Project Name")
    project_id = st.text_input("Project ID")
    update_date = st.date_input("Date of Update", format="MM/DD/YY")

    # Key Dates
    st.subheader("Key Construction Dates")
    permit_date = st.date_input("Permit Received")
    mobilization_date = st.date_input("Mobilization Start")
    concrete_date = st.date_input("Concrete Pour Date")
    tco_date = st.date_input("TCO Date")
    turnover_date = st.date_input("Turnover to Ops")

    # General Notes
    st.subheader("Weekly Notes")
    notes = st.text_area("Add bullet points for site progress, delays, weather, or issues:", placeholder="\n- Framing completed on main structure\n- Waiting on inspection scheduling\n- Rain delayed landscaping work")

    # File Uploads
    uploaded_files = st.file_uploader("Upload relevant documents (PDFs, Images, etc.)", type=None, accept_multiple_files=True)

    submitted = st.form_submit_button("Submit Report")

# Handle Submission
if submitted:
    if not submitted_by or not project_name or not project_id:
        st.warning("Please complete all required fields.")
    else:
        st.success(f"✅ Weekly report submitted for project: {project_name}")

        st.markdown("---")
        st.markdown(f"**Submitted by:** {submitted_by}")
        st.markdown(f"**Project:** {project_name} ({project_id})")
        st.markdown(f"**Date:** {update_date.strftime('%m/%d/%y')}")

        st.markdown("### 📅 Key Dates")
        st.markdown(f"- Permit Received: {permit_date.strftime('%m/%d/%y')}")
        st.markdown(f"- Mobilization Start: {mobilization_date.strftime('%m/%d/%y')}")
        st.markdown(f"- Concrete Pour: {concrete_date.strftime('%m/%d/%y')}")
        st.markdown(f"- TCO Date: {tco_date.strftime('%m/%d/%y')}")
        st.markdown(f"- Turnover: {turnover_date.strftime('%m/%d/%y')}")

        if notes:
            st.markdown("### 📝 Weekly Notes")
            bullet_points = notes.split("\n")
            for point in bullet_points:
                if point.strip():
                    st.markdown(f"- {point.strip()}")

        if uploaded_files:
            st.markdown("### 📎 Uploaded Files")
            for file in uploaded_files:
                st.markdown(f"- {file.name}")

        # Optional: Log the data, send an email, or write to a database/file here
