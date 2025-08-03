import streamlit as st
import pandas as pd
import datetime
import re
import matplotlib.pyplot as plt
import gspread
from google.oauth2.service_account import Credentials
import base64
from io import BytesIO
import plotly.express as px

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
for col in ["TCO", "Ops Walk", "Turnover", "Open to Train", "Store Opening"]:
    df[col] = pd.to_datetime(df[col], errors='coerce')
for col in [f"Baseline {c}" for c in ["TCO", "Ops Walk", "Turnover", "Open to Train", "Store Opening"]]:
    if col in df.columns:
        df[col] = pd.to_datetime(df[col], errors='coerce')

df['Store Number'] = df['Store Number'].astype(str).str.strip()

def build_trend_summary(df):
    date_fields = ["TCO", "Ops Walk", "Turnover", "Open to Train", "Store Opening"]
    trend_list = []
    delta_list = []

    for _, row in df.iterrows():
        baseline_dates = [row.get(f"Baseline {col}") for col in date_fields]
        if all(pd.isna(d) or d == "" for d in baseline_dates):
            trend_list.append("No Baseline Dates")
            delta_list.append(0)
        else:
            store_open = row.get("Store Opening")
            baseline_open = row.get("Baseline Store Opening")

            if pd.notna(store_open) and pd.notna(baseline_open):
                delta = (pd.to_datetime(store_open) - pd.to_datetime(baseline_open)).days
                delta_list.append(delta)
                if delta > 0:
                    trend_list.append("Pushed")
                elif delta < 0:
                    trend_list.append("Pulled In")
                else:
                    trend_list.append("Held")
            else:
                trend_list.append("No Baseline Dates")
                delta_list.append(0)

    df["Delta Days"] = delta_list
    df["Trend"] = trend_list
    return df

df = build_trend_summary(df)

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

summary_cols = ['Store Name', 'Store Number', 'Prototype', 'CPM', 'Delta Days', 'Trend', 'Notes Filtered']
summary_df = df[summary_cols].drop_duplicates(subset=['Store Name']).reset_index(drop=True)

st.subheader("📋 Submitted Reports Overview")
submitted_count = len(summary_df)
st.markdown(f"<h4><span style='color:red;'><b>{submitted_count}</b></span> form responses have been submitted</h4>", unsafe_allow_html=True)
st.dataframe(summary_df, use_container_width=True)

st.subheader("🔐 Generate Weekly Summary Report")
password = st.text_input("Enter Password", type="password")

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
    fig.update_layout(xaxis_title="Trend", yaxis_title="Number of Projects", showlegend=False)
    return fig

def build_html_report(df):
    html = [
        """
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; font-size: 14px; }
                .entry { margin-bottom: 20px; padding: 10px; border: 1px solid #ccc; border-radius: 8px; }
                .label { font-weight: bold; margin-right: 5px; }
                ul { padding-left: 20px; }
                table { width: 100%; border-collapse: collapse; margin-top: 20px; }
                th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                th { background-color: #f4f4f4; }
                .store-header { font-size: 16px; font-weight: bold; }
            </style>
        </head>
        <body>
        """
    ]

    group_col = "Subject" if "Subject" in df.columns else "Store Name"
    for group_name, group_df in df.groupby(group_col):
        html.append(f"<h2>{group_name}</h2>")
        for _, row in group_df.iterrows():
            store_number = str(row.get("Store Number", "")).strip()
            store_name = str(row.get("Store Name", "")).strip()
            prototype = str(row.get("Prototype", "")).strip()
            cpm = str(row.get("CPM", "")).strip()

            header_line = f"<div class='store-header'>{store_number} - {store_name}, {prototype} ({cpm})</div>"
            html.append(f'<div class="entry">{header_line}<ul>')

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

            notes = [re.sub(r"^[\\s\u2022\-\u2013\u25CF]+", "", n) for n in str(row.get("Notes", "")).splitlines() if n.strip()]
            if notes:
                html.append("<li><span class='label'>Notes:</span><ul>")
                html += [f"<li>{n}</li>" for n in notes]
                html.append("</ul></li>")

            html.append("</ul></div>")

    html.append("</body></html>")
    return "".join(html)

if st.button("Generate Report"):
    if password == "1234":
        st.plotly_chart(render_trend_bar(df))
        html_report = build_html_report(df)
        st.components.v1.html(html_report, height=1000, scrolling=True)
        st.download_button(
            "Download Summary as HTML",
            data=html_report,
            file_name=f"Weekly_Summary_{datetime.datetime.now().strftime('%Y%m%d')}.html",
            mime="text/html"
        )
    else:
        st.error("❌ Incorrect password.")

    trend_order = ["pulled in", "pushed", "held", "baseline"]
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
        f'<img src="data:image/png;base64,{img_base64}" style="max-width:600px; display:block; margin:auto;">',
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
            
            info_line = f"<div style='font-weight:bold; font-size:1.2em;'>{store_number} - {store_name}, {prototype} ({cpm})</div>"
            html.append(info_line)


            date_fields = ["TCO", "Ops Walk", "Turnover", "Open to Train", "Store Opening"]
            html.append("<li><span class='label'>Dates:</span><ul>")
            for field in date_fields:
                val = row.get(field)
                baseline_val = row.get(f"⚪ Baseline {field}")
                if pd.notna(baseline_val) and val == baseline_val:
                    html.append(f"<li><b style='color:red;'> Baseline</b>: {field} - {val}</li>")
                else:
                    html.append(f"<li>{field}: {val}</li>")
            html.append("</ul></li>")

            notes = [re.sub(r"^[\s•\-–●]+", "", n) for n in str(row.get("Notes", "")).splitlines() if n.strip()]
            if notes:
                html.append("<li><span class='label'>Notes:</span><ul>")
                html += [f"<li>{n}</li>" for n in notes]
                html.append("</ul></li>")

            html.append("</ul></div>")

    html.append("</body></html>")
    return df, "".join(html)

if st.button("Generate Report"):
    df_result, html = generate_weekly_summary(df, summary_df, password)
    if html is not None:
        st.markdown("### Weekly Summary")
        st.components.v1.html(html, height=900, scrolling=True)
        st.download_button(
            "Download Summary as HTML",
            data=html,
            file_name=f"Weekly_Summary_{datetime.datetime.now().strftime('%Y%m%d')}.html",
            mime="text/html"
        )
    else:
        st.error(html)
