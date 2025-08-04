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

# --- Use 'Year Week' as timestamp ---
if 'Year Week' not in df.columns:
    st.error("❌ Column 'Year Week' not found in data. Cannot calculate week label.")
    st.stop()

df['Year Week'] = pd.to_datetime(df['Year Week'], errors='coerce')

# Use ISO week format (Monday start, standard business)
df['Week Label'] = df['Year Week'].dt.strftime('%G Week %V')
df['Year'] = df['Year Week'].dt.isocalendar().year

# Optional: Format store names and clean up strings
if 'Store Name' in df.columns:
    df['Store Name'] = df['Store Name'].str.title()

if 'Store Number' in df.columns:
    df['Store Number'] = df['Store Number'].astype(str).str.strip()

if 'Baseline' in df.columns:
    df['Baseline'] = df['Baseline'].astype(str).str.strip()

# Baseline mapping (for reference)
baseline_df = df[df.get('Baseline') == "/True"].copy()
baseline_map = baseline_df.set_index('Store Number')['Week Label'].to_dict()

# --- Input Password ---
st.subheader("🔐 Generate Weekly Summary Report")
password = st.text_input("Enter Password", type="password")

# --- Weekly Overview Section: NOW AFTER password check ---
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

    # --- Current Week's Data (Sunday to Saturday) ---
today = datetime.date.today()
start_of_week = today - datetime.timedelta(days=today.weekday() + 1 if today.weekday() != 6 else 0)
start_of_week = start_of_week if today.weekday() != 6 else today
end_of_week = start_of_week + datetime.timedelta(days=6)

# Format label as "2025 Week 32"
current_week_number = start_of_week.isocalendar()[1]
current_year = start_of_week.year
week_label = f"{current_year} Week {current_week_number:02d}"

# Filter using adjusted week range
df['Date'] = pd.to_datetime(df['Year Week'], errors='coerce').dt.date
current_week_df = df[(df['Date'] >= start_of_week) & (df['Date'] <= end_of_week)]

# Display week range + red submission count
st.markdown(
    f"""### 📋 <span style='color:red'>{len(current_week_df)}</span> Submissions for the week of {start_of_week.strftime('%B %d')}–{end_of_week.strftime('%B %d')} (week {current_week_number} of the year), {current_year}""",
    unsafe_allow_html=True
)

# Show original columns plus Week Label
if 'Week Label' not in current_week_df.columns:
    current_week_df['Week Label'] = current_week_df['Year Week'].dt.strftime('%G Week %V')

columns_to_display = df.columns.tolist()
if 'Week Label' not in columns_to_display:
    columns_to_display.append('Week Label')

st.dataframe(current_week_df[columns_to_display].reset_index(drop=True), use_container_width=True)

    # Ensure Date column exists
    df['Date'] = pd.to_datetime(df['Year Week'], errors='coerce').dt.date
    current_week_df = df[(df['Date'] >= start_of_week) & (df['Date'] <= end_of_week)]

    # Display header with red count
    st.markdown(
        f"""### 📋 <span style='color:red'>{len(current_week_df)}</span> Submissions for the week of {start_of_week.strftime('%B %d')}–{end_of_week.strftime('%B %d')} (week {current_week_number} of the year), {current_year}""",
        unsafe_allow_html=True
    )

    # Use same columns as main submission table, plus Week Label
    columns_to_show = ['Store Number', 'Store Name', 'CPM', 'Prototype', 'Week Label']
    st.dataframe(current_week_df[columns_to_show].reset_index(drop=True), use_container_width=True)

else:
    st.info("Please enter the password to view weekly submission volume and reports.")

# --- Format store names for main df ---
df['Store Name'] = df['Store Name'].str.title()

# Convert date columns to datetime
df['Store Opening'] = pd.to_datetime(df['Store Opening'], errors='coerce')
df['Baseline'] = df['Baseline'].astype(str).str.strip()
df['Store Number'] = df['Store Number'].astype(str).str.strip()

# Separate baseline & non-baseline entries
baseline_df = df[df['Baseline'] == "/True"].copy()
baseline_map = baseline_df.set_index('Store Number')['Store Opening'].to_dict()

# Trend calculation
def compute_trend(row):
    store_number = row['Store Number']
    current_open = row['Store Opening']
    if row['Baseline'] == "/True":
        return "baseline"
    baseline_open = baseline_map.get(store_number)
    if pd.isna(current_open) or pd.isna(baseline_open):
        return "no baseline dates"
    if current_open > baseline_open:
        return "pushed"
    elif current_open < baseline_open:
        return "pulled in"
    else:
        return "held"

df['Trend'] = df.apply(compute_trend, axis=1)

# Calculate delta
def compute_delta(row):
    baseline_open = baseline_map.get(row['Store Number'])
    if pd.isna(row['Store Opening']) or pd.isna(baseline_open):
        return 0
    return (row['Store Opening'] - baseline_open).days

df['Store Opening Delta'] = df.apply(compute_delta, axis=1)

# Flag logic with red asterisk
def flag_delta(delta):
    if isinstance(delta, int) and abs(delta) > 5:
        return '<span style="color:red;font-weight:bold;">*</span>'
    return ""

df['Flag'] = df['Store Opening Delta'].apply(flag_delta)

# Filter notes for keywords
keywords = ["behind schedule", "lagging", "delay", "critical path", "cpm impact", "work on hold", "stop work order",
            "reschedule", "off track", "schedule drifting", "missed milestone", "budget overrun", "cost impact",
            "change order pending", "claim submitted", "dispute", "litigation risk", "schedule variance",
            "material escalation", "labor shortage", "equipment shortage", "low productivity", "rework required",
            "defects found", "qc failure", "weather delays", "permit delays", "regulatory hurdles",
            "site access issues", "awaiting sign-off", "conflict", "identified risk", "mitigation", "forecast revised"]

def check_notes(text):
    text_lower = str(text).lower()
    return any(kw in text_lower for kw in keywords)

df['Notes'] = df['Notes'].fillna("")
df['Notes Filtered'] = df['Notes'].apply(lambda x: x if check_notes(x) else "see report below")

summary_cols = ['Store Name', 'Store Number', 'Prototype', 'CPM', 'Flag', 'Store Opening Delta', 'Trend', 'Notes Filtered']
summary_df = df[summary_cols].drop_duplicates(subset=['Store Number']).reset_index(drop=True)

# Main Display
st.subheader("📋 Submitted Reports Overview")
st.markdown(f"<h4><span style='color:red;'><b>{len(df)}</b></span> form responses have been submitted</h4>", unsafe_allow_html=True)
st.dataframe(df[['Store Number', 'Store Name', 'CPM', 'Prototype']], use_container_width=True)

# --- (Optional) The rest of your report generation and plotting code here ---
# (If you want me to add that too, just ask!)

