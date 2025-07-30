import streamlit as st
from datetime import datetime
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from io import StringIO

# --- Google Sheets Setup ---
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]
creds = Credentials.from_service_account_info(
    st.secrets["gcp_service_account"], scopes=SCOPES
)
client = gspread.authorize(creds)
sheet = client.open("Your Google Sheet Name").sheet1

# --- Helper Functions ---
def get_current_year_week():
    now = datetime.now()
    year, week, _ = now.isocalendar()
    return f"{year} Week {week}"

def get_store_names():
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    return sorted(df["Store Name"].dropna().unique())

def get_previous_week_data(current_week):
    all_data = pd.DataFrame(sheet.get_all_records())
    return all_data[all_data["Yr Wk"] != current_week]

def extract_keyword_notes(note):
    keywords = ["delay", "permit", "weather", "inspection", "reschedule", "utility"]
    note_lower = note.lower()
    return any(keyword in note_lower for keyword in keywords)

def compute_store_opening_trend(prev_date, curr_date):
    if prev_date < curr_date:
        return "pushed"
    elif prev_date > curr_date:
        return "pulled in"
    else:
        return "held"

# --- App UI ---
st.title("Weekly Construction Update")

with st.form("project_form"):
    store_options = get_store_names()
    store_name = st.selectbox("Select Store", options=store_options)
    baseline_toggle = st.checkbox("Is this the baseline week for this project?", value=False)

    tco_date = st.date_input("TCO Date")
    ops_walk_date = st.date_input("Ops Walk Date")
    turnover_date = st.date_input("Turnover Date")
    open_to_train_date = st.date_input("Open to Train Date")
    store_opening_date = st.date_input("Store Opening Date")
    notes = st.text_area("Project Notes")

    submitted = st.form_submit_button("Submit")

    if submitted:
        year_week = get_current_year_week()

        row = {
            "Store Name": store_name,
            "Baseline": "Yes" if baseline_toggle else "No",
            "TCO": tco_date.strftime("%m/%d/%Y"),
            "Ops Walk": ops_walk_date.strftime("%m/%d/%Y"),
            "Turnover": turnover_date.strftime("%m/%d/%Y"),
            "Open to Train": open_to_train_date.strftime("%m/%d/%Y"),
            "Store Opening": store_opening_date.strftime("%m/%d/%Y"),
            "Notes": notes,
            "Yr Wk": year_week
        }

        sheet.append_row(list(row.values()))
        st.success("Submission saved!")

# --- Password-Protected Summary ---
password = st.text_input("Enter password to view executive summary", type="password")
if password == st.secrets["report_password"]:
    data = pd.DataFrame(sheet.get_all_records())
    current_week = get_current_year_week()
    current_data = data[data["Yr Wk"] == current_week]
    previous_data = get_previous_week_data(current_week)

    def parse_date_safe(val):
        try:
            return datetime.strptime(val, "%m/%d/%Y")
        except Exception:
            return None

    summary_rows = []

    for _, row in current_data.iterrows():
        store = row["Store Name"]
        current_open = parse_date_safe(row["Store Opening"])
        baseline_row = data[(data["Store Name"] == store) & (data["Baseline"] == "Yes")].head(1)
        prev_row = previous_data[(previous_data["Store Name"] == store)].sort_values(by="Yr Wk", ascending=False).head(1)

        if not baseline_row.empty:
            baseline_open = parse_date_safe(baseline_row.iloc[0]["Store Opening"])
            delta = (current_open - baseline_open).days if current_open and baseline_open else None
        else:
            delta = None

        if not prev_row.empty:
            prev_open = parse_date_safe(prev_row.iloc[0]["Store Opening"])
            trend = compute_store_opening_trend(prev_open, current_open)
        else:
            trend = "N/A"

        summary_rows.append({
            "Project": store,
            "Flag": "Critical" if delta and abs(delta) >= 5 else "",
            "Store Opening Delta": delta,
            "Trend": trend,
            "Notes": row["Notes"] if extract_keyword_notes(row["Notes"]) else "see report below"
        })

    summary_df = pd.DataFrame(summary_rows)

    # Display summary table
    st.subheader("Executive Summary")
    st.dataframe(summary_df)

    # Generate HTML summary
    html_summary = f"""
    <html>
    <head><style>
    table {{
        width: 100%;
        border-collapse: collapse;
    }}
    th, td {{
        border: 1px solid #ddd;
        padding: 8px;
    }}
    th {{
        background-color: #f2f2f2;
    }}
    </style></head>
    <body>
    <h2>Executive Summary – {current_week}</h2>
    {summary_df.to_html(index=False)}
    <h3>Full Report</h3>
    {current_data.to_html(index=False)}
    </body>
    </html>
    """

    st.download_button("Download HTML Summary", data=html_summary, file_name=f"Construction_Summary_{current_week}.html", mime="text/html")
