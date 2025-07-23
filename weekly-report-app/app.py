import streamlit as st
import pandas as pd
import datetime
import re
from pathlib import Path
from io import BytesIO

# Setup SharePoint-synced folder path (Update this if needed)
ONEDRIVE_BASE = Path(r"C:\Users\lsloan\OneDrive - RaceTrac Petroleum Inc\Construction Weekly Updates")

# Week logic
def get_current_week_folder():
    today = datetime.datetime.now()
    week_num = today.isocalendar().week
    return ONEDRIVE_BASE / f"Week {week_num} {today.year}"

def get_excel_path():
    folder = get_current_week_folder()
    folder.mkdir(parents=True, exist_ok=True)
    return folder / f"Week {datetime.datetime.now().isocalendar().week} {datetime.datetime.now().year}.xlsx"

# Save entry to Excel
def save_to_excel(entry_data):
    path = get_excel_path()
    df = pd.DataFrame([entry_data])
    if path.exists():
        existing = pd.read_excel(path, engine='openpyxl')
        df = pd.concat([existing, df], ignore_index=True)
    df.to_excel(path, index=False, engine='openpyxl')

# HTML report generation
def generate_weekly_summary(password):
    if password != "1234":
        return None, "❌ Incorrect password."

    path = get_excel_path()
    if not path.exists():
        return None, "⚠️ No entries submitted this week."

    df = pd.read_excel(path, engine='openpyxl')
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
                val = pd.to_datetime(row.get(label, ''), errors='coerce')
                html.append(f"<li><span class='label'>{label}:</span> {val.strftime('%m/%d/%y') if not pd.isna(val) else ''}</li>")
            html.append("</ul></li>")

            notes = [re.sub(r"^[\s•\-–●]+", "", n) for n in str(row.get("Notes", "")).splitlines() if n.strip()]
            if notes:
                html.append("<li><span class='label'>Notes:</span><ul>")
                html += [f"<li>{n}</li>" for n in notes]
                html.append("</ul></li>")

            html.append("</ul></div>")

    html.append("</body></html>")
    return df, "".join(html)

# ------------------- Streamlit App -------------------
st.set_page_config(page_title="Weekly Construction Report", layout="centered")
st.title("📝 Weekly Store Report Form")

# Form Input
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

    # Auto-bulleted notes
    st.subheader("Notes")
    notes = st.text_area("Notes (each line auto-bulleted)", value="• ", height=200)

    submitted = st.form_submit_button("Submit")

    if submitted:
        data = {
            "Store Name": store_name,
            "Store Number": store_number,
            "Subject": subject,
            "TCO Date": tco_date.strftime('%m/%d/%y'),
            "Ops Walk Date": ops_walk_date.strftime('%m/%d/%y'),
            "Turnover Date": turnover_date.strftime('%m/%d/%y'),
            "Open to Train Date": open_to_train_date.strftime('%m/%d/%y'),
            "Store Opening": store_opening.strftime('%m/%d/%y'),
            "Notes": notes
        }
        data.update(types)
        save_to_excel(data)
        st.success("✅ Entry saved successfully!")

# Report Generation
st.subheader("🔐 Generate Weekly Report")
password = st.text_input("Enter Password", type="password")
if st.button("Generate Report"):
    df, html = generate_weekly_summary(password)
    if df is not None:
        st.success("✅ Report generated below. You can also download it.")
        st.components.v1.html(html, height=800, scrolling=True)
        st.download_button("Download HTML Report", data=html, file_name="Weekly_Report.html", mime="text/html")
    else:
        st.error(html)
