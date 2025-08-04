import streamlit as st
import pandas as pd
import datetime
import gspread
from google.oauth2.service_account import Credentials
import matplotlib.pyplot as plt
from io import BytesIO
import base64
import re

# --- Auth & Google Sheets Setup ---
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=SCOPES)
client = gspread.authorize(creds)

SPREADSHEET_ID = "1cfr5rCRoRXuDJonarDbokznlaHHVpn1yUfTwo_ePL3w"
WORKSHEET_NAME = "Sheet1"

# --- Load Data ---
@st.cache_data(ttl=600)
def load_data():
    try:
        sheet = client.open_by_key(SPREADSHEET_ID).worksheet(WORKSHEET_NAME)
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        return df
    except Exception as e:
        st.error(f"Failed to load data from Google Sheet: {e}")
        return pd.DataFrame()

df = load_data()

if df.empty:
    st.warning("⚠️ No data loaded from Google Sheet yet.")
    st.stop()

# --- Preprocess Data (add Year Week etc from second script) ---
df.columns = df.columns.str.strip()
df['Year Week'] = pd.to_datetime(df['Year Week'], errors='coerce')
df['Week Label'] = df['Year Week'].dt.strftime('%G Week %V')
df['Year'] = df['Year Week'].dt.isocalendar().year
df['Date'] = df['Year Week'].dt.date

if 'Store Name' in df.columns:
    df['Store Name'] = df['Store Name'].str.title()
if 'Store Number' in df.columns:
    df['Store Number'] = df['Store Number'].astype(str).str.strip()
if 'Baseline' in df.columns:
    df['Baseline'] = df['Baseline'].astype(str).str.strip()

# --- Current Week Display (replace old Submitted Reports Overview) ---
today = datetime.date.today()
start_of_week = today - datetime.timedelta(days=today.weekday() + 1 if today.weekday() != 6 else 0)
start_of_week = start_of_week if today.weekday() != 6 else today
end_of_week = start_of_week + datetime.timedelta(days=6)

current_week_number = start_of_week.isocalendar()[1]
current_year = start_of_week.year
week_label = f"{current_year} Week {current_week_number:02d}"

current_week_df = df[(df['Date'] >= start_of_week) & (df['Date'] <= end_of_week)]

st.markdown(
    f"""### 📋 <span style='color:red'>{len(current_week_df)}</span> Submissions for the week of {start_of_week.strftime('%B %d')}–{end_of_week.strftime('%B %d')} (week {current_week_number} of the year), {current_year}""",
    unsafe_allow_html=True
)
columns_to_show = ['Store Number', 'Store Name', 'CPM', 'Prototype', 'Week Label']
st.dataframe(current_week_df[columns_to_show].reset_index(drop=True), use_container_width=True)

# --- Password Protected Report & Folder Dropdown ---

st.subheader("🔐 Generate Weekly Summary Report")

password = st.text_input("Enter Password", type="password")

if password == "1234":

    st.markdown("## 🗓️ Weekly Submission Volume by Year")

    years = sorted(df['Year'].dropna().unique(), reverse=True)
    for year in years:
        with st.expander(f"📁 {year}"):
            year_data = df[df['Year'] == year]
            weekly_counts = year_data.groupby('Week Label').size().reset_index(name='Count')
            for _, row in weekly_counts.iterrows():
                week = row['Week Label']
                count = row['Count']
                with st.expander(f"📆 {week} — {count} submission(s)"):
                    st.dataframe(year_data[year_data['Week Label'] == week].reset_index(drop=True))

    # --- Existing Detailed Weekly Summary Report Logic ---
    # (Use your existing code for baseline, trend calculation, summary_df, etc.)

    # After processing, button to generate report:
    if st.button("Generate Detailed Weekly Summary Report"):
        df_result, html = generate_weekly_summary(df, summary_df, password)
        if html is not None:
            st.markdown("### Weekly Summary")
            st.components.v1.html(html, height=1000, scrolling=True)
            st.download_button(
                label="📥 Download Summary as HTML",
                data=html.encode('utf-8'),
                file_name=f"Weekly_Summary_{datetime.datetime.now().strftime('%Y%m%d')}.html",
                mime="text/html",
                use_container_width=True
            )
        else:
            st.error(html)

else:
    if password:
        st.error("❌ Incorrect password.")
    else:
        st.info("Please enter the password to view the full report.")

