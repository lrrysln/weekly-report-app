import streamlit as st
import pandas as pd
from datetime import datetime
import os

# ✅ Path to your synced SharePoint/OneDrive folder
SYNCED_FOLDER = r"C:\Users\lsloan\RaceTrac\Construction and Engineering Leadership - Documents\General\Larry Sloan\Construction Weekly Updates"

# ✅ Create the file name for this week's file
today = datetime.today()
week_number = today.isocalendar()[1]
year = today.year
file_name = f"Week {week_number} {year}.xlsx"
file_path = os.path.join(SYNCED_FOLDER, file_name)

# ✅ Form UI
st.title("Weekly Construction Update Form")

with st.form("weekly_update"):
    date = st.date_input("Date")
    prototype = st.text_input("Prototype")
    address = st.text_input("Address")
    cpm = st.text_input("CPM")
    start_date = st.date_input("Start Date")
    tco_date = st.date_input("TCO Date")
    turnover_date = st.date_input("Turnover Date")
    notes = st.text_area("Notes (press enter for new bullet)")

    submitted = st.form_submit_button("Submit")
    if submitted:
        try:
            # Format notes for HTML display
            notes_html = "<ul>" + "".join([f"<li>{line.strip()}</li>" for line in notes.split("\n") if line.strip()]) + "</ul>"

            # Format all dates as MM/DD/YY
            formatted_date = date.strftime("%m/%d/%y")
            formatted_start = start_date.strftime("%m/%d/%y")
            formatted_tco = tco_date.strftime("%m/%d/%y")
            formatted_turnover = turnover_date.strftime("%m/%d/%y")

            # New row of data
            new_data = {
                "Date": formatted_date,
                "Prototype": prototype,
                "Address": address,
                "CPM": cpm,
                "Start Date": formatted_start,
                "TCO Date": formatted_tco,
                "Turnover Date": formatted_turnover,
                "Notes": notes  # raw notes saved, HTML used only for display
            }

            # Check if file exists
            if os.path.exists(file_path):
                df = pd.read_excel(file_path)
                df = pd.concat([df, pd.DataFrame([new_data])], ignore_index=True)
            else:
                df = pd.DataFrame([new_data])

            df.to_excel(file_path, index=False)
            st.success(f"✅ Entry submitted and saved to {file_name}")

            # Optionally: display live HTML preview
            st.markdown("### Live Report Preview")
            st.markdown(notes_html, unsafe_allow_html=True)

        except Exception as e:
            st.error(f"❌ Failed to save entry: {e}")
