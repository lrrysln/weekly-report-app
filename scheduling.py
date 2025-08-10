# streamlit_app.py
import streamlit as st
import pandas as pd
import math
from datetime import datetime
from collections import Counter
from io import BytesIO

import plotly.express as px

from fpdf import FPDF

# Optional python-pptx
try:
    from pptx import Presentation
    from pptx.util import Inches
    PPTX_AVAILABLE = True
except Exception:
    PPTX_AVAILABLE = False

st.set_page_config(page_title="Post-Construction Performance Dashboard", layout="wide")

# ----------------- Helper functions (same logic as CLI script) -----------------
def parse_dates(df, cols):
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors='coerce')
    return df

def safe_div(a, b):
    try:
        if a is None or b is None: return None
        if pd.isna(a) or pd.isna(b): return None
        if b == 0: return None
        return a / b
    except Exception:
        return None

def compute_duration_days(start, finish):
    if pd.isna(start) or pd.isna(finish):
        return None
    return (finish - start).days

def normalize_delay_causes(series):
    result = []
    for val in series.fillna(''):
        if not val:
            result.append([])
        else:
            parts = [p.strip().lower() for p in (str(val).replace(',', ';').split(';')) if p.strip()]
            result.append(parts)
    return result

def compute_project_kpis(raw):
    delay_lists = normalize_delay_causes(raw.get('delay_causes', pd.Series(['']*len(raw))))
    rows = []
    for idx, row in raw.iterrows():
        planned_start = row.get('planned_start')
        planned_finish = row.get('planned_finish')
        actual_start = row.get('actual_start')
        actual_finish = row.get('actual_finish')
        planned_cost = row.get('planned_cost')
        actual_cost = row.get('actual_cost')
        area = row.get('area_sqft')

        planned_duration = compute_duration_days(planned_start, planned_finish)
        actual_duration = compute_duration_days(actual_start, actual_finish)
        schedule_variance_days = None if planned_duration is None or actual_duration is None else actual_duration - planned_duration

        schedule_variance_pct = None
        if planned_duration and planned_duration != 0 and schedule_variance_days is not None:
            schedule_variance_pct = (actual_duration - planned_duration) / planned_duration * 100

        cost_variance = None if pd.isna(planned_cost) or pd.isna(actual_cost) else actual_cost - planned_cost
        cost_variance_pct = None
        if planned_cost and planned_cost != 0 and not pd.isna(cost_variance):
            cost_variance_pct = cost_variance / planned_cost * 100

        # CPI/EVM proxy
        if 'earned_value' in row and not pd.isna(row.get('earned_value')) and not pd.isna(actual_cost):
            ev = row.get('earned_value')
            ac = actual_cost
            cpi = safe_div(ev, ac)
        elif not pd.isna(row.get('percent_complete')) and not pd.isna(planned_cost) and not pd.isna(actual_cost):
            ev = row.get('percent_complete') / 100.0 * planned_cost
            ac = actual_cost
            cpi = safe_div(ev, ac)
        else:
            cpi = None

        cost_per_sqft = None
        if area and not pd.isna(actual_cost) and area != 0:
            cost_per_sqft = actual_cost / area

        rows.append({
            'project_id': row.get('project_id'),
            'project_name': row.get('project_name'),
            'asset_type': row.get('asset_type'),
            'planned_duration_days': planned_duration,
            'actual_duration_days': actual_duration,
            'schedule_variance_days': schedule_variance_days,
            'schedule_variance_pct': schedule_variance_pct,
            'planned_cost': planned_cost,
            'actual_cost': actual_cost,
            'cost_variance': cost_variance,
            'cost_variance_pct': cost_variance_pct,
            'CPI': cpi,
            'cost_per_sqft': cost_per_sqft,
            'safety_incidents': row.get('safety_incidents', 0),
            'contractor': row.get('contractor'),
            'weather_delay_days': row.get('weather_delay_days', 0),
            'defects_count': row.get('defects_count', 0),
            'warranty_claims': row.get('warranty_claims', 0),
            'critical_path_changes': row.get('critical_path_changes', 0),
            'delay_causes_list': delay_lists[idx],
        })
    return pd.DataFrame(rows)

def aggregate_portfolio_kpis(kpi_df):
    res = {}
    count = len(kpi_df)
    res['project_count'] = count
    if count == 0:
        return res
    res['avg_planned_duration'] = pd.Series(kpi_df['planned_duration_days']).dropna().mean()
    res['avg_actual_duration'] = pd.Series(kpi_df['actual_duration_days']).dropna().mean()
    res['median_schedule_variance_days'] = pd.Series(kpi_df['schedule_variance_days']).dropna().median()
    res['avg_schedule_variance_pct'] = pd.Series(kpi_df['schedule_variance_pct']).dropna().mean()
    res['avg_cost_variance_pct'] = pd.Series(kpi_df['cost_variance_pct']).dropna().mean()
    res['avg_CPI'] = pd.Series(kpi_df['CPI']).dropna().mean()
    res['avg_cost_per_sqft'] = pd.Series(kpi_df['cost_per_sqft']).dropna().mean()
    res['total_safety_incidents'] = int(pd.Series(kpi_df['safety_incidents']).fillna(0).sum())
    res['avg_weather_delay_days'] = pd.Series(kpi_df['weather_delay_days']).dropna().mean()
    res['avg_critical_path_changes'] = pd.Series(kpi_df['critical_path_changes']).dropna().mean()
    return res

def compute_delay_cause_breakdown(kpi_df):
    cnt = Counter()
    for lst in kpi_df['delay_causes_list'].fillna([]):
        cnt.update(lst)
    items = sorted(cnt.items(), key=lambda x: x[1], reverse=True)
    return pd.DataFrame(items, columns=['cause', 'count'])

def contractor_scorecard(kpi_df):
    groups = kpi_df.groupby('contractor', dropna=True)
    rows = []
    for name, g in groups:
        rows.append({
            'contractor': name,
            'projects': len(g),
            'avg_schedule_variance_pct': g['schedule_variance_pct'].dropna().mean(),
            'avg_cost_variance_pct': g['cost_variance_pct'].dropna().mean(),
            'total_safety_incidents': int(g['safety_incidents'].fillna(0).sum()),
            'avg_CPI': g['CPI'].dropna().mean()
        })
    return pd.DataFrame(rows).sort_values('projects', ascending=False)

# ----------------- Caching compute-heavy functions -----------------
@st.cache_data
def load_dataframe(uploaded_file):
    ext = uploaded_file.name.split('.')[-1].lower()
    if ext in ('xls', 'xlsx'):
        df = pd.read_excel(uploaded_file)
    else:
        df = pd.read_csv(uploaded_file)
    # normalize columns: strip whitespace
    df.columns = [c.strip() for c in df.columns]
    df = parse_dates(df, ['planned_start','planned_finish','actual_start','actual_finish'])
    return df

@st.cache_data
def compute_all_kpis(df):
    kpis = compute_project_kpis(df)
    portfolio = aggregate_portfolio_kpis(kpis)
    delay = compute_delay_cause_breakdown(kpis)
    contractor = contractor_scorecard(kpis)
    return kpis, portfolio, delay, contractor

# ----------------- UI -----------------
st.title("🏗️ Post-Construction Performance Dashboard (Streamlit)")

with st.sidebar:
    st.header("Upload & Options")
    uploaded = st.file_uploader("Upload projects CSV or Excel", type=['csv','xls','xlsx'])
    pptx_checkbox = st.checkbox("Create PPTX (requires python-pptx)", value=False)
    generate_btn = st.button("Generate Reports (PDF & Excel)", type="primary")
    st.markdown("---")
    st.write("PDF generation runs when you click **Generate Reports**.")
    st.write("PPTX will be created only if checked and python-pptx is installed on the server.")

if not uploaded:
    st.info("Upload a CSV/Excel file with project-level rows to begin. See recommended columns in the README (project_id, project_name, planned_start, planned_finish, actual_start, actual_finish, planned_cost, actual_cost, area_sqft, delay_causes, safety_incidents, contractor, weather_delay_days, percent_complete, earned_value, defects_count, warranty_claims, critical_path_changes).")
    st.stop()

# Load dataframe
try:
    raw_df = load_dataframe(uploaded)
except Exception as e:
    st.error(f"Could not read uploaded file: {e}")
    st.stop()

st.success(f"Loaded {len(raw_df)} rows from {uploaded.name}")

# Compute KPIs
with st.spinner("Computing KPIs..."):
    kpi_df, portfolio_kpis, delay_df, contractor_df = compute_all_kpis(raw_df)

# Tabs
tabs = st.tabs(["Executive Summary","Per-Project KPIs","Delay Causes","Contractor Scorecard","Downloads"])

# ========== Executive Summary ==========
with tabs[0]:
    st.header("Executive Summary")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Projects", portfolio_kpis.get('project_count', 0))
    c2.metric("Avg Planned Duration (days)", f"{portfolio_kpis.get('avg_planned_duration'):.1f}" if portfolio_kpis.get('avg_planned_duration') else "n/a")
    c3.metric("Avg Actual Duration (days)", f"{portfolio_kpis.get('avg_actual_duration'):.1f}" if portfolio_kpis.get('avg_actual_duration') else "n/a")
    c4.metric("Avg Cost Variance (%)", f"{portfolio_kpis.get('avg_cost_variance_pct'):.1f}%" if portfolio_kpis.get('avg_cost_variance_pct') else "n/a")

    st.markdown("### Duration: planned vs actual (interactive)")
    # Prepare duration chart
    dur_chart_df = kpi_df[['project_name','planned_duration_days','actual_duration_days']].dropna(subset=['project_name'])
    if not dur_chart_df.empty:
        dur_chart_df = dur_chart_df.sort_values('planned_duration_days', ascending=False).head(50)
        dur_melt = dur_chart_df.melt(id_vars='project_name', value_vars=['planned_duration_days','actual_duration_days'],
                                     var_name='type', value_name='days')
        fig_dur = px.bar(dur_melt, x='days', y='project_name', color='type', orientation='h',
                         title='Planned vs Actual Duration (days)', barmode='group', height=600)
        st.plotly_chart(fig_dur, use_container_width=True)
    else:
        st.info("Not enough duration data to build chart.")

    st.markdown("### Cost variance (interactive)")
    cv_df = kpi_df[['project_name','cost_variance_pct']].dropna()
    if not cv_df.empty:
        cv_df = cv_df.sort_values('cost_variance_pct', ascending=False).head(50)
        fig_cv = px.bar(cv_df, x='cost_variance_pct', y='project_name', orientation='h', height=600,
                        labels={'cost_variance_pct':'Cost Variance (%)','project_name':'Project'})
        st.plotly_chart(fig_cv, use_container_width=True)
    else:
        st.info("Not enough cost data to build chart.")

    st.markdown("### Delay cause breakdown (interactive)")
    if not delay_df.empty:
        fig_delay = px.pie(delay_df, names='cause', values='count', title='Delay Cause Breakdown')
        st.plotly_chart(fig_delay, use_container_width=True)
    else:
        st.info("No delay cause tags found in data.")

# ========== Per-Project KPIs ==========
with tabs[1]:
    st.header("Per-Project KPIs")
    st.write("Sortable, filterable table of per-project KPIs.")
    # Format some columns
    display_df = kpi_df.copy()
    # Nicely format percentages
    def fmt_pct(x):
        return f"{x:.1f}%" if pd.notna(x) else ""
    if 'schedule_variance_pct' in display_df.columns:
        display_df['schedule_variance_pct'] = display_df['schedule_variance_pct'].apply(lambda x: fmt_pct(x))
    if 'cost_variance_pct' in display_df.columns:
        display_df['cost_variance_pct'] = display_df['cost_variance_pct'].apply(lambda x: fmt_pct(x))
    st.dataframe(display_df.fillna(""), use_container_width=True)

# ========== Delay Causes ==========
with tabs[2]:
    st.header("Delay Cause Breakdown & Table")
    st.write("Counts of delay causes across projects")
    if not delay_df.empty:
        st.plotly_chart(px.bar(delay_df.sort_values('count', ascending=False), x='count', y='cause', orientation='h', title='Delay Causes'), use_container_width=True)
        st.dataframe(delay_df, use_container_width=True)
    else:
        st.info("No delay causes found.")

# ========== Contractor Scorecard ==========
with tabs[3]:
    st.header("Contractor Scorecard")
    if not contractor_df.empty:
        st.plotly_chart(px.bar(contractor_df.head(30), x='projects', y='contractor', orientation='h', title='Projects per Contractor'), use_container_width=True)
        st.dataframe(contractor_df.fillna(""), use_container_width=True)
    else:
        st.info("No contractor data available.")

# ========== Downloads & Report Generation ==========
with tabs[4]:
    st.header("Downloads & Report Generation")
    st.write("Generate outputs. PDF is created when you click **Generate Reports**. Excel is available immediately. PPTX only if checked in sidebar and python-pptx is installed on the server.")

    # Prepare Excel bytes (always available)
    def create_excel_bytes(raw_df, kpi_df, portfolio_kpis, delay_df, contractor_df):
        out = BytesIO()
        with pd.ExcelWriter(out, engine='openpyxl') as writer:
            raw_df.to_excel(writer, sheet_name='raw_data', index=False)
            kpi_df.to_excel(writer, sheet_name='per_project_kpis', index=False)
            delay_df.to_excel(writer, sheet_name='delay_causes', index=False)
            contractor_df.to_excel(writer, sheet_name='contractor_scorecard', index=False)
            pd.DataFrame([portfolio_kpis]).to_excel(writer, sheet_name='portfolio_summary', index=False)
        out.seek(0)
        return out.read()

    excel_bytes = create_excel_bytes(raw_df, kpi_df, portfolio_kpis, delay_df, contractor_df)
    excel_name = f"post_construction_report_{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}.xlsx"
    st.download_button("Download Excel", data=excel_bytes, file_name=excel_name, mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    # PDF and PPTX generation on demand
    if generate_btn:
        with st.spinner("Generating PDF (and optional PPTX)..."):
            # Create some temporary images from plotly for embedding in PDF
            charts = {}
            # Duration chart image
            try:
                if not dur_chart_df.empty:
                    charts['duration'] = fig_dur.to_image(format='png', width=1200, height=600, scale=2)
            except Exception:
                charts['duration'] = None
            try:
                if not cv_df.empty:
                    charts['cost_variance'] = fig_cv.to_image(format='png', width=1200, height=600, scale=2)
            except Exception:
                charts['cost_variance'] = None
            try:
                if not delay_df.empty:
                    charts['delay_pie'] = fig_delay.to_image(format='png', width=800, height=800, scale=2)
            except Exception:
                charts['delay_pie'] = None

            # Create PDF in memory
            pdf = FPDF(orientation='P', unit='mm', format='A4')
            pdf.set_auto_page_break(auto=True, margin=15)
            pdf.add_page()
            pdf.set_font("Arial", 'B', 16)
            pdf.cell(0, 8, "Post-Construction Executive Summary", ln=True)
            pdf.ln(2)
            pdf.set_font("Arial", size=11)
            pdf.cell(0, 6, f"Projects analyzed: {portfolio_kpis.get('project_count', 0)}", ln=True)
            pdf.cell(0, 6, f"Avg planned duration (days): {format_number(portfolio_kpis.get('avg_planned_duration'))}", ln=True)
            pdf.cell(0, 6, f"Avg actual duration (days): {format_number(portfolio_kpis.get('avg_actual_duration'))}", ln=True)
            pdf.cell(0, 6, f"Median schedule variance (days): {format_number(portfolio_kpis.get('median_schedule_variance_days'))}", ln=True)
            pdf.cell(0, 6, f"Avg schedule variance (%): {format_percent(portfolio_kpis.get('avg_schedule_variance_pct'))}", ln=True)
            pdf.cell(0, 6, f"Avg cost variance (%): {format_percent(portfolio_kpis.get('avg_cost_variance_pct'))}", ln=True)
            pdf.cell(0, 6, f"Avg CPI: {format_number(portfolio_kpis.get('avg_CPI'))}", ln=True)
            pdf.ln(4)

            # embed images if present
            for key in ('duration','cost_variance','delay_pie'):
                img = charts.get(key)
                if img:
                    # write bytes to fpdf from memory by saving to BytesIO and using FPDF.image via temp file workaround
                    img_b = BytesIO(img)
                    # FPDF.image needs a filename — use temporary file in memory by writing to BytesIO + trick: s output to 'S' not supported for image
                    # Simpler: write to a temporary file
                    import tempfile, os
                    tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
                    try:
                        tmp.write(img_b.read())
                        tmp.flush()
                        tmp.close()
                        # Fit width 180mm (A4 margin)
                        pdf.image(tmp.name, w=180)
                        pdf.ln(4)
                    finally:
                        try:
                            os.unlink(tmp.name)
                        except Exception:
                            pass

            # top projects
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(0, 6, "Top Projects (by cost variance % / schedule variance):", ln=True)
            pdf.set_font("Arial", size=10)
            top_projects = kpi_df.copy()
            top_projects['abs_cost_var_pct'] = top_projects['cost_variance_pct'].abs().fillna(0)
            top_projects_sorted = top_projects.sort_values(['abs_cost_var_pct','schedule_variance_pct'], ascending=[False, False])
            if not top_projects_sorted.empty:
                for _, r in top_projects_sorted.head(6).iterrows():
                    name = (r.get('project_name') or str(r.get('project_id')))[:50]
                    scv = format_percent(r.get('schedule_variance_pct'))
                    ccv = format_percent(r.get('cost_variance_pct'))
                    pdf.multi_cell(0, 5, f"• {name} — Schedule var: {scv}, Cost var: {ccv}")
            pdf.ln(3)
            pdf.set_font("Arial", size=8)
            pdf.cell(0, 6, f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}", ln=True)

            # Output PDF bytes
            try:
                pdf_bytes = pdf.output(dest='S').encode('latin-1')
            except TypeError:
                # older fpdf behavior
                pdf_file = BytesIO()
                pdf.output(pdf_file)
                pdf_bytes = pdf_file.getvalue()

            pdf_name = f"executive_summary_{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}.pdf"
            st.success("PDF generated successfully.")
            st.download_button("Download PDF", data=pdf_bytes, file_name=pdf_name, mime="application/pdf")

            # Optional PPTX generation
            if pptx_checkbox:
                if not PPTX_AVAILABLE:
                    st.warning("python-pptx not installed on server — cannot create PPTX.")
                else:
                    prs = Presentation()
                    s = prs.slides.add_slide(prs.slide_layouts[0])
                    s.shapes.title.text = "Post-Construction Performance Report"
                    try:
                        s.placeholders[1].text = f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"
                    except Exception:
                        pass

                    # portfolio slide
                    slide = prs.slides.add_slide(prs.slide_layouts[5])
                    slide.shapes.title.text = "Portfolio Summary"
                    tf = slide.shapes.placeholders[1].text_frame
                    tf.text = f"Projects: {portfolio_kpis.get('project_count',0)}"
                    p = tf.add_paragraph()
                    p.text = f"Avg schedule variance (%): {format_percent(portfolio_kpis.get('avg_schedule_variance_pct'))}"

                    # attach chart images
                    for key, b in charts.items():
                        if b:
                            tmp = BytesIO(b)
                            # pptx wants a filename-like object; save to temp file
                            import tempfile, os
                            tmpf = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
                            try:
                                tmpf.write(tmp.getvalue())
                                tmpf.flush()
                                tmpf.close()
                                slide = prs.slides.add_slide(prs.slide_layouts[5])
                                slide.shapes.title.text = key.replace('_',' ').title()
                                slide.shapes.add_picture(tmpf.name, Inches(0.5), Inches(1.2), width=Inches(9))
                            finally:
                                try:
                                    os.unlink(tmpf.name)
                                except Exception:
                                    pass

                    # project detail slides (top 10)
                    for _, row in kpi_df.head(10).iterrows():
                        slide = prs.slides.add_slide(prs.slide_layouts[5])
                        slide.shapes.title.text = str(row.get('project_name') or row.get('project_id'))
                        body = slide.shapes.placeholders[1].text_frame
                        body.text = f"Planned dur: {row.get('planned_duration_days')} days"
                        body.add_paragraph().text = f"Actual dur: {row.get('actual_duration_days')} days"
                        body.add_paragraph().text = f"Schedule var (%): {format_percent(row.get('schedule_variance_pct'))}"
                        body.add_paragraph().text = f"Cost var (%): {format_percent(row.get('cost_variance_pct'))}"
                        body.add_paragraph().text = f"CPI: {format_number(row.get('CPI'))}"

                    # write to bytes
                    pptx_io = BytesIO()
                    prs.save(pptx_io)
                    pptx_io.seek(0)
                    pptx_name = f"post_construction_report_{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}.pptx"
                    st.download_button("Download PPTX", data=pptx_io.read(), file_name=pptx_name, mime="application/vnd.openxmlformats-officedocument.presentationml.presentation")
            else:
                st.info("PPTX generation skipped (checkbox not checked).")

    else:
        st.info("Click 'Generate Reports' in the sidebar to create PDF and optional PPTX.")

# ----------------- Utility formatting functions -----------------
def format_number(x):
    if x is None or (isinstance(x, float) and math.isnan(x)): return "n/a"
    if isinstance(x, float): return f"{x:,.2f}"
    return str(x)

def format_percent(x):
    if x is None or (isinstance(x, float) and math.isnan(x)): return "n/a"
    return f"{x:.1f}%"
