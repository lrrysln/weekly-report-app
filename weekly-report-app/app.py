# weekly_report_app.py

import streamlit as st
import pandas as pd
import plotly.express as px
from textblob import TextBlob
from datetime import datetime

# ---------- Sample Data (Replace this with your real data source) ----------
data = {
    "Project": ["Falcon", "Atlas", "Helix", "Zenith", "Nova"],
    "PM Note": [
        "Electrical delay on Floor 2 due to missing conduit shipment.",
        "Permit finally approved, all systems go.",
        "Same HVAC issue persists. No resolution yet.",
        "No issues this week, things are on schedule.",
        "Budget overrun due to unexpected design change."
    ],
    "Milestone_Baseline": ["2025-08-15", "2025-08-10", "2025-07-25", "2025-08-01", "2025-08-05"],
    "Milestone_Current": ["2025-08-24", "2025-08-10", "2025-07-21", "2025-08-05", "2025-08-04"],
    "Changes": [2, 0, 2, 2, 1]
}
df = pd.DataFrame(data)
df["Milestone_Baseline"] = pd.to_datetime(df["Milestone_Baseline"])
df["Milestone_Current"] = pd.to_datetime(df["Milestone_Current"])

# ---------- Smart Flagging System ----------
def flag_note(note):
    critical_keywords = ["delay", "missing", "permit", "issue", "overrun", "claim", "inspection", "behind"]
    if any(word in note.lower() for word in critical_keywords):
        return "🚨 Critical"
    elif TextBlob(note).sentiment.polarity < -0.2:
        return "⚠️ Watch"
    else:
        return "✅ Good"

df["Flag"] = df["PM Note"].apply(flag_note)

# ---------- Milestone Delta + Trend ----------
df["Delta_Days"] = (df["Milestone_Current"] - df["Milestone_Baseline"]).dt.days
df["Trend"] = df["Delta_Days"].apply(lambda x: "📉 Slipped" if x > 0 else "📈 Pulled In" if x < 0 else "➖ Held")

# ---------- Stale Issue Detection ----------
df["Stale Issue"] = df["PM Note"].apply(lambda note: True if "same" in note.lower() or "persists" in note.lower() else False)

# ---------- Note Quality Scoring ----------
def note_score(note):
    if len(note.split()) < 5:
        return "Low (Too Short)"
    elif "good" in note.lower() and len(note.split()) < 10:
        return "Low (Generic)"
    else:
        return "High (Detailed)"

df["Note Quality"] = df["PM Note"].apply(note_score)

# ---------- Streamlit UI ----------
st.set_page_config(page_title="Weekly Construction Report", layout="wide")
st.title("🧠 Project Risk & Schedule Summary")
st.subheader(f"Weekly Snapshot — {datetime.today().strftime('%B %d, %Y')}")

# ---------- Display Table ----------
st.markdown("### 🗂️ PM Notes Summary")
st.dataframe(df[["Project", "Flag", "Delta_Days", "Trend", "Stale Issue", "Note Quality", "PM Note"]].sort_values(by="Flag", ascending=False), use_container_width=True)

# ---------- Plotly Bar Chart ----------
st.markdown("### 📊 Milestone Trends Overview")
trend_counts = df["Trend"].value_counts().reset_index()
trend_counts.columns = ["Trend", "Count"]
fig = px.bar(trend_counts, x="Trend", y="Count", title="Milestone Trend Breakdown", color="Trend", color_discrete_map={
    "📉 Slipped": "red",
    "📈 Pulled In": "green",
    "➖ Held": "blue"
})
st.plotly_chart(fig, use_container_width=True)

# ---------- Download CSV ----------
st.markdown("### 📥 Download Report")
csv = df.to_csv(index=False).encode("utf-8")
st.download_button(
    label="Download Report as CSV",
    data=csv,
    file_name=f"weekly_project_report_{datetime.today().strftime('%Y%m%d')}.csv",
    mime="text/csv"
)
