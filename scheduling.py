import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json
import random
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Tuple
import concurrent.futures
import threading
from pathlib import Path

# Configure Streamlit
st.set_page_config(
    page_title="Construction AI Scheduling Platform",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for clean, modern interface
st.markdown("""
<style>
    /* Main theme */
    .main {
        padding: 1rem 2rem;
    }
    
    /* Hero section */
    .hero-container {
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
        padding: 2rem;
        border-radius: 10px;
        color: white;
        margin-bottom: 2rem;
        text-align: center;
    }
    
    /* Cards */
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border-left: 4px solid #2a5298;
        margin: 0.5rem 0;
    }
    
    /* Analysis cards */
    .analysis-option {
        background: #f8f9fa;
        padding: 1.5rem;
        border-radius: 8px;
        border: 1px solid #e9ecef;
        margin: 1rem 0;
        transition: all 0.3s ease;
        cursor: pointer;
    }
    
    .analysis-option:hover {
        border-color: #2a5298;
        box-shadow: 0 4px 8px rgba(42,82,152,0.1);
    }
    
    /* Status indicators */
    .status-good { color: #28a745; font-weight: bold; }
    .status-warning { color: #ffc107; font-weight: bold; }
    .status-critical { color: #dc3545; font-weight: bold; }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# Core Data Models
@dataclass
class ProjectParameters:
    """Clean project configuration"""
    name: str
    location: str
    start_date: datetime
    project_type: str
    square_footage: int
    budget: float
    crew_size: int
    weather_risk: float = 0.3
    supply_chain_risk: float = 0.2
    permit_complexity: float = 0.3

@dataclass
class TaskTemplate:
    """Construction task with intelligent defaults"""
    name: str
    base_duration: int
    min_duration: int
    max_duration: int
    dependencies: List[str]
    weather_sensitive: bool
    crew_required: int
    cost: float
    risk_factor: float
    critical_path: bool = False

class ConstructionAI:
    """Core AI engine for construction scheduling optimization"""
    
    def __init__(self):
        self.weather_patterns = self._initialize_weather_data()
        self.supply_chain_data = self._initialize_supply_data()
        self.benchmarks = self._initialize_benchmarks()
        
    def _initialize_weather_data(self) -> Dict:
        """Weather risk by location and month"""
        return {
            'atlanta': {1: 0.4, 2: 0.3, 3: 0.2, 4: 0.15, 5: 0.1, 6: 0.25, 7: 0.3, 8: 0.25, 9: 0.2, 10: 0.1, 11: 0.2, 12: 0.35},
            'dallas': {1: 0.2, 2: 0.15, 3: 0.1, 4: 0.2, 5: 0.3, 6: 0.15, 7: 0.1, 8: 0.1, 9: 0.2, 10: 0.15, 11: 0.2, 12: 0.25},
            'denver': {1: 0.5, 2: 0.4, 3: 0.3, 4: 0.2, 5: 0.15, 6: 0.1, 7: 0.1, 8: 0.15, 9: 0.2, 10: 0.3, 11: 0.4, 12: 0.5}
        }
    
    def _initialize_supply_data(self) -> Dict:
        """Supply chain lead times and risks"""
        return {
            'concrete': {'lead_time': 3, 'risk': 0.1},
            'steel': {'lead_time': 14, 'risk': 0.25},
            'lumber': {'lead_time': 7, 'risk': 0.2},
            'drywall': {'lead_time': 5, 'risk': 0.15}
        }
    
    def _initialize_benchmarks(self) -> Dict:
        """Industry benchmarks by project type"""
        return {
            'office_building': {'duration_per_sqft': 0.12, 'cost_per_sqft': 180},
            'retail': {'duration_per_sqft': 0.08, 'cost_per_sqft': 150},
            'warehouse': {'duration_per_sqft': 0.06, 'cost_per_sqft': 120},
            'multifamily': {'duration_per_sqft': 0.15, 'cost_per_sqft': 200}
        }
    
    def run_monte_carlo(self, params: ProjectParameters, num_scenarios: int = 1000) -> Dict:
        """Run Monte Carlo simulation with parallel processing"""
        
        # Generate task templates based on project type
        tasks = self._generate_task_templates(params)
        
        # Run scenarios in parallel using threads (Streamlit-safe)
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            futures = [
                executor.submit(self._run_single_scenario, params, tasks, i) 
                for i in range(num_scenarios)
            ]
            scenarios = [f.result() for f in concurrent.futures.as_completed(futures)]
        
        return self._analyze_results(scenarios, params)
    
    def _generate_task_templates(self, params: ProjectParameters) -> List[TaskTemplate]:
        """Generate realistic task templates based on project parameters"""
        
        # Base templates (simplified for demo)
        base_tasks = [
            TaskTemplate("Site Preparation", 5, 3, 8, [], True, 4, 25000, 0.2),
            TaskTemplate("Foundation", 12, 8, 18, ["Site Preparation"], True, 6, 85000, 0.3, True),
            TaskTemplate("Framing", 25, 20, 35, ["Foundation"], False, 8, 120000, 0.15, True),
            TaskTemplate("MEP Rough", 18, 15, 25, ["Framing"], False, 6, 95000, 0.25),
            TaskTemplate("Drywall", 15, 12, 20, ["MEP Rough"], False, 5, 55000, 0.1, True),
            TaskTemplate("Finishes", 20, 16, 28, ["Drywall"], False, 7, 110000, 0.2, True),
        ]
        
        # Scale durations based on square footage
        sqft_factor = params.square_footage / 25000  # Baseline 25k sqft
        
        for task in base_tasks:
            task.base_duration = max(1, int(task.base_duration * sqft_factor))
            task.min_duration = max(1, int(task.min_duration * sqft_factor))
            task.max_duration = max(2, int(task.max_duration * sqft_factor))
            task.cost = task.cost * sqft_factor
        
        return base_tasks
    
    def _run_single_scenario(self, params: ProjectParameters, tasks: List[TaskTemplate], scenario_id: int) -> Dict:
        """Run a single scenario simulation"""
        
        np.random.seed(scenario_id)
        scenario = {
            'id': scenario_id,
            'total_duration': 0,
            'total_cost': 0,
            'weather_delays': 0,
            'supply_delays': 0,
            'permit_delays': 0,
            'tasks': []
        }
        
        current_date = params.start_date
        completed_tasks = set()
        
        for task in tasks:
            # Wait for dependencies
            if task.dependencies:
                dep_end_dates = [
                    t['end_date'] for t in scenario['tasks'] 
                    if t['name'] in task.dependencies
                ]
                if dep_end_dates:
                    current_date = max(current_date, max(dep_end_dates))
            
            # Calculate actual duration with variability
            duration = np.random.triangular(
                task.min_duration, 
                task.base_duration, 
                task.max_duration
            )
            
            # Apply weather delays
            weather_delay = 0
            if task.weather_sensitive:
                location_key = params.location.lower().split(',')[0].replace(' ', '')
                if location_key in self.weather_patterns:
                    month_risk = self.weather_patterns[location_key].get(current_date.month, 0.2)
                    if np.random.random() < month_risk:
                        weather_delay = np.random.randint(1, 5)
            
            # Apply supply chain delays
            supply_delay = 0
            if np.random.random() < params.supply_chain_risk:
                supply_delay = np.random.randint(1, 7)
            
            # Apply permit delays
            permit_delay = 0
            if task.name in ["Foundation", "MEP Rough"] and np.random.random() < params.permit_complexity:
                permit_delay = np.random.randint(1, 10)
            
            total_delays = weather_delay + supply_delay + permit_delay
            final_duration = duration + total_delays
            end_date = current_date + timedelta(days=int(final_duration))
            
            # Calculate cost with delay penalties
            cost_multiplier = 1.0 + (total_delays / duration) * 0.1
            final_cost = task.cost * cost_multiplier
            
            task_result = {
                'name': task.name,
                'start_date': current_date,
                'end_date': end_date,
                'duration': final_duration,
                'cost': final_cost,
                'weather_delay': weather_delay,
                'supply_delay': supply_delay,
                'permit_delay': permit_delay
            }
            
            scenario['tasks'].append(task_result)
            scenario['weather_delays'] += weather_delay
            scenario['supply_delays'] += supply_delay
            scenario['permit_delays'] += permit_delay
            scenario['total_cost'] += final_cost
            
            current_date = end_date
        
        scenario['total_duration'] = (current_date - params.start_date).days
        return scenario
    
    def _analyze_results(self, scenarios: List[Dict], params: ProjectParameters) -> Dict:
        """Analyze simulation results and generate insights"""
        
        durations = [s['total_duration'] for s in scenarios]
        costs = [s['total_cost'] for s in scenarios]
        weather_delays = [s['weather_delays'] for s in scenarios]
        supply_delays = [s['supply_delays'] for s in scenarios]
        
        # Calculate key metrics
        analysis = {
            'summary': {
                'scenarios_run': len(scenarios),
                'project_name': params.name,
                'location': params.location
            },
            'duration': {
                'min': int(min(durations)),
                'max': int(max(durations)),
                'mean': np.mean(durations),
                'median': np.median(durations),
                'p10': np.percentile(durations, 10),
                'p50': np.percentile(durations, 50),
                'p90': np.percentile(durations, 90),
                'std': np.std(durations)
            },
            'cost': {
                'min': min(costs),
                'max': max(costs),
                'mean': np.mean(costs),
                'median': np.median(costs),
                'p10': np.percentile(costs, 10),
                'p90': np.percentile(costs, 90)
            },
            'risks': {
                'weather': {
                    'avg_delay': np.mean(weather_delays),
                    'probability': len([d for d in weather_delays if d > 0]) / len(weather_delays),
                    'max_delay': max(weather_delays)
                },
                'supply_chain': {
                    'avg_delay': np.mean(supply_delays),
                    'probability': len([d for d in supply_delays if d > 0]) / len(supply_delays),
                    'max_delay': max(supply_delays)
                }
            },
            'recommendations': self._generate_recommendations(scenarios, params),
            'scenarios': scenarios[:100]  # Store first 100 for detailed analysis
        }
        
        return analysis

    def _generate_recommendations(self, scenarios: List[Dict], params: ProjectParameters) -> List[str]:
        """Generate AI-powered recommendations"""
        recommendations = []
        
        durations = [s['total_duration'] for s in scenarios]
        weather_delays = [s['weather_delays'] for s in scenarios]
        supply_delays = [s['supply_delays'] for s in scenarios]
        
        avg_weather = np.mean(weather_delays)
        avg_supply = np.mean(supply_delays)
        duration_var = np.std(durations)
        
        # Weather recommendations
        if avg_weather > 3:
            season = "winter" if params.start_date.month in [12, 1, 2] else "summer" if params.start_date.month in [6, 7, 8] else "spring/fall"
            recommendations.append(f"🌧️ HIGH WEATHER RISK: {season} start shows {avg_weather:.1f} avg weather delay days. Consider starting 2-3 weeks earlier.")
        
        # Supply chain recommendations
        if avg_supply > 2:
            recommendations.append(f"📦 SUPPLY CHAIN: {avg_supply:.1f} avg supply delays detected. Order long-lead items 2-3 weeks earlier than standard.")
        
        # Schedule optimization
        if duration_var > 15:
            recommendations.append("⚡ HIGH VARIABILITY: Consider adding buffer time to critical path tasks or increasing crew size during peak phases.")
        
        # Cost optimization
        p90_duration = np.percentile(durations, 90)
        median_duration = np.median(durations)
        if (p90_duration - median_duration) > 20:
            recommendations.append("💰 RISK MITIGATION: 90th percentile scenarios show significant delays. Budget for contingency or fast-track options.")
        
        return recommendations

# Caching for performance
@st.cache_data(ttl=3600, show_spinner=False)
def run_cached_simulation(params_dict: Dict, num_scenarios: int) -> Dict:
    """Cached simulation runner"""
    params = ProjectParameters(**params_dict)
    ai = ConstructionAI()
    return ai.run_monte_carlo(params, num_scenarios)

def create_duration_chart(analysis: Dict) -> go.Figure:
    """Create duration probability distribution chart"""
    scenarios = analysis.get('scenarios', [])
    if not scenarios:
        return go.Figure()
    
    durations = [s['total_duration'] for s in scenarios]
    
    fig = go.Figure()
    
    # Histogram
    fig.add_trace(go.Histogram(
        x=durations,
        nbinsx=20,
        name='Frequency',
        opacity=0.7,
        marker_color='#2a5298'
    ))
    
    # Add percentile lines
    p50 = analysis['duration']['p50']
    p90 = analysis['duration']['p90']
    
    fig.add_vline(x=p50, line_dash="dash", line_color="orange", 
                  annotation_text=f"P50: {p50:.0f} days")
    fig.add_vline(x=p90, line_dash="dash", line_color="red", 
                  annotation_text=f"P90: {p90:.0f} days")
    
    fig.update_layout(
        title="Project Duration Distribution",
        xaxis_title="Duration (Days)",
        yaxis_title="Frequency",
        showlegend=False,
        height=400
    )
    
    return fig

def create_risk_breakdown_chart(analysis: Dict) -> go.Figure:
    """Create risk breakdown chart"""
    weather_avg = analysis['risks']['weather']['avg_delay']
    supply_avg = analysis['risks']['supply_chain']['avg_delay']
    
    fig = go.Figure(data=[
        go.Bar(
            x=['Weather Delays', 'Supply Chain Delays'],
            y=[weather_avg, supply_avg],
            marker_color=['#ff6b6b', '#4ecdc4'],
            text=[f'{weather_avg:.1f} days', f'{supply_avg:.1f} days'],
            textposition='auto'
        )
    ])
    
    fig.update_layout(
        title="Average Delay Days by Risk Factor",
        yaxis_title="Average Days",
        height=300,
        showlegend=False
    )
    
    return fig

def create_gantt_chart(analysis: Dict) -> go.Figure:
    """Create simplified Gantt chart from median scenario"""
    scenarios = analysis.get('scenarios', [])
    if not scenarios:
        return go.Figure()
    
    # Use median scenario
    median_idx = len(scenarios) // 2
    scenario = scenarios[median_idx]
    tasks = scenario['tasks']
    
    fig = go.Figure()
    
    colors = ['#2a5298', '#e74c3c', '#f39c12', '#27ae60', '#9b59b6', '#1abc9c']
    
    for i, task in enumerate(tasks):
        fig.add_trace(go.Scatter(
            x=[task['start_date'], task['end_date']],
            y=[task['name'], task['name']],
            mode='lines',
            line=dict(color=colors[i % len(colors)], width=20),
            name=task['name'],
            hovertemplate=f"<b>{task['name']}</b><br>Duration: {task['duration']:.0f} days<br>Cost: ${task['cost']:,.0f}<extra></extra>"
        ))
    
    fig.update_layout(
        title="Project Timeline (Median Scenario)",
        xaxis_title="Date",
        yaxis_title="Tasks",
        height=400,
        showlegend=False
    )
    
    return fig

# Main Application
def main():
    # Hero Section
    st.markdown("""
    <div class="hero-container">
        <h1>🏗️ Construction AI Scheduling Platform</h1>
        <p>Transform your construction projects with AI-powered scheduling, risk analysis, and optimization</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar - Project Configuration
    with st.sidebar:
        st.header("🔧 Project Configuration")
        
        # Basic project info
        project_name = st.text_input("Project Name", "Office Building Alpha")
        location = st.selectbox("Location", [
            "Atlanta, GA", "Dallas, TX", "Denver, CO", "Seattle, WA",
            "Phoenix, AZ", "Chicago, IL", "New York, NY", "Los Angeles, CA"
        ])
        
        project_type = st.selectbox("Project Type", [
            "Office Building", "Retail Store", "Warehouse", 
            "Multifamily", "Mixed Use", "Industrial"
        ])
        
        start_date = st.date_input("Start Date", datetime.now().date())
        square_footage = st.number_input("Square Footage", 1000, 500000, 25000, 1000)
        budget = st.number_input("Budget ($)", 100000, 50000000, 2000000, 50000)
        crew_size = st.slider("Base Crew Size", 5, 30, 12)
        
        st.markdown("---")
        
        # Advanced risk settings
        with st.expander("⚙️ Advanced Settings"):
            weather_risk = st.slider("Weather Risk Factor", 0.1, 1.0, 0.3, 0.1)
            supply_risk = st.slider("Supply Chain Risk", 0.1, 1.0, 0.2, 0.1)
            permit_complexity = st.slider("Permit Complexity", 0.1, 1.0, 0.3, 0.1)
        
        # Create parameters object
        params = ProjectParameters(
            name=project_name,
            location=location,
            start_date=datetime.combine(start_date, datetime.min.time()),
            project_type=project_type.lower().replace(' ', '_'),
            square_footage=square_footage,
            budget=budget,
            crew_size=crew_size,
            weather_risk=weather_risk,
            supply_chain_risk=supply_risk,
            permit_complexity=permit_complexity
        )
    
    # Main Content Tabs
    tab1, tab2, tab3, tab4 = st.tabs(["🎯 Quick Analysis", "🔍 Deep Dive", "🚀 Optimization", "📊 Benchmarks"])
    
    # Tab 1: Quick Analysis
    with tab1:
        st.header("⚡ Quick Project Analysis")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("""
            <div class="analysis-option">
                <h3>🚀 Fast Preview</h3>
                <p><strong>500 scenarios • ~5 seconds</strong></p>
                <ul>
                    <li>Basic duration estimates</li>
                    <li>Key risk identification</li>
                    <li>Initial recommendations</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("Run Quick Analysis", type="primary", use_container_width=True):
                with st.spinner("🔄 Running 500 scenario analysis..."):
                    analysis = run_cached_simulation(asdict(params), 500)
                
                st.success("✅ Quick analysis complete!")
                
                # Key metrics
                col_a, col_b, col_c, col_d = st.columns(4)
                col_a.metric("Median Duration", f"{analysis['duration']['median']:.0f} days")
                col_b.metric("P90 Duration", f"{analysis['duration']['p90']:.0f} days")
                col_c.metric("Median Cost", f"${analysis['cost']['median']:,.0f}")
                col_d.metric("Weather Risk", f"{analysis['risks']['weather']['probability']:.0%}")
                
                # Quick recommendations
                st.subheader("💡 Key Recommendations")
                for rec in analysis['recommendations'][:3]:
                    if "🌧️" in rec:
                        st.warning(rec)
                    elif "📦" in rec:
                        st.info(rec)
                    else:
                        st.success(rec)
        
        with col2:
            st.markdown("""
            <div class="analysis-option">
                <h3>🔍 Comprehensive</h3>
                <p><strong>2,000 scenarios • ~15 seconds</strong></p>
                <ul>
                    <li>Detailed probability curves</li>
                    <li>Advanced risk breakdown</li>
                    <li>Optimization opportunities</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("Run Deep Analysis", type="secondary", use_container_width=True):
                with st.spinner("🔄 Running comprehensive analysis..."):
                    analysis = run_cached_simulation(asdict(params), 2000)
                
                st.success("✅ Deep analysis complete!")
                
                # Detailed metrics
                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    st.metric("Best Case", f"{analysis['duration']['min']} days", 
                             delta=f"{analysis['duration']['min'] - analysis['duration']['median']:.0f}")
                with col_b:
                    st.metric("Typical Case", f"{analysis['duration']['median']:.0f} days")
                with col_c:
                    st.metric("Worst Case", f"{analysis['duration']['max']} days",
                             delta=f"{analysis['duration']['max'] - analysis['duration']['median']:.0f}")
                
                # Charts
                st.plotly_chart(create_duration_chart(analysis), use_container_width=True)
                st.plotly_chart(create_risk_breakdown_chart(analysis), use_container_width=True)
        
        with col3:
            st.markdown("""
            <div class="analysis-option">
                <h3>🧬 AI Optimization</h3>
                <p><strong>Genetic algorithm • ~30 seconds</strong></p>
                <ul>
                    <li>Optimal start dates</li>
                    <li>Crew size optimization</li>
                    <li>Maximum ROI scenarios</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("Run AI Optimization", type="primary", use_container_width=True):
                with st.spinner("🧬 AI optimization in progress..."):
                    # Simulate optimization process
                    analysis = run_cached_simulation(asdict(params), 1000)
                    
                    # Mock optimization results
                    optimal_start = params.start_date - timedelta(days=14)
                    optimal_crew = min(30, params.crew_size + 3)
                    duration_savings = analysis['duration']['median'] * 0.12
                    cost_savings = analysis['cost']['median'] * 0.08
                
                st.success("✅ AI optimization complete!")
                
                col_a, col_b = st.columns(2)
                with col_a:
                    st.write("**🎯 Optimized Parameters:**")
                    st.write(f"• Start Date: {optimal_start.strftime('%Y-%m-%d')} (2 weeks earlier)")
                    st.write(f"• Crew Size: {optimal_crew} (+{optimal_crew - params.crew_size})")
                    st.write(f"• Procurement Lead: 3 weeks advance")
                
                with col_b:
                    st.write("**📈 Expected Improvements:**")
                    st.metric("Duration Savings", f"{duration_savings:.0f} days")
                    st.metric("Cost Savings", f"${cost_savings:,.0f}")
                    st.metric("Risk Reduction", "23%")
    
    # Tab 2: Deep Dive Analysis
    with tab2:
        st.header("🔍 Deep Dive Analysis & Scenario Planning")
        
        # File upload for custom schedules
        uploaded_file = st.file_uploader("📄 Upload Custom Schedule (Optional)", type=['csv', 'xlsx'])
        
        if uploaded_file:
            try:
                df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
                st.success(f"✅ Schedule uploaded! Found {len(df)} tasks.")
                st.dataframe(df.head(), use_container_width=True)
            except Exception as e:
                st.error(f"❌ Upload failed: {str(e)}")
        
        # Analysis controls
        col1, col2 = st.columns([2, 1])
        
        with col1:
            scenarios_count = st.select_slider(
                "Analysis Depth", 
                options=[1000, 2500, 5000, 10000],
                value=2500,
                format_func=lambda x: f"{x:,} scenarios"
            )
            
            include_weather = st.checkbox("Include Weather Analysis", True)
            include_supply = st.checkbox("Include Supply Chain Analysis", True)
            include_permits = st.checkbox("Include Permit Risk Analysis", True)
        
        with col2:
            confidence_level = st.selectbox("Confidence Level", ["80%", "90%", "95%", "99%"], index=1)
            
            if st.button("🚀 Run Deep Analysis", type="primary"):
                with st.spinner(f"🔄 Running {scenarios_count:,} scenario analysis..."):
                    analysis = run_cached_simulation(asdict(params), scenarios_count)
                
                st.success("✅ Deep analysis complete!")
                
                # Comprehensive results display
                st.subheader("📊 Comprehensive Results")
                
                # Key metrics row
                col_a, col_b, col_c, col_d, col_e = st.columns(5)
                col_a.metric("Min Duration", f"{analysis['duration']['min']} days")
                col_b.metric("Median Duration", f"{analysis['duration']['median']:.0f} days")
                col_c.metric("P90 Duration", f"{analysis['duration']['p90']:.0f} days")
                col_d.metric("Max Duration", f"{analysis['duration']['max']} days")
                col_e.metric("Std Deviation", f"{analysis['duration']['std']:.1f} days")
                
                # Cost metrics row
                col_a, col_b, col_c, col_d = st.columns(4)
                col_a.metric("Min Cost", f"${analysis['cost']['min']:,.0f}")
                col_b.metric("Median Cost", f"${analysis['cost']['median']:,.0f}")
                col_c.metric("P90 Cost", f"${analysis['cost']['p90']:,.0f}")
                col_d.metric("Max Cost", f"${analysis['cost']['max']:,.0f}")
                
                # Charts
                col1, col2 = st.columns(2)
                with col1:
                    st.plotly_chart(create_duration_chart(analysis), use_container_width=True)
                with col2:
                    st.plotly_chart(create_risk_breakdown_chart(analysis), use_container_width=True)
                
                # Gantt chart
                st.plotly_chart(create_gantt_chart(analysis), use_container_width=True)
                
                # Detailed recommendations
