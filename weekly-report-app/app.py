import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# === GOOGLE SHEET AUTH ===
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_name("your_credentials_file.json", scope)
gc = gspread.authorize(credentials)

# === LOAD GOOGLE SHEET DATA ===
sheet_url = "https://docs.google.com/spreadsheets/d/1VLq9D1GqStPv3Fa7yzm8HbMWRHBaChfG6FLZObT8Rog/edit#gid=135253558"
sheet = gc.open_by_url(sheet_url)
worksheet = sheet.get_worksheet(0)
data = worksheet.get_all_records()
df = pd.DataFrame(data)

# === CLEAN & NORMALIZE DATA ===
for col in ["Flag", "Store Number", "Store Name"]:
    df[col] = df[col].astype(str).str.strip()

df["Store Name"] = df["Store Name"].str.lower()
df["Store Opening"] = pd.to_datetime(df["Store Opening"], errors="coerce")
df["Year Week"] = pd.to_datetime(df["Year Week"], errors="coerce")

# === BASELINE VS CURRENT SPLIT ===
baseline_df = df[df["Flag"] == "/True"].copy()
current_df = df[df["Flag"] != "/True"].copy()

# === FIND LATEST BASELINE FOR EACH STORE ===
latest_baseline = (
    baseline_df.sort_values("Year Week", ascending=False)
    .drop_duplicates(subset=["Store Number"], keep="first")
    .set_index("Store Number")[["Store Opening"]]
    .rename(columns={"Store Opening": "Baseline Opening"})
)

# === MERGE BASELINE INTO CURRENT DATA ===
current_df = current_df.merge(
    latest_baseline,
    how="left",
    left_on="Store Number",
    right_index=True
)

# === TREND CALCULATION FUNCTION ===
def determine_trend(row):
    if pd.isna(row["Baseline Opening"]) or pd.isna(row["Store Opening"]):
        return "⚫ No Data"
    elif row["Store Opening"] > row["Baseline Opening"]:
        return "🔴 Pushed"
    elif row["Store Opening"] < row["Baseline Opening"]:
        return "🟢 Pulled In"
    elif row["Store Opening"] == row["Baseline Opening"]:
        return "🟡 Held"
    return "⚫ No Data"

current_df["Trend"] = current_df.apply(determine_trend, axis=1)

# === STREAMLIT DISPLAY ===
st.title("📊 Construction Schedule Trend Analysis")

st.markdown("This dashboard compares the most recent project dates to baselines and categorizes schedule movements:")

# Show current trend data
st.dataframe(current_df[["Store Number", "Store Name", "Store Opening", "Baseline Opening", "Trend"]])

# Display trend bar chart
trend_counts = current_df["Trend"].value_counts().reset_index()
trend_counts.columns = ["Trend", "Count"]

st.subheader("📈 Trend Breakdown")
st.bar_chart(trend_counts.set_index("Trend"))

# Optionally export to CSV
csv = current_df.to_csv(index=False)
st.download_button("📥 Download Trend Report", csv, "store_trend_report.csv", "text/csv")
