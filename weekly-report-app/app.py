import streamlit as st
import pandas as pd
import datetime
import calendar
import io
import base64
from collections import defaultdict

# --- CONFIG ---
PASSWORD = "your_password_here"  # Replace this with your actual password
SHEET_PATH = "data/weekly_data.csv"  # Replace with your actual path or data fetching method

# --- CACHE DATA ---
@st.cache_data(show_spinner=False)
def load_data():
    df = pd.read_csv(SHEET_PATH)
    df['Start'] = pd.to_datetime(df['Start'], errors='coerce')
    df['TCO'] = pd.to_datetime(df['TCO'], errors='coerce')
    df['Store Opening'] = pd.to_datetime(df['Store Opening'], errors='coerce')
    df['Turnover'] = pd.to_datetime(df['Turnover'], errors='coerce')
    df['Week Start'] = pd.to_datetime(df['Year Week'].str.extract(r'(\d{4}) week (\d{1,2})').apply(lambda x: datetime.date.fromisocalendar(int(x[0]), int(x[1]), 1), axis=1))
    return df

# --- FUNCTIONS ---
def generate_weekly_report(df, week_label):
    week_df = df[df['Year Week'] == week_label].copy()
    if week_df.empty:
        return "<p>No data for this week.</p>"

    summary_html = f"<h3 style='color:darkblue;'>Weekly Summary Report - {week_label}</h3><ul>"
    for _, row in week_df.iterrows():
        summary_html += f"<li><strong>{row['Store Name']} ({row['Store Number']})</strong> - {row['Subject']} | Prototype: {row['Prototype']} | CPM: {row['CPM']}<br>"
        summary_html += f"Start: {row['Start'].date() if pd.notna(row['Start']) else 'N/A'}, TCO: {row['TCO'].date() if pd.notna(row['TCO']) else 'N/A'}, Turnover: {row['Turnover'].date() if pd.notna(row['Turnover']) else 'N/A'}, Store Opening: {row['Store Opening'].date() if pd.notna(row['Store Opening']) else 'N/A'}<br>"
        summary_html += f"Notes: {row[' Notes']}</li><br>"
    summary_html += "</ul>"
    return summary_html

def get_current_week_label():
    today = datetime.date.today()
    iso_year, iso_week, _ = today.isocalendar()
    return f"{iso_year} week {iso_week}"

def to_html_download(report_html, filename):
    b64 = base64.b64encode(report_html.encode()).decode()
    return f'<a href="data:text/html;base64,{b64}" download="{filename}">Download Report</a>'

# --- APP ---
st.title("📊 Construction Weekly Overview")
df = load_data()
st.dataframe(df[["Year Week", "Store Name", "Store Number", "Subject", "Prototype"]], use_container_width=True)

# Password Access
st.markdown("---")
st.subheader("🔐 Enter password to view reports")
password = st.text_input("Password", type="password")

if password == PASSWORD:
    st.success("Access granted")

    current_week_label = get_current_week_label()
    st.subheader(f"📝 Current Week Summary: {current_week_label}")

    html_summary = generate_weekly_report(df, current_week_label)
    st.components.v1.html(html_summary, height=400, scrolling=True)

    st.markdown(to_html_download(html_summary, f"Weekly_Report_{current_week_label}.html"), unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("📂 Past Weekly Reports")

    years = sorted(df['Year Week'].str.extract(r'(\d{4})')[0].astype(int).unique(), reverse=True)
    for year in years:
        with st.expander(f"Year {year}"):
            year_df = df[df['Year Week'].str.startswith(str(year))]
            weeks = sorted(year_df['Year Week'].unique(), reverse=True)
            for week in weeks:
                with st.expander(week):
                    display_df = year_df[year_df['Year Week'] == week]
                    st.dataframe(display_df.drop(columns=['__PowerAppsId__', 'Week Start']), use_container_width=True)
else:
    if password:
        st.error("Incorrect password. Please try again.")
