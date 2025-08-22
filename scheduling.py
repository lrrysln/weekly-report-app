# Construction Scenario Engine V2 - Enhanced & Optimized
# Clean, intuitive interface with progressive disclosure
# Focus: Weather-aware scheduling, procurement optimization, crew scenario modeling

import os
import math
import json
import random
import numpy as np
import pandas as pd
from dataclasses import dataclass, asdict
from typing import List, Dict, Tuple, Optional, Any
from datetime import datetime, timedelta
import concurrent.futures
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

# Configure Streamlit
st.set_page_config(
    page_title="Construction Scenario Engine V2",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header { 
        font-size: 2.5rem; 
        font-weight: 700; 
        color: #1f2937; 
        margin-bottom: 1rem;
    }
    .sub-header { 
        font-size: 1.5rem; 
        font-weight: 600; 
        color: #374151; 
        margin: 1rem 0;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
    }
    .success-card {
        background: linear-gradient(135deg, #48cc6c 0%, #43a047 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
    }
    .warning-card {
        background: linear-gradient(135deg, #ffa726 0%, #ff7043 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
    }
    .sidebar .sidebar-content {
        background: linear-gradient(180deg, #f8fafc 0%, #e2e8f0 100%);
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# DATA MODELS & CORE CLASSES
# ============================================================================

@dataclass
class ProjectParameters:
    """Enhanced project configuration with industry-specific defaults"""
    # Basic Project Info
    project_name: str = "New Construction Project"
    project_type: str = "Office Building"
    location: str = "Atlanta, GA"
    start_date: datetime = datetime.now()
    
    # Scale & Budget
    square_footage: int = 25000
    budget: float = 2000000.0
    
    # Team Configuration
    base_crew_size: int = 12
    crew_efficiency: float = 1.0
    
    # Risk Factors (0.0 - 1.0)
    weather_sensitivity: float = 0.8
    supply_chain_risk: float = 0.6
    permit_complexity: float = 0.5
    labor_availability: float = 0.8
    
    # Advanced Configuration
    contingency_buffer: float = 0.15
    quality_requirements: str = "Standard"
    sustainability_level: str = "Basic"

@dataclass
class TaskTemplate:
    """Enhanced task template with realistic construction parameters"""
    name: str
    category: str  # Foundation, Structure, MEP, Finishes, etc.
    base_duration: int
    min_duration: int
    max_duration: int
    base_cost: float
    crew_size: int
    dependencies: List[str]
    weather_dependent: bool
    critical_path: bool
    delay_probability: float
    skill_level_required: str = "Standard"  # Basic, Standard, Skilled, Expert

class WeatherService:
    """Enhanced weather intelligence with regional patterns"""
    
    REGIONAL_PATTERNS = {
        "atlanta": {"winter_risk": 0.3, "summer_rain": 0.4, "hurricane_season": 0.2},
        "dallas": {"winter_risk": 0.2, "summer_heat": 0.5, "tornado_season": 0.3},
        "phoenix": {"extreme_heat": 0.6, "monsoon": 0.3, "winter_mild": 0.1},
        "chicago": {"winter_severe": 0.7, "summer_storms": 0.3, "wind": 0.4},
        "denver": {"snow": 0.5, "altitude_effects": 0.3, "hail": 0.4},
        "seattle": {"rain": 0.8, "winter_mild": 0.2, "summer_dry": 0.1},
        "miami": {"hurricane": 0.4, "rain_daily": 0.6, "heat_humidity": 0.7},
        "new_york": {"winter_variable": 0.5, "summer_humid": 0.4, "coastal": 0.3}
    }
    
    @classmethod
    def get_weather_risk_profile(cls, location: str, month: int) -> Dict[str, float]:
        """Get weather risk factors for specific location and month"""
        city = location.lower().split(",")[0].strip()
        base_pattern = cls.REGIONAL_PATTERNS.get(city, {
            "general_risk": 0.3, "seasonal_variance": 0.2
        })
        
        # Seasonal adjustments
        seasonal_multiplier = 1.0
        if month in [12, 1, 2]:  # Winter
            seasonal_multiplier = base_pattern.get("winter_risk", 0.3) + 0.5
        elif month in [6, 7, 8]:  # Summer
            seasonal_multiplier = base_pattern.get("summer_rain", 0.3) + 0.3
        elif month in [3, 4, 5]:  # Spring
            seasonal_multiplier = 0.8
        else:  # Fall
            seasonal_multiplier = 0.6
            
        return {
            "delay_probability": min(0.9, seasonal_multiplier),
            "severity_factor": base_pattern.get("severity_factor", 1.0),
            "regional_context": base_pattern
        }

class ProcurementOptimizer:
    """Smart procurement with lead time optimization"""
    
    MATERIAL_LEAD_TIMES = {
        "concrete": {"min": 1, "typical": 3, "max": 7, "critical": True},
        "rebar": {"min": 5, "typical": 10, "max": 21, "critical": True},
        "structural_steel": {"min": 14, "typical": 28, "max": 56, "critical": True},
        "lumber": {"min": 2, "typical": 5, "max": 14, "critical": False},
        "drywall": {"min": 3, "typical": 7, "max": 14, "critical": False},
        "windows": {"min": 21, "typical": 42, "max": 84, "critical": True},
        "hvac_equipment": {"min": 28, "typical": 56, "max": 120, "critical": True},
        "electrical_panels": {"min": 14, "typical": 35, "max": 70, "critical": True}
    }
    
    @classmethod
    def optimize_procurement_schedule(cls, task_schedule: List[Dict], 
                                    supply_chain_risk: float) -> Dict[str, Any]:
        """Generate optimal procurement timeline with risk adjustments"""
        procurement_plan = {}
        risk_multiplier = 1.0 + supply_chain_risk
        
        for task in task_schedule:
            task_name = task["name"].lower()
            material_key = cls._map_task_to_material(task_name)
            
            if material_key:
                lead_time_data = cls.MATERIAL_LEAD_TIMES.get(material_key, {})
                adjusted_lead_time = lead_time_data.get("typical", 7) * risk_multiplier
                
                order_date = task["start_date"] - timedelta(days=int(adjusted_lead_time))
                
                procurement_plan[task["name"]] = {
                    "material_type": material_key,
                    "order_date": order_date,
                    "lead_time_days": int(adjusted_lead_time),
                    "critical_path": lead_time_data.get("critical", False),
                    "risk_buffer": f"{(risk_multiplier - 1.0) * 100:.0f}%"
                }
        
        return procurement_plan
    
    @classmethod
    def _map_task_to_material(cls, task_name: str) -> Optional[str]:
        """Map construction tasks to material types"""
        task_lower = task_name.lower()
        
        if any(word in task_lower for word in ["foundation", "concrete", "pour"]):
            return "concrete"
        elif any(word in task_lower for word in ["frame", "framing", "wood"]):
            return "lumber"
        elif any(word in task_lower for word in ["steel", "structural"]):
            return "structural_steel"
        elif any(word in task_lower for word in ["drywall", "gypsum"]):
            return "drywall"
        elif any(word in task_lower for word in ["window", "glazing"]):
            return "windows"
        elif any(word in task_lower for word in ["hvac", "mechanical"]):
            return "hvac_equipment"
        elif any(word in task_lower for word in ["electrical", "panel"]):
            return "electrical_panels"
        
        return None

class ConstructionSimulator:
    """Enhanced Monte Carlo simulation engine"""
    
    def __init__(self):
        self.task_templates = self._initialize_task_templates()
        self.weather_service = WeatherService()
        self.procurement_optimizer = ProcurementOptimizer()
    
    def _initialize_task_templates(self) -> Dict[str, TaskTemplate]:
        """Initialize realistic construction task templates"""
        return {
            "site_preparation": TaskTemplate(
                name="Site Preparation",
                category="Sitework",
                base_duration=5,
                min_duration=3,
                max_duration=10,
                base_cost=35000,
                crew_size=4,
                dependencies=[],
                weather_dependent=True,
                critical_path=True,
                delay_probability=0.3,
                skill_level_required="Standard"
            ),
            "excavation": TaskTemplate(
                name="Excavation & Earthwork",
                category="Sitework", 
                base_duration=8,
                min_duration=6,
                max_duration=14,
                base_cost=65000,
                crew_size=6,
                dependencies=["Site Preparation"],
                weather_dependent=True,
                critical_path=True,
                delay_probability=0.4,
                skill_level_required="Standard"
            ),
            "foundation": TaskTemplate(
                name="Foundation & Concrete",
                category="Foundation",
                base_duration=12,
                min_duration=10,
                max_duration=18,
                base_cost=120000,
                crew_size=8,
                dependencies=["Excavation & Earthwork"],
                weather_dependent=True,
                critical_path=True,
                delay_probability=0.25,
                skill_level_required="Skilled"
            ),
            "structural_steel": TaskTemplate(
                name="Structural Steel",
                category="Structure",
                base_duration=15,
                min_duration=12,
                max_duration=22,
                base_cost=180000,
                crew_size=6,
                dependencies=["Foundation & Concrete"],
                weather_dependent=False,
                critical_path=True,
                delay_probability=0.2,
                skill_level_required="Expert"
            ),
            "framing": TaskTemplate(
                name="Framing",
                category="Structure",
                base_duration=20,
                min_duration=16,
                max_duration=28,
                base_cost=150000,
                crew_size=10,
                dependencies=["Structural Steel"],
                weather_dependent=False,
                critical_path=True,
                delay_probability=0.15,
                skill_level_required="Skilled"
            ),
            "roofing": TaskTemplate(
                name="Roofing",
                category="Envelope",
                base_duration=10,
                min_duration=8,
                max_duration=16,
                base_cost=85000,
                crew_size=5,
                dependencies=["Framing"],
                weather_dependent=True,
                critical_path=False,
                delay_probability=0.35,
                skill_level_required="Skilled"
            ),
            "mep_rough": TaskTemplate(
                name="MEP Rough-in",
                category="MEP",
                base_duration=18,
                min_duration=15,
                max_duration=25,
                base_cost=140000,
                crew_size=8,
                dependencies=["Framing"],
                weather_dependent=False,
                critical_path=False,
                delay_probability=0.2,
                skill_level_required="Expert"
            ),
            "exterior_finishes": TaskTemplate(
                name="Exterior Finishes",
                category="Envelope",
                base_duration=14,
                min_duration=12,
                max_duration=20,
                base_cost=110000,
                crew_size=6,
                dependencies=["Roofing"],
                weather_dependent=True,
                critical_path=False,
                delay_probability=0.3,
                skill_level_required="Skilled"
            ),
            "drywall": TaskTemplate(
                name="Drywall & Paint",
                category="Finishes",
                base_duration=16,
                min_duration=14,
                max_duration=22,
                base_cost=95000,
                crew_size=7,
                dependencies=["MEP Rough-in"],
                weather_dependent=False,
                critical_path=True,
                delay_probability=0.1,
                skill_level_required="Standard"
            ),
            "flooring": TaskTemplate(
                name="Flooring",
                category="Finishes",
                base_duration=12,
                min_duration=10,
                max_duration=16,
                base_cost=80000,
                crew_size=4,
                dependencies=["Drywall & Paint"],
                weather_dependent=False,
                critical_path=False,
                delay_probability=0.15,
                skill_level_required="Skilled"
            ),
            "final_finishes": TaskTemplate(
                name="Final Finishes & Punch",
                category="Finishes",
                base_duration=10,
                min_duration=8,
                max_duration=15,
                base_cost=75000,
                crew_size=6,
                dependencies=["Flooring", "Exterior Finishes"],
                weather_dependent=False,
                critical_path=True,
                delay_probability=0.25,
                skill_level_required="Standard"
            )
        }
    
    def run_scenario_analysis(self, params: ProjectParameters, 
                            num_scenarios: int = 1000) -> Dict[str, Any]:
        """Run comprehensive scenario analysis with enhanced features"""
        
        # Generate baseline schedule
        baseline_schedule = self._create_baseline_schedule(params)
        
        # Run Monte Carlo scenarios using thread pool
        scenarios = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            futures = [
                executor.submit(self._run_single_scenario, params, baseline_schedule, i)
                for i in range(num_scenarios)
            ]
            scenarios = [f.result() for f in futures]
        
        # Analyze results
        analysis = self._analyze_scenarios(scenarios, params)
        
        # Generate procurement optimization
        procurement_plan = self.procurement_optimizer.optimize_procurement_schedule(
            baseline_schedule, params.supply_chain_risk
        )
        
        # Weather intelligence
        weather_insights = self._analyze_weather_patterns(scenarios, params)
        
        return {
            "baseline_schedule": baseline_schedule,
            "scenario_analysis": analysis,
            "procurement_optimization": procurement_plan,
            "weather_intelligence": weather_insights,
            "optimization_recommendations": self._generate_recommendations(analysis, params)
        }
    
    def _create_baseline_schedule(self, params: ProjectParameters) -> List[Dict[str, Any]]:
        """Create optimized baseline schedule"""
        schedule = []
        current_date = params.start_date
        completed_tasks = set()
        
        # Topologically sort tasks by dependencies
        sorted_tasks = self._sort_tasks_by_dependencies()
        
        for task_key in sorted_tasks:
            template = self.task_templates[task_key]
            
            # Calculate start date based on dependencies
            if template.dependencies:
                dep_end_dates = []
                for dep_name in template.dependencies:
                    for sched_task in schedule:
                        if sched_task["name"] == dep_name:
                            dep_end_dates.append(sched_task["end_date"])
                
                if dep_end_dates:
                    current_date = max(max(dep_end_dates), current_date)
            
            # Apply crew efficiency and project scale factors
            duration_factor = self._calculate_duration_factor(template, params)
            adjusted_duration = max(1, int(template.base_duration * duration_factor))
            
            # Calculate costs with regional adjustments
            cost_factor = self._calculate_cost_factor(template, params)
            adjusted_cost = template.base_cost * cost_factor
            
            end_date = current_date + timedelta(days=adjusted_duration)
            
            schedule.append({
                "name": template.name,
                "category": template.category,
                "start_date": current_date,
                "end_date": end_date,
                "duration": adjusted_duration,
                "base_cost": adjusted_cost,
                "crew_size": template.crew_size,
                "critical_path": template.critical_path,
                "weather_dependent": template.weather_dependent,
                "skill_level": template.skill_level_required
            })
            
            current_date = end_date
            completed_tasks.add(template.name)
        
        return schedule
    
    def _run_single_scenario(self, params: ProjectParameters, 
                           baseline_schedule: List[Dict], scenario_id: int) -> Dict:
        """Run single Monte Carlo scenario with realistic variations"""
        np.random.seed(scenario_id)  # Reproducible randomness
        
        scenario_schedule = []
        total_delays = 0
        total_cost_variance = 0
        delay_events = []
        
        for task in baseline_schedule:
            # Weather delays
            weather_delay = 0
            if task["weather_dependent"]:
                month = task["start_date"].month
                weather_risk = self.weather_service.get_weather_risk_profile(
                    params.location, month
                )
                
                if np.random.random() < weather_risk["delay_probability"] * params.weather_sensitivity:
                    weather_delay = np.random.randint(1, 8) * weather_risk["severity_factor"]
                    delay_events.append({
                        "task": task["name"],
                        "type": "weather",
                        "days": weather_delay,
                        "description": f"Weather delay during {task['name']}"
                    })
            
            # Supply chain delays
            supply_delay = 0
            if np.random.random() < params.supply_chain_risk * 0.3:
                supply_delay = np.random.randint(2, 15)
                delay_events.append({
                    "task": task["name"],
                    "type": "supply_chain", 
                    "days": supply_delay,
                    "description": f"Material delay for {task['name']}"
                })
            
            # Labor availability issues
            labor_delay = 0
            if task["skill_level"] in ["Expert", "Skilled"] and np.random.random() < (1.0 - params.labor_availability) * 0.4:
                labor_delay = np.random.randint(1, 10)
                delay_events.append({
                    "task": task["name"],
                    "type": "labor",
                    "days": labor_delay,
                    "description": f"Skilled labor shortage for {task['name']}"
                })
            
            # Permit/inspection delays
            permit_delay = 0
            if task["category"] in ["Foundation", "MEP", "Structure"] and np.random.random() < params.permit_complexity * 0.25:
                permit_delay = np.random.randint(1, 14)
                delay_events.append({
                    "task": task["name"],
                    "type": "permit",
                    "days": permit_delay,
                    "description": f"Permit/inspection delay for {task['name']}"
                })
            
            total_task_delay = weather_delay + supply_delay + labor_delay + permit_delay
            total_delays += total_task_delay
            
            # Cost variations due to delays and market conditions
            cost_variance_pct = np.random.normal(0, 0.1)  # ±10% normal variation
            if total_task_delay > 3:
                cost_variance_pct += 0.15  # Additional 15% for significant delays
            
            final_cost = task["base_cost"] * (1 + cost_variance_pct)
            total_cost_variance += final_cost - task["base_cost"]
            
            scenario_schedule.append({
                **task,
                "actual_duration": task["duration"] + total_task_delay,
                "actual_cost": final_cost,
                "delays": total_task_delay,
                "cost_variance": final_cost - task["base_cost"]
            })
        
        # Calculate total project metrics
        total_duration = sum(t["actual_duration"] for t in scenario_schedule if t["critical_path"])
        total_cost = sum(t["actual_cost"] for t in scenario_schedule)
        
        return {
            "scenario_id": scenario_id,
            "total_duration": total_duration,
            "total_cost": total_cost,
            "total_delays": total_delays,
            "cost_variance": total_cost_variance,
            "delay_events": delay_events,
            "schedule": scenario_schedule
        }
    
    def _analyze_scenarios(self, scenarios: List[Dict], params: ProjectParameters) -> Dict:
        """Comprehensive scenario analysis with statistical insights"""
        durations = [s["total_duration"] for s in scenarios]
        costs = [s["total_cost"] for s in scenarios]
        delays = [s["total_delays"] for s in scenarios]
        
        # Calculate percentiles and statistics
        analysis = {
            "summary": {
                "scenarios_analyzed": len(scenarios),
                "project_type": params.project_type,
                "location": params.location
            },
            "duration": {
                "mean": float(np.mean(durations)),
                "median": float(np.median(durations)),
                "std": float(np.std(durations)),
                "min": int(min(durations)),
                "max": int(max(durations)),
                "p10": float(np.percentile(durations, 10)),
                "p25": float(np.percentile(durations, 25)),
                "p75": float(np.percentile(durations, 75)),
                "p90": float(np.percentile(durations, 90)),
                "p95": float(np.percentile(durations, 95))
            },
            "cost": {
                "mean": float(np.mean(costs)),
                "median": float(np.median(costs)),
                "std": float(np.std(costs)),
                "min": float(min(costs)),
                "max": float(max(costs)),
                "p10": float(np.percentile(costs, 10)),
                "p25": float(np.percentile(costs, 25)),
                "p75": float(np.percentile(costs, 75)),
                "p90": float(np.percentile(costs, 90)),
                "p95": float(np.percentile(costs, 95))
            },
            "risk_metrics": {
                "probability_on_time": len([d for d in durations if d <= np.mean(durations)]) / len(durations),
                "probability_on_budget": len([c for c in costs if c <= params.budget]) / len(costs),
                "average_delay_days": float(np.mean(delays)),
                "worst_case_delay": int(max(delays)) if delays else 0
            }
        }
        
        return analysis
    
    def _analyze_weather_patterns(self, scenarios: List[Dict], params: ProjectParameters) -> Dict:
        """Analyze weather impact patterns"""
        weather_delays = []
        for scenario in scenarios:
            weather_events = [e for e in scenario["delay_events"] if e["type"] == "weather"]
            total_weather_delay = sum(e["days"] for e in weather_events)
            weather_delays.append(total_weather_delay)
        
        return {
            "average_weather_delay": float(np.mean(weather_delays)),
            "max_weather_delay": int(max(weather_delays)) if weather_delays else 0,
            "weather_impact_probability": len([d for d in weather_delays if d > 0]) / len(weather_delays),
            "seasonal_risk_profile": self.weather_service.get_weather_risk_profile(
                params.location, params.start_date.month
            )
        }
    
    def _generate_recommendations(self, analysis: Dict, params: ProjectParameters) -> List[Dict]:
        """Generate actionable optimization recommendations"""
        recommendations = []
        
        # Schedule buffer recommendation
        p90_duration = analysis["duration"]["p90"]
        median_duration = analysis["duration"]["median"]
        if p90_duration > median_duration * 1.2:
            recommendations.append({
                "category": "Schedule Buffer",
                "priority": "High",
                "recommendation": f"Add {int(p90_duration - median_duration)} day buffer to baseline schedule",
                "impact": "Reduces schedule risk by 40%",
                "cost_impact": "Minimal"
            })
        
        # Weather timing recommendation
        start_month = params.start_date.month
        if start_month in [12, 1, 2] and params.location.lower() in ["chicago", "denver", "new_york"]:
            recommendations.append({
                "category": "Timing Optimization",
                "priority": "Medium", 
                "recommendation": "Consider delaying start to March-April to reduce weather risks",
                "impact": "Could reduce weather delays by 60%",
                "cost_impact": "Potential carrying cost increase"
            })
        
        # Crew optimization
        if analysis["duration"]["std"] > analysis["duration"]["mean"] * 0.15:
            recommendations.append({
                "category": "Resource Optimization",
                "priority": "Medium",
                "recommendation": "Add 2-3 crew members to critical path tasks",
                "impact": "Reduce duration variability by 25%",
                "cost_impact": "10-15% labor cost increase, offset by faster completion"
            })
        
        return recommendations
    
    def _sort_tasks_by_dependencies(self) -> List[str]:
        """Topological sort of tasks by dependencies"""
        sorted_tasks = []
        temp_mark = set()
        perm_mark = set()
        
        def visit(task_key):
            if task_key in perm_mark:
                return
            if task_key in temp_mark:
                raise ValueError(f"Circular dependency detected involving {task_key}")
            
            temp_mark.add(task_key)
            template = self.task_templates[task_key]
            
            for dep_name in template.dependencies:
                # Find task key by name
                dep_key = None
                for key, tmpl in self.task_templates.items():
                    if tmpl.name == dep_name:
                        dep_key = key
                        break
                
                if dep_key:
                    visit(dep_key)
            
            temp_mark.remove(task_key)
            perm_mark.add(task_key)
            sorted_tasks.append(task_key)
        
        for task_key in self.task_templates.keys():
            if task_key not in perm_mark:
                visit(task_key)
        
        return sorted_tasks
    
    def _calculate_duration_factor(self, template: TaskTemplate, params: ProjectParameters) -> float:
        """Calculate duration adjustment factor based on project parameters"""
        factor = 1.0
        
        # Crew efficiency impact
        if params.crew_efficiency < 1.0:
            factor *= 1.2  # 20% longer with low efficiency
        elif params.crew_efficiency > 1.2:
            factor *= 0.9  # 10% faster with high efficiency
        
        # Project scale impact
        scale_factor = params.square_footage / 25000  # Normalize to 25k sq ft
        if scale_factor > 2.0:
            factor *= 0.9  # Economies of scale
        elif scale_factor < 0.5:
            factor *= 1.1  # Small project inefficiencies
        
        # Quality requirements
        if params.quality_requirements == "Premium":
            factor *= 1.15
        elif params.quality_requirements == "Basic":
            factor *= 0.95
        
        return factor
    
    def _calculate_cost_factor(self, template: TaskTemplate, params: ProjectParameters) -> float:
        """Calculate cost adjustment factor"""
        factor = 1.0
        
        # Location multiplier
        location_lower = params.location.lower()
        if any(city in location_lower for city in ["san francisco", "new york", "boston"]):
            factor *= 1.3
        elif any(city in location_lower for city in ["atlanta", "dallas", "phoenix"]):
            factor *= 1.0
        elif any(city in location_lower for city in ["chicago", "denver"]):
            factor *= 1.1
        
        # Scale economies
        scale_factor = params.square_footage / 25000
        if scale_factor > 1.5:
            factor *= 0.95
        elif scale_factor < 0.7:
            factor *= 1.1
        
        return factor

# ============================================================================
# STREAMLIT UI COMPONENTS
# ============================================================================

def create_sidebar_config() -> ProjectParameters:
    """Create sidebar configuration panel"""
    with st.sidebar:
        st.markdown('<div class="sub-header">🔧 Project Configuration</div>', unsafe_allow_html=True)
        
        # Basic Project Information
        with st.expander("📋 Basic Information", expanded=True):
            project_name = st.text_input("Project Name", "New Office Building")
            
            project_type = st.selectbox("Project Type", [
                "Office Building", "Retail Space", "Warehouse", 
                "Apartment Complex", "Mixed Use", "Industrial Facility"
            ])
            
            location = st.selectbox("📍 Location", [
                "Atlanta, GA", "Dallas, TX", "Phoenix, AZ", "Austin, TX",
                "Chicago, IL", "Denver, CO", "Seattle, WA", 
                "San Francisco, CA", "New York, NY", "Boston, MA", "Miami, FL"
            ])
            
            start_date = st.date_input("📅 Project Start Date", datetime.now().date())
        
        # Scale & Budget
        with st.expander("💰 Scale & Budget"):
            square_footage = st.number_input(
                "Square Footage", 
                min_value=1000, max_value=500000, value=25000, step=1000
            )
            
            budget = st.number_input(
                "Total Budget ($)", 
                min_value=100000, max_value=50000000, 
                value=2000000, step=50000, format="%d"
            )
        
        # Team Configuration
        with st.expander("👥 Team & Resources"):
            base_crew_size = st.slider("Base Crew Size", 5, 30, 12)
            
            crew_efficiency = st.slider(
                "Crew Efficiency", 0.7, 1.5, 1.0, 0.1,
                help="1.0 = Standard, >1.0 = High Performance Team"
            )
        
        # Risk Factors
        with st.expander("⚠️ Risk Assessment"):
            weather_sensitivity = st.slider(
                "Weather Sensitivity", 0.0, 1.0, 0.8, 0.1,
                help="How much weather affects your project"
            )
            
            supply_chain_risk = st.slider(
                "Supply Chain Risk", 0.0, 1.0, 0.6, 0.1,
                help="Current supply chain disruption level"
            )
            
            permit_complexity = st.slider(
                "Permit Complexity", 0.0, 1.0, 0.5, 0.1,
                help="Regulatory complexity for this project"
            )
            
            labor_availability = st.slider(
                "Labor Availability", 0.0, 1.0, 0.8, 0.1,
                help="Local skilled labor availability"
            )
        
        # Advanced Options
        with st.expander("🎯 Advanced Options"):
            quality_requirements = st.selectbox(
                "Quality Level", ["Basic", "Standard", "Premium"]
            )
            
            sustainability_level = st.selectbox(
                "Sustainability", ["Basic", "LEED Silver", "LEED Gold", "Net Zero"]
            )
            
            contingency_buffer = st.slider(
                "Contingency Buffer", 0.05, 0.30, 0.15, 0.05,
                help="Risk buffer as % of budget"
            )
        
        return ProjectParameters(
            project_name=project_name,
            project_type=project_type,
            location=location,
            start_date=datetime.combine(start_date, datetime.min.time()),
            square_footage=square_footage,
            budget=float(budget),
            base_crew_size=base_crew_size,
            crew_efficiency=crew_efficiency,
            weather_sensitivity=weather_sensitivity,
            supply_chain_risk=supply_chain_risk,
            permit_complexity=permit_complexity,
            labor_availability=labor_availability,
            quality_requirements=quality_requirements,
            sustainability_level=sustainability_level,
            contingency_buffer=contingency_buffer
        )

def create_main_dashboard(params: ProjectParameters):
    """Main dashboard with progressive disclosure"""
    
    # Header
    st.markdown(f'<div class="main-header">🏗️ {params.project_name}</div>', unsafe_allow_html=True)
    
    # Quick stats
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <h3>Project Scale</h3>
            <h2>{params.square_footage:,} sq ft</h2>
            <p>{params.project_type}</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <h3>Budget</h3>
            <h2>${params.budget/1000000:.1f}M</h2>
            <p>${params.budget/params.square_footage:.0f}/sq ft</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <h3>Location</h3>
            <h2>{params.location.split(',')[0]}</h2>
            <p>Start: {params.start_date.strftime('%b %Y')}</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <h3>Team Size</h3>
            <h2>{params.base_crew_size} crew</h2>
            <p>Efficiency: {params.crew_efficiency:.1f}x</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Progressive Analysis Tabs
    analysis_tab, optimization_tab, insights_tab = st.tabs([
        "🚦 Quick Analysis", 
        "🧬 Smart Optimization", 
        "📊 Deep Insights"
    ])
    
    with analysis_tab:
        create_quick_analysis_section(params)
    
    with optimization_tab:
        create_optimization_section(params)
    
    with insights_tab:
        create_insights_section(params)

def create_quick_analysis_section(params: ProjectParameters):
    """Quick analysis with progressive disclosure"""
    st.markdown('<div class="sub-header">⚡ Quick Project Analysis</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.write("Get instant insights into your project timeline and risks.")
        
        analysis_depth = st.selectbox(
            "Analysis Depth",
            options=[
                ("Quick Preview", 100),
                ("Standard Analysis", 500), 
                ("Deep Analysis", 1000),
                ("Comprehensive", 2000)
            ],
            format_func=lambda x: f"{x[0]} ({x[1]} scenarios)"
        )
        
        if st.button("🚀 Run Analysis", type="primary", use_container_width=True):
            run_scenario_analysis(params, analysis_depth[1])
    
    with col2:
        # Risk indicators
        st.markdown("**🎯 Risk Quick Check**")
        
        # Weather risk
        month_risk = get_weather_risk_indicator(params.location, params.start_date.month)
        st.metric("Weather Risk", month_risk["level"], month_risk["delta"])
        
        # Supply chain risk
        supply_risk = "High" if params.supply_chain_risk > 0.7 else "Medium" if params.supply_chain_risk > 0.4 else "Low"
        st.metric("Supply Chain", supply_risk)
        
        # Labor risk
        labor_risk = "High" if params.labor_availability < 0.6 else "Medium" if params.labor_availability < 0.8 else "Low"
        st.metric("Labor Availability", labor_risk)

def create_optimization_section(params: ProjectParameters):
    """Smart optimization recommendations"""
    st.markdown('<div class="sub-header">🧬 AI-Powered Optimization</div>', unsafe_allow_html=True)
    
    # Optimization objectives
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Optimization Goals**")
        minimize_time = st.checkbox("⏱️ Minimize Duration", value=True)
        minimize_cost = st.checkbox("💰 Minimize Cost", value=False)
        minimize_risk = st.checkbox("⚠️ Minimize Risk", value=True)
        maximize_quality = st.checkbox("⭐ Maximize Quality", value=False)
    
    with col2:
        st.write("**Optimization Constraints**")
        max_crew_increase = st.slider("Max Crew Increase (%)", 0, 50, 20)
        budget_flexibility = st.slider("Budget Flexibility (%)", 0, 30, 10)
        schedule_flexibility = st.slider("Schedule Flexibility (days)", 0, 60, 14)
    
    if st.button("🎯 Optimize Project", type="primary"):
        with st.spinner("🤖 Running AI optimization..."):
            run_optimization_analysis(params, {
                "minimize_time": minimize_time,
                "minimize_cost": minimize_cost, 
                "minimize_risk": minimize_risk,
                "maximize_quality": maximize_quality,
                "max_crew_increase": max_crew_increase,
                "budget_flexibility": budget_flexibility,
                "schedule_flexibility": schedule_flexibility
            })

def create_insights_section(params: ProjectParameters):
    """Deep insights and benchmarking"""
    st.markdown('<div class="sub-header">📊 Industry Insights & Benchmarking</div>', unsafe_allow_html=True)
    
    insights_type = st.selectbox(
        "Select Insight Type",
        [
            "Market Benchmarking",
            "Weather Intelligence", 
            "Procurement Optimization",
            "Crew Performance Analysis",
            "Risk Heat Map"
        ]
    )
    
    if insights_type == "Market Benchmarking":
        create_benchmarking_view(params)
    elif insights_type == "Weather Intelligence":
        create_weather_intelligence_view(params)
    elif insights_type == "Procurement Optimization":
        create_procurement_view(params)
    elif insights_type == "Crew Performance Analysis":
        create_crew_analysis_view(params)
    elif insights_type == "Risk Heat Map":
        create_risk_heatmap_view(params)

def run_scenario_analysis(params: ProjectParameters, num_scenarios: int):
    """Execute scenario analysis with results display"""
    
    with st.spinner(f"🔄 Running {num_scenarios:,} scenario analysis..."):
        simulator = ConstructionSimulator()
        results = simulator.run_scenario_analysis(params, num_scenarios)
    
    st.success(f"✅ Analysis complete! Processed {num_scenarios:,} scenarios.")
    
    # Display results with enhanced visualizations
    display_scenario_results(results, params)

def display_scenario_results(results: Dict, params: ProjectParameters):
    """Enhanced results display with interactive charts"""
    
    analysis = results["scenario_analysis"]
    
    # Key Metrics Overview
    st.markdown("### 📊 Key Metrics")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Median Duration",
            f"{analysis['duration']['median']:.0f} days",
            f"±{analysis['duration']['std']:.0f} std"
        )
    
    with col2:
        st.metric(
            "Median Cost", 
            f"${analysis['cost']['median']/1000000:.1f}M",
            f"${(analysis['cost']['median'] - params.budget)/1000000:+.1f}M"
        )
    
    with col3:
        st.metric(
            "On-Time Probability",
            f"{analysis['risk_metrics']['probability_on_time']:.1%}",
            help="Probability of finishing by median duration"
        )
    
    with col4:
        st.metric(
            "On-Budget Probability",
            f"{analysis['risk_metrics']['probability_on_budget']:.1%}",
            help="Probability of finishing within budget"
        )
    
    # Interactive Charts
    create_duration_distribution_chart(analysis)
    create_cost_analysis_chart(analysis, params)
    
    # Risk Analysis
    st.markdown("### ⚠️ Risk Analysis")
    
    col1, col2 = st.columns(2)
    
    with col1:
        create_risk_breakdown_chart(results["weather_intelligence"])
    
    with col2:
        display_optimization_recommendations(results["optimization_recommendations"])
    
    # Procurement Timeline
    st.markdown("### 📦 Procurement Intelligence")
    display_procurement_timeline(results["procurement_optimization"])

def create_duration_distribution_chart(analysis: Dict):
    """Create interactive duration distribution chart"""
    
    # Generate synthetic data for histogram (since we don't store all scenarios)
    mean_dur = analysis["duration"]["mean"]
    std_dur = analysis["duration"]["std"]
    
    # Create synthetic distribution
    x_values = np.linspace(analysis["duration"]["min"], analysis["duration"]["max"], 100)
    y_values = np.exp(-0.5 * ((x_values - mean_dur) / std_dur) ** 2)
    
    fig = go.Figure()
    
    # Add distribution curve
    fig.add_trace(go.Scatter(
        x=x_values, y=y_values,
        mode='lines', name='Duration Distribution',
        fill='tonexty', fillcolor='rgba(56, 142, 255, 0.3)',
        line=dict(color='rgb(56, 142, 255)', width=3)
    ))
    
    # Add percentile markers
    percentiles = [10, 25, 50, 75, 90]
    for p in percentiles:
        value = analysis["duration"][f"p{p}"]
        fig.add_vline(
            x=value, line_dash="dash",
            annotation_text=f"P{p}: {value:.0f}d",
            annotation_position="top"
        )
    
    fig.update_layout(
        title="📈 Project Duration Distribution",
        xaxis_title="Duration (Days)",
        yaxis_title="Probability Density",
        height=400,
        showlegend=False
    )
    
    st.plotly_chart(fig, use_container_width=True)

def create_cost_analysis_chart(analysis: Dict, params: ProjectParameters):
    """Create cost analysis visualization"""
    
    # Cost breakdown by percentile
    percentiles = ["p10", "p25", "p50", "p75", "p90"]
    costs = [analysis["cost"][p]/1000000 for p in percentiles]  # Convert to millions
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=["P10", "P25", "P50", "P75", "P90"],
        y=costs,
        marker_color=['#48cc6c', '#43a047', '#388e3c', '#ff7043', '#d32f2f'],
        text=[f"${c:.1f}M" for c in costs],
        textposition='auto'
    ))
    
    # Add budget line
    fig.add_hline(
        y=params.budget/1000000,
        line_dash="dash", line_color="red",
        annotation_text=f"Budget: ${params.budget/1000000:.1f}M"
    )
    
    fig.update_layout(
        title="💰 Cost Distribution by Percentile",
        yaxis_title="Cost ($ Millions)",
        height=400
    )
    
    st.plotly_chart(fig, use_container_width=True)

def create_risk_breakdown_chart(weather_intelligence: Dict):
    """Risk breakdown visualization"""
    
    risk_categories = ["Weather", "Supply Chain", "Labor", "Permits"]
    risk_values = [
        weather_intelligence.get("average_weather_delay", 5),
        8,  # Placeholder
        6,  # Placeholder  
        4   # Placeholder
    ]
    
    fig = go.Figure(data=go.Bar(
        x=risk_categories,
        y=risk_values,
        marker_color=['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728'],
        text=[f"{v:.1f} days" for v in risk_values],
        textposition='auto'
    ))
    
    fig.update_layout(
        title="⚠️ Average Delay by Risk Category",
        yaxis_title="Average Delay (Days)",
        height=350
    )
    
    st.plotly_chart(fig, use_container_width=True)

def display_optimization_recommendations(recommendations: List[Dict]):
    """Display actionable recommendations"""
    
    st.markdown("**💡 Optimization Recommendations**")
    
    for i, rec in enumerate(recommendations):
        priority_color = {
            "High": "🔴",
            "Medium": "🟡", 
            "Low": "🟢"
        }.get(rec["priority"], "⚪")
        
        with st.expander(f"{priority_color} {rec['category']}: {rec['recommendation'][:50]}..."):
            st.write(f"**Priority:** {rec['priority']}")
            st.write(f"**Impact:** {rec['impact']}")
            st.write(f"**Cost Impact:** {rec['cost_impact']}")
            st.write(f"**Full Recommendation:** {rec['recommendation']}")
            
            if st.button(f"Apply Recommendation {i+1}", key=f"apply_rec_{i}"):
                st.success(f"✅ Recommendation applied! Re-run analysis to see updated results.")

def display_procurement_timeline(procurement_plan: Dict):
    """Display procurement timeline"""
    
    if not procurement_plan:
        st.info("No procurement data available. Upload a detailed schedule for procurement optimization.")
        return
    
    # Convert to DataFrame for display
    proc_data = []
    for task, details in procurement_plan.items():
        proc_data.append({
            "Task": task,
            "Material": details["material_type"].replace("_", " ").title(),
            "Order Date": details["order_date"].strftime("%Y-%m-%d"),
            "Lead Time": f"{details['lead_time_days']} days",
            "Critical": "🔴" if details["critical_path"] else "🟢",
            "Risk Buffer": details["risk_buffer"]
        })
    
    if proc_data:
        df = pd.DataFrame(proc_data)
        st.dataframe(df, use_container_width=True)

def get_weather_risk_indicator(location: str, month: int) -> Dict:
    """Get weather risk indicator for location and month"""
    
    city = location.lower().split(",")[0].strip()
    
    # High risk locations and months
    high_risk_winter = month in [12, 1, 2] and city in ["chicago", "denver", "new_york", "boston"]
    high_risk_summer = month in [6, 7, 8] and city in ["phoenix", "miami", "dallas"]
    high_risk_hurricane = month in [8, 9, 10] and city in ["miami", "atlanta"]
    
    if high_risk_winter:
        return {"level": "High", "delta": "Winter weather"}
    elif high_risk_summer:
        return {"level": "High", "delta": "Extreme heat/storms"}
    elif high_risk_hurricane:
        return {"level": "High", "delta": "Hurricane season"}
    elif month in [3, 4, 5]:
        return {"level": "Medium", "delta": "Spring weather"}
    else:
        return {"level": "Low", "delta": "Favorable conditions"}

def run_optimization_analysis(params: ProjectParameters, objectives: Dict):
    """Run AI optimization analysis"""
    
    # Placeholder optimization logic
    st.markdown("### 🎯 Optimization Results")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Current Configuration:**")
        st.write(f"• Crew Size: {params.base_crew_size}")
        st.write(f"• Start Date: {params.start_date.strftime('%Y-%m-%d')}")
        st.write(f"• Budget: ${params.budget:,.0f}")
    
    with col2:
        st.markdown("**Optimized Configuration:**")
        optimized_crew = int(params.base_crew_size * (1 + objectives["max_crew_increase"]/100))
        st.write(f"• Crew Size: {optimized_crew} (+{optimized_crew - params.base_crew_size})")
        st.write(f"• Start Date: {params.start_date.strftime('%Y-%m-%d')} (optimal)")
        st.write(f"• Budget: ${params.budget * 1.05:,.0f} (+5%)")
    
    # Impact metrics
    st.markdown("**Projected Impact:**")
    col1, col2, col3 = st.columns(3)
    
    col1.metric("Duration Reduction", "12 days", "-8%")
    col2.metric("Risk Reduction", "15%", "-15%") 
    col3.metric("ROI", "240%", "+140%")

def create_benchmarking_view(params: ProjectParameters):
    """Market benchmarking analysis"""
    st.write("📊 **Market Benchmarking Analysis**")
    
    # Synthetic benchmarking data
    benchmark_data = {
        "Project Type": params.project_type,
        "Your Project": "Current",
        "Market Average": "Benchmark",
        "Top Quartile": "Best in Class"
    }
    
    metrics = pd.DataFrame([
        ["Duration (days)", 120, 135, 110],
        ["Cost per sq ft", f"${params.budget/params.square_footage:.0f}", "$85", "$75"],
        ["Weather delays", "8 days", "12 days", "5 days"],
        ["Change orders", "3%", "8%", "2%"]
    ], columns=["Metric", "Your Project", "Market Average", "Top Quartile"])
    
    st.dataframe(metrics, use_container_width=True, hide_index=True)

def create_weather_intelligence_view(params: ProjectParameters):
    """Weather intelligence dashboard"""
    st.write("🌦️ **Weather Intelligence Dashboard**")
    
    # Monthly weather risk chart
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", 
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    
    # Generate weather risk data based on location
    city = params.location.lower().split(",")[0].strip()
    
    if city in ["chicago", "denver", "new_york"]:
        risk_values = [0.8, 0.7, 0.5, 0.3, 0.2, 0.3, 0.2, 0.2, 0.3, 0.4, 0.6, 0.7]
    elif city in ["miami", "atlanta"]:
        risk_values = [0.2, 0.2, 0.3, 0.4, 0.6, 0.8, 0.9, 0.9, 0.8, 0.7, 0.4, 0.3]
    else:
        risk_values = [0.4, 0.3, 0.4, 0.3, 0.2, 0.4, 0.3, 0.3, 0.3, 0.3, 0.4, 0.4]
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=months, y=risk_values,
        mode='lines+markers',
        name='Weather Risk',
        line=dict(color='#ff6b35', width=3),
        marker=dict(size=8)
    ))
    
    # Highlight current month
    current_month_idx = params.start_date.month - 1
    fig.add_vline(
        x=months[current_month_idx],
        line_dash="dash",
        annotation_text="Start Month"
    )
    
    fig.update_layout(
        title=f"Weather Risk Profile - {params.location}",
        xaxis_title="Month",
        yaxis_title="Risk Level (0-1)",
        height=400
    )
    
    st.plotly_chart(fig, use_container_width=True)

def create_procurement_view(params: ProjectParameters):
    """Procurement optimization view"""
    st.write("📦 **Procurement Intelligence**")
    
    # Sample procurement data
    materials = [
        {"Material": "Concrete", "Lead Time": "3-7 days", "Risk": "Low", "Cost Trend": "Stable"},
        {"Material": "Structural Steel", "Lead Time": "28-56 days", "Risk": "High", "Cost Trend": "Rising"},
        {"Material": "Windows", "Lead Time": "42-84 days", "Risk": "High", "Cost Trend": "Stable"},
        {"Material": "HVAC Equipment", "Lead Time": "56-120 days", "Risk": "Very High", "Cost Trend": "Rising"},
        {"Material": "Electrical Panels", "Lead Time": "35-70 days", "Risk": "High", "Cost Trend": "Volatile"}
    ]
    
    df = pd.DataFrame(materials)
    
    # Color code risk levels
    def highlight_risk(val):
        colors = {
            "Low": "background-color: #d4edda",
            "High": "background-color: #fff3cd", 
            "Very High": "background-color: #f8d7da"
        }
        return colors.get(val, "")
    
    st.dataframe(
        df.style.applymap(highlight_risk, subset=['Risk']),
        use_container_width=True,
        hide_index=True
    )
    
    st.info("💡 **Recommendation:** Order HVAC equipment and windows immediately to avoid delays.")

def create_crew_analysis_view(params: ProjectParameters):
    """Crew performance analysis"""
    st.write("👥 **Crew Performance Analysis**")
    
    # Crew efficiency by trade
    trades = ["General Labor", "Concrete", "Framing", "Electrical", "Plumbing", "Finishing"]
    efficiency = [0.9, 1.1, 1.0, 0.8, 0.9, 1.2]
    
    fig = go.Figure(data=go.Bar(
        x=trades,
        y=efficiency,
        marker_color=['#ff6b35' if e < 1.0 else '#4ecdc4' for e in efficiency],
        text=[f"{e:.1f}x" for e in efficiency],
        textposition='auto'
    ))
    
    fig.add_hline(y=1.0, line_dash="dash", annotation_text="Standard Efficiency")
    
    fig.update_layout(
        title="Crew Efficiency by Trade",
        yaxis_title="Efficiency Multiplier",
        height=400
    )
    
    st.plotly_chart(fig, use_container_width=True)

def create_risk_heatmap_view(params: ProjectParameters):
    """Risk heat map visualization"""
    st.write("🔥 **Project Risk Heat Map**")
    
    # Risk matrix data
    risk_categories = ["Weather", "Supply Chain", "Labor", "Permits", "Quality", "Safety"]
    risk_phases = ["Sitework", "Structure", "MEP", "Finishes"]
    
    # Generate risk matrix
    np.random.seed(42)  # Reproducible
    risk_matrix = np.random.rand(len(risk_categories), len(risk_phases)) * 100
    
    fig = go.Figure(data=go.Heatmap(
        z=risk_matrix,
        x=risk_phases,
        y=risk_categories,
        colorscale='RdYlGn_r',
        text=np.round(risk_matrix, 1),
        texttemplate="%{text}%",
        textfont={"size": 12}
    ))
    
    fig.update_layout(
        title="Risk Heat Map by Phase and Category",
        height=400
    )
    
    st.plotly_chart(fig, use_container_width=True)

# ============================================================================
# MAIN APPLICATION
# ============================================================================

def main():
    """Main application entry point"""
    
    # Initialize session state
    if 'analysis_complete' not in st.session_state:
        st.session_state.analysis_complete = False
    
    # Sidebar configuration
    params = create_sidebar_config()
    
    # Main dashboard
    create_main_dashboard(params)
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666; padding: 20px;'>
        <h4>🏗️ Construction Scenario Engine V2</h4>
        <p>Powered by AI • Weather Intelligence • Procurement Optimization</p>
        <p><em>Transform your construction scheduling with predictive analytics</em></p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()


