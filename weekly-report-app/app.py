
import streamlit as st
import pandas as pd
import datetime
import re
from pathlib import Path

# Set up Streamlit page
st.set_page_config(page_title="Weekly Construction Report", layout="centered")
st.title("📝 Weekly Store Report Form")

# ✅ SharePoint-synced base path
BASE_PATH = Path(r"C:\Users\lsloan\RaceTrac\Construction and Engineering Leadership - Documents\General\Larry Sloan\Construction Weekly Updates")

# 🔧 Helper Functions
def get_current_week_folder():
    today = datetime.datetime.now()
    week_number = today.isocalendar().week
    week_folder = BASE_PATH / f"Week {week_number} {today.year}"
    week_folder.mkdir(parents=True, exist_ok=True)
    return week_folder

def get_excel_path():
    folder = get_current_week_folder()
    week_number = datetime.datetime.now().isocalendar().week
    year = datetime.datetime.now().year
    return folder / f"Week {week_number} {year}.xlsx"

def save_to_excel(entry_data):
    excel_path = get_excel_path()
    new_df = pd.DataFrame([entry_data])

    if excel_path.exists():
        existing_df = pd.read_excel(excel_path, engine="openpyxl")
        combined_df = pd.concat([existing_df, new_df], ignore_index=True)
    else:
        combined_df = new_df

    combined_df.to_excel(excel_path, index=False, engine="openpyxl")
    return excel_path

def generate_weekly_summary(password):
    if password != "1234":
        return None, "❌ Incorrect password."

    path = get_excel_path()
    if not path.exists():
        return None, "⚠️ No entries submitted this week."

    df = pd.read_excel(path, engine="openpyxl")
    if df.empty:
        return None, "🚫 No data to summarize."

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

            types = [col for col in [
                "RaceWay EDO Stores", "RT EFC - Traditional", "RT 5.5k EDO Stores",
                "RT EFC EDO Stores", "RT Travel Centers"] if row.get(col)]
            if types:
                html.append("<li><span class='label'>Types:</span><ul>")
                html += [f"<li>{t}</li>" for t in types]
                html.append("</ul></li>")

            html.append("<li><span class='label'>Dates:</span><ul>")
            for label in ["TCO Date", "Ops Walk Date", "Turnover Date", "Open to Train Date", "Store Opening"]:
                try:
                    val = pd.to_datetime(row.get(label, ''), errors='coerce')
                    html.append(f"<li><span class='label'>{label}:</span> {val.strftime('%m/%d/%y') if not pd.isna(val) else ''}</li>")
                except:
                    html.append(f"<li><span class='label'>{label}:</span> {row.get(label, '')}</li>")
            html.append("</ul></li>")

            notes = [re.sub(r"^[\s•\-–●]+", "", n) for n in str(row.get("Notes", "")).splitlines() if n.strip()]
            if notes:
                html.append("<li><span class='label'>Notes:</span><ul>")
                html += [f"<li>{n}</li>" for n in notes]
                html.append("</ul></li>")

            html.append("</ul></div>")

    html.append("</body></html>")
    return df, "".join(html)

def get_weekly_filename():
    today = datetime.datetime.now()
    week_num = today.isocalendar().week
    return f"Week {week_num} {today.year} Report.html"

# 📝 Streamlit Form
with st.form("entry_form", clear_on_submit=True):
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

    st.subheader("Important Dates (MM/DD/YY)")
    tco_date = st.date_input("TCO Date")
    ops_walk_date = st.date_input("Ops Walk Date")
    turnover_date = st.date_input("Turnover Date")
    open_to_train_date = st.date_input("Open to Train Date")
    store_opening = st.date_input("Store Opening")

    st.subheader("Notes")
    notes = st.text_area("Add Notes (Press enter for each bullet)", value="• ", height=200)

    submitted = st.form_submit_button("Submit")

    if submitted:
        entry = {
            "Store Name": store_name,
            "Store Number": store_number,
            "Subject": subject,
            "TCO Date": tco_date.strftime("%m/%d/%y"),
            "Ops Walk Date": ops_walk_date.strftime("%m/%d/%y"),
            "Turnover Date": turnover_date.strftime("%m/%d/%y"),
            "Open to Train Date": open_to_train_date.strftime("%m/%d/%y"),
            "Store Opening": store_opening.strftime("%m/%d/%y"),
            "Notes": notes
        }
        entry.update(types)

        try:
            saved_path = save_to_excel(entry)
            st.success("✅ Entry saved successfully!")
            st.info(f"📁 Saved to: `{saved_path}`")
        except Exception as e:
            st.error(f"❌ Failed to save entry: {e}")

# 🔐 Report Generation Section
st.subheader("🔐 Generate Weekly Report")
password = st.text_input("Enter Password to Generate Report", type="password")
if st.button("Generate Report"):
    df, html = generate_weekly_summary(password)
    if df is not None:
        st.success("✅ Report generated successfully!")
        st.components.v1.html(html, height=800, scrolling=True)
        st.download_button("Download HTML Report", data=html, file_name=get_weekly_filename(), mime="text/html")
    else:
        st.error(html)
