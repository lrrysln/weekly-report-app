import streamlit as st
import pandas as pd
import datetime
import re
import gspread
from google.oauth2.service_account import Credentials
import plotly.express as px
import base64
from io import BytesIO

# --- Google Sheets Setup ---
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
    st.warning("⚠️ No data loaded from Google Sheet.")
    st.stop()

# --- Preprocessing ---
df.columns = df.columns.str.strip()
df["Store Name"] = df["Store Name"].str.title()
df["Store Number"] = df["Store Number"].astype(str).str.strip()

for col in ["TCO", "Ops Walk", "Turnover", "Open to Train", "Store Opening"]:
    df[col] = pd.to_datetime(df[col], errors="coerce")
for col in [f"Baseline {c}" for c in ["TCO", "Ops Walk", "Turnover", "Open to Train", "Store Opening"]]:
    if col in df.columns:
        df[col] = pd.to_datetime(df[col], errors="coerce")

# --- Trend logic ---
def build_trend_summary(df):
    date_fields = ["TCO", "Ops Walk", "Turnover", "Open to Train", "Store Opening"]
    trend_list, delta_list = [], []

    for _, row in df.iterrows():
        baseline_dates = [row.get(f"Baseline {col}") for col in date_fields]
        if all(pd.isna(d) or d == "" for d in baseline_dates):
            trend_list.append("No Baseline Dates")
            delta_list.append(0)
        else:
            actual = row.get("Store Opening")
            baseline = row.get("Baseline Store Opening")
            if pd.notna(actual) and pd.notna(baseline):
                delta = (actual - baseline).days
                delta_list.append(delta)
                trend_list.append("Pushed" if delta > 0 else "Pulled In" if delta < 0 else "Held")
            else:
                trend_list.append("No Baseline Dates")
                delta_list.append(0)

    df["Delta Days"] = delta_list
    df["Trend"] = trend_list
    return df

df = build_trend_summary(df)

# --- Notes filter ---
keywords = ["behind schedule", "delay", "critical path", "work on hold", "stop work", "reschedule", "off track"]
df["Notes"] = df["Notes"].fillna("")
df["Notes Filtered"] = df["Notes"].apply(lambda x: x if any(k in x.lower() for k in keywords) else "see report below")

# --- Summary table ---
summary_cols = ['Store Name', 'Store Number', 'Prototype', 'CPM', 'Delta Days', 'Trend', 'Notes Filtered']
summary_df = df[summary_cols].drop_duplicates(subset=["Store Name"]).reset_index(drop=True)

# --- UI ---
st.subheader("📋 Submitted Reports Overview")
st.markdown(f"<h4><b style='color:red'>{len(summary_df)}</b> form responses have been submitted</h4>", unsafe_allow_html=True)
st.dataframe(summary_df, use_container_width=True)

st.subheader("🔐 Generate Weekly Summary Report")
password = st.text_input("Enter Password", type="password")

# --- Bar Chart ---
def render_trend_bar(df):
    trend_counts = df["Trend"].value_counts().reindex(["Held", "Baseline", "Pushed", "Pulled In", "No Baseline Dates"], fill_value=0)
    color_map = {
        "Held": "#FDC01A",
        "Baseline": "#0E2D72",
        "Pushed": "#E2231A",
        "Pulled In": "#40C4F3",
        "No Baseline Dates": "#cccccc"
    }
    fig = px.bar(
        x=trend_counts.index,
        y=trend_counts.values,
        labels={"x": "Trend", "y": "Count"},
        color=trend_counts.index,
        color_discrete_map=color_map,
        title="Trend Breakdown"
    )
    fig.update_layout(xaxis_title="Trend", yaxis_title="Count", showlegend=False)
    return fig

# --- HTML Report ---
def build_html_report(df, summary_df):
    today = datetime.date.today()
    week_number = today.isocalendar()[1]
    year = today.year

    trend_counts = summary_df["Trend"].value_counts().reindex(["Pulled In", "Pushed", "Held", "No Baseline Dates"], fill_value=0)

    html = [
        "<html><head><style>",
        "body{font-family:Arial;padding:20px;font-size:14px;}",
        "h1{text-align:center}",
        "h2{background:#f2f2f2;padding:10px;border-radius:4px;}",
        ".store-header{font-weight:bold;font-size:16px;margin-top:10px;}",
        "ul{margin:0;padding-left:20px;}",
        ".label{font-weight:bold;}",
        "table{width:100%;border-collapse:collapse;}",
        "th,td{border:1px solid #ddd;padding:8px;text-align:left;}",
        "th{background:#f4f4f4;}",
        "</style></head><body>",
        f"<h1>{year} - Week {week_number} Weekly Summary</h1>",
        "<h2>Trend Summary</h2>",
        trend_counts.rename_axis("Trend").reset_index().rename(columns={"index":"Trend", "Trend":"Count"}).to_html(index=False),
        "<h2>Executive Summary</h2>",
        summary_df.to_html(index=False, escape=False)
    ]

    group_col = "Subject" if "Subject" in df.columns else "Store Name"
    for group_name, group_df in df.groupby(group_col):
        html.append(f"<h2>{group_name}</h2>")
        for _, row in group_df.iterrows():
            header = f"{row.get('Store Number', '')} - {row.get('Store Name', '')}, {row.get('Prototype', '')} ({row.get('CPM', '')})"
            html.append(f"<div class='store-header'>{header}</div><ul>")

            date_fields = ["TCO", "Ops Walk", "Turnover", "Open to Train", "Store Opening"]
            html.append("<li><span class='label'>Dates:</span><ul>")
            for field in date_fields:
                val = row.get(field)
                baseline_val = row.get(f"Baseline {field}")
                if pd.notna(baseline_val) and val == baseline_val:
                    html.append(f"<li><b style='color:red;'>Baseline</b>: {field} - {val}</li>")
                else:
                    html.append(f"<li>{field}: {val}</li>")
            html.append("</ul></li>")

            notes = [re.sub(r"^[\s•\-–●]+", "", n) for n in str(row.get("Notes", "")).splitlines() if n.strip()]
            if notes:
                html.append("<li><span class='label'>Notes:</span><ul>")
                html += [f"<li>{n}</li>" for n in notes]
                html.append("</ul></li>")
            html.append("</ul>")

    html.append("</body></html>")
    return "".join(html)

# --- Generate Report ---
if st.button("Generate Report"):
    if password != "1234":
        st.error("❌ Incorrect password.")
    else:
        st.plotly_chart(render_trend_bar(df), use_container_width=True)
        html_report = build_html_report(df, summary_df)
        st.components.v1.html(html_report, height=1000, scrolling=True)
        st.download_button(
            "Download Summary as HTML",
            data=html_report,
            file_name=f"Weekly_Summary_{datetime.datetime.now().strftime('%Y%m%d')}.html",
            mime="text/html"
        )
