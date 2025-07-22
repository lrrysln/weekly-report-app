import streamlit as st
import pandas as pd
import datetime
import re
from pathlib import Path

# Constants
PASSWORD = "1234"
IMAGE_LINK = """<img src='data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAKgAAACUCAMAAAAwLZJQAAAAwFBMVEUOLXLsMST...ElFTkSuQmCC' style='float:right; width:100px;'>"""

# Paths
DOWNLOADS = Path.home() / "Downloads"

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

def format_date(date_input):
    if isinstance(date_input, datetime.date):
        return date_input.strftime("%m/%d/%y")
    return ""

def generate_weekly_summary(password):
    if password != PASSWORD:
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
            IMAGE_LINK,
            "<h1>Weekly Summary Report</h1>"]

    for subject, group in df.groupby("Subject"):
        html.append(f"<h2>{subject}</h2>")
        for _, row in group.iterrows():
            html.append('<div class="entry"><ul>')
            html.append(f"<li><span class='label'>Store Name:</span> {row.get('Store Name', '')}</li>")
            html.append(f"<li><span class='label'>Store Number:</span> {row.get('Store Number', '')}</li>")

            types = [col for col in ["RaceWay EDO Stores", "RT EFC - Traditional", "RT 5.5k EDO Stores",
                                     "RT EFC EDO Stores", "RT Travel Centers"] if row.get(col)]
            if types:
                html.append("<li><span class='label'>Types:</span><ul>")
                html += [f"<li>{t}</li>" for t in types]
                html.append("</ul></li>")

            html.append("<li><span class='label'>Dates:</span><ul>")
            for label in ["TCO Date", "Ops Walk Date", "Turnover Date", "Open to Train Date", "Store Opening"]:
                html.append(f"<li><span class='label'>{label}:</span> {row.get(label, '')}</li>")
            html.append("</ul></li>")

            notes = [re.sub(r"^[\\s•\-–●]+", "", n) for n in str(row.get("Notes", "")).splitlines() if n.strip()]
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
    path = week_folder / get_weekly_filename()
    with open(path, "w", encoding="utf-8") as f:
        f.write(html_content)
    return path

# Streamlit UI
st.title("📝 Weekly Store Report Form")
st.markdown(IMAGE_LINK, unsafe_allow_html=True)

with st.form("entry_form"):
    st.subheader("Store Info")
    store_name = st.text_input("Store Name")
    store_number = st.text_input("Store Number")

    st.subheader("Project Details")
    subject = st.selectbox("Subject", [
        "New Construction", "EDO Additions", "Phase 1/ Demo - New Construction Sites",
        "Remodels", "6k Remodels", "EV Project", "Traditional Special Project"])

    st.subheader("Dates")
    tco_date = st.date_input("TCO Date")
    ops_walk_date = st.date_input("Ops Walk Date")
    turnover_date = st.date_input("Turnover Date")
    open_train_date = st.date_input("Open to Train Date")
    store_opening = st.date_input("Store Opening")

    st.subheader("Types")
    rw_edo = st.checkbox("RaceWay EDO Stores")
    rt_trad = st.checkbox("RT EFC - Traditional")
    rt_55k = st.checkbox("RT 5.5k EDO Stores")
    rt_efc = st.checkbox("RT EFC EDO Stores")
    rt_travel = st.checkbox("RT Travel Centers")

    st.subheader("Notes")
    notes = st.text_area("Notes (press enter to create bullet)", height=150)

    col1, col2 = st.columns([1, 1])
    with col1:
        submitted = st.form_submit_button("Submit")
    with col2:
        cleared = st.form_submit_button("Clear")

if submitted:
    entry = {
        "Store Name": store_name,
        "Store Number": store_number,
        "Subject": subject,
        "TCO Date": format_date(tco_date),
        "Ops Walk Date": format_date(ops_walk_date),
        "Turnover Date": format_date(turnover_date),
        "Open to Train Date": format_date(open_train_date),
        "Store Opening": format_date(store_opening),
        "RaceWay EDO Stores": rw_edo,
        "RT EFC - Traditional": rt_trad,
        "RT 5.5k EDO Stores": rt_55k,
        "RT EFC EDO Stores": rt_efc,
        "RT Travel Centers": rt_travel,
        "Notes": notes,
    }
    save_to_excel(entry)
    st.success("✅ Entry submitted!")
    st.experimental_rerun()

st.subheader("🔐 Generate Weekly Report")
password_input = st.text_input("Enter password to generate report", type="password")
if st.button("Generate Report"):
    df, html_content = generate_weekly_summary(password_input)
    if df is not None:
        report_path = save_html_report(html_content)
        st.download_button("📄 Download HTML Report", html_content, file_name=report_path.name)
        st.markdown(html_content, unsafe_allow_html=True)
    else:
        st.error(html_content)
