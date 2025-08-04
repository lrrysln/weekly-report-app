import streamlit as st
import pandas as pd
import base64
from datetime import datetime

st.set_page_config(layout="wide")
st.title("📊 Weekly Construction Summary Report")

# Password gate
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    with st.form("auth_form", clear_on_submit=False):
        password = st.text_input("Enter password", type="password")
        submitted = st.form_submit_button("Submit")
        if submitted:
            if password == st.secrets["access_password"]:
                st.session_state.authenticated = True
            else:
                st.error("Incorrect password")
    st.stop()

# Upload Excel file
uploaded_file = st.file_uploader("Upload the Weekly Excel File", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)

    # Filter necessary summary columns
    summary_cols = ['Store Name', 'Store Number', 'Prototype', 'CPM', 'Flag', 'Store Opening Delta', 'Trend', 'Notes Filtered']
    summary_df = df[summary_cols].drop_duplicates(subset=['Store Number']).reset_index(drop=True)

    # ✅ Generate and display the HTML report
    def generate_weekly_summary(df, summary_df):
        def format_date(value):
            if pd.isna(value):
                return "N/A"
            try:
                return pd.to_datetime(value).strftime("%m/%d/%y")
            except:
                return str(value)

        html = []
        html.append("<div style='font-family: Arial, sans-serif;'>")
        html.append("<h2 style='text-align: center;'>🗓️ Detailed Weekly Summary</h2>")

        for _, row in summary_df.iterrows():
            store_num = row['Store Number']
            store_df = df[df['Store Number'] == store_num]

            html.append(f"<h3 style='margin-bottom: 0;'>{row['Store Name']} ({store_num}) - {row['Prototype']}</h3>")
            html.append(f"<p><strong>CPM:</strong> {row['CPM']} | <strong>Flag:</strong> {row['Flag']}</p>")
            html.append(f"<p><strong>Store Opening Delta:</strong> {row['Store Opening Delta']} | <strong>Trend:</strong> {row['Trend']}</p>")

            notes = row['Notes Filtered']
            notes_html = "<ul style='margin-top: 0;'>"
            for note in str(notes).split("\n"):
                if note.strip():
                    notes_html += f"<li>{note.strip()}</li>"
            notes_html += "</ul>"

            html.append(f"<p><strong>📝 Notes:</strong>{notes_html}</p>")

            # Group date columns
            milestone_headers = ['TCO', 'Ops Walk', 'Turnover', 'Open to Train', 'Store Opening']
            date_section = "<p><strong>📅 Dates:</strong></p><ul style='margin-top: 0;'>"
            for header in milestone_headers:
                milestone_dates = store_df[header].dropna().unique()
                milestone_dates_formatted = [format_date(d) for d in milestone_dates]
                milestone_html = "<ul style='margin-top: 0; margin-left: 20px;'>"
                for date in milestone_dates_formatted:
                    milestone_html += f"<li>{date}</li>"
                milestone_html += "</ul>"
                date_section += f"<li><u>{header}</u>: {milestone_html}</li>"
            date_section += "</ul>"

            html.append(date_section)
            html.append("<hr style='margin: 30px 0;'>")

        html.append("</div>")
        return "".join(html)

    html_report = generate_weekly_summary(df, summary_df)
    st.subheader("📄 Weekly Report (Preview)")
    st.components.v1.html(html_report, height=1000, scrolling=True)

    b64 = base64.b64encode(html_report.encode()).decode()
    href = f'<a href="data:text/html;base64,{b64}" download="weekly_summary.html">📥 Download Full Report as HTML</a>'
    st.markdown(href, unsafe_allow_html=True)
