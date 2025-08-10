#!/usr/bin/env python3
import argparse
import os
import math
from datetime import datetime
from collections import Counter, defaultdict

import pandas as pd
import matplotlib.pyplot as plt
from fpdf import FPDF

# Optional import for PPTX output
try:
    from pptx import Presentation
    from pptx.util import Inches, Pt
    PPTX_AVAILABLE = True
except Exception:
    PPTX_AVAILABLE = False

# ---------- Helper functions ----------
def parse_dates(df, cols):
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors='coerce')
    return df

def safe_div(a, b):
    try:
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
    """Return a list of cleaned delay cause lists per row."""
    result = []
    for val in series.fillna(''):
        if not val:
            result.append([])
        else:
            # split on ; or , and strip, lower
            parts = [p.strip().lower() for p in (str(val).replace(',', ';').split(';')) if p.strip()]
            result.append(parts)
    return result

# ---------- KPI calculations ----------
def compute_project_kpis(df):
    """Compute per-project KPIs and append as columns; return kpi_df."""
    kpis = []
    delay_lists = normalize_delay_causes(df.get('delay_causes', pd.Series(['']*len(df))))
    for idx, row in df.iterrows():
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

        # EVM / CPI (simple)
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

        kpis.append({
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
    return pd.DataFrame(kpis)

def aggregate_portfolio_kpis(kpi_df):
    """Return a dict of portfolio-level KPIs."""
    res = {}
    count = len(kpi_df)
    res['project_count'] = count
    if count == 0:
        return res

    # averages
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
    # return as sorted DataFrame
    items = sorted(cnt.items(), key=lambda x: x[1], reverse=True)
    return pd.DataFrame(items, columns=['cause', 'count'])

def contractor_scorecard(kpi_df):
    # For each contractor compute avg schedule variance pct, avg cost variance pct, projects, safety incidents
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

# ---------- Reporting ----------
def save_excel(output_path, raw_df, kpi_df, portfolio_kpis, delay_df, contractor_df):
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        raw_df.to_excel(writer, sheet_name='raw_data', index=False)
        kpi_df.to_excel(writer, sheet_name='per_project_kpis', index=False)
        delay_df.to_excel(writer, sheet_name='delay_causes', index=False)
        contractor_df.to_excel(writer, sheet_name='contractor_scorecard', index=False)
        # Portfolio: write summary as a single-row DF
        pd.DataFrame([portfolio_kpis]).to_excel(writer, sheet_name='portfolio_summary', index=False)

def create_charts(outdir, kpi_df, delay_df):
    charts = {}
    # Duration comparison chart (planned vs actual)
    try:
        small = kpi_df[['project_name','planned_duration_days','actual_duration_days']].dropna(subset=['project_name'])
        small = small.sort_values('planned_duration_days', na_position='last').head(15)
        fig, ax = plt.subplots(figsize=(8, max(4, len(small)*0.4)))
        idx = range(len(small))
        ax.barh(idx, small['planned_duration_days'].fillna(0), label='Planned')
        ax.barh(idx, small['actual_duration_days'].fillna(0), left=small['planned_duration_days'].fillna(0), label='Actual (stacked)')
        ax.set_yticks(idx)
        ax.set_yticklabels(small['project_name'])
        ax.set_xlabel('Days')
        ax.set_title('Planned vs Actual Duration (sample)')
        ax.legend()
        plt.tight_layout()
        p1 = os.path.join(outdir, 'chart_duration.png')
        fig.savefig(p1, dpi=150)
        plt.close(fig)
        charts['duration'] = p1
    except Exception as e:
        print("Could not create duration chart:", e)

    # Cost variance chart
    try:
        small = kpi_df[['project_name','cost_variance_pct']].dropna().sort_values('cost_variance_pct', ascending=False).head(20)
        fig, ax = plt.subplots(figsize=(8, max(3, len(small)*0.35)))
        ax.barh(range(len(small)), small['cost_variance_pct'])
        ax.set_yticks(range(len(small)))
        ax.set_yticklabels(small['project_name'])
        ax.set_xlabel('Cost variance %')
        ax.set_title('Top Cost Variances (%)')
        plt.tight_layout()
        p2 = os.path.join(outdir, 'chart_cost_variance.png')
        fig.savefig(p2, dpi=150)
        plt.close(fig)
        charts['cost_variance'] = p2
    except Exception as e:
        print("Could not create cost variance chart:", e)

    # Delay causes pie
    try:
        if not delay_df.empty:
            fig, ax = plt.subplots(figsize=(6,6))
            ax.pie(delay_df['count'], labels=delay_df['cause'], autopct='%1.1f%%', startangle=140)
            ax.set_title('Delay Cause Breakdown')
            plt.tight_layout()
            p3 = os.path.join(outdir, 'chart_delay_causes.png')
            fig.savefig(p3, dpi=150)
            plt.close(fig)
            charts['delay_pie'] = p3
    except Exception as e:
        print("Could not create delay causes chart:", e)

    return charts

def create_pdf_summary(pdf_path, portfolio_kpis, charts, top_projects_df):
    pdf = FPDF(orientation='P', unit='mm', format='A4')
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 8, "Post-Construction Executive Summary", ln=True)
    pdf.ln(2)

    pdf.set_font("Arial", size=11)
    # key KPIs
    pdf.cell(0, 6, f"Projects analyzed: {portfolio_kpis.get('project_count', 0)}", ln=True)
    pdf.cell(0, 6, f"Avg planned duration (days): {format_number(portfolio_kpis.get('avg_planned_duration'))}", ln=True)
    pdf.cell(0, 6, f"Avg actual duration (days): {format_number(portfolio_kpis.get('avg_actual_duration'))}", ln=True)
    pdf.cell(0, 6, f"Median schedule variance (days): {format_number(portfolio_kpis.get('median_schedule_variance_days'))}", ln=True)
    pdf.cell(0, 6, f"Avg schedule variance (%): {format_percent(portfolio_kpis.get('avg_schedule_variance_pct'))}", ln=True)
    pdf.cell(0, 6, f"Avg cost variance (%): {format_percent(portfolio_kpis.get('avg_cost_variance_pct'))}", ln=True)
    pdf.cell(0, 6, f"Avg CPI: {format_number(portfolio_kpis.get('avg_CPI'))}", ln=True)
    pdf.ln(4)

    # charts
    x = 0
    for key in ('duration', 'cost_variance', 'delay_pie'):
        if charts.get(key) and os.path.exists(charts[key]):
            try:
                # embed image scaled
                pdf.image(charts[key], w=180)
                pdf.ln(4)
            except Exception as e:
                print("Could not embed chart in PDF:", e)

    # Top projects snippet
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 6, "Top Projects (by cost variance % / schedule variance):", ln=True)
    pdf.set_font("Arial", size=10)
    if not top_projects_df.empty:
        for _, r in top_projects_df.head(6).iterrows():
            name = r.get('project_name', 'n/a')[:50]
            scv = format_percent(r.get('schedule_variance_pct'))
            ccv = format_percent(r.get('cost_variance_pct'))
            pdf.multi_cell(0, 5, f"• {name} — Schedule var: {scv}, Cost var: {ccv}")
    pdf.ln(3)
    pdf.set_font("Arial", size=8)
    pdf.cell(0, 6, f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}", ln=True)

    pdf.output(pdf_path)
    print("Saved PDF:", pdf_path)

def format_number(x):
    if x is None or (isinstance(x, float) and math.isnan(x)): return "n/a"
    if isinstance(x, float): return f"{x:,.2f}"
    return str(x)

def format_percent(x):
    if x is None or (isinstance(x, float) and math.isnan(x)): return "n/a"
    return f"{x:.1f}%"

def create_pptx(pptx_path, kpi_df, charts, portfolio_kpis):
    if not PPTX_AVAILABLE:
        print("python-pptx not available — skipping PPTX creation.")
        return
    prs = Presentation()
    # Title slide
    s = prs.slides.add_slide(prs.slide_layouts[0])
    title = s.shapes.title
    subtitle = s.placeholders[1]
    title.text = "Post-Construction Performance Report"
    subtitle.text = f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"

    # Portfolio summary slide
    s2 = prs.slides.add_slide(prs.slide_layouts[5])
    title = s2.shapes.title
    title.text = "Portfolio Summary"
    tf = s2.shapes.placeholders[1].text_frame
    tf.text = f"Projects: {portfolio_kpis.get('project_count',0)}"
    p = tf.add_paragraph()
    p.text = f"Avg schedule variance (%): {format_percent(portfolio_kpis.get('avg_schedule_variance_pct'))}"

    # Charts slide(s)
    for key in charts:
        if os.path.exists(charts[key]):
            slide = prs.slides.add_slide(prs.slide_layouts[5])
            slide.shapes.title.text = key.replace('_',' ').title()
            left = Inches(0.5); top = Inches(1.2); width = Inches(9)
            slide.shapes.add_picture(charts[key], left, top, width=width)

    # Add a few project detail slides
    for i, row in kpi_df.head(10).iterrows():
        slide = prs.slides.add_slide(prs.slide_layouts[5])
        slide.shapes.title.text = row.get('project_name') or str(row.get('project_id'))
        body = slide.shapes.placeholders[1].text_frame
        body.text = f"Planned dur: {row.get('planned_duration_days')} days"
        body.add_paragraph().text = f"Actual dur: {row.get('actual_duration_days')} days"
        body.add_paragraph().text = f"Schedule var (%): {format_percent(row.get('schedule_variance_pct'))}"
        body.add_paragraph().text = f"Cost var (%): {format_percent(row.get('cost_variance_pct'))}"
        body.add_paragraph().text = f"CPI: {format_number(row.get('CPI'))}"
    prs.save(pptx_path)
    print("Saved PPTX:", pptx_path)

# ---------- CLI ----------
def main():
    parser = argparse.ArgumentParser(description="Post-Construction Performance Report generator")
    parser.add_argument('--input', '-i', required=True, help="Input CSV or Excel with project rows")
    parser.add_argument('--outdir', '-o', default='reports', help="Output directory")
    parser.add_argument('--pptx', action='store_true', help="Also create a PowerPoint (requires python-pptx)")
    args = parser.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    # Load data
    ext = os.path.splitext(args.input)[1].lower()
    if ext in ('.xlsx', '.xls'):
        raw = pd.read_excel(args.input)
    else:
        raw = pd.read_csv(args.input)

    # Standardize column names (lower)
    raw.columns = [c.strip() for c in raw.columns]
    # parse dates
    raw = parse_dates(raw, ['planned_start','planned_finish','actual_start','actual_finish'])

    # compute KPIs
    kpi_df = compute_project_kpis(raw)
    portfolio_kpis = aggregate_portfolio_kpis(kpi_df)
    delay_df = compute_delay_cause_breakdown(kpi_df)
    contractor_df = contractor_scorecard(kpi_df)

    # Save Excel
    timestamp = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
    excel_path = os.path.join(args.outdir, f"post_construction_report_{timestamp}.xlsx")
    save_excel(excel_path, raw, kpi_df, portfolio_kpis, delay_df, contractor_df)
    print("Saved Excel:", excel_path)

    # Create charts
    charts = create_charts(args.outdir, kpi_df, delay_df)

    # PDF executive summary
    pdf_path = os.path.join(args.outdir, f"executive_summary_{timestamp}.pdf")
    # Determine "top projects" by cost variance magnitude
    top_projects = kpi_df.copy()
    top_projects['abs_cost_var_pct'] = top_projects['cost_variance_pct'].abs().fillna(0)
    top_projects_sorted = top_projects.sort_values(['abs_cost_var_pct','schedule_variance_pct'], ascending=[False, False])
    create_pdf_summary(pdf_path, portfolio_kpis, charts, top_projects_sorted)

    # optional PPTX
    if args.pptx:
        pptx_path = os.path.join(args.outdir, f"post_construction_report_{timestamp}.pptx")
        create_pptx(pptx_path, kpi_df, charts, portfolio_kpis)

    print("Done. Outputs in:", os.path.abspath(args.outdir))

if __name__ == '__main__':
    main()

