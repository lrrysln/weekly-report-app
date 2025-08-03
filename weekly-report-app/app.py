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

# Clean column names
df.columns = df.columns.str.strip()

# Format store names
df['Store Name'] = df['Store Name'].str.title()

# Convert date columns to datetime
df['Store Opening'] = pd.to_datetime(df['Store Opening'], errors='coerce')
df['Baseline'] = df['Baseline'].astype(str).str.strip()
df['Store Number'] = df['Store Number'].astype(str).str.strip()

# Separate baseline & non-baseline entries
baseline_df = df[df['Baseline'] == "/True"].copy()
baseline_df_sorted = baseline_df.sort_values(by='Store Opening', ascending=False)
baseline_map = baseline_df_sorted.drop_duplicates(subset='Store Number', keep='first')\
                                 .set_index('Store Number')['Store Opening'].to_dict()

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
    elif current_open == baseline_open:
        return "held"
    
    return "no baseline dates"

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

st.subheader("🔐 Generate Weekly Summary Report")
password = st.text_input("Enter Password", type="password")

# Custom Bar Colors
def create_trend_figure(trend_counts):
    hex_colors = {
        "held": "#FDC01A",
        "baseline": "#0E2D72",
        "pushed": "#E2231A",
        "pulled in": "#40C4F3",
        "no baseline dates": "#999999"
    }
    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.bar(trend_counts.index, trend_counts.values,
                  color=[hex_colors.get(x, "#999") for x in trend_counts.index])
    ax.set_ylabel("Count")
    ax.set_xlabel("Trend")
    ax.set_title("📊 Store Opening Trend Breakdown")
    ax.grid(axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout()
    return fig

def fig_to_base64(fig):
    buf = BytesIO()
    fig.savefig(buf, format="png", bbox_inches='tight')
    buf.seek(0)
    return base64.b64encode(buf.read()).decode()

def generate_weekly_summary(df, summary_df, password):
    if password != "1234":
        return None, "❌ Incorrect password."

    trend_order = ["pulled in", "pushed", "held", "baseline", "no baseline dates"]
    trend_counts = summary_df['Trend'].value_counts().reindex(trend_order, fill_value=0)
    fig = create_trend_figure(trend_counts)
    img_base64 = fig_to_base64(fig)

    today = datetime.date.today()
    week_number = today.isocalendar()[1]
    year = today.year

    html = [
        "<html><head><style>",
        "body{font-family:Arial;padding:20px}",
        "h1{text-align:center}",
        "h2{background:#cce5ff;padding:10px;border-radius:4px}",
        ".entry{border:1px solid #ccc;padding:10px;margin:10px 0;border-radius:4px;background:#f9f9f9}",
        "ul{margin:0;padding-left:20px}",
        ".label{font-weight:bold}",
        "table {border-collapse: collapse; width: 100%; text-align: center;}",
        "th, td {border: 1px solid #ddd; padding: 8px; text-align: center;}",
        "th {background-color: #f2f2f2;}",
        "</style></head><body>",
        f"<h1>{year} Week: {week_number} Weekly Summary Report</h1>",
        f'<img src="data:image/png;base64,{img_base64}" style="max-width:800px; display:block; margin:auto;">',
        "<h2>Trend Summary Table</h2>",
        trend_counts.rename_axis("Trend").reset_index().rename(columns={"index": "Trend", "Trend": "Count"}).to_html(index=False),
        "<h2>Executive Summary</h2>",
        summary_df.to_html(index=False, escape=False),
        "<hr>"
    ]

group_col = "Subject" if "Subject" in df.columns else "Store Name"
for group_name, group_df in df.groupby(group_col):
    html.append(f"<h2>{group_name}</h2>")
    for _, row in group_df.iterrows():
        store_number = row.get('Store Number', '')
        store_name = row.get('Store Name', '')
        prototype = row.get('Prototype', '')
        cpm = row.get('CPM', '')
        html.append(f"<div style='font-weight:bold; font-size:1.2em;'>{store_number} - {store_name}, {prototype} ({cpm})</div>")

        date_fields = ["TCO", "Ops Walk", "Turnover", "Open to Train", "Store Opening"]
        html.append("<li><span class='label'>Dates:</span><ul>")
        for field in date_fields:
            val = row.get(field)

            # Check if the value is a valid date before formatting
            if isinstance(val, (datetime.datetime, datetime.date)) and pd.notna(val):
                val_str = val.strftime("%m/%d/%y")
            else:
                val_str = ""  # or "N/A" if you'd prefer

            baseline_val = row.get(f"⚪ Baseline {field}")
            if pd.notna(baseline_val) and val_str == baseline_val:
                html.append(f"<li><b style='color:red;'> Baseline</b>: {field} - {val_str}</li>")
            else:
                html.append(f"<li>{field}: {val_str}</li>")
        html.append("</ul></li>")

        # ✅ This is now correctly indented
        notes = [re.sub(r"^[\s•\-–●]+", "", n) for n in str(row.get("Notes", "")).splitlines() if n.strip()]
        if notes:
            html.append("<li><span class='label'>Notes:</span><ul>")
            html += [f"<li style='margin-left: 40px;'>{n}</li>" for n in notes]
            html.append("</ul></li>")

        html.append("</ul></div>")

html.append("</body></html>")
return df, "".join(html)

if st.button("Generate Report"):
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
