import streamlit as st
import pandas as pd
from datetime import date
import os
from pathlib import Path

# ---------------- CONFIG ----------------
USE_TEST_FILE = True  # <-- set to False when ready to use real SharePoint-synced file

# Real OneDrive-synced path (update when ready to go live)
REAL_EXCEL_PATH = r"C:\Users\lsloan\RaceTrac\Construction and Engineering Leadership - Documents\General\Larry Sloan\Construction Weekly Updates\Construction Weekly Updates.xlsx"

# Local test file
TEST_EXCEL_PATH = "test_weekly_report.xlsx"

EXCEL_PATH = TEST_EXCEL_PATH if USE_TEST_FILE else REAL_EXCEL_PATH
SHEET_NAME = "Sheet1"

# Column schema for the Excel log
COLUMNS = [
    "Week",
    "Project Name",
    "Milestone",
    "Baseline Date",
    "Last Week Date",
    "This Week Date",
    "Δ Days",
    "Trend",
    "# Changes",
    "Confidence",
    "Notes",
]


# ---------------- HELPERS ----------------
def get_week_label(d: date | None = None) -> str:
    d = d or date.today()
    wk = d.isocalendar()[1]
    return f"Week {wk} {d.year}"


def ensure_file():
    """Create the Excel file with headers if it does not exist."""
    if not os.path.exists(EXCEL_PATH):
        df = pd.DataFrame(columns=COLUMNS)
        df.to_excel(EXCEL_PATH, index=False, sheet_name=SHEET_NAME)


def append_row(row_dict: dict):
    """Append a row to the Excel file."""
    ensure_file()
    df = pd.read_excel(EXCEL_PATH, engine="openpyxl")
    df = pd.concat([df, pd.DataFrame([row_dict])], ignore_index=True)
    df.to_excel(EXCEL_PATH, index=False, engine="openpyxl")


def compute_trend(baseline, last_week, this_week):
    """
    baseline/last_week/this_week are pandas Timestamps or NaT.
    Returns (delta_days, trend_icon).
    - Δ Days: this_week - baseline
    - Trend: compare this_week vs last_week
    """
    if pd.isna(this_week) or pd.isna(baseline):
        delta_days = None
    else:
        delta_days = (this_week - baseline).days

    if pd.isna(this_week) or pd.isna(last_week):
        trend = "❔"
    elif this_week > last_week:
        trend = "📉 Slipped"
    elif this_week < last_week:
        trend = "📈 Pulled"
    else:
        trend = "➖ Held"

    return delta_days, trend


def summarize_history(df: pd.DataFrame) -> pd.DataFrame:
    """
    Build an executive summary rollup from the history log (all weeks, all rows).
    Summary rows = latest row per (Project Name, Milestone), with baseline + last & this week comparisons.
    """
    if df.empty:
        return df

    # Convert date cols to datetime
    for col in ["Baseline Date", "Last Week Date", "This Week Date"]:
        df[col] = pd.to_datetime(df[col], errors="coerce")

    # Sort by Week insertion order (assume file is historical append; keep natural order)
    # If you want stricter ordering, parse Week column; here we just use row order.
    df = df.reset_index(drop=True)

    # Group by Project + Milestone
    rows = []
    for (proj, ms), g in df.groupby(["Project Name", "Milestone"]):
        g = g.reset_index(drop=True)

        # Baseline = first non-na baseline found in group
        baseline = g["Baseline Date"].dropna().iloc[0] if not g["Baseline Date"].dropna().empty else pd.NaT

        # Latest row for this group (most recent entry in file)
        latest = g.iloc[-1]
        this_week = latest["This Week Date"]

        # Last Week: take the most recent prior row (2nd to last) if present
        if len(g) > 1:
            last_week = g.iloc[-2]["This Week Date"]
        else:
            last_week = pd.NaT

        delta_days, trend = compute_trend(baseline, last_week, this_week)

        # # Changes = count of distinct This Week Dates in history (excluding NaT)
        changes = g["This Week Date"].dropna().nunique() - 1 if g["This Week Date"].dropna().nunique() > 0 else 0
        if changes < 0:
            changes = 0

        rows.append(
            {
                "Project Name": proj,
                "Milestone": ms,
                "Baseline": baseline.date().strftime("%m/%d/%y") if not pd.isna(baseline) else "",
                "Last Week": last_week.date().strftime("%m/%d/%y") if not pd.isna(last_week) else "",
                "This Week": this_week.date().strftime("%m/%d/%y") if not pd.isna(this_week) else "",
                "Δ Days": delta_days if delta_days is not None else "",
                "Trend": trend,
                "# Changes": changes,
                "Latest Confidence": latest.get("Confidence", ""),
                "Latest Notes": latest.get("Notes", ""),
            }
        )

    return pd.DataFrame(rows)


# ---------------- UI ----------------
st.title("📊 Milestone History Logger (Test Mode)" if USE_TEST_FILE else "📊 Milestone History Logger")

if USE_TEST_FILE:
    st.info("Test mode is ON. Data will be saved to a local file: `test_weekly_report.xlsx`.")

week_label = get_week_label()

with st.form("milestone_form", clear_on_submit=True):
    st.subheader(f"Submit Milestone Update ({week_label})")

    col1, col2 = st.columns(2)
    with col1:
        project_name = st.text_input("Project Name")
    with col2:
        milestone = st.selectbox(
            "Milestone",
            [
                "Store Opening",
                "TCO / CO",
                "POD Walk",
                "Turnover",
                "Open to Train",
                "Permit",
                "Other",
            ],
        )

    col3, col4, col5 = st.columns(3)
    with col3:
        baseline_date = st.date_input("Baseline Date")
    with col4:
        last_week_date = st.date_input("Last Week Date")
    with col5:
        this_week_date = st.date_input("This Week Date")

    confidence = st.selectbox("Confidence", ["Green", "Yellow", "Red", "N/A"], index=3)

    notes = st.text_area("Notes (each bullet on new line)", height=120, placeholder="- Equipment delay\n- Weather hold")

    # Buttons side-by-side
    c1, c2 = st.columns([1, 1])
    with c1:
        submit_btn = st.form_submit_button("Submit")
    with c2:
        gen_btn = st.form_submit_button("Generate Report")

# ---- HANDLE SUBMIT ----
if submit_btn:
    row_dict = {
        "Week": week_label,
        "Project Name": project_name,
        "Milestone": milestone,
        "Baseline Date": baseline_date.strftime("%Y-%m-%d"),
        "Last Week Date": last_week_date.strftime("%Y-%m-%d"),
        "This Week Date": this_week_date.strftime("%Y-%m-%d"),
        # We'll calculate Δ/Trend/#Changes when generating the report; store blanks in raw log
        "Δ Days": "",
        "Trend": "",
        "# Changes": "",
        "Confidence": confidence,
        "Notes": notes.strip(),
    }
    try:
        append_row(row_dict)
        st.success("✅ Entry logged.")
    except Exception as e:
        st.error(f"❌ Failed to log entry: {e}")

# ---- HANDLE GENERATE REPORT ----
if gen_btn:
    try:
        ensure_file()
        raw_df = pd.read_excel(EXCEL_PATH, engine="openpyxl")

        if raw_df.empty:
            st.warning("No data logged yet.")
        else:
            summary_df = summarize_history(raw_df)

            st.subheader("Executive Summary")
            st.dataframe(summary_df, use_container_width=True)

            # Quick metrics
            slipped = (summary_df["Trend"].str.contains("Slipped")).sum()
            pulled = (summary_df["Trend"].str.contains("Pulled")).sum()
            held = (summary_df["Trend"].str.contains("Held")).sum()

            m1, m2, m3 = st.columns(3)
            m1.metric("📉 Slipped", slipped)
            m2.metric("📈 Pulled In", pulled)
            m3.metric("➖ Held", held)

            # Download summary
            csv_data = summary_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                "Download Summary CSV",
                data=csv_data,
                file_name=f"{week_label}_milestone_summary.csv",
                mime="text/csv",
            )

    except Exception as e:
        st.error(f"❌ Failed to generate report: {e}")
