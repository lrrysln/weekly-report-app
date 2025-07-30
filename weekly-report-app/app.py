import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import base64
from io import BytesIO
from datetime import datetime, date
from google.oauth2.service_account import Credentials
import gspread

# Google Sheets credentials and client setup
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_file("credentials.json", scopes=SCOPES)
client = gspread.authorize(creds)
sh = client.open("Construction Weekly Updates")

# Get current week and year
current_week = date.today().isocalendar()[1]
current_year = date.today().year

# Load data from Google Sheets
def load_data():
    worksheet = sh.get_worksheet(0)
    data = worksheet.get_all_records()
    return pd.DataFrame(data)

def generate_report(df):
    trend_map = {
        "pulled in": "🟢 Pulled In",
        "pushed": "🔴 Pushed",
        "held": "🟡 Held",
        "baseline": "⚪ Baseline"
    }

    summary_df = df.copy()
    summary_df['Trend'] = df.index.map(trend_map)
    trend_counts = summary_df['Trend'].value_counts().reindex(['🟢 Pulled In', '🔴 Pushed', '🟡 Held', '⚪ Baseline'], fill_value=0)

    # Plotting
    fig, ax = plt.subplots()
    trend_counts.plot(kind='bar', ax=ax, color=["green", "red", "gold", "grey"])
    plt.title("Trend Overview")
    plt.xlabel("Trend")
    plt.ylabel("Count")
    plt.tight_layout()

    buffer = BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)
    img_base64 = base64.b64encode(buffer.read()).decode('utf-8')

    # Report HTML
    html = [f"<h1>{current_year} Week: {current_week} Weekly Summary Report</h1>"]
    html.append(f'<img src="data:image/png;base64,{img_base64}" style="max-width:600px; display:block; margin:auto;">')

    group_col = 'Subject'
    date_fields = ["CPM", "Start", "TCO", "Turnover"]

    for group_name, group_df in df.groupby(group_col):
        html.append(f"<h3>{group_name}</h3><ul>")
        for _, row in group_df.iterrows():
            html.append("<li><ul>")
            for field in date_fields:
                val = row.get(field)
                if val:
                    date_str = datetime.strptime(val, "%Y-%m-%d").strftime("%m/%d") if isinstance(val, str) else val.strftime("%m/%d")
                    if row.get(f"Baseline_{field}") == val:
                        html.append(f"<li><b style='color:red;'>Baseline</b>: {field} - {date_str}</li>")
                    else:
                        html.append(f"<li>{field}: {date_str}</li>")
            note = row.get("Notes", "").strip()
            if note:
                bullets = ''.join([f"<li>{line.strip()}</li>" for line in note.split('\n') if line.strip()])
                html.append(f"<li><strong>Notes:</strong><ul>{bullets}</ul></li>")
            html.append("</ul></li>")
        html.append("</ul>")

    return "\n".join(html)

# Streamlit app
st.set_page_config(layout="wide")
st.title("Weekly Construction Report")

df = load_data()
if not df.empty:
    report_html = generate_report(df)
    st.markdown(report_html, unsafe_allow_html=True)
else:
    st.warning("No data available from Google Sheets.")
