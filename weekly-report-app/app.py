import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from google.oauth2.service_account import Credentials
import base64
from datetime import datetime

# --- Google Sheets Auth ---
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]
creds = Credentials.from_service_account_info(
    st.secrets["gcp_service_account"], scopes=SCOPES
)
client = gspread.authorize(creds)
SPREADSHEET_ID = "1cfr5rCRoRXuDJonarDbokznlaHHVpn1yUfTwo_ePL3w"
WORKSHEET_NAME = "Sheet1"

# --- Helper Functions ---
def create_trend_figure(trend_counts):
    fig = px.bar(
        trend_counts,
        x="Trend",
        y="Count",
        color="Trend",
        color_discrete_map={
            "📈 Improving": "green",
            "📉 Declining": "red",
            "⏸️ No Change": "gray",
        },
        title="Weekly Submission Volume by Trend",
    )
    return fig

def fig_to_base64(fig):
    fig_bytes = fig.to_image(format="png")
    return base64.b64encode(fig_bytes).decode()

def generate_weekly_summary(df, summary_df):
    html = []
    html.append("<html><head><style>")
    html.append("table {border-collapse: collapse; width: 100%;}")
    html.append("th, td {border: 1px solid #ccc; padding: 8px; text-align: left;}")
    html.append("th {background-color: #f2f2f2;}")
    html.append("</style></head><body>")
    html.append("<h2>📊 Executive Summary</h2>")

    for _, row in summary_df.iterrows():
        store_number = row["Store Number"]
        store_name = row["Store Name"]
        prototype = row["Prototype"]
        cpm = row["CPM"]
        flag = row["Flag"]
        delta = row["Store Opening Delta"]
        trend = row["Trend"]
        notes_filtered = row["Notes Filtered"]

        # Card-style HTML block
        html.append(f"""
        <div style='border:2px solid #ddd; border-left:5px solid {"green" if trend=="📈 Improving" else "red" if trend=="📉 Declining" else "gray"}; padding:16px; margin-bottom:20px; border-radius:8px;'>
            <h3>{store_name} ({store_number})</h3>
            <p><strong>Prototype:</strong> {prototype} | <strong>CPM:</strong> {cpm} | <strong>Flag:</strong> {flag}</p>
            <p><strong>Store Opening Delta:</strong> {delta} days</p>
            <p><strong>Trend:</strong> {trend}</p>
            <p><strong>Notes:</strong><br>{notes_filtered.replace('\n', '<br>')}</p>
        </div>
        """)

    html.append("</body></html>")
    return "".join(html)

# --- Data Load ---
@st.cache_data(ttl=600)
def load_data():
    worksheet = client.open_by_key(SPREADSHEET_ID).worksheet(WORKSHEET_NAME)
    data = worksheet.get_all_records()
    return pd.DataFrame(data)

df = load_data()

# --- Clean column names ---
df.columns = df.columns.str.strip()

# --- Filter by Password ---
if "password_entered" not in st.session_state:
    st.session_state.password_entered = False

if not st.session_state.password_entered:
    password = st.text_input("Enter password:", type="password")
    if password == st.secrets["access_password"]:
        st.session_state.password_entered = True
    else:
        st.stop()

# --- Main Dashboard Content ---
st.title("📋 Weekly Construction Report Summary")

# --- Preprocess Data ---
df["Submission Date"] = pd.to_datetime(df["Submission Date"], errors="coerce")
df["Year"] = df["Submission Date"].dt.year
df["Week"] = df["Submission Date"].dt.strftime("Week %U")

trend_counts = df["Trend"].value_counts().reset_index()
trend_counts.columns = ["Trend", "Count"]

# --- Weekly Submission Volume Chart ---
fig = create_trend_figure(trend_counts)
st.plotly_chart(fig)

# --- Summary Table ---
summary_cols = ['Store Name', 'Store Number', 'Prototype', 'CPM', 'Flag', 'Store Opening Delta', 'Trend', 'Notes Filtered']
summary_df = df[summary_cols].drop_duplicates(subset=['Store Number']).reset_index(drop=True)

# ✅ Generate and display the HTML report
html_report = generate_weekly_summary(df, summary_df)
st.subheader("📄 Weekly Report (Preview)")
st.components.v1.html(html_report, height=1000, scrolling=True)

b64 = base64.b64encode(html_report.encode()).decode()
href = f'<a href="data:text/html;base64,{b64}" download="weekly_summary.html">📥 Download Full Report as HTML</a>'
st.markdown(href, unsafe_allow_html=True)
