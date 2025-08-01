import streamlit as st
import pandas as pd
from datetime import datetime

# Streamlit page setup
st.set_page_config(page_title="Weekly Construction Summary", layout="wide")
st.title("📅 Weekly Construction Report Summary")

# Upload Excel file
uploaded_file = st.file_uploader("Upload Excel File", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)

    # Clean date columns
    df['Store Opening'] = pd.to_datetime(df['Store Opening'], errors='coerce')
    df['⚪ Baseline Store Opening'] = pd.to_datetime(df['⚪ Baseline Store Opening'], errors='coerce')

    # Sort to calculate trend
    df.sort_values(by=['Store Number', 'Year Week'], inplace=True)
    trends = []
    last_store_dates = {}

    for _, row in df.iterrows():
        store = row['Store Number']
        curr_open = row['Store Opening']
        baseline = row['⚪ Baseline Store Opening']
        prev_open = last_store_dates.get(store)

        if pd.isna(curr_open):
            trend = "🟡 Held"
        elif pd.notna(baseline) and curr_open == baseline:
            trend = "⚪ Baseline"
        elif prev_open:
            if curr_open < prev_open:
                trend = "🟢 Pulled In"
            elif curr_open > prev_open:
                trend = "🔴 Pushed"
            else:
                trend = "🟡 Held"
        else:
            trend = "🟡 Held"

        trends.append(trend)
        last_store_dates[store] = curr_open

    df['Trend'] = trends

    # ---- Report Display ----
    st.subheader("📝 Executive Summary")

    for _, row in df.iterrows():
        header = f"<span style='font-size:18px'><strong>{row['Store Number']} - {row['Store Name']}, {row['Prototype']} ({row['CPM']})</strong></span>"
        st.markdown(header, unsafe_allow_html=True)

        for field in ['Notes', 'Milestone Risk', 'Support Needed', 'Schedule Risk']:
            content = row.get(field)
            if pd.notna(content) and str(content).strip():
                for line in str(content).split('\n'):
                    line = line.strip()
                    if line:
                        st.markdown(f"- **{line}**")

        st.markdown("---")

    # ---- Trend Chart ----
    st.subheader("📊 Trend Summary")

    trend_counts = df['Trend'].value_counts().reindex(
        ['🟢 Pulled In', '🔴 Pushed', '⚪ Baseline', '🟡 Held'], fill_value=0
    )

    st.bar_chart(trend_counts)

else:
    st.info("Upload an Excel file with the required columns to begin.")
