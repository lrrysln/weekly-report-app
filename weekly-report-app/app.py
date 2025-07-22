import streamlit as st
from datetime import datetime
import base64

st.set_page_config(page_title="Weekly Report Generator", layout="centered")
st.title("Weekly Construction Update Generator")

# --- Form Input ---
with st.form("update_form", clear_on_submit=True):
    update_date = st.date_input("Date of Update")
    prototype = st.selectbox("Prototype", ["6K Remodel", "10K New Build", "20K New Build"])
    site = st.text_input("Site Name")
    cpm = st.text_input("CPM")
    start_date = st.date_input("Construction Start")
    tco = st.date_input("TCO Date")
    turnover = st.date_input("Turnover Date")
    notes = st.text_area("Notes (use bullets with Enter between each line)")
    submitted = st.form_submit_button("Submit")

# --- Display Report + HTML Download ---
if submitted:
    # Convert line breaks in notes to HTML bullet points
    bullet_notes = "".join(f"<li>{line.strip()}</li>" for line in notes.splitlines() if line.strip())
    report_date = update_date.strftime("%m/%d/%y")
    start_date_fmt = start_date.strftime("%m/%d/%y")
    tco_fmt = tco.strftime("%m/%d/%y")
    turnover_fmt = turnover.strftime("%m/%d/%y")

    html_report = f"""
    <html>
    <body>
        <h2>Weekly Construction Update</h2>
        <p><strong>Date of Update:</strong> {report_date}</p>
        <p><strong>Prototype:</strong> {prototype}</p>
        <p><strong>Site:</strong> {site}</p>
        <p><strong>CPM:</strong> {cpm}</p>
        <p><strong>Construction Start:</strong> {start_date_fmt}</p>
        <p><strong>TCO Date:</strong> {tco_fmt}</p>
        <p><strong>Turnover Date:</strong> {turnover_fmt}</p>
        <p><strong>Notes:</strong></p>
        <ul>
            {bullet_notes}
        </ul>
    </body>
    </html>
    """

    # Display the HTML report inline
    st.markdown("### 📋 Generated Report")
    st.components.v1.html(html_report, height=500, scrolling=True)

    # Offer download button
    b64 = base64.b64encode(html_report.encode()).decode()
    href = f'<a href="data:text/html;base64,{b64}" download="weekly_report_{site}_{report_date}.html">📥 Download HTML Report</a>'
    st.markdown(href, unsafe_allow_html=True)
