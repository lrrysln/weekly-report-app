import streamlit as st
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
