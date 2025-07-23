import streamlit as st
import datetime
import os
import pandas as pd
from pathlib import Path
import streamlit.components.v1 as components

# ----- CONFIGURATION -----
PASSWORD = "report2025"
SAVE_DIR = Path("reports")
SAVE_DIR.mkdir(exist_ok=True)

# ----- FUNCTIONS -----
def format_date(d):
    return d.strftime("%m/%d/%Y") if d else ""

def process_notes(notes):
    lines = notes.strip().split("\n")
    bullet_lines = [f"\u2022 {line.lstrip('• ').strip()}" for line in lines if line.strip()]
    return "\n".join(bullet_lines)

def save_report(data, filename):
    with open(SAVE_DIR / filename, "w") as f:
        f.write(data)

def generate_html(data):
    return f"""
    <html>
        <body style='background-color: black; color: red;'>
            <h2>{data['subject']}</h2>
            <p><strong>Store:</strong> {data['store_name']} (#{data['store_number']})</p>
            <p><strong>Project Manager:</strong> {data['project_manager']}</p>
            <p><strong>TCO Date:</strong> {data['tco_date']}</p>
            <p><strong>Ops Walk Date:</strong> {data['ops_walk_date']}</p>
            <p><strong>Turnover Date:</strong> {data['turnover_date']}</p>
            <p><strong>Open to Train Date:</strong> {data['open_to_train_date']}</p>
            <p><strong>Store Opening:</strong> {data['store_opening']}</p>
            <p><strong>Store Types:</strong> {data['store_types']}</p>
            <p><strong>Notes:</strong><br>{data['notes'].replace(chr(10), '<br>')}</p>
        </body>
    </html>
    """

# ----- FORM LAYOUT -----
st.title("📝 Weekly Store Report Form")

with st.form("entry_form"):
    st.subheader("Store Info")
    store_name = st.text_input("Store Name")
    store_number = st.text_input("Store Number")

    st.subheader("Project Details")
    subject = st.selectbox("Subject", ["Select Subject", "New Construction", "EDO Additions", "Phase 1/ Demo - New Construction Sites",
        "Remodels", "6k Remodels", "EV Project", "Traditional Special Project",
        "Miscellaneous Items of Note", "Potential Projects",
        "Complete - Awaiting Post Completion Site Visit", "2025 Completed Projects"])

    project_manager = st.selectbox("Project Manager", ["Select Project Manager", "Gretchen Sevin", "Angie R", "Tate Godwin", "Tyler Robledo",
        "Dave Matthews", "Chad Smith", "Jeb C", "Wes M",
        "Phillip Jeffcoat", "Dj Garland"])

    st.subheader("Store Types")
    store_types_list = []
    if st.checkbox("RaceWay EDO Stores"): store_types_list.append("RaceWay EDO Stores")
    if st.checkbox("RT EFC - Traditional"): store_types_list.append("RT EFC - Traditional")
    if st.checkbox("RT 5.5k EDO Stores"): store_types_list.append("RT 5.5k EDO Stores")
    if st.checkbox("RT EFC EDO Stores"): store_types_list.append("RT EFC EDO Stores")
    if st.checkbox("RT Travel Centers"): store_types_list.append("RT Travel Centers")

    st.subheader("Important Dates")
    tco_date = st.date_input("Select TCO Date", value=None)
    ops_walk_date = st.date_input("Select Ops Walk Date", value=None)
    turnover_date = st.date_input("Select Turnover Date", value=None)
    open_to_train_date = st.date_input("Select Open to Train Date", value=None)
    store_opening = st.date_input("Select Store Opening Date", value=None)

    st.subheader("Notes")
    custom_css = """
    <style>
    textarea {
        font-family: monospace;
        line-height: 1.6;
        white-space: pre-wrap;
    }
    </style>
    """
    st.markdown(custom_css, unsafe_allow_html=True)
    notes_input = st.text_area("Use Enter to create new notes. Bullets will appear automatically.", value="• ", height=200)

    password = st.text_input("Enter password to generate report:", type="password")

    col1, col2 = st.columns(2)
    with col1:
        submit_entry = st.form_submit_button("Submit Entry")
    with col2:
        submitted = st.form_submit_button("Generate Report")

if submitted or submit_entry:
    if password == PASSWORD:
        formatted_data = {
            "store_name": store_name,
            "store_number": store_number,
            "subject": subject,
            "project_manager": project_manager,
            "tco_date": format_date(tco_date),
            "ops_walk_date": format_date(ops_walk_date),
            "turnover_date": format_date(turnover_date),
            "open_to_train_date": format_date(open_to_train_date),
            "store_opening": format_date(store_opening),
            "store_types": ", ".join(store_types_list),
            "notes": process_notes(notes_input),
        }

        html_report = generate_html(formatted_data)

        if submitted:
            st.subheader("📄 Report Preview")
            components.html(html_report, height=600, scrolling=True)

            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            base_filename = f"{formatted_data['store_number']}_{timestamp}"
            html_filename = f"{base_filename}.html"

            save_report(html_report, html_filename)

            with open(SAVE_DIR / html_filename, "rb") as f:
                st.download_button("Download HTML Report", f, file_name=html_filename, mime="text/html")

            st.success("Report submitted and saved successfully.")
            st.experimental_rerun()
        else:
            st.success("Entry submitted without generating report.")
    else:
        st.error("Incorrect password. Report not generated.")
