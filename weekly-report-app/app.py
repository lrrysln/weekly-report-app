import streamlit as st
import pandas as pd
from datetime import datetime
import os

# Define synced OneDrive folder location for saving weekly Excel files
SYNCED_FOLDER = r"C:\Users\lsloan\RaceTrac\Construction and Engineering Leadership - Documents\General\Larry Sloan\Construction Weekly Updates"

# Create weekly filename
week_number = datetime.today().isocalendar()[1]
year = datetime.today().year
excel_filename = f"Week {week_number} {year}.xlsx"
file_path = os.path.join(SYNCED_FOLDER, excel_filename)

# Form layout
st.title("Weekly Construction Update Form")

with st.form("update_form"):
    password = st.text_input("1234", type="password")
    prototype = st.selectbox("Prototype", ["Store", "EV", "Remodel"])
    site = st.text_input("Site #")
    address = st.text_input("Address (MM/DD/YY format will be used in report)")
    cpm = st.text_input("CPM")
    start_date = st.date_input("Start Date")
    tco_date = st.date_input("TCO Date")
    turnover_date = st.date_input("Turnover Date")
    notes = st.text_area("Notes (press enter for new bullet)", height=150)

    submitted = st.form_submit_button("Generate Report")

# When form is submitted and password is correct
if submitted:
    if password != "your_password_here":
        st.error("Incorrect password")
    else:
        try:
            # Format dates as MM/DD/YY
            start = start_date.strftime("%m/%d/%y")
            tco = tco_date.strftime("%m/%d/%y")
            turnover = turnover_date.strftime("%m/%d/%y")

            # Raw text for Excel; HTML version for display
            raw_notes = notes
            html_notes = "<ul>" + "".join([f"<li>{line.strip()}</li>" for line in raw_notes.split("\n") if line.strip()]) + "</ul>"

            # Create a row of data
            new_row = {
                "Prototype": prototype,
                "Site #": site,
                "Address": address,
                "CPM": cpm,
                "Start Date": start,
                "TCO Date": tco,
                "Turnover Date": turnover,
                "Notes": raw_notes
            }

            # Load or create file
            if os.path.exists(file_path):
                df = pd.read_excel(file_path)
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            else:
                df = pd.DataFrame([new_row])

            df.to_excel(file_path, index=False)
            st.success(f"✅ Entry saved to {excel_filename}")

            # Show live HTML report preview
            st.markdown("### Live Report Preview")
            st.markdown(f"""
                <b>Prototype:</b> {prototype}  
                <b>Site #:</b> {site}  
                <b>Address:</b> {address}  
                <b>CPM:</b> {cpm}  
                <b>Start Date:</b> {start}  
                <b>TCO Date:</b> {tco}  
                <b>Turnover Date:</b> {turnover}  
                <b>Notes:</b> {html_notes}
            """, unsafe_allow_html=True)

            # Clear form fields
            st.experimental_rerun()

        except Exception as e:
            st.error(f"❌ Failed to save entry: {e}")
