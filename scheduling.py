# streamlit_app.py - V1 Construction Management Dashboard
import streamlit as st
import pandas as pd
import numpy as np
import math
from datetime import datetime, timedelta
from collections import Counter
from io import BytesIO
import json

import plotly.express as px
import plotly.graph_objects as go

from fpdf import FPDF

# Optional python-pptx
try:
    from pptx import Presentation
    from pptx.util import Inches
    PPTX_AVAILABLE = True
except Exception:
    PPTX_AVAILABLE = False

st.set_page_config(page_title="Construction Management Dashboard V1", layout="wide")

# ================== STAGE 1: PRE-DEVELOPMENT FUNCTIONS ==================

def calculate_roi_irr(land_cost, build_cost, soft_costs, financing_cost, total_revenue, hold_period_years=2):
    """Simple ROI/IRR calculator for deal analysis"""
    try:
        total_cost = land_cost + build_cost + soft_costs + financing_cost
        net_profit = total_revenue - total_cost
        roi = (net_profit / total_cost) * 100 if total_cost > 0 else 0
        
        # Simple IRR approximation (not exact but good for V1)
        annual_return = net_profit / hold_period_years
        irr = (annual_return / total_cost) * 100 if total_cost > 0 else 0
        
        return {
            'total_cost': total_cost,
            'net_profit': net_profit,
            'roi': roi,
            'irr': irr,
            'margin': (net_profit / total_revenue) * 100 if total_revenue > 0 else 0
        }
    except Exception:
        return None

def risk_flags(land_cost, build_cost, contingency_pct, financing_secured):
    """Basic risk flagging for pre-development stage"""
    flags = []
    
    if contingency_pct < 5:
        flags.append("⚠️ LOW CONTINGENCY: Less than 5% contingency is risky")
    if contingency_pct > 20:
        flags.append("⚠️ HIGH CONTINGENCY: Over 20% suggests high uncertainty")
    
    if not financing_secured:
        flags.append("🔴 FINANCING RISK: Financing not yet secured")
    
    cost_ratio = build_cost / land_cost if land_cost > 0 else 0
    if cost_ratio > 5:
        flags.append("⚠️ HIGH BUILD-TO-LAND RATIO: Build cost is >5x land cost")
    
    return flags

# ================== STAGE 2: DEVELOPMENT FUNCTIONS ==================

def analyze_schedule_risks(schedule_df):
    """Analyze uploaded schedule for risks and issues"""
    risks = []
    
    if 'duration' not in schedule_df.columns:
        return ["❌ No duration column found in schedule"]
    
    # Check for unrealistic durations
    long_tasks = schedule_df[schedule_df['duration'] > 60]
    if len(long_tasks) > 0:
        risks.append(f"⚠️ {len(long_tasks)} tasks with >60 day duration - check if realistic")
    
    # Check for very short critical tasks
    short_tasks = schedule_df[schedule_df['duration'] < 1]
    if len(short_tasks) > 0:
        risks.append(f"⚠️ {len(short_tasks)} tasks with <1 day duration - may cause scheduling issues")
    
    # Basic overlap detection (simplified)
    if 'start_date' in schedule_df.columns and 'finish_date' in schedule_df.columns:
        schedule_df['start_date'] = pd.to_datetime(schedule_df['start_date'], errors='coerce')
        schedule_df['finish_date'] = pd.to_datetime(schedule_df['finish_date'], errors='coerce')
        
        overlaps = 0
        for i, row in schedule_df.iterrows():
            for j, other_row in schedule_df.iterrows():
                if i != j and pd.notna(row['start_date']) and pd.notna(other_row['start_date']):
                    if (row['start_date'] <= other_row['finish_date'] and 
                        row['finish_date'] >= other_row['start_date']):
                        overlaps += 1
        
        if overlaps > len(schedule_df) * 0.3:  # If >30% of tasks overlap
            risks.append(f"⚠️ High task overlap detected - review dependencies")
    
    return risks if risks else ["✅ No major schedule risks detected"]

def weather_risk_analysis(start_date, end_date, location="General"):
    """Simple weather risk analysis (V1 version - rules based)"""
    try:
        start = pd.to_datetime(start_date)
        end = pd.to_datetime(end_date)
        
        risks = []
        
        # Winter months risk
        winter_months = [12, 1, 2]
        if start.month in winter_months or end.month in winter_months:
            risks.append("❄️ WINTER RISK: Project spans winter months - expect weather delays")
        
        # Spring mud season
        spring_months = [3, 4]
        if start.month in spring_months or end.month in spring_months:
            risks.append("🌧️ SPRING RISK: Mud season may impact site access")
        
        # Hurricane season (if applicable)
        hurricane_months = [6, 7, 8, 9, 10, 11]
        if any(month in hurricane_months for month in [start.month, end.month]):
            risks.append("🌀 HURRICANE SEASON: June-November weather risk")
        
        # Long duration risk
        duration = (end - start).days
        if duration > 365:
            risks.append("📅 LONG DURATION: >1 year projects face higher weather variability")
        
        return risks if risks else ["✅ No significant weather risks identified"]
    
    except Exception:
        return ["❌ Could not analyze weather risk - check date format"]

# ================== STAGE 3: POST-DEVELOPMENT FUNCTIONS (from your existing code) ==================

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

# ================== MAIN APP UI ==================

st.title("🏗️ Construction Management Dashboard V1")
st.caption("Pre-Development → Development → Post-Development Analysis")

# Initialize session state
if 'current_stage' not in st.session_state:
    st.session_state.current_stage = 'pre_dev'

# Navigation
col1, col2, col3 = st.columns(3)
with col1:
    if st.button("📊 Pre-Development", use_container_width=True, 
                 type="primary" if st.session_state.current_stage == 'pre_dev' else "secondary"):
        st.session_state.current_stage = 'pre_dev'
with col2:
    if st.button("🚧 Development", use_container_width=True,
                 type="primary" if st.session_state.current_stage == 'dev' else "secondary"):
        st.session_state.current_stage = 'dev'
with col3:
    if st.button("📈 Post-Development", use_container_width=True,
                 type="primary" if st.session_state.current_stage == 'post_dev' else "secondary"):
        st.session_state.current_stage = 'post_dev'

st.markdown("---")

# ================== STAGE 1: PRE-DEVELOPMENT ==================
if st.session_state.current_stage == 'pre_dev':
    st.header("📊 Pre-Development: Deal Analysis")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Project Economics")
        
        # Basic inputs
        project_name = st.text_input("Project Name", value="Sample Development")
        
        c1, c2 = st.columns(2)
        with c1:
            land_cost = st.number_input("Land Cost ($)", value=500000, step=10000)
            build_cost = st.number_input("Build Cost ($)", value=1500000, step=10000)
        with c2:
            soft_costs = st.number_input("Soft Costs ($)", value=200000, step=5000)
            financing_cost = st.number_input("Financing Cost ($)", value=150000, step=5000)
        
        c3, c4 = st.columns(2)
        with c3:
            total_revenue = st.number_input("Expected Revenue ($)", value=2800000, step=10000)
            contingency_pct = st.slider("Contingency %", 0.0, 25.0, 10.0, 0.5)
        with c4:
            hold_period = st.number_input("Hold Period (years)", value=2.0, step=0.25)
            financing_secured = st.checkbox("Financing Secured?", value=False)
        
        # Calculate metrics
        metrics = calculate_roi_irr(land_cost, build_cost, soft_costs, financing_cost, total_revenue, hold_period)
        
        if metrics:
            st.subheader("Deal Metrics")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total Cost", f"${metrics['total_cost']:,.0f}")
            c2.metric("Net Profit", f"${metrics['net_profit']:,.0f}")
            c3.metric("ROI", f"{metrics['roi']:.1f}%")
            c4.metric("IRR (approx)", f"{metrics['irr']:.1f}%")
            
            # Profit margin gauge
            fig = go.Figure(go.Indicator(
                mode = "gauge+number",
                value = metrics['margin'],
                domain = {'x': [0, 1], 'y': [0, 1]},
                title = {'text': "Profit Margin %"},
                gauge = {
                    'axis': {'range': [None, 50]},
                    'bar': {'color': "darkgreen"},
                    'steps': [
                        {'range': [0, 10], 'color': "lightgray"},
                        {'range': [10, 20], 'color': "yellow"},
                        {'range': [20, 50], 'color': "lightgreen"}],
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': 15}}))
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("Risk Analysis")
        
        # Risk flags
        risks = risk_flags(land_cost, build_cost, contingency_pct, financing_secured)
        
        if risks:
            for risk in risks:
                st.warning(risk)
        else:
            st.success("✅ No major risks identified")
        
        # Cost breakdown
        st.subheader("Cost Breakdown")
        costs_df = pd.DataFrame({
            'Category': ['Land', 'Build', 'Soft Costs', 'Financing'],
            'Amount': [land_cost, build_cost, soft_costs, financing_cost]
        })
        
        fig = px.pie(costs_df, values='Amount', names='Category', title='Cost Distribution')
        st.plotly_chart(fig, use_container_width=True)
        
        # Export deal summary
        if st.button("📄 Export Deal Summary", use_container_width=True):
            deal_summary = {
                'project_name': project_name,
                'land_cost': land_cost,
                'build_cost': build_cost,
                'total_cost': metrics['total_cost'],
                'expected_revenue': total_revenue,
                'roi': metrics['roi'],
                'irr': metrics['irr'],
                'risks': risks,
                'generated': datetime.now().strftime('%Y-%m-%d %H:%M')
            }
            
            st.download_button(
                "Download JSON",
                json.dumps(deal_summary, indent=2),
                f"{project_name.replace(' ', '_')}_deal_summary.json",
                "application/json"
            )

# ================== STAGE 2: DEVELOPMENT ==================
elif st.session_state.current_stage == 'dev':
    st.header("🚧 Development: Schedule & Risk Analysis")
    
    # Schedule upload section
    st.subheader("Schedule Analysis")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        uploaded_schedule = st.file_uploader("Upload Schedule (CSV/Excel)", type=['csv', 'xlsx'], key='schedule')
        
        if not uploaded_schedule:
            st.info("Upload a schedule file to begin analysis. Required columns: task_name, duration, start_date, finish_date")
            
            # Sample schedule data
            sample_schedule = """task_name,duration,start_date,finish_date,critical_path
Site Prep,5,2025-06-01,2025-06-06,Yes
Excavation,8,2025-06-07,2025-06-15,Yes
Foundation,12,2025-06-16,2025-06-28,Yes
Framing,20,2025-06-29,2025-07-19,Yes
Roofing,10,2025-07-20,2025-07-30,No
MEP Rough,15,2025-07-15,2025-07-30,No
Drywall,8,2025-08-01,2025-08-09,Yes"""
            
            st.download_button("Download Sample Schedule", sample_schedule, "sample_schedule.csv", "text/csv")
        
        else:
            try:
                # Load schedule
                if uploaded_schedule.name.endswith('.csv'):
                    schedule_df = pd.read_csv(uploaded_schedule)
                else:
                    schedule_df = pd.read_excel(uploaded_schedule)
                
                st.success(f"Loaded {len(schedule_df)} tasks")
                st.dataframe(schedule_df.head())
                
                # Schedule risk analysis
                risks = analyze_schedule_risks(schedule_df)
                
                st.subheader("Schedule Risk Analysis")
                for risk in risks:
                    if "✅" in risk:
                        st.success(risk)
                    else:
                        st.warning(risk)
                
                # Basic Gantt chart
                if 'start_date' in schedule_df.columns and 'finish_date' in schedule_df.columns:
                    schedule_df['start_date'] = pd.to_datetime(schedule_df['start_date'], errors='coerce')
                    schedule_df['finish_date'] = pd.to_datetime(schedule_df['finish_date'], errors='coerce')
                    
                    # Create Gantt chart
                    fig = px.timeline(
                        schedule_df.dropna(subset=['start_date', 'finish_date']).head(20), 
                        x_start='start_date', 
                        x_end='finish_date', 
                        y='task_name',
                        color='critical_path' if 'critical_path' in schedule_df.columns else None,
                        title='Project Schedule (Gantt Chart)'
                    )
                    fig.update_layout(height=600)
                    st.plotly_chart(fig, use_container_width=True)
                
            except Exception as e:
                st.error(f"Error loading schedule: {e}")
    
    with col2:
        st.subheader("Weather Risk Analysis")
        
        project_start = st.date_input("Project Start Date", datetime.now().date())
        project_end = st.date_input("Project End Date", (datetime.now() + timedelta(days=180)).date())
        project_location = st.text_input("Location", "General")
        
        if st.button("Analyze Weather Risk"):
            weather_risks = weather_risk_analysis(project_start, project_end, project_location)
            
            for risk in weather_risks:
                if "✅" in risk:
                    st.success(risk)
                else:
                    st.warning(risk)
        
        st.subheader("Quick Actions")
        
        if st.button("📊 Generate Schedule Report", use_container_width=True):
            st.info("Schedule report generation coming in V1.1")
        
        if st.button("⚡ Optimize Critical Path", use_container_width=True):
            st.info("AI-powered optimization coming in V1.2")

# ================== STAGE 3: POST-DEVELOPMENT ==================
elif st.session_state.current_stage == 'post_dev':
    st.header("📈 Post-Development: Performance Analysis")
    
    # Your existing post-development code with some UI improvements
    uploaded_file = st.file_uploader("Upload Completed Projects Data", type=['csv', 'xlsx'], key='post_dev')
    
    if not uploaded_file:
        st.info("""
        Upload a CSV/Excel file with completed project data. Required columns:
        - project_id, project_name
        - planned_start, planned_finish, actual_start, actual_finish
        - planned_cost, actual_cost (optional)
        - delay_causes, contractor (optional)
        """)
        
        # Sample post-dev data
        sample_post_dev = """project_id,project_name,planned_start,planned_finish,actual_start,actual_finish,planned_cost,actual_cost,delay_causes,contractor
P001,Downtown Office,2024-01-01,2024-06-30,2024-01-05,2024-07-15,2000000,2150000,weather;permits,ABC Construction
P002,Retail Plaza,2024-02-01,2024-08-31,2024-02-01,2024-09-15,1500000,1475000,materials,XYZ Builders
P003,Warehouse,2024-03-01,2024-07-01,2024-03-10,2024-07-20,800000,850000,labor;weather,ABC Construction"""
        
        st.download_button("Download Sample Post-Dev Data", sample_post_dev, "sample_post_dev.csv", "text/csv")
        st.stop()
    
    # Load and process data (using your existing functions)
    try:
        if uploaded_file.name.endswith('.csv'):
            raw_df = pd.read_csv(uploaded_file)
        else:
            raw_df = pd.read_excel(uploaded_file)
        
        raw_df.columns = [c.strip() for c in raw_df.columns]
        raw_df = parse_dates(raw_df, ['planned_start','planned_finish','actual_start','actual_finish'])
        
        st.success(f"Loaded {len(raw_df)} completed projects")
        
        # Compute KPIs
        kpi_df = compute_project_kpis(raw_df)
        
        # Dashboard metrics
        col1, col2, col3, col4 = st.columns(4)
        
        avg_schedule_var = kpi_df['schedule_variance_pct'].mean()
        avg_cost_var = kpi_df['cost_variance_pct'].mean()
        total_projects = len(kpi_df)
        avg_duration = kpi_df['actual_duration_days'].mean()
        
        col1.metric("Total Projects", total_projects)
        col2.metric("Avg Duration (days)", f"{avg_duration:.0f}" if pd.notna(avg_duration) else "N/A")
        col3.metric("Avg Schedule Variance", f"{avg_schedule_var:.1f}%" if pd.notna(avg_schedule_var) else "N/A")
        col4.metric("Avg Cost Variance", f"{avg_cost_var:.1f}%" if pd.notna(avg_cost_var) else "N/A")
        
        # Charts
        st.subheader("Project Performance Overview")
        
        # Schedule performance
        schedule_chart_df = kpi_df[['project_name', 'planned_duration_days', 'actual_duration_days']].dropna()
        if not schedule_chart_df.empty:
            fig = go.Figure()
            fig.add_trace(go.Bar(name='Planned', x=schedule_chart_df['project_name'], y=schedule_chart_df['planned_duration_days']))
            fig.add_trace(go.Bar(name='Actual', x=schedule_chart_df['project_name'], y=schedule_chart_df['actual_duration_days']))
            fig.update_layout(title='Planned vs Actual Duration', barmode='group')
            st.plotly_chart(fig, use_container_width=True)
        
        # Cost performance
        cost_chart_df = kpi_df[['project_name', 'cost_variance_pct']].dropna()
        if not cost_chart_df.empty:
            fig = px.bar(cost_chart_df, x='project_name', y='cost_variance_pct', 
                        title='Cost Variance by Project (%)')
            fig.add_hline(y=0, line_dash="dash", line_color="red")
            st.plotly_chart(fig, use_container_width=True)
        
        # Project details table
        st.subheader("Project Details")
        st.dataframe(kpi_df[['project_name', 'planned_duration_days', 'actual_duration_days', 
                            'schedule_variance_pct', 'cost_variance_pct', 'contractor']].fillna("N/A"), 
                    use_container_width=True)
        
        # Export functionality
        if st.button("📊 Generate Executive Summary", use_container_width=True):
            st.info("Executive summary generation available - see your existing code!")
    
    except Exception as e:
        st.error(f"Error processing data: {e}")

# ================== SIDEBAR INFORMATION ==================
with st.sidebar:
    st.header("ℹ️ Dashboard Info")
    st.write("**Version:** 1.0 (Lean MVP)")
    st.write("**Stage:** Pre-Launch Testing")
    
    st.markdown("### 🎯 Current Features")
    st.markdown("""
    **Pre-Development:**
    - Deal calculator (ROI/IRR)
    - Risk flagging
    - Cost breakdown
    
    **Development:**
    - Schedule upload & analysis
    - Risk detection
    - Weather risk assessment
    - Basic Gantt charts
    
    **Post-Development:**
    - Performance KPIs
    - Variance analysis
    - Contractor scorecards
    """)
    
    st.markdown("### 🚀 Coming in V1.1")
    st.markdown("""
    - Advanced weather API integration
    - Enhanced ML delay prediction
    - Multi-project portfolio view
    - Automated report generation
    """)
    
    if st.button("💬 Feedback", use_container_width=True):
        st.info("Send feedback to: feedback@yourconstructionapp.com")

# Footer
st.markdown("---")
st.caption("🏗️ Construction Management Dashboard V1 | Built with Streamlit | Ready for pilot testing")
