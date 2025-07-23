import streamlit as st
import pandas as pd
from datetime import datetime
import os

# 🔧 CONFIGURE: Local path synced with SharePoint/OneDrive
SAVE_FOLDER = r"C:\Users\lsloan\RaceTrac\Construction and Engineering Leadership - Documents\General\Larry Sloan\Construction Weekly Updates"

# Helper: Format notes into bullet points
def format_notes(notes_input):
    lines = notes_input.strip().split("\n")
    bullets = "".join([f"<li>{line.strip()}</li>" for line in lines if line.strip()])
    return f"<ul>{bullets}</ul>" if bullets else ""

# Helper: Get current week label
def get_week_label():
    today = datetime.now()
    week_num = today.isocalendar().week
    return f"Week {week_num} {today.year}"

# Helper: Get or create weekly Excel file
def save_submission(data_dict):
    week_label = get_week_label()
    filename = f"{week_label}.xlsx"
    file_path = os.path.join(SAVE_FOLDER, filename)

    new_df = pd.DataFrame([data_dict])

    try:
        if os.path.exists(file_path):
            existing_df = pd.read_excel(file_path)
            updated_df = pd.concat([existing_df, new_df], ignore_index=True)
        else:
            updated_df = new_df
        updated_df.to_excel(file_path, index=False)
        return True, file_path
    except Exception as e:
        return False, str(e)

# ---- Streamlit UI ----
st.title("Weekly Construction Report Form")

with st.form("entry_form", clear_on_submit=False):
    st.write("### Submit Construction Update")
    date = st.date_input("Date", datetime.now())
    formatted_date = date.strftime("%m/%d/%y")

    project_name = st.text_input("Project Name")
    prototype = st.selectbox("Prototype", ["GAS", "EV", "Remodel", "Other"])
    status = st.text_input("Current Status")
    notes = st.text_area("Notes (press Enter for bullets)", height=150)

    submitted = st.form_submit_button("Submit")
    clear = st.form_submit_button("Clear")

# Actions on Submit
if submitted:
    html_notes = format_notes(notes)
    submission = {
        "Date": formatted_date,
        "Project": project_name,
        "Prototype": prototype,
        "Status": status,
        "Notes": notes,
        "HTML Notes": html_notes
    }

    success, msg = save_submission(submission)
    if success:
        st.success(f"✅ Entry saved to: {msg}")
        # Show HTML preview
        st.markdown("### 🔍 HTML Report Preview")
        st.markdown(f"""
        <div>
            <strong>Date:</strong> {formatted_date}<br>
            <strong>Project:</strong> {project_name}<br>
            <strong>Prototype:</strong> {prototype}<br>
            <strong>Status:</strong> {status}<br>
            <strong>Notes:</strong> {html_notes}
        </div>
        """, unsafe_allow_html=True)
    else:
        st.error(f"❌ Failed to save entry: {msg}")

elif clear:
    st.experimental_rerun()
