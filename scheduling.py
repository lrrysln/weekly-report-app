import streamlit as st
import pandas as pd
import sqlite3
from PyPDF2 import PdfMerger
from datetime import datetime
import io
import matplotlib.pyplot as plt
import seaborn as sns
from fpdf import FPDF

# === DB Setup and Functions ===
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

# === Historical Data & Analysis Functions ===
def load_sample_data():
    data = [
        ['ProjectA', 'Foundation', '2025-01-01', '2025-01-10', '2025-01-01', '2025-01-12', None, 100, 5000],
        ['ProjectA', 'Framing', '2025-01-11', '2025-01-25', '2025-01-13', '2025-01-28', 'Weather', 200, 12000],
        ['ProjectA', 'Finishes', '2025-01-26', '2025-02-10', '2025-01-29', '2025-02-08', None, 150, 8000],
        ['ProjectB', 'Foundation', '2025-02-01', '2025-02-12', '2025-02-02', '2025-02-14', 'Material Delay', 110, 5200],
        ['ProjectB', 'Framing', '2025-02-13', '2025-02-28', '2025-02-15', '2025-03-05', 'Labor Shortage', 210, 12500],
        ['ProjectB', 'Finishes', '2025-03-01', '2025-03-15', '2025-03-06', '2025-03-16', None, 160, 9000],
    ]
    df = pd.DataFrame(data, columns=['project_id', 'activity', 'planned_start', 'planned_end', 'actual_start', 'actual_end', 'delay_reason', 'labor_hours', 'cost'])
    for col in ['planned_start', 'planned_end', 'actual_start', 'actual_end']:
        df[col] = pd.to_datetime(df[col])
    return df

def calculate_kpis(df):
    df['planned_duration'] = (df['planned_end'] - df['planned_start']).dt.days
    df['actual_duration'] = (df['actual_end'] - df['actual_start']).dt.days
    df['schedule_variance'] = df['planned_duration'] - df['actual_duration']
    df['spi'] = df['planned_duration'] / df['actual_duration']
    df['delay_days'] = (df['actual_end'] - df['planned_end']).dt.days.clip(lower=0)
    return df

def project_summary(df):
    summary = df.groupby('project_id').agg(
        total_planned_duration=('planned_duration', 'sum'),
        total_actual_duration=('actual_duration', 'sum'),
        total_labor_hours=('labor_hours', 'sum'),
        total_cost=('cost', 'sum'),
        avg_spi=('spi', 'mean'),
        total_delay_days=('delay_days', 'sum')
    ).reset_index()
    summary['schedule_variance'] = summary['total_planned_duration'] - summary['total_actual_duration']
    return summary

def delay_cause_analysis(df):
    delays = df[df['delay_days'] > 0]
    cause_counts = delays['delay_reason'].value_counts().reset_index()
    cause_counts.columns = ['delay_reason', 'count']
    return cause_counts

def plot_gantt_chart(df, project_id):
    project_df = df[df['project_id'] == project_id]
    fig, ax = plt.subplots(figsize=(10, 3))
    y_pos = range(len(project_df))
    ax.barh(y_pos, project_df['planned_duration'], left=project_df['planned_start'].map(lambda d: d.toordinal()), color='lightblue', label='Planned')
    ax.barh(y_pos, project_df['actual_duration'], left=project_df['actual_start'].map(lambda d: d.toordinal()), color='orange', alpha=0.6, label='Actual')
    ax.set_yticks(y_pos)
    ax.set_yticklabels(project_df['activity'])
    x_ticks = ax.get_xticks()
    x_labels = [datetime.fromordinal(int(tick)).strftime('%Y-%m-%d') for tick in x_ticks]
    ax.set_xticklabels(x_labels, rotation=45, ha='right')
    ax.set_title(f'Gantt Chart for {project_id}')
    ax.legend()
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    plt.close(fig)
    buf.seek(0)
    return buf

def plot_delay_causes(cause_counts):
    fig, ax = plt.subplots()
    sns.barplot(x='count', y='delay_reason', data=cause_counts, ax=ax)
    ax.set_title('Delay Causes Frequency')
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    plt.close(fig)
    buf.seek(0)
    return buf

class PDFReport(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 16)
        self.cell(0, 10, 'Construction Project Analysis Report', 0, 1, 'C')
        self.ln(10)
    def chapter_title(self, title):
        self.set_font('Arial', 'B', 14)
        self.cell(0, 10, title, 0, 1)
        self.ln(4)
    def chapter_body(self, text):
        self.set_font('Arial', '', 12)
        self.multi_cell(0, 10, text)
        self.ln(5)
    def add_image(self, img_buffer, w=180):
        self.image(img_buffer, w=w)
        self.ln(10)

def generate_pdf_report(df, summary_df, delay_causes):
    pdf = PDFReport()
    pdf.add_page()
    pdf.chapter_title('Project Summary')
    for _, row in summary_df.iterrows():
        txt = (f"Project: {row['project_id']}\n"
               f"Planned Duration: {row['total_planned_duration']} days\n"
               f"Actual Duration: {row['total_actual_duration']} days\n"
               f"Schedule Variance: {row['schedule_variance']} days\n"
               f"Average SPI: {row['avg_spi']:.2f}\n"
               f"Total Labor Hours: {row['total_labor_hours']}\n"
               f"Total Cost: ${row['total_cost']}\n"
               f"Total Delay Days: {row['total_delay_days']}\n")
        pdf.chapter_body(txt)
        gantt_img = plot_gantt_chart(df, row['project_id'])
        pdf.add_image(gantt_img)
    pdf.chapter_title('Delay Cause Analysis')
    if delay_causes.empty:
        pdf.chapter_body("No delays reported across projects.")
    else:
        pdf.chapter_body("Frequency of delay causes across projects:")
        delay_img = plot_delay_causes(delay_causes)
        pdf.add_image(delay_img)
    pdf_output = io.BytesIO()
    pdf.output(pdf_output)
    pdf_output.seek(0)
    return pdf_output

# === Streamlit App UI ===

def main():
    st.title("📄 Project Schedule PDF Extractor, Storage & Analysis")

    # Initialize DB
    init_db()

    # Display stored activities from DB
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
        # Mock extraction from PDFs
        for i, pdf_file in enumerate(uploaded_files):
            for line in range(1, 6):
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

        # Download extracted CSV & Excel
        csv_data = df.to_csv(index=False).encode('utf-8')
        st.download_button("⬇️ Download extracted data as CSV", csv_data, "extracted_activities.csv", "text/csv")

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Activities')
            writer.save()
        processed_data = output.getvalue()
        st.download_button("⬇️ Download extracted data as Excel", processed_data, "extracted_activities.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        if st.button("💾 Save extracted data to local database"):
            save_activities_to_db(all_data)
            st.success(f"Saved {len(all_data)} rows to local database!")

        if st.button("📎 Combine all uploaded PDFs into one file"):
            merger = PdfMerger()
            for pdf_file in uploaded_files:
                pdf_file.seek(0)
                merger.append(pdf_file)
            combined_pdf_path = f"combined_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            merger.write(combined_pdf_path)
            merger.close()
            with open(combined_pdf_path, "rb") as f:
                st.download_button("⬇️ Download Combined PDF", f, combined_pdf_path, "application/pdf")
            st.success("Combined PDF ready for download!")

    else:
        st.info("Upload PDFs to extract and store project activity data.")

    # === Historical Data Analysis ===
    st.header("📊 Historical Project Schedule Analysis")

    # Load and process sample data
    hist_df = load_sample_data()
    hist_df = calculate_kpis(hist_df)
    summary_df = project_summary(hist_df)
    delay_causes = delay_cause_analysis(hist_df)

    st.subheader("Summary Table")
    st.dataframe(summary_df)

    st.subheader("Select Project for Gantt Chart")
    project_option = st.selectbox("Project:", summary_df['project_id'].unique())
    gantt_img_buf = plot_gantt_chart(hist_df, project_option)
    st.image(gantt_img_buf)

    st.subheader("Delay Cause Analysis")
    if delay_causes.empty:
        st.write("No delays reported across projects.")
    else:
        delay_img_buf = plot_delay_causes(delay_causes)
        st.image(delay_img_buf)

    if st.button("📄 Generate PDF Analysis Report"):
        pdf_buffer = generate_pdf_report(hist_df, summary_df, delay_causes)
        st.download_button("⬇️ Download Analysis Report PDF", pdf_buffer, "construction_analysis_report.pdf", "application/pdf")

if __name__ == "__main__":
    main()
