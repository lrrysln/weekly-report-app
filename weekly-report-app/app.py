import streamlit as st
import pandas as pd
import datetime
import re
import matplotlib.pyplot as plt
import gspread
from google.oauth2.service_account import Credentials
import base64
from io import BytesIO

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

# --- Preprocess Data ---
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

# --- Current Week Display ---
today = datetime.date.today()
start_of_week = today - datetime.timedelta(days=today.weekday() + 1 if today.weekday() != 6 else 0)
start_of_week = start_of_week if today.weekday() != 6 else today
end_of_week = start_of_week + datetime.timedelta(days=6)

current_week_number = start_of_week.isocalendar()[1]
current_year = start_of_week.year

current_week_df = df[(df['Date'] >= start_of_week) & (df['Date'] <= end_of_week)]

st.markdown(
    f"""### <span style='color:red'>{len(current_week_df)}</span> Submissions for the week of {start_of_week.strftime('%B %d')}–{end_of_week.strftime('%B %d')} (week {current_week_number} of the year), {current_year}""",
    unsafe_allow_html=True
)

columns_to_show = ['Store Number', 'Store Name', 'CPM', 'Prototype', 'Week Label']
st.dataframe(current_week_df[columns_to_show].reset_index(drop=True), use_container_width=True)

# --- Password Protected Section ---
st.subheader("Generate Weekly Summary Report")

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    input_password = st.text_input("Enter Password", type="password")
    if st.button("Submit"):
        if input_password == "1234":
            st.session_state.authenticated = True
        else:
            st.error("❌ Incorrect password.")
    st.stop()

st.markdown("## Weekly Submission Volume by Year")
years = sorted(df['Year'].dropna().unique(), reverse=True)
for year in years:
    with st.expander(f"📁 {year}"):
        year_data = df[df['Year'] == year]
        weekly_counts = year_data.groupby('Week Label').size().reset_index(name='Count')
        for _, row in weekly_counts.iterrows():
            week = row['Week Label']
            count = row['Count']
            with st.expander(f" {week} — {count} submission(s)"):
                st.dataframe(year_data[year_data['Week Label'] == week].reset_index(drop=True))

# --- Data for Summary ---
df['Baseline'] = df['Baseline'].astype(str).str.strip()
baseline_df = df[df['Baseline'] == "/True"].copy()
baseline_df['Store Opening'] = pd.to_datetime(baseline_df['Store Opening'], errors='coerce')
baseline_map = baseline_df.set_index('Store Number')['Store Opening'].to_dict()

df['Store Opening'] = pd.to_datetime(df['Store Opening'], errors='coerce').dt.normalize()
baseline_df['Store Opening'] = pd.to_datetime(baseline_df['Store Opening'], errors='coerce').dt.normalize()

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

def compute_delta(row):
    baseline_open = baseline_map.get(row['Store Number'])
    if pd.isna(row['Store Opening']) or pd.isna(baseline_open):
        return 0
    return (row['Store Opening'] - baseline_open).days

df['Store Opening Delta'] = df.apply(compute_delta, axis=1)

def flag_delta(delta):
    if isinstance(delta, int) and abs(delta) > 5:
        return '<span style="color:red;font-weight:bold;">*</span>'
    return ""

df['Flag'] = df['Store Opening Delta'].apply(flag_delta)

keywords = [
    "behind schedule", "lagging", "delay", "critical path", "cpm impact", "work on hold", "stop work order",
    "reschedule", "off track", "schedule drifting", "missed milestone", "budget overrun", "cost impact",
    "change order pending", "claim submitted", "dispute", "litigation risk", "schedule variance",
    "material escalation", "labor shortage", "equipment shortage", "low productivity", "rework required",
    "defects found", "qc failure", "weather delays", "permit delays", "regulatory hurdles",
    "site access issues", "awaiting sign-off", "conflict", "identified risk", "mitigation", "forecast revised"
]

def check_notes(text):
    text_lower = str(text).lower()
    return any(kw in text_lower for kw in keywords)

df['Notes'] = df['Notes'].fillna("")
df['Notes Filtered'] = df['Notes'].apply(lambda x: x if check_notes(x) else "see report below")

summary_cols = ['Store Name', 'Store Number', 'Prototype', 'CPM', 'Flag', 'Store Opening Delta', 'Trend', 'Notes Filtered']
df_sorted = df.sort_values(['Store Number', 'Year Week'], ascending=[True, False])
summary_df = df_sorted.groupby('Store Number').first().reset_index()
summary_df = summary_df[summary_cols]

def create_trend_figure(trend_counts):
    hex_colors = {
        "held": "#FDC01A",
        "baseline": "#0E2D72",
        "pushed": "#E2231A",
        "pulled in": "#40C4F3",
        "no baseline dates": "#999999"
    }
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(trend_counts.index, trend_counts.values, color=[hex_colors.get(x, "#999") for x in trend_counts.index])
    ax.set_ylabel("Count")
    ax.set_xlabel("Trend")
    ax.set_title("Store Opening Trend Breakdown")
    ax.grid(axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout()
    return fig

def fig_to_base64(fig):
    buf = BytesIO()
    fig.savefig(buf, format="png", bbox_inches='tight')
    buf.seek(0)
    return base64.b64encode(buf.read()).decode()

def generate_weekly_summary(df, summary_df, password):
    today = datetime.date.today()
    start_of_week = today - datetime.timedelta(days=today.weekday() + 1 if today.weekday() != 6 else 0)
    start_of_week = start_of_week if today.weekday() != 6 else today
    end_of_week = start_of_week + datetime.timedelta(days=6)

    df_week = df[(df['Date'] >= start_of_week) & (df['Date'] <= end_of_week)].copy()
    summary_week_df = summary_df[summary_df['Store Number'].isin(df_week['Store Number'])].copy()

    trend_order = ["pulled in", "pushed", "held", "baseline", "no baseline dates"]
    trend_counts = summary_week_df['Trend'].value_counts().reindex(trend_order, fill_value=0)
    fig = create_trend_figure(trend_counts)
    img_base64 = fig_to_base64(fig)

    week_number = today.isocalendar()[1]
    year = today.year

    html = [
        "<html><head><style>",
        "body {font-family: Arial, sans-serif; padding: 20px; margin: 0 auto; max-width: 1200px; width: 95%; background-color: #fff;}",
        "h1 {text-align: center; font-size: 2em;}",
        "h2 {background: #cce5ff; padding: 10px; border-radius: 4px; font-size: 1.4em;}",
        ".entry {border: 1px solid #ccc; padding: 10px; margin: 10px 0; border-radius: 4px; background: #f9f9f9;}",
        ".label {font-weight: bold;}",
        "table {border-collapse: collapse; width: 100%; table-layout: fixed; word-wrap: break-word;}",
        "th, td {border: 1px solid #ddd; padding: 8px; text-align: center; word-wrap: break-word;}",
        "th {background-color: #f2f2f2; text-decoration: underline;}",
        "img {max-width: 90%; height: auto; display: block; margin: 20px auto;}",
        "ul {margin: 0; padding-left: 20px;}",
        "li {margin-bottom: 4px;}",

        # Optional mobile responsiveness
        "@media (max-width: 768px) { body {padding: 10px;} h1 {font-size: 1.4em;} h2 {font-size: 1.1em;} }",

        "</style></head><body>",
        f"<h1>{year} Week: {week_number} Weekly Summary Report</h1>",
        f'<img src="data:image/png;base64,{img_base64}">',
        "<h2>Trend Summary Table</h2>",
        trend_counts.rename_axis("Trend").reset_index().rename(columns={"index": "Trend", "Trend": "Count"}).to_html(index=False),
        "<table class='exec-summary'>",
        summary_week_df.to_html(index=False, escape=False, classes="exec-summary", border=0),
        "</table>",

    ]

    group_col = "Subject" if "Subject" in df_week.columns else "Store Name"
    for group_name, group_df in df_week.groupby(group_col):
        html.append(f"<h2>{group_name}</h2>")
        for _, row in group_df.iterrows():
            html.append(f"<div style='font-weight:bold; font-size:1.2em;'>{row.get('Store Number', '')} - {row.get('Store Name', '')}, {row.get('Prototype', '')} ({row.get('CPM', '')})</div>")

            date_fields = ["TCO", "Ops Walk", "Turnover", "Open to Train", "Store Opening"]
            html.append("<li><span class='label'>Dates:</span><ul>")
            for field in date_fields:
                val = row.get(field)
                try:
                    if isinstance(val, str) and val.strip():
                        val_date = pd.to_datetime(val, errors='coerce')
                    elif isinstance(val, (datetime.datetime, datetime.date)):
                        val_date = val
                    else:
                        val_date = None

                    if val_date is not None and not pd.isna(val_date):
                        val = val_date.strftime("%m/%d/%y")
                    else:
                        val = "N/A"
                except Exception:
                    val = str(val) if val else "N/A"

                html.append(f"<li style='margin-left: 40px;'><u>{field}</u>: {val}</li>")
            html.append("</ul></li>")

            notes = [re.sub(r"^[\s•\-–●]+", "", n) for n in str(row.get("Notes", "")).splitlines() if n.strip()]
            if notes:
                html.append("<li><span class='label'>Notes:</span><ul>")
                html += [f"<li style='margin-left: 40px;'>{n}</li>" for n in notes]
                html.append("</ul></li>")

            html.append("</ul></div>")

    html.append("</body></html>")
    return df_week, "".join(html)


if st.button("Generate Detailed Weekly Summary Report"):
    df_result, html = generate_weekly_summary(df, summary_df, password="1234")
    if html:
        st.markdown("### Weekly Summary")
        st.components.v1.html(html, height=1000, scrolling=True)
        st.download_button(
            label="📥 Download Summary as HTML",
            data=html.encode('utf-8'),
            file_name=f"Weekly_Summary_{datetime.datetime.now().strftime('%Y%m%d')}.html",
            mime="text/html",
            use_container_width=True
        )
