import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from fpdf import FPDF
from datetime import datetime
import io

# --- Sample Data Loading (replace with your actual data source) ---
# Expected format for schedule data: project_id, activity, planned_start, planned_end, actual_start, actual_end, delay_reason, labor_hours, cost

def load_data():
    # For demo, create dummy data for two projects
    data = [
        # project_id, activity, planned_start, planned_end, actual_start, actual_end, delay_reason, labor_hours, cost
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

# --- KPI Calculations ---
def calculate_kpis(df):
    df['planned_duration'] = (df['planned_end'] - df['planned_start']).dt.days
    df['actual_duration'] = (df['actual_end'] - df['actual_start']).dt.days
    df['schedule_variance'] = df['planned_duration'] - df['actual_duration']
    df['spi'] = df['planned_duration'] / df['actual_duration']
    df['delay_days'] = (df['actual_end'] - df['planned_end']).dt.days.clip(lower=0)  # Only positive delays
    return df

# --- Summarize Project-level Data ---
def project_summary(df):
    summary = df.groupby('project_id').agg(
        total_planned_duration = ('planned_duration', 'sum'),
        total_actual_duration = ('actual_duration', 'sum'),
        total_labor_hours = ('labor_hours', 'sum'),
        total_cost = ('cost', 'sum'),
        avg_spi = ('spi', 'mean'),
        total_delay_days = ('delay_days', 'sum')
    ).reset_index()
    summary['schedule_variance'] = summary['total_planned_duration'] - summary['total_actual_duration']
    return summary

# --- Delay Cause Analysis ---
def delay_cause_analysis(df):
    delays = df[df['delay_days'] > 0]
    cause_counts = delays['delay_reason'].value_counts().reset_index()
    cause_counts.columns = ['delay_reason', 'count']
    return cause_counts

# --- Visualizations ---
def plot_gantt_chart(df, project_id):
    project_df = df[df['project_id'] == project_id]
    fig, ax = plt.subplots(figsize=(10, 3))
    y_pos = range(len(project_df))
    
    ax.barh(y_pos, project_df['planned_duration'], left=project_df['planned_start'].map(lambda d: d.toordinal()), color='lightblue', label='Planned')
    ax.barh(y_pos, project_df['actual_duration'], left=project_df['actual_start'].map(lambda d: d.toordinal()), color='orange', alpha=0.6, label='Actual')
    
    ax.set_yticks(y_pos)
    ax.set_yticklabels(project_df['activity'])
    
    # Format x-axis as dates
    x_ticks = ax.get_xticks()
    x_labels = [datetime.fromordinal(int(tick)).strftime('%Y-%m-%d') for tick in x_ticks]
    ax.set_xticklabels(x_labels, rotation=45, ha='right')
    
    ax.set_title(f'Gantt Chart for {project_id}')
    ax.legend()
    plt.tight_layout()
    
    # Save plot to buffer
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

# --- PDF Report Generation ---
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
    
    # Project Summaries
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
    
    # Delay Analysis
    pdf.chapter_title('Delay Cause Analysis')
    if delay_causes.empty:
        pdf.chapter_body("No delays reported across projects.")
    else:
        pdf.chapter_body("Frequency of delay causes across projects:")
        delay_img = plot_delay_causes(delay_causes)
        pdf.add_image(delay_img)
    
    # You can add more sections here: Trends, KPIs over time, Comparisons, Recommendations
    
    pdf.output('construction_analysis_report.pdf')

# --- Main Flow ---
def main():
    df = load_data()
    df = calculate_kpis(df)
    summary_df = project_summary(df)
    delay_causes = delay_cause_analysis(df)
    
    generate_pdf_report(df, summary_df, delay_causes)
    print("PDF report generated: construction_analysis_report.pdf")

if __name__ == "__main__":
    main()
