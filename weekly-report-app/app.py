import streamlit as st
import pandas as pd
import datetime
import re
from pathlib import Path

# --- Constants ---
LOGO_BASE64 = "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"

# Paths
DOWNLOADS = Path.home() / "Downloads"

# Utility functions
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

def format_date_mmddyy(date_obj):
    if isinstance(date_obj, (datetime.date, datetime.datetime)):
        return date_obj.strftime("%m,%d,%y")
    return ""

def generate_weekly_summary(password):
    if password != "1234":
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

    # Start building HTML with embedded logo top-right
    html = [
        "<html><head><style>",
        "body{font-family:Arial;padding:20px;position:relative;}",
        "h1{text-align:center;margin-bottom:40px;}",
        "h2{background:#cce5ff;padding:10px;border-radius:4px;margin-top:30px;}",
        ".entry{border:1px solid #ccc;padding:10px;margin:10px 0;border-radius:4px;background:#f9f9f9}",
        "ul{margin:0;padding-left:20px;}",
        ".label{font-weight:bold;}",
        ".logo {position:absolute; top:10px; right:10px; width:100px;}",
        "</style></head><body>",
        f'<img class="logo" src="data:image/png;base64,{LOGO_BASE64}" alt="Logo"/>',
        "<h1>Weekly Summary Report</h1>"
    ]

    for subject, group in df.groupby("Subject"):
        html.append(f"<h2>{subject}</h2>")
        for _, row in group.iterrows():
            html.append('<div class="entry"><ul>')
            html.append(f"<li><span class='label'>Store Name:</span> {row.get('Store Name', '')}</li>")
            html.append(f"<li><span class='label'>Store Number:</span> {row.get('Store Number', '')}</li>")

            types = [col for col in
                     ["RaceWay EDO Stores", "RT EFC - Traditional", "RT 5.5k EDO Stores", "RT EFC EDO Stores",
                      "RT Travel Centers"] if row.get(col)]
            if types:
                html.append("<li><span class='label'>Types:</span><ul>")
                html += [f"<li>{t}</li>" for t in types]
                html.append("</ul></li>")

            # Format all date fields MM,DD,YY
            html.append("<li><span class='label'>Dates:</span><ul>")
            for label in ["TCO Date", "Ops Walk Date", "Turnover Date", "Open to Train Date", "Store Opening"]:
                dt = row.get(label, "")
                if pd.isna(dt):
                    formatted = ""
                else:
                    try:
                        dt_parsed = pd.to_datetime(dt)
                        formatted = format_date_mmddyy(dt_parsed)
                    except Exception:
                        formatted = str(dt)
                html.append(f"<li><span class='label'>{label}:</span> {formatted}</li>")
            html.append("</ul></li>")

            # Clean notes: strip bullet characters from each line, then add bullets
            raw_notes = str(row.get("Notes", ""))
            notes = [re.sub(r"^[\s•\-–●]+", "", n).strip() for n in raw_notes.splitlines() if n.strip()]
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
    filename = get_weekly_filename()
    path = week_folder / filename
    with open(path, "w", encoding="utf-8") as f:
        f.write(html_content)
    return path

# --- Streamlit UI ---

st.title("📝 Weekly Store Report Form")

# Columns for logo and form title
col1, col2 = st.columns([9,1])
with col2:
    st.image(f"data:image/png;base64,{LOGO_BASE64}", width=100)

# Initialize session state for clearing
if "form_cleared" not in st.session_state:
    st.session_state.form_cleared = False

def clear_form():
    st.session_state.form_cleared = True

with st.form("entry_form", clear_on_submit=False):
    st.subheader("Store Info")
    store_name = st.text_input("Store Name", key="store_name")
    store_number = st.text_input("Store Number", key="store_number")

    st.subheader("Project Details")

