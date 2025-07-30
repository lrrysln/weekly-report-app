import streamlit as st
import pandas as pd
import datetime
import re
import matplotlib.pyplot as plt
import gspread
from google.oauth2.service_account import Credentials
import base64
from io import BytesIO

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

if "gcp_service_account" not in st.secrets:
    st.error("Service account credentials not found.")
    st.stop()

creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=SCOPES)
client = gspread.authorize(creds)

SPREADSHEET_ID = "1cfr5rCRoRXuDJonarDbokznlaHHVpn1yUfTwo_ePL3w"
WORKSHEET_NAME = "Sheet1"

@st.cache_data(ttl=600)
def load_data():
    try:
        sheet = client.open_by_key(SPREADSHEET_ID).worksheet(WORKSHEET_NAME)
        return pd.DataFrame(sheet.get_all_records())
    except Exception as e:
        st.error(f"Failed to load data from Google Sheet: {e}")
        return pd.DataFrame()

df = load_data()
if df.empty:
    st.warning("⚠️ No data loaded from Google Sheet yet.")
    st.stop()
df.columns = [c.strip() for c in df.columns]

date_cols = [col for col in df.columns if any(k in col for k in ["⚪ Baseline", "TCO", "Walk", "Turnover", "Open to Train", "Store Opening", "Start"])]
for col in date_cols:
    df[col] = pd.to_datetime(df[col], errors='coerce')

if "⚪ Baseline Store Opening" in df.columns:
    df['Store Opening Delta'] = (
        pd.to_datetime(df['Store Opening'], errors='coerce') -
        pd.to_datetime(df['⚪ Baseline Store Opening'], errors='coerce')
    ).dt.days
else:
    df['Store Opening Delta'] = None

df['Flag'] = df['Store Opening Delta'].apply(lambda x: "Critical" if pd.notna(x) and x >= 5 else "")

trend_map = {}
grouped = df.groupby('Store Name')
for store, grp in grouped:
    grp = grp.sort_values('Year Week')
    prev = None
    for idx, row in grp.iterrows():
        cur = pd.to_datetime(row.get("Store Opening"), errors='coerce')
        base = pd.to_datetime(row.get("⚪ Baseline Store Opening"), errors='coerce')
        if pd.isna(cur):
            trend_map[idx] = "🟡 Held"
        elif pd.notna(base) and cur == base:
            trend_map[idx] = "⚪ Baseline"
        elif prev is None:
            trend_map[idx] = "🟡 Held"
        else:
            trend_map[idx] = "🟢 Pulled In" if cur < prev else "🔴 Pushed" if cur > prev else "🟡 Held"
        prev = cur
df['Trend'] = df.index.map(trend_map)

keywords = ["behind schedule", "lagging", "delay", "critical path", "cpm impact", "work on hold",
            "stop work order", "reschedule", "off track", "schedule drifting", "missed milestone",
            "budget overrun", "cost impact", "change order pending", "claim submitted", "dispute",
            "litigation risk", "schedule variance", "material escalation", "labor shortage",
            "equipment shortage", "low productivity", "rework required", "defects found", "qc failure",
            "weather delays", "permit delays", "regulatory hurdles", "site access issues",
            "awaiting sign‑off", "conflict", "identified risk", "mitigation", "forecast revised"]

def check_notes(text):
    text = str(text).lower()
    return any(kw in text for kw in keywords)

df['Notes'] = df['Notes'].fillna("")
df['Notes Filtered'] = df['Notes'].apply(lambda x: x if check_notes(x) else "see report below")

summary_cols = ['Store Name', 'Store Number', 'Prototype', 'CPM', 'Flag', 'Store Opening Delta', 'Trend', 'Notes Filtered']
summary_df = df[summary_cols].drop_duplicates(subset=['Store Name']).reset_index(drop=True)

def plot_trends(df):
    counts = df['Trend'].value_counts().reindex(['🟢 Pulled In','🔴 Pushed','🟡 Held','⚪ Baseline'], fill_value=0)
    colors = {'🟢 Pulled In':'green','🔴 Pushed':'red','🟡 Held':'yellow','⚪ Baseline':'grey'}
    fig, ax = plt.subplots()
    ax.bar(counts.index, counts.values, color=[colors[t] for t in counts.index])
    for bar in ax.patches:
        ax.annotate(f"{int(bar.get_height())}", (bar.get_x()+bar.get_width()/2, bar.get_height()), ha='center', va='bottom')
    ax.set_ylabel("Count"); ax.set_xlabel("Trend")
    plt.tight_layout()
    return fig

def fig_to_base64(fig):
    buf = BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight')
    buf.seek(0)
    return base64.b64encode(buf.read()).decode()

def generate_weekly_summary(df, summary_df, fig, password):
    if password != "1234":
        return None, "❌ Incorrect password."
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
        f'<img src="data:image/png;base64,{img_base64}" style="max-width:600px; display:block; margin:auto;">',
        "<h2>Executive Summary</h2>",
        summary_df.to_html(index=False, escape=False),
        "<hr>"
    ]

    group_col = "Subject" if "Subject" in df.columns else "Store Name"
    for group_name, grp in df.groupby(group_col):
        html.append(f"<h2>{group_name}</h2>")
        for _, row in grp.iterrows():
            html.append('<div class="entry"><ul>')
            html.append(f"<li><span class='label'>Store Name:</span> {row.get('Store Name','')}</li>")
            html.append(f"<li><span class='label'>Store Number:</span> {row.get('Store Number','')}</li>")
            html.append(f"<li><span class='label'>Prototype:</span> {row.get('Prototype','')}</li>")
            html.append(f"<li><span class='label'>CPM:</span> {row.get('CPM','')}</li>")
            html.append("<li><span class='label'>Dates:</span><ul>")
            for field in ["TCO","Ops Walk","Turnover","Open to Train","Store Opening"]:
                val = row.get(field)
                base_val = row.get(f"⚪ Baseline {field}")
                if pd.notna(base_val) and val == base_val:
                    html.append(f"<li><b style='color:red;'> Baseline</b>: {field} - {val}</li>")
                else:
                    html.append(f"<li>{field}: {val}</li>")
            html.append("</ul></li>")
            notes = [re.sub(r"^[\s•\-–●]+","",line) for line in str(row.get('Notes',"")).splitlines() if line.strip()]
            if notes:
                html.append("<li><span class='label'>Notes:</span><ul>")
                html += [f"<li>{n}</li>" for n in notes]
                html.append("</ul></li>")
            html.append("</ul></div>")
    html.append("</body></html>")
    return df, "".join(html)

st.subheader("🔐 Generate Weekly Summary Report")
password = st.text_input("Enter Password", type="password")

fig = plot_trends(summary_df)

if password:
    df_result, html = generate_weekly_summary(df, summary_df, fig, password)
    if html and "Incorrect password" not in html:
        if st.button("Generate Report"):
            st.markdown("### Weekly Summary")
            st.components.v1.html(html, height=800, scrolling=True)
            st.download_button(
                "Download Summary as HTML",
                data=html,
                file_name=f"Weekly_Summary_{datetime.datetime.now().strftime('%Y%m%d')}.html",
                mime="text/html"
            )
    elif html:
        st.error(html)

st.subheader("📋 Submitted Reports Overview")
st.dataframe(summary_df[['Store Number','Store Name','Prototype','CPM']])
