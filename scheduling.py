import streamlit as st
import pandas as pd
import math
from datetime import datetime
from collections import Counter
from io import BytesIO
import plotly.express as px

EXPECTED_COLUMNS = [
    'project_id', 'project_name', 'asset_type', 'planned_start', 'planned_finish',
    'actual_start', 'actual_finish', 'planned_cost', 'actual_cost', 'area_sqft',
    'delay_causes', 'safety_incidents', 'contractor', 'weather_delay_days',
    'percent_complete', 'earned_value', 'defects_count', 'warranty_claims',
    'critical_path_changes'
]

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
    for lst in kpi_df['delay_causes_list'].apply(lambda x: x if isinstance(x, list) else []):
        cnt.update(lst)
    items = sorted(cnt.items(), key=lambda x: x[1], reverse=True)
    return pd.DataFrame(items, columns=['cause', 'count'])

def contractor_scorecard(kpi_df):
    rows = []
    for contractor, group in kpi_df.groupby('contractor', dropna=True):
        rows.append({
            "contractor": contractor,
            "projects": len(group),
            "avg_schedule_variance_pct": group['schedule_variance_pct'].dropna().mean() if 'schedule_variance_pct' in group.columns else None,
            "avg_cost_variance_pct": group['cost_variance_pct'].dropna().mean() if 'cost_variance_pct' in group.columns else None,
            "total_safety_incidents": int(group['safety_incidents'].fillna(0).sum()) if 'safety_incidents' in group.columns else 0,
            "avg_CPI": group['CPI'].dropna().mean() if 'CPI' in group.columns else None
        })
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    return df.sort_values('projects', ascending=False)

@st.cache_data
def load_dataframe(uploaded_file):
    ext = uploaded_file.name.split('.')[-1].lower()
    if ext in ('xls', 'xlsx'):
        df = pd.read_excel(uploaded_file)
    else:
        df = pd.read_csv(uploaded_file)
    df.columns = [c.strip() for c in df.columns]
    return df

st.title("🏗️ Post-Construction Performance Dashboard")

uploaded = st.file_uploader("Upload schedule data CSV or Excel", type=['csv','xls','xlsx'])
if not uploaded:
    st.info("Please upload a data file.")
    st.stop()

try:
    raw_df = load_dataframe(uploaded)
except Exception as e:
    st.error(f"Error loading file: {e}")
    st.stop()

st.write("Preview of uploaded data:")
st.dataframe(raw_df.head())

uploaded_cols = raw_df.columns.tolist()
missing_cols = [c for c in EXPECTED_COLUMNS if c not in uploaded_cols]

if not missing_cols:
    st.success("All expected columns detected.")
    df_for_kpis = raw_df.copy()
    df_for_kpis = parse_dates(df_for_kpis, ['planned_start','planned_finish','actual_start','actual_finish'])
else:
    st.warning(f"Missing expected columns: {missing_cols}")
    st.markdown("Map your file's columns to expected KPI fields:")

    mapping = {}
    for col in EXPECTED_COLUMNS:
        options = ["(none)"] + uploaded_cols
        default_index = options.index(col) if col in options else 0
        mapping[col] = st.selectbox(f"Map '{col}' to:", options, index=default_index, key=col)

    if st.button("Process Mapped Data"):
        mapped_data = {}
        for col, mapped_col in mapping.items():
            if mapped_col != "(none)":
                mapped_data[col] = raw_df[mapped_col]
            else:
                # Provide default values if sensible
                if col in ['safety_incidents', 'weather_delay_days', 'defects_count', 'warranty_claims', 'critical_path_changes']:
                    mapped_data[col] = 0
                else:
                    mapped_data[col] = pd.NA
        df_for_kpis = pd.DataFrame(mapped_data)
        df_for_kpis = parse_dates(df_for_kpis, ['planned_start','planned_finish','actual_start','actual_finish'])
        st.success("Data mapped and ready.")
        st.dataframe(df_for_kpis.head())
    else:
        st.stop()

if 'df_for_kpis' in locals():
    kpi_df = compute_project_kpis(df_for_kpis)
    portfolio_kpis = aggregate_portfolio_kpis(kpi_df)
    delay_df = compute_delay_cause_breakdown(kpi_df)
    contractor_df = contractor_scorecard(kpi_df)

    tabs = st.tabs(["Executive Summary","Per-Project KPIs","Delay Causes","Contractor Scorecard"])

    with tabs[0]:
        st.header("Executive Summary")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Projects", portfolio_kpis.get('project_count', 0))
        c2.metric("Avg Planned Duration (days)", f"{portfolio_kpis.get('avg_planned_duration'):.1f}" if portfolio_kpis.get('avg_planned_duration') else "n/a")
        c3.metric("Avg Actual Duration (days)", f"{portfolio_kpis.get('avg_actual_duration'):.1f}" if portfolio_kpis.get('avg_actual_duration') else "n/a")
        c4.metric("Avg Cost Variance (%)", f"{portfolio_kpis.get('avg_cost_variance_pct'):.1f}%" if portfolio_kpis.get('avg_cost_variance_pct') else "n/a")

        st.markdown("### Duration: Planned vs Actual")
        dur_chart_df = kpi_df[['project_name','planned_duration_days','actual_duration_days']].dropna(subset=['project_name'])
        if not dur_chart_df.empty:
            dur_chart_df = dur_chart_df.sort_values('planned_duration_days', ascending=False).head(50)
            dur_melt = dur_chart_df.melt(id_vars='project_name', value_vars=['planned_duration_days','actual_duration_days'],
                                        var_name='type', value_name='days')
            fig = px.bar(dur_melt, x='days', y='project_name', color='type', orientation='h',
                         barmode='group', height=600)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Not enough data to plot durations.")

    with tabs[1]:
        st.header("Per-Project KPIs")
        st.dataframe(kpi_df.fillna(""), use_container_width=True)

    with tabs[2]:
        st.header("Delay Causes Breakdown")
        if not delay_df.empty:
            fig = px.bar(delay_df.sort_values('count', ascending=False), x='count', y='cause', orientation='h')
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(delay_df)
        else:
            st.info("No delay cause data found.")

    with tabs[3]:
        st.header("Contractor Scorecard")
        if not contractor_df.empty:
            fig = px.bar(contractor_df.head(30), x='projects', y='contractor', orientation='h')
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(contractor_df.fillna(""))
        else:
            st.info("No contractor data found.")
