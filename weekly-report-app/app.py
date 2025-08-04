import streamlit as st
import pandas as pd
import datetime
import os
from io import BytesIO
from dateutil.parser import parse
from streamlit.components.v1 import html

# ------------------- CONFIG -----------------------
st.set_page_config(page_title="Construction Weekly Tracker", layout="wide")

# ------------------- PASSWORD PROTECTION -----------------------
PASSWORD = "1234"
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if st.session_state.get("password_entered") != True:
    password = st.text_input("Enter password:", type="password")
    if st.button("Submit"):
        if password == "1234":
            st.session_state["password_entered"] = True
            st.rerun()
        else:
            st.error("Incorrect password.")

    st.stop()

# ------------------- LOAD AND CACHE DATA -----------------------
@st.cache_data(ttl=3600)
def load_data():
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet(WORKSHEET_NAME)
    df['Date'] = pd.to_datetime(df['Start'], errors='coerce')
    df['Week'] = df['Date'].dt.isocalendar().week
    df['Year'] = df['Date'].dt.isocalendar().year
    df['Week_Label'] = df['Year'].astype(str) + " Week " + df['Week'].astype(str)
    return df

df = load_data()

# ------------------- DETERMINE CURRENT WEEK -----------------------
today = datetime.date.today()
start_of_week = today - datetime.timedelta(days=today.weekday() + 1)  # Sunday
end_of_week = start_of_week + datetime.timedelta(days=6)

current_week_df = df[(df['Date'] >= pd.to_datetime(start_of_week)) & (df['Date'] <= pd.to_datetime(end_of_week))]

# ------------------- GENERATE WEEKLY SUMMARY REPORT -----------------------
def generate_weekly_report(data):
    summary = f"""
    <h2 style='color:#004aad'>Weekly Construction Summary – Week {start_of_week.strftime('%U')} ({start_of_week} to {end_of_week})</h2>
    <p><strong>Total Entries:</strong> {len(data)}</p>
    <table border='1' style='border-collapse: collapse; width:100%'>
        <tr>
            <th>Store Name</th>
            <th>Store #</th>
            <th>Prototype</th>
            <th>CPM</th>
            <th>Start</th>
            <th>TCO</th>
            <th>Ops Walk</th>
            <th>Turnover</th>
            <th>Open to Train</th>
            <th>Store Opening</th>
            <th>Notes</th>
        </tr>
    """
    for _, row in data.iterrows():
        summary += f"""
            <tr>
                <td>{row.get('Store Name','')}</td>
                <td>{row.get('Store Number','')}</td>
                <td>{row.get('Prototype','')}</td>
                <td>{row.get('CPM','')}</td>
                <td>{row.get('Start','')}</td>
                <td>{row.get('TCO','')}</td>
                <td>{row.get('Ops Walk','')}</td>
                <td>{row.get('Turnover','')}</td>
                <td>{row.get('Open to Train','')}</td>
                <td>{row.get('Store Opening','')}</td>
                <td>{row.get('Notes','').replace('\n', '<br>')}</td>
            </tr>
        """
    summary += "</table>"
    return summary

# ------------------- MAIN UI -----------------------
st.title("🏗️ Construction Weekly Tracker")

# 👉 CURRENT WEEK REPORT
st.subheader(f"📋 Current Week Report: {start_of_week.strftime('%B %d')} - {end_of_week.strftime('%B %d, %Y')}")
if current_week_df.empty:
    st.warning("No submissions yet for this week.")
else:
    report_html = generate_weekly_report(current_week_df)
    html(report_html, height=600, scrolling=True)

    # Download as HTML
    download_button = st.download_button(
        label="📥 Download Weekly Summary (HTML)",
        data=report_html,
        file_name=f"Weekly_Summary_{start_of_week}_to_{end_of_week}.html",
        mime="text/html"
    )

# 👉 YEAR/WEEK HISTORICAL REVIEW
st.markdown("---")
st.subheader("📚 Past Weekly Submissions by Year")

years = sorted(df['Year'].dropna().unique(), reverse=True)

for year in years:
    with st.expander(f"📅 {year}"):
        year_df = df[df['Year'] == year]
        weeks = sorted(year_df['Week'].dropna().unique(), reverse=True)
        for week in weeks:
            week_df = year_df[year_df['Week'] == week]
            label = f"Week {int(week)}"
            with st.expander(label):
                display_df = week_df[[
                    "Store Name", "Store Number", "Prototype", "CPM", "Start", "TCO",
                    "Ops Walk", "Turnover", "Open to Train", "Store Opening", "Notes"
                ]]
                st.dataframe(display_df, use_container_width=True)

# Optional footer
st.markdown("<br><hr><p style='text-align:center;'>Construction Weekly Tracker • © 2025</p>", unsafe_allow_html=True)
