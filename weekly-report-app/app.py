import streamlit as st
from datetime import datetime

st.title("Weekly Report Submission")

with st.form("weekly_form"):
    update_date = st.date_input("Date of Update")
    prototype = st.selectbox("Prototype", ["6K Remodel", "10K New Build", "20K New Build"])
    site = st.text_input("Site Name")
    cpm = st.text_input("CPM")
    start_date = st.date_input("Construction Start")
    tco = st.date_input("TCO Date")
    turnover = st.date_input("Turnover Date")
    notes = st.text_area("Notes (use bullets for updates)")

    submitted = st.form_submit_button("Submit")

if submitted:
    st.success("✅ Weekly update submitted successfully!")
    st.write("**Date of Update:**", update_date.strftime('%m/%d/%y'))
    st.write("**Prototype:**", prototype)
    st.write("**Site:**", site)
    st.write("**CPM:**", cpm)
    st.write("**Start Date:**", start_date.strftime('%m/%d/%y'))
    st.write("**TCO:**", tco.strftime('%m/%d/%y'))
    st.write("**Turnover:**", turnover.strftime('%m/%d/%y'))
    st.write("**Notes:**")
    for line in notes.split("\n"):
        st.write("-", line.strip())
