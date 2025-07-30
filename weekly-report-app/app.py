import streamlit as st
import pandas as pd
import base64
import io
from datetime import datetime, date
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')

st.set_page_config(layout="wide")
st.title("2025 Week: 31 Weekly Summary Report")

# --- File uploader ---
uploaded_file = st.file_uploader("Upload Excel File", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)

    # --- Capitalize first letter of each word in 'Store Name' column ---
    if 'Store Name' in df.columns:
        df['Store Name'] = df['Store Name'].str.title()

    # --- Format date columns ---
    date_fields = ['CPM Date', 'Start Date', 'TCO Date', 'Turnover Date']
    for field in date_fields:
        if field in df.columns:
            df[field] = pd.to_datetime(df[field], errors='coerce').dt.strftime('%m/%d')

    # --- Trend logic ---
    for field in date_fields:
        baseline_col = f'Baseline {field}'
        if baseline_col in df.columns:
            df[baseline_col] = pd.to_datetime(df[baseline_col], errors='coerce').dt.strftime('%m/%d')
            df[field + ' Trend'] = df.apply(
                lambda row: 'baseline' if row[field] == row[baseline_col] else (
                    'pulled in' if pd.to_datetime(row[field], errors='coerce') < pd.to_datetime(row[baseline_col], errors='coerce') else (
                        'pushed' if pd.to_datetime(row[field], errors='coerce') > pd.to_datetime(row[baseline_col], errors='coerce') else 'held'
                    )
                ), axis=1
            )

    # --- Summary section ---
    summary_html = "<h2 style='text-align:center;'>Executive Summary</h2><ul>"
    trend_counts = {"pulled in": 0, "pushed": 0, "held": 0, "baseline": 0}

    for field in date_fields:
        trend_col = field + ' Trend'
        if trend_col in df.columns:
            counts = df[trend_col].value_counts().to_dict()
            for key in trend_counts:
                trend_counts[key] += counts.get(key, 0)

    for trend, count in trend_counts.items():
        color = {'pulled in': 'green', 'pushed': 'red', 'held': 'orange', 'baseline': 'gray'}[trend]
        summary_html += f"<li><b style='color:{color};'>{trend.title()}</b>: {count}</li>"
    summary_html += "</ul>"

    # --- Grouped notes display ---
    group_col = 'Subject' if 'Subject' in df.columns else df.columns[0]
    grouped = df.groupby(group_col)

    html = [summary_html, "<hr>"]
    for group_name, group_df in grouped:
        html.append(f"<h3 style='margin-top:20px;'>{group_name}</h3><ul>")
        for _, row in group_df.iterrows():
            store_name = row.get('Store Name', 'N/A')
            html.append(f"<li><b>{store_name}</b><ul>")
            for field in date_fields:
                date_val = row.get(field, '')
                baseline_val = row.get(f'Baseline {field}', '')
                trend = row.get(field + ' Trend', 'unknown')
                if pd.notna(date_val):
                    label = f"<span style='color:red; font-weight:bold;'>Baseline</span> " if date_val == baseline_val else ""
                    html.append(f"<li>{field}: {label}{date_val} ({trend})</li>")
            notes = str(row.get('Notes', '')).strip()
            if notes:
                note_lines = notes.split('\n')
                html.append("<li>Notes:<ul>")
                for line in note_lines:
                    html.append(f"<li>{line}</li>")
                html.append("</ul></li>")
            html.append("</ul></li>")
        html.append("</ul>")

    report_html = "".join(html)
    st.markdown(report_html, unsafe_allow_html=True)

    # --- Generate bar chart ---
    fig, ax = plt.subplots()
    ax.bar(trend_counts.keys(), trend_counts.values(), color=["green", "red", "orange", "gray"])
    ax.set_title("Weekly Trend Summary")
    ax.set_ylabel("Count")
    st.pyplot(fig)

    # --- Encode HTML for download ---
    html_bytes = report_html.encode('utf-8')
    b64 = base64.b64encode(html_bytes).decode()
    href = f'<a href="data:text/html;base64,{b64}" download="2025_Week_31_Report.html">Download Report as HTML</a>'
    st.markdown(href, unsafe_allow_html=True)

    # --- Optional Image Output (if needed later) ---
    # img_buf = io.BytesIO()
    # fig.savefig(img_buf, format='png')
    # img_buf.seek(0)
    # img_base64 = base64.b64encode(img_buf.read()).decode()
    # st.markdown(f'<img src="data:image/png;base64,{img_base64}" style="max-width:600px; display:block; margin:auto;">', unsafe_allow_html=True)
