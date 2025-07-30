import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

# --- Auth to Google Sheets ---
SCOPES = ["https://www.googleapis.com/auth/spreadsheets",
          "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=SCOPES)
client = gspread.authorize(creds)

# --- Load Sheet ---
SHEET_NAME = "Construction Weekly Updates"
WORKSHEET_NAME = "Sheet1"

@st.cache_data(ttl=60)
def load_sheet():
    try:
        sheet = client.open(SHEET_NAME).worksheet(WORKSHEET_NAME)
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        df.columns = df.columns.str.strip()  # Remove whitespace from headers
        print("🔍 Sheet columns:", df.columns.tolist())  # Debugging
        return df
    except Exception as e:
        st.error(f"❌ Failed to load data from Google Sheet: {e}")
        return pd.DataFrame()

def get_store_names():
    df = load_sheet()
    return sorted(df["Store Name"].dropna().unique())

# --- Streamlit UI ---
st.title("Weekly Construction Update")

store_options = get_store_names()
selected_store = st.selectbox("Select a Store", store_options)

with st.form("update_form"):
    week_of = st.date_input("Week of the Year", value=datetime.today())
    subject = st.text_input("Subject")
    notes = st.text_area("Notes", height=150)

    submitted = st.form_submit_button("Submit")

    if submitted:
        df = load_sheet()

        new_entry = {
            "Week of the Year": week_of.strftime("%m/%d/%Y"),
            "Store Name": selected_store,
            "Subject": subject,
            "Notes": notes,
        }

        df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)

        # Save to Google Sheet
        sheet = client.open(SHEET_NAME).worksheet(WORKSHEET_NAME)
        sheet.update([df.columns.values.tolist()] + df.values.tolist())

        st.success("✅ Update submitted successfully.")
        st.write("Preview of your entry:", pd.DataFrame([new_entry]))
