import pandas as pd
from datetime import datetime, timedelta

# Copy the original dataframe
test_df = df.copy()

# Create fake data for testing
fake_data = pd.DataFrame([
    {
        "Timestamp": datetime.now() - timedelta(weeks=2),
        "Store Number": "1234",
        "Store Name": "Mock Store A",
        "Prototype": "Prototype A",
        "CPM": "PM1",
        "Baseline": datetime(2025, 8, 1),
        "Store Opening": datetime(2025, 8, 5),
        "Notes": "Initial week"
    },
    {
        "Timestamp": datetime.now() - timedelta(weeks=1),
        "Store Number": "1234",
        "Store Name": "Mock Store A",
        "Prototype": "Prototype A",
        "CPM": "PM1",
        "Baseline": datetime(2025, 8, 1),
        "Store Opening": datetime(2025, 8, 7),
        "Notes": "Second week"
    },
    {
        "Timestamp": datetime.now(),
        "Store Number": "5678",
        "Store Name": "Mock Store B",
        "Prototype": "Prototype B",
        "CPM": "PM2",
        "Baseline": datetime(2025, 8, 1),
        "Store Opening": datetime(2025, 8, 10),
        "Notes": "Only one entry"
    },
])

# Concatenate with your actual data
test_df = pd.concat([test_df, fake_data], ignore_index=True)

# Ensure datetime types
test_df["Baseline"] = pd.to_datetime(test_df["Baseline"], errors="coerce")
test_df["Store Opening"] = pd.to_datetime(test_df["Store Opening"], errors="coerce")
test_df["Timestamp"] = pd.to_datetime(test_df["Timestamp"], errors="coerce")

# Recalculate Delta and Trend
test_df["Delta Days"] = (test_df["Store Opening"] - test_df["Baseline"]).dt.days
test_df["Trend"] = test_df.sort_values("Timestamp").groupby("Store Number")["Delta Days"].diff().fillna(0)

# Preview
st.dataframe(test_df[["Timestamp", "Store Number", "Store Name", "Delta Days", "Trend", "Notes"]])
