import streamlit as st
import pandas as pd
import datetime
import gspread
from google.oauth2.service_account import Credentials

# --- Auth & Google Sheets Setup ---
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=SCOPES)
client = gspread.authorize(creds)

SPREADSHEET_ID = "1cfr5rCRoRXuDJonarDbokznlaHHVpn1yUfTwo_ePL3w"
WORKSHEET_NAME = "Sheet1"

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

# Clean column names
df.columns = df.columns.str.strip()

# Show available columns for reference
st.write("🧪 Available Columns:", df.columns.tolist())

# --- Use 'Year Week' as timestamp ---
if 'Year Week' not in df.columns:
    st.error("❌ Column 'Year Week' not found in data. Cannot calculate week label.")
    st.stop()

df['Year Week'] = pd.to_datetime(df['Year Week'], errors='coerce')

# Use ISO week format
df['Week Label'] = df['Year Week'].dt.strftime('%G Week %V')
df['Year'] = df['Year Week'].dt.isocalendar().year

# Optional: Format strings
if 'Store Name' in df.columns:
    df['Store Name'] = df['Store Name'].str.title()
if 'Store Number' in df.columns:
    df['Store Number'] = df['Store Number'].astype(str).str.strip()
if 'Baseline' in df.columns:
    df['Baseline'] = df['Baseline'].astype(str).str.strip()

# Baseline mapping
baseline_df = df[df.get('Baseline') == "/True"].copy()
baseline_map = baseline_df.set_index('Store Number')['Week Label'].to_dict()

# --- Weekly Submission Volume by Year (Moved Above Report) ---
st.markdown("## 📂 Weekly Submission Volume by Year")

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

# --- Current Week Data ---
today = datetime.datetime.now()
start_of_week = today - datetime.timedelta(days=today.weekday() + 1) if today.weekday() != 6 else today
end_of_week = start_of_week + datetime.timedelta(days=6)

# Create label
week_number = start_of_week.isocalendar().week
year = start_of_week.isocalendar().year
week_label = f"{year} Week {week_number:02d}"

# Filter submissions within the Sunday–Saturday range
mask = (df['Year Week'] >= start_of_week) & (df['Year Week'] <= end_of_week)
current_week_df = df[mask].copy()

# Update Week Label column for filtered records
current_week_df['Week Label'] = current_week_df['Year Week'].dt.strftime('%G Week %V')

# Red + bold report heading
report_range = f"{start_of_week.strftime('%B %d')}–{end_of_week.strftime('%B %d')}"
st.markdown(
    f"<h4 style='color:red;font-weight:bold;'>📋 {len(current_week_df)} Submissions for the week of {report_range} (week {week_number} of the year), {year}</h4>",
    unsafe_allow_html=True
)

# Final Report Table (same columns as submission)
columns_to_display = [col for col in df.columns if col in current_week_df.columns]
if 'Week Label' not in columns_to_display:
    columns_to_display.append('Week Label')

st.dataframe(current_week_df[columns_to_display].reset_index(drop=True))
