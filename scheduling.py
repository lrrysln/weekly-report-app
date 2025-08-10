import streamlit as st
import pandas as pd
import sqlite3
from PyPDF2 import PdfMerger
from datetime import datetime
import io

# ========== DB Setup and Functions ==========
DB_PATH = 'activities.sqlite'

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
    CREATE TABLE IF NOT EXISTS activities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_code TEXT,
        project_name TEXT,
        activity_id TEXT,
        activity_name TEXT,
        duration INTEGER,
        start_date TEXT,
        finish_date TEXT,
        float INTEGER,
        notes TEXT
    )
    ''')
    conn.commit()
    conn.close()

def save_activities_to_db(data):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    for row in data:
        c.execute('''
        INSERT INTO activities (project_code, project_name, activity_id, activity_name, duration, start_date, finish_date, float, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            row.get('Project Code'),
            row.get('Project Name'),
            row.get('Activity ID'),
            row.get('Activity Name'),
            row.get('Duration'),
            row['Start Date'].strftime('%Y-%m-%d') if row.get('Start Date') else None,
            row['Finish Date'].strftime('%Y-%m-%d') if row.get('Finish Date') else None,
            row.get('Float'),
            row.get('Notes')
        ))
    conn.commit()
    conn.close()

def load_activities_from_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT project_code, project_name, activity_id, activity_name, duration, start_date, finish_date, float, notes FROM activities')
    rows = c.fetchall()
    conn.close()
    data = []
    for r in rows:
        data.append({
            "Project Code": r[0],
            "Project Name": r[1],
            "Activity ID": r[2],
            "Activity Name": r[3],
            "Duration": r[4],
            "Start Date": pd.to_datetime(r[5]) if r[5] else None,
            "Finish Date": pd.to_datetime(r[6]) if r[6] else None,
            "Float": r[7],
            "Notes": r[8]
        })
    return data

# Initialize DB on app start
init_db()

# ========== Streamlit UI ==========

st.title("📄 Project Schedule PDF Extractor & Storage")

# Load and display previously stored data
stored_data = load_activities_from_db()
if stored_data:
    st.header("📂 Previously Stored Activities")
    stored_df = pd.DataFrame(stored_data)
    st.dataframe(stored_df)
else:
    st.info("No stored data found in local database yet.")

# Upload PDFs
uploaded_files = st.file_uploader(
    "Upload one or more project schedule PDFs", 
    type=['pdf'], 
    accept_multiple_files=True
)

all_data = []

if uploaded_files:
    # Simulate extraction process (replace with your actual extraction)
    for i, pdf_file in enumerate(uploaded_files):
        for line in range(1, 6):  # simulate 5 lines per PDF
            all_data.append({
                "Project Code": f"PC-{i+1}",
                "Project Name": f"Project {i+1}",
                "Activity ID": f"A{i+1}-{line}",
                "Activity Name": f"Activity {line} from PDF {pdf_file.name}",
                "Duration": 5 + line,
                "Start Date": pd.Timestamp("2025-01-01") + pd.Timedelta(days=line),
                "Finish Date": pd.Timestamp("2025-01-06") + pd.Timedelta(days=line),
                "Float": 0,
                "Notes": None
            })
    df = pd.DataFrame(all_data)
    st.header("Extracted Activity Data Preview")
    st.dataframe(df)

    # Download extracted data as CSV
    csv_data = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="⬇️ Download extracted data as CSV",
        data=csv_data,
        file_name="extracted_activities.csv",
        mime="text/csv"
    )

    # Download extracted data as Excel
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Activities')
        writer.save()
    processed_data = output.getvalue()
    st.download_button(
        label="⬇️ Download extracted data as Excel",
        data=processed_data,
        file_name="extracted_activities.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # Save to DB button
    if st.button("💾 Save extracted data to local database"):
        save_activities_to_db(all_data)
        st.success(f"Saved {len(all_data)} rows to local database!")

    # Combine PDFs button
    if st.button("📎 Combine all uploaded PDFs into one file"):
        merger = PdfMerger()
        for pdf_file in uploaded_files:
            pdf_file.seek(0)
            merger.append(pdf_file)
        combined_pdf_path = f"combined_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        merger.write(combined_pdf_path)
        merger.close()
        with open(combined_pdf_path, "rb") as f:
            st.download_button(
                label="⬇️ Download Combined PDF",
                data=f,
                file_name=combined_pdf_path,
                mime="application/pdf"
            )
        st.success("Combined PDF ready for download!")

else:
    st.info("Upload PDFs to extract and store project activity data.")
