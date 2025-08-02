# --- Normalize Dates ---
df["Store Opening"] = pd.to_datetime(df["Store Opening"], errors="coerce", dayfirst=False)
df["Flag"] = df["Flag"].astype(str).str.strip()
df["Store Number"] = df["Store Number"].astype(str).str.strip()

# --- Separate Baseline and Current Week Rows ---
baseline_df = df[df["Flag"] == "/True"].copy()
current_df = df[df["Flag"] != "/True"].copy()

# --- Get Most Recent Baseline per Store ---
latest_baseline = (
    baseline_df.sort_values("Year Week", ascending=False)
    .drop_duplicates(subset=["Store Number"], keep="first")
    .set_index("Store Number")[["Store Opening"]]
    .rename(columns={"Store Opening": "Baseline Opening"})
)

# --- Merge Current Rows with Baseline ---
current_df = current_df.merge(
    latest_baseline, how="left", left_on="Store Number", right_index=True
)

# --- Calculate Trend and Delta ---
def calculate_trend(row):
    current_date = row["Store Opening"]
    baseline_date = row["Baseline Opening"]
    
    if pd.isna(current_date) or pd.isna(baseline_date):
        return pd.Series(["⚫ No Data", None])
    
    delta = (current_date - baseline_date).days
    
    if delta > 0:
        return pd.Series(["🔴 Pushed", delta])
    elif delta < 0:
        return pd.Series(["🟢 Pulled In", delta])
    else:
        return pd.Series(["🟡 Held", 0])

current_df[["Trend", "Delta Days"]] = current_df.apply(calculate_trend, axis=1)

# --- Assign Trend for Baseline Rows ---
baseline_df["Trend"] = "🟤 Baseline"
baseline_df["Delta Days"] = 0

# --- Combine All ---
combined = pd.concat([baseline_df, current_df], ignore_index=True)

# --- Display Clean Table ---
st.subheader("📋 Store Opening Trend Table")
st.dataframe(combined[[
    "Store Name", "Store Number", "Prototype", "CPM", "Delta Days", "Trend"
]])

# --- Plot Trend Counts ---
st.subheader("📊 Store Opening Trend Summary")
trend_counts = combined["Trend"].value_counts()

fig, ax = plt.subplots()
trend_counts.plot(kind='bar', ax=ax, color=["#A9A9A9", "#3CBA54", "#DA3E52", "#F4C300", "#808080"])
ax.set_title("Store Opening Trend Count")
ax.set_xlabel("Trend")
ax.set_ylabel("Number of Stores")
st.pyplot(fig)
