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
    st.error("Missing service account in secrets") 
    st.stop()

creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=SCOPES)
client = gspread.authorize(creds)

SPREADSHEET_ID = "1cfr5rCRoRXuDJonarDbokznlaHHVpn1yUfTwo_ePL3w"
WORKSHEET_NAME = "Sheet1"

@st.cache_data(ttl=600)
def load_data():
    try:
        # st.write("⏳ Using Spreadsheet ID:", SPREADSHEET_ID)
        sheet = client.open_by_key(SPREADSHEET_ID)
        # st.write("✅ Opened spreadsheet. Looking for worksheet:", WORKSHEET_NAME)
        worksheet = sheet.worksheet(WORKSHEET_NAME)
        # st.write("✅ Worksheet found. Fetching records...")
        records = worksheet.get_all_records()
        df = pd.DataFrame(records)
        # st.success("✅ Data loaded")
        return df
    except Exception as e:
        st.error(f"Failed loading: {e}")
        return pd.DataFrame()


df = load_data()
if df.empty:
    st.warning("No data loaded")
    st.stop()

df.columns = [c.strip() for c in df.columns]
st.write("DEBUG df.columns:", list(df.columns))

# Ensure Baseline column exists and correct dtype
if "Baseline" not in df.columns:
    st.error("'Baseline' column missing.")
    st.stop()
df['Baseline'] = df['Baseline'].astype(str).str.strip().str.lower().map({'true': True, 'false': False})
# parse store-opening and baseline‑opening dates
df['Store Opening'] = pd.to_datetime(df['Store Opening'], errors='coerce')
df['Baseline Store Opening'] = pd.to_datetime(df.get('⚪ Baseline Store Opening', pd.NaT), errors='coerce')

# Group by store to assign baseline date and compute deltas + trends
trend_map = {}
delta_map = {}
baseline_date_by_store = {}

for store, grp in df.groupby('Store Name'):
    # sort entries chronologically or by any order—use index order or date
    grp = grp.sort_values('Store Opening').copy()
    # find baseline entry
    base_rows = grp[grp['Baseline'] == True]
    if not base_rows.empty:
        baseline_date = base_rows.iloc[0]['Store Opening']
        baseline_date_by_store[store] = baseline_date
    for idx, row in grp.iterrows():
        cur = row['Store Opening']
        is_base = bool(row['Baseline'])
        if is_base:
            trend_map[idx] = "⚪ Baseline"
            delta_map[idx] = 0
        else:
            baseline_date = baseline_date_by_store.get(store)
            if pd.notna(baseline_date) and pd.notna(cur):
                delta_map[idx] = (cur - baseline_date).days
            else:
                delta_map[idx] = None

        # For trend (non-baseline): compare to previous date in this group
        prev_idx = grp.index[grp.index.get_loc(idx) - 1] if grp.index.get_loc(idx) > 0 else None
        if is_base:
            pass
        elif prev_idx is not None:
            prev_date = grp.loc[prev_idx, 'Store Opening']
            if pd.isna(cur):
                trend_map[idx] = "🟡 Held"
            elif cur < prev_date:
                trend_map[idx] = "🟢 Pulled In"
            elif cur > prev_date:
                trend_map[idx] = "🔴 Pushed"
            else:
                trend_map[idx] = "🟡 Held"
        else:
            trend_map[idx] = "🟡 Held"

df['Store Opening Delta'] = df.index.map(delta_map)
df['Trend'] = df.index.map(trend_map)
df['Flag'] = df['Store Opening Delta'].apply(lambda x: "Critical" if pd.notna(x) and x >= 5 else "")

# Notes filter logic unchanged
keywords = [  "delay", "delayed", "issue", "problem", "risk", "concern", 
    "escalate", "critical", "slip", "slipped", "pushed", "hold", 
    "change", "reschedule", "blocker", "pending", "approval" ]  
def check_notes(x): return any(kw in str(x).lower() for kw in keywords)
df['Notes'] = df['Notes'].fillna("")
df['Notes Filtered'] = df['Notes'].apply(lambda x: x if check_notes(x) else "see report below")

# Executive summary
summary_df = df.sort_values(['Store Name']).drop_duplicates('Store Name')[
    ['Store Name','Store Number','Prototype','CPM','Flag','Store Opening Delta','Trend','Notes Filtered']
].reset_index(drop=True).rename(columns={'Notes Filtered':'Notes'})

# Plot counts with baseline included
counts = summary_df['Trend'].value_counts().reindex(['🟢 Pulled In','🔴 Pushed','🟡 Held','⚪ Baseline'], fill_value=0)
colors = {'🟢 Pulled In':'green','🔴 Pushed':'red','🟡 Held':'yellow','⚪ Baseline':'grey'}
fig, ax = plt.subplots()
ax.bar(counts.index, counts.values, color=[colors[t] for t in counts.index])
for bar in ax.patches:
    ax.annotate(f"{int(bar.get_height())}", (bar.get_x()+bar.get_width()/2, bar.get_height()), ha='center', va='bottom')
ax.set_ylabel("Count"); ax.set_xlabel("Trend")
plt.tight_layout()

# Your unchanged report‐HTML generation code
def fig_to_base64(fig):
    buf = BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight')
    buf.seek(0)
    return base64.b64encode(buf.read()).decode()

def generate_weekly_summary(df, summary_df, fig, password):
    if password != "1234":
        return None, "❌ Incorrect password."
    img_b64 = fig_to_base64(fig)
    today = datetime.date.today(); week = today.isocalendar()[1]; year = today.year
    html = [
        "<html><head><style>",
        "body{font-family:Arial;padding:20px}", "h1{text-align:center}",
        "h2{background:#cce5ff;padding:10px;border-radius:4px}",
        ".entry{…}", "ul{…}", ".label{…}", "table{…}", "th, td{…}", "</style></head><body>",
        f"<h1>{year} Week: {week} Weekly Summary Report</h1>",
        f'<img src="data:image/png;base64,{img_b64}" style="max-width:600px; display:block; margin:auto;">',
        "<h2>Executive Summary</h2>",
        summary_df.to_html(index=False, escape=False),
        "<hr>"
    ]
    group_col = "Subject" if "Subject" in df.columns else "Store Name"
    for gm, grp in df.groupby(group_col):
        html.append(f"<h2>{gm}</h2>")
        for _, row in grp.iterrows():
            html.append('<div class="entry"><ul>')
            html.append(f"<li><span class='label'>Store Name:</span> {row['Store Name']}</li>")
            html.append(f"<li><span class='label'>Store Number:</span> {row['Store Number']}</li>")
            html.append(f"<li><span class='label'>Prototype:</span> {row['Prototype']}</li>")
            html.append(f"<li><span class='label'>CPM:</span> {row['CPM']}</li>")
            html.append("<li><span class='label'>Dates:</span><ul>")
            for f in ["TCO","Ops Walk","Turnover","Open to Train","Store Opening"]:
                v = row.get(f)
                bv = row.get(f"⚪ Baseline {f}")
                if pd.notna(bv) and v == bv:
                    html.append(f"<li><b style='color:red;'> Baseline</b>: {f} - {v}</li>")
                else:
                    html.append(f"<li>{f}: {v}</li>")
            html.append("</ul></li>")
            notes = [re.sub(r"^[\s•\-–●]+","", ln) for ln in str(row['Notes']).splitlines() if ln.strip()]
            if notes:
                html.append("<li><span class='label'>Notes:</span><ul>")
                html += [f"<li>{n}</li>" for n in notes]
                html.append("</ul></li>")
            html.append("</ul></div>")
    html.append("</body></html>")
    return df, "".join(html)

st.subheader("🔐 Generate Weekly Summary Report")
pwd = st.text_input("Enter Password", type="password")
if pwd and st.button("Generate Report"):
    df_r, html = generate_weekly_summary(df, summary_df, fig, pwd)
    if html and "Incorrect password" not in html:
        st.markdown("### Weekly Summary")
        st.components.v1.html(html, height=800, scrolling=True)
        st.download_button("Download HTML", data=html,
                            file_name=f"Weekly_Summary_{datetime.datetime.now().strftime('%Y%m%d')}.html", mime="text/html")
    else:
        st.error(html)

st.subheader("📋 Submitted Reports Overview")
st.dataframe(summary_df[['Store Number','Store Name','Prototype','CPM']])
