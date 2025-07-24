import streamlit as st
import pandas as pd
import plotly.express as px
from textblob import TextBlob
from datetime import datetime

# --- Session State for dynamic list ---
if "projects" not in st.session_state:
    st.session_state.projects = [
        {"Project": "Falcon", "PM Note": "Electrical delay on Floor 2 due to missing conduit shipment.", "Milestone_Baseline": "2025-08-15", "Milestone_Current": "2025-08-24", "Changes": 2, "Submitted": True},
        {"Project": "Atlas", "PM Note": "Permit finally approved, all systems go.", "Milestone_Baseline": "2025-08-10", "Milestone_Current": "2025-08-10", "Changes": 0, "Submitted": True},
        {"Project": "Helix", "PM Note": "Same HVAC issue persists. No resolution yet.", "Milestone_Baseline": "2025-07-25", "Milestone_Current": "2025-07-21", "Changes": 2, "Submitted": True},
        {"Project": "Zenith", "PM Note": "No issues this week, things are on schedule.", "Milestone_Baseline": "2025-08-01", "Milestone_Current": "2025-08-05", "Changes": 2, "Submitted": True},
        {"Project": "Nova", "PM Note": "Budget overrun due to unexpected design change.", "Milestone_Baseline": "2025-08-05", "Milestone_Current": "2025-08-04", "Changes": 1, "Submitted": True}
    ]
    st.session_state.opened_projects = []

# --- Add New Project ---
st.sidebar.markdown("## ➕ Add New Job")
with st.sidebar.form("add_job"):
    name = st.text_input("Project Name")
    baseline = st.date_input("Baseline Milestone Date")
    note = st.text_area("Initial PM Note")
    submitted = st.form_submit_button("Add Job")
    if submitted and name and baseline:
        st.session_state.projects.append({
            "Project": name,
            "PM Note": note,
            "Milestone_Baseline": str(baseline),
            "Milestone_Current": str(baseline),
            "Changes": 0,
            "Submitted": True
        })
        st.success(f"Added {name} to active jobs.")

# --- DataFrame Build ---
df = pd.DataFrame(st.session_state.projects)
df["Milestone_Baseline"] = pd.to_datetime(df["Milestone_Baseline"])
df["Milestone_Current"] = pd.to_datetime(df["Milestone_Current"])
df["Delta_Days"] = (df["Milestone_Current"] - df["Milestone_Baseline"]).dt.days
df["Trend"] = df["Delta_Days"].apply(lambda x: "📉 Slipped" if x > 0 else "📈 Pulled In" if x < 0 else "➖ Held")

# --- Flagging System ---
critical_keywords = ["delay", "missing", "permit", "issue", "overrun", "claim", "inspection", "behind", "lean"]
def flag_note(note):
    if any(word in note.lower() for word in critical_keywords):
        return "🚨 Critical"
    elif TextBlob(note).sentiment.polarity < -0.2:
        return "⚠️ Watch"
    else:
        return "✅ Good"
df["Flag"] = df["PM Note"].apply(flag_note)

# --- Note Repetition + Risk ---
df["Stale Issue"] = df["PM Note"].apply(lambda n: any(w in n.lower() for w in ["same", "persists", "repeated"]))
df["Note Quality"] = df["PM Note"].apply(lambda n: "Low" if len(n.split()) < 5 else "High")

# --- Store Completion Check ---
st.markdown("### ✅ Mark Stores as Opened")
for i, row in df.iterrows():
    if row["Project"] not in st.session_state.opened_projects:
        if st.checkbox(f"Mark {row['Project']} as opened", key=f"open_{i}"):
            st.session_state.opened_projects.append(row["Project"])
df = df[~df["Project"].isin(st.session_state.opened_projects)]

# --- PM Tracking Simulation ---
total_pms = 10
submitted_count = df["Submitted"].sum()
pending = total_pms - submitted_count
st.info(f"**PM Notes Submitted:** {submitted_count}/{total_pms} — Waiting on {pending}")

# --- Title + Summary ---
st.title("Project Risk & Schedule Summary")
st.subheader(f"Weekly Snapshot — {datetime.today().strftime('%B %d, %Y')}")

# --- Legend ---
st.markdown("""
**Legend:**
- 🚨 Critical = keyword or major issue
- ⚠️ Watch = negative tone or weak note
- ✅ Good = no immediate concern
- 🔁 Stale = repeated issues
- 📉 Slipped = delayed milestone
- 📈 Pulled In = accelerated
- ➖ Held = on time
""")

# --- Plot Trends ---
trend_counts = df["Trend"].value_counts().reset_index()
trend_counts.columns = ["Trend", "Count"]
fig = px.bar(trend_counts, x="Trend", y="Count", color="Trend", title="Milestone Trends", color_discrete_map={
    "📉 Slipped": "red",
    "📈 Pulled In": "green",
    "➖ Held": "blue"
})
st.plotly_chart(fig, use_container_width=True)

# --- Sparkline Stability Score ---
df["Stability Score"] = df["Changes"].apply(lambda x: "High Risk" if x >= 3 else "Moderate" if x == 2 else "Stable")
st.markdown("### 🚦 Stability Score by Project")
st.dataframe(df[["Project", "Stability Score", "Changes", "Delta_Days", "Trend", "Flag", "Stale Issue", "Note Quality", "PM Note"]])

# --- Download CSV ---
st.markdown("### 📥 Export CSV")
csv = df.to_csv(index=False).encode("utf-8")
st.download_button("Download Report", data=csv, file_name="weekly_project_report.csv", mime="text/csv")
