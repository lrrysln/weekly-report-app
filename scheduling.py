import streamlit as st
import pandas as pd
from io import StringIO

st.set_page_config(page_title="Schedule Upload & KPI Prep", layout="wide")

# --- Step 1: Show instructions and template download ---
st.title("📋 Schedule Data Upload & KPI Preparation")

st.markdown("""
Welcome! This app helps you prepare your schedule data for KPI analysis.

**Required Columns in your final data:**

- `project_id` (unique project or activity identifier)
- `project_name` (optional, but recommended)
- `planned_start` (planned start date, e.g. 2025-06-01)
- `planned_finish` (planned finish date)
- `actual_start` (actual start date)
- `actual_finish` (actual finish date)
- `planned_cost` (optional)
- `actual_cost` (optional)
- `delay_causes` (optional; can be semicolon or comma separated)

You can download a **CSV template** below to see expected columns and sample data.
""")

# CSV template content as string
csv_template = """project_id,project_name,planned_start,planned_finish,actual_start,actual_finish,planned_cost,actual_cost,delay_causes
P001,Site Excavation,2025-06-01,2025-06-10,2025-06-02,2025-06-11,100000,110000,weather;permits
P002,Foundation,2025-06-11,2025-06-20,2025-06-12,2025-06-21,150000,145000,materials
P003,Framing,2025-06-21,2025-07-05,2025-06-22,2025-07-06,200000,210000,
"""

st.download_button(
    label="Download CSV Template",
    data=csv_template,
    file_name="kpi_input_template.csv",
    mime="text/csv",
)

st.markdown("---")

# --- Step 2: Upload raw schedule file ---
uploaded_file = st.file_uploader("Upload your raw schedule CSV or Excel file", type=['csv', 'xls', 'xlsx'])

if uploaded_file:
    # Read uploaded file to DataFrame
    try:
        if uploaded_file.name.endswith('.csv'):
            raw_df = pd.read_csv(uploaded_file)
        else:
            raw_df = pd.read_excel(uploaded_file)
        st.success(f"Loaded {len(raw_df)} rows.")
        st.dataframe(raw_df.head())

        # --- Step 3: Let user map raw columns to expected KPI columns ---
        st.markdown("## Map your raw columns to expected KPI fields")

        cols = raw_df.columns.tolist()

        project_id_col = st.selectbox("Project ID column", options=cols)
        project_name_col = st.selectbox("Project Name column (optional)", options=["<None>"] + cols)
        planned_start_col = st.selectbox("Planned Start Date column", options=cols)
        planned_finish_col = st.selectbox("Planned Finish Date column", options=cols)
        actual_start_col = st.selectbox("Actual Start Date column", options=cols)
        actual_finish_col = st.selectbox("Actual Finish Date column", options=cols)
        planned_cost_col = st.selectbox("Planned Cost column (optional)", options=["<None>"] + cols)
        actual_cost_col = st.selectbox("Actual Cost column (optional)", options=["<None>"] + cols)
        delay_causes_col = st.selectbox("Delay Causes column (optional)", options=["<None>"] + cols)

        if st.button("Process & Preview KPI Data"):
            # Build cleaned DataFrame
            kpi_df = pd.DataFrame()
            kpi_df['project_id'] = raw_df[project_id_col]

            if project_name_col != "<None>":
                kpi_df['project_name'] = raw_df[project_name_col]
            else:
                kpi_df['project_name'] = None

            kpi_df['planned_start'] = pd.to_datetime(raw_df[planned_start_col], errors='coerce')
            kpi_df['planned_finish'] = pd.to_datetime(raw_df[planned_finish_col], errors='coerce')
            kpi_df['actual_start'] = pd.to_datetime(raw_df[actual_start_col], errors='coerce')
            kpi_df['actual_finish'] = pd.to_datetime(raw_df[actual_finish_col], errors='coerce')

            if planned_cost_col != "<None>":
                kpi_df['planned_cost'] = pd.to_numeric(raw_df[planned_cost_col], errors='coerce')
            else:
                kpi_df['planned_cost'] = None

            if actual_cost_col != "<None>":
                kpi_df['actual_cost'] = pd.to_numeric(raw_df[actual_cost_col], errors='coerce')
            else:
                kpi_df['actual_cost'] = None

            if delay_causes_col != "<None>":
                kpi_df['delay_causes'] = raw_df[delay_causes_col].fillna("")
            else:
                kpi_df['delay_causes'] = ""

            st.success("Processed KPI Data Preview:")
            st.dataframe(kpi_df.head())

            st.info("Now you can feed this `kpi_df` DataFrame into your KPI calculation functions or dashboards.")

    except Exception as e:
        st.error(f"Error loading file: {e}")
else:
    st.info("Upload a schedule CSV or Excel file to begin.")
