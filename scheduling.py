# Construction Scenario Engine V2 - Complete Enhanced System
# Preserves all V1 functionality while adding advanced V2 features
# Categories: Core Analysis, Weather Intelligence, Schedule Upload, Optimization, Portfolio

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
import io
import re

# Configure Streamlit
st.set_page_config(
    page_title="Construction Scenario Engine V2",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for enhanced UI
st.markdown("""
<style>
    .main-header { 
        font-size: 2.5rem; 
        font-weight: 700; 
        color: #1f2937; 
        margin-bottom: 1rem;
    }
    .category-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        font-weight: 600;
        margin: 1rem 0;
    }
    .weather-alert {
        background: linear-gradient(135deg, #ff6b35 0%, #f7931e 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        border-left: 5px solid #ff4500;
    }
    .success-card {
        background: linear-gradient(135deg, #48cc6c 0%, #43a047 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
    }
    .feature-card {
        border: 2px solid #e2e8f0;
        border-radius: 10px;
        padding: 1.5rem;
        margin: 1rem 0;
        background: #f8fafc;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# ENHANCED DATA MODELS (V1 + V2)
# ============================================================================

@dataclass
class SimulationParameters:
    """V1 Core simulation parameters - preserved exactly"""
    location: str
    start_date: datetime
    crew_size: int
    budget: float
    project_type: str
    square_footage: int
    weather_sensitivity: float = 0.7
    supply_chain_risk: float = 0.3
    permit_risk: float = 0.4
    labor_availability: float = 0.8

@dataclass
class TaskTemplate:
    """V1 Task template - preserved exactly"""
    name: str
    base_duration: int
    min_duration: int
    max_duration: int
    dependencies: List[str]
    weather_sensitive: bool
    crew_required: int
    cost: float
    delay_probability: float
    critical_path: bool

@dataclass 
class ProjectParameters:
    """V2 Enhanced project configuration"""
    project_name: str = "New Construction Project"
    project_type: str = "Office Building"
    location: str = "Atlanta, GA"
    start_date: datetime = datetime.now()
    square_footage: int = 25000
    budget: float = 2000000.0
    base_crew_size: int = 12
    crew_efficiency: float = 1.0
    weather_sensitivity: float = 0.8
    supply_chain_risk: float = 0.6
    permit_complexity: float = 0.5
    labor_availability: float = 0.8
    contingency_buffer: float = 0.15
    quality_requirements: str = "Standard"
    sustainability_level: str = "Basic"

# ============================================================================
# V2 ENHANCED WEATHER INTELLIGENCE SYSTEM
# ============================================================================

class WeatherIntelligenceEngine:
    """Advanced weather intelligence with regional patterns and forecasting"""
    
    REGIONAL_WEATHER_PATTERNS = {
        "atlanta": {
            "winter_risk": 0.3, "summer_storms": 0.6, "hurricane_season": 0.3,
            "mud_season": [3, 4], "optimal_months": [5, 6, 9, 10]
        },
        "dallas": {
            "winter_risk": 0.2, "summer_heat": 0.7, "tornado_season": 0.4,
            "extreme_heat_months": [6, 7, 8], "optimal_months": [3, 4, 10, 11]
        },
        "phoenix": {
            "extreme_heat": 0.8, "monsoon": 0.4, "winter_mild": 0.1,
            "extreme_heat_months": [5, 6, 7, 8, 9], "optimal_months": [11, 12, 1, 2, 3]
        },
        "chicago": {
            "winter_severe": 0.8, "summer_storms": 0.4, "wind": 0.5,
            "winter_months": [11, 12, 1, 2, 3], "optimal_months": [5, 6, 7, 8, 9]
        },
        "denver": {
            "snow": 0.6, "altitude_effects": 0.3, "hail": 0.5,
            "winter_months": [11, 12, 1, 2, 3, 4], "optimal_months": [6, 7, 8, 9]
        },
        "seattle": {
            "rain": 0.8, "winter_mild": 0.3, "summer_dry": 0.1,
            "rainy_season": [10, 11, 12, 1, 2, 3, 4], "optimal_months": [6, 7, 8, 9]
        },
        "miami": {
            "hurricane": 0.5, "daily_rain": 0.7, "heat_humidity": 0.8,
            "hurricane_season": [6, 7, 8, 9, 10, 11], "optimal_months": [12, 1, 2, 3, 4]
        },
        "new_york": {
            "winter_variable": 0.6, "summer_humid": 0.5, "coastal_storms": 0.4,
            "winter_months": [12, 1, 2, 3], "optimal_months": [5, 6, 9, 10]
        }
    }
    
    WEATHER_IMPACT_BY_TRADE = {
        "concrete": {"rain": 0.9, "freeze": 0.95, "wind": 0.3, "heat": 0.4},
        "sitework": {"rain": 0.95, "freeze": 0.8, "wind": 0.2, "heat": 0.3},
        "roofing": {"rain": 0.98, "wind": 0.9, "heat": 0.6, "freeze": 0.7},
        "exterior": {"rain": 0.8, "wind": 0.6, "heat": 0.4, "freeze": 0.6},
        "framing": {"rain": 0.4, "wind": 0.7, "heat": 0.2, "freeze": 0.5},
        "interior": {"rain": 0.1, "wind": 0.0, "heat": 0.2, "freeze": 0.3}
    }
    
    @classmethod
    def get_weather_intelligence(cls, location: str, start_date: datetime, 
                               project_duration: int) -> Dict[str, Any]:
        """Comprehensive weather intelligence for project planning"""
        city = location.lower().split(",")[0].strip()
        pattern = cls.REGIONAL_WEATHER_PATTERNS.get(city, {})
        
        # Monthly risk assessment
        monthly_risks = []
        current_month = start_date.month
        
        for month_offset in range(project_duration // 30 + 2):
            month = ((current_month - 1 + month_offset) % 12) + 1
            risk_level = cls._calculate_monthly_risk(pattern, month)
            monthly_risks.append({
                "month": month,
                "month_name": datetime(2024, month, 1).strftime("%B"),
                "risk_level": risk_level,
                "risk_category": cls._get_risk_category(risk_level),
                "recommended_activities": cls._get_monthly_recommendations(pattern, month)
            })
        
        # Seasonal planning insights
        seasonal_insights = cls._generate_seasonal_insights(pattern, start_date, project_duration)
        
        # Weather-optimized schedule suggestions
        schedule_optimizations = cls._generate_schedule_optimizations(pattern, start_date)
        
        return {
            "location_profile": pattern,
            "monthly_risk_forecast": monthly_risks,
            "seasonal_insights": seasonal_insights,
            "schedule_optimizations": schedule_optimizations,
            "optimal_start_months": pattern.get("optimal_months", [5, 6, 9, 10]),
            "high_risk_periods": cls._identify_high_risk_periods(pattern, start_date)
        }
    
    @classmethod
    def _calculate_monthly_risk(cls, pattern: Dict, month: int) -> float:
        """Calculate weather risk for specific month"""
        base_risk = 0.3
        
        if "winter_months" in pattern and month in pattern["winter_months"]:
            base_risk += pattern.get("winter_severe", pattern.get("winter_risk", 0.5))
        elif "extreme_heat_months" in pattern and month in pattern["extreme_heat_months"]:
            base_risk += pattern.get("extreme_heat", pattern.get("summer_heat", 0.4))
        elif "hurricane_season" in pattern and month in pattern["hurricane_season"]:
            base_risk += pattern.get("hurricane", 0.4)
        elif "rainy_season" in pattern and month in pattern["rainy_season"]:
            base_risk += pattern.get("rain", 0.4)
        
        return min(0.95, base_risk)
    
    @classmethod
    def _get_risk_category(cls, risk_level: float) -> str:
        """Categorize risk level"""
        if risk_level >= 0.7:
            return "High Risk"
        elif risk_level >= 0.4:
            return "Medium Risk"
        else:
            return "Low Risk"
    
    @classmethod
    def _get_monthly_recommendations(cls, pattern: Dict, month: int) -> List[str]:
        """Get activity recommendations for specific month"""
        recommendations = []
        
        if "winter_months" in pattern and month in pattern["winter_months"]:
            recommendations.extend([
                "Prioritize interior work",
                "Pre-order materials for spring",
                "Focus on design and planning phases"
            ])
        elif "optimal_months" in pattern and month in pattern["optimal_months"]:
            recommendations.extend([
                "Maximize exterior work",
                "Schedule critical path activities",
                "Plan intensive construction phases"
            ])
        elif "extreme_heat_months" in pattern and month in pattern["extreme_heat_months"]:
            recommendations.extend([
                "Start work earlier in day",
                "Increase hydration protocols",
                "Consider night shifts for certain activities"
            ])
        
        return recommendations
    
    @classmethod
    def _generate_seasonal_insights(cls, pattern: Dict, start_date: datetime, 
                                  duration: int) -> Dict[str, Any]:
        """Generate comprehensive seasonal insights"""
        insights = {
            "weather_risk_score": 0.5,  # Default
            "seasonal_challenges": [],
            "seasonal_opportunities": [],
            "timing_recommendations": []
        }
        
        start_month = start_date.month
        
        # Calculate weather risk score for project timeline
        total_risk = 0
        months_in_project = duration // 30 + 1
        
        for i in range(months_in_project):
            month = ((start_month - 1 + i) % 12) + 1
            monthly_risk = cls._calculate_monthly_risk(pattern, month)
            total_risk += monthly_risk
        
        insights["weather_risk_score"] = total_risk / months_in_project
        
        # Seasonal challenges and opportunities
        if start_month in pattern.get("winter_months", []):
            insights["seasonal_challenges"].append("Cold weather delays")
            insights["timing_recommendations"].append("Consider spring start for reduced delays")
        
        if start_month in pattern.get("optimal_months", []):
            insights["seasonal_opportunities"].append("Optimal weather conditions")
            insights["timing_recommendations"].append("Excellent timing for project start")
        
        return insights
    
    @classmethod
    def _generate_schedule_optimizations(cls, pattern: Dict, start_date: datetime) -> List[Dict]:
        """Generate schedule optimization recommendations"""
        optimizations = []
        
        optimal_months = pattern.get("optimal_months", [])
        current_month = start_date.month
        
        if current_month not in optimal_months:
            # Find next optimal start month
            next_optimal = None
            for i in range(1, 13):
                check_month = ((current_month - 1 + i) % 12) + 1
                if check_month in optimal_months:
                    next_optimal = check_month
                    break
            
            if next_optimal:
                months_to_wait = (next_optimal - current_month) % 12
                if months_to_wait <= 6:  # Only suggest if within 6 months
                    optimizations.append({
                        "type": "Start Date Optimization",
                        "current_risk": "Medium-High",
                        "recommended_action": f"Delay start by {months_to_wait} months",
                        "expected_benefit": "25-40% reduction in weather delays",
                        "trade_off": "Carrying costs and schedule pressure"
                    })
        
        return optimizations
    
    @classmethod
    def _identify_high_risk_periods(cls, pattern: Dict, start_date: datetime) -> List[Dict]:
        """Identify specific high-risk periods"""
        high_risk_periods = []
        
        # Hurricane season
        if "hurricane_season" in pattern:
            high_risk_periods.append({
                "period": "Hurricane Season",
                "months": pattern["hurricane_season"],
                "risk_type": "Hurricane/Tropical Storms",
                "mitigation": "Plan interior work, secure materials and equipment"
            })
        
        # Winter weather
        if "winter_months" in pattern:
            high_risk_periods.append({
                "period": "Winter Weather",
                "months": pattern["winter_months"],
                "risk_type": "Snow/Ice/Freezing",
                "mitigation": "Focus on interior trades, heated enclosures"
            })
        
        return high_risk_periods

# ============================================================================
# V1 CORE SIMULATOR (PRESERVED)
# ============================================================================

class ConstructionScenarioSimulator:
    """V1 Core Monte Carlo simulation engine - preserved exactly"""
    
    def __init__(self, task_templates: Optional[Dict[str, TaskTemplate]] = None):
        self.task_templates = task_templates or self._initialize_task_templates()
        self.delay_factors = self._initialize_delay_factors()
        self.seasonal_multipliers = self._initialize_seasonal_patterns()
        self.holiday_calendar = self._initialize_holidays()
    
    def _initialize_task_templates(self) -> Dict[str, TaskTemplate]:
        """V1 task templates - preserved exactly"""
        return {
            'site_prep': TaskTemplate(
                name='Site Preparation',
                base_duration=5, min_duration=3, max_duration=8,
                dependencies=[], weather_sensitive=True, crew_required=3,
                cost=25000, delay_probability=0.2, critical_path=True
            ),
            'excavation': TaskTemplate(
                name='Excavation',
                base_duration=7, min_duration=5, max_duration=12,
                dependencies=['Site Preparation'], weather_sensitive=True, crew_required=4,
                cost=45000, delay_probability=0.3, critical_path=True
            ),
            'foundation': TaskTemplate(
                name='Foundation',
                base_duration=10, min_duration=8, max_duration=15,
                dependencies=['Excavation'], weather_sensitive=True, crew_required=6,
                cost=85000, delay_probability=0.25, critical_path=True
            ),
            'framing': TaskTemplate(
                name='Framing',
                base_duration=20, min_duration=15, max_duration=28,
                dependencies=['Foundation'], weather_sensitive=False, crew_required=8,
                cost=120000, delay_probability=0.15, critical_path=True
            ),
            'roofing': TaskTemplate(
                name='Roofing',
                base_duration=8, min_duration=6, max_duration=12,
                dependencies=['Framing'], weather_sensitive=True, crew_required=4,
                cost=65000, delay_probability=0.35, critical_path=False
            ),
            'mep_rough': TaskTemplate(
                name='MEP Rough-In',
                base_duration=15, min_duration=12, max_duration=20,
                dependencies=['Framing'], weather_sensitive=False, crew_required=6,
                cost=95000, delay_probability=0.2, critical_path=False
            ),
            'drywall': TaskTemplate(
                name='Drywall',
                base_duration=12, min_duration=10, max_duration=16,
                dependencies=['MEP Rough-In'], weather_sensitive=False, crew_required=5,
                cost=55000, delay_probability=0.1, critical_path=True
            ),
            'finishes': TaskTemplate(
                name='Finishes',
                base_duration=18, min_duration=15, max_duration=25,
                dependencies=['Drywall'], weather_sensitive=False, crew_required=7,
                cost=110000, delay_probability=0.2, critical_path=True
            ),
        }
    
    def _initialize_delay_factors(self) -> Dict[str, Dict]:
        """V1 delay factors - preserved exactly"""
        return {
            'weather': {
                'extreme_weather_prob': 0.1,
                'extreme_weather_delay': (3, 7)
            },
            'supply_chain': {
                'material_delay_prob': 0.15,
                'material_delay_range': (2, 14),
                'price_increase_prob': 0.08,
                'price_increase_range': (0.05, 0.25)
            },
            'labor': {
                'shortage_prob': 0.12,
                'shortage_delay_range': (1, 5),
                'productivity_variance': (0.8, 1.2)
            },
            'permits': {
                'delay_prob': 0.2,
                'delay_range': (1, 21),
                'inspection_fail_prob': 0.05,
                'reinspection_delay': (2, 5)
            }
        }
    
    def _initialize_seasonal_patterns(self) -> Dict[int, float]:
        """V1 seasonal patterns - preserved exactly"""
        return {
            1: 0.85, 2: 0.88, 3: 0.92, 4: 0.95, 5: 1.08, 6: 1.12,
            7: 1.15, 8: 1.12, 9: 1.08, 10: 1.02, 11: 0.95, 12: 0.88
        }
    
    def _initialize_holidays(self) -> List[str]:
        """V1 holidays - preserved exactly"""
        return ['01-01', '05-30', '07-04', '09-05', '11-24', '12-25']
    
    def run_monte_carlo_simulation(self, params: SimulationParameters, num_scenarios: int = 1000) -> Dict:
        """V1 Monte Carlo simulation - preserved exactly"""
        scenarios = list(range(num_scenarios))
        max_workers = min(32, max(4, (os.cpu_count() or 4) * 2))
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as ex:
            results = list(ex.map(lambda sid: self.run_single_scenario(params, sid), scenarios))
        return self._analyze_simulation_results(results, params)
    
    def run_single_scenario(self, params: SimulationParameters, scenario_id: int) -> Dict:
        """V1 single scenario runner - implementation preserved"""
        np.random.seed(scenario_id)
        scenario_result = {
            'scenario_id': scenario_id,
            'total_duration': 0,
            'total_cost': 0,
            'delay_events': [],
            'critical_path_changes': 0,
            'weather_delays': 0,
            'supply_chain_delays': 0,
            'permit_delays': 0,
            'tasks': []
        }
        
        # Implementation details preserved from V1
        name_to_template = {t.name: t for t in self.task_templates.values()}
        ordered_names = self._order_tasks_by_dependencies(list(name_to_template.keys()), name_to_template)
        
        current_date = params.start_date
        tasks_done = []
        
        for task_name in ordered_names:
            template = name_to_template[task_name]
            
            if template.dependencies:
                max_dep_end = params.start_date
                for dep in template.dependencies:
                    dep_end = self._get_task_end_date(tasks_done, dep)
                    if dep_end and dep_end > max_dep_end:
                        max_dep_end = dep_end
                current_date = max(current_date, max_dep_end)
            
            task_result = self._simulate_task_execution(template, current_date, params, scenario_id)
            tasks_done.append(task_result)
            scenario_result['tasks'].append(task_result)
            scenario_result['total_cost'] += task_result['actual_cost']
            scenario_result['total_duration'] = (task_result['end_date'] - params.start_date).days
            
            for delay in task_result['delays']:
                scenario_result['delay_events'].append(delay)
                if delay['type'] == 'weather':
                    scenario_result['weather_delays'] += delay['days']
                elif delay['type'] == 'supply_chain':
                    scenario_result['supply_chain_delays'] += delay['days']
                elif delay['type'] == 'permit':
                    scenario_result['permit_delays'] += delay['days']
            
            current_date = task_result['end_date']
        
        return scenario_result
    
    def _order_tasks_by_dependencies(self, names: List[str], name_to_template: Dict[str, TaskTemplate]) -> List[str]:
        """V1 dependency ordering - preserved exactly"""
        ordered, temp_mark, perm_mark = [], set(), set()
        
        def visit(n):
            if n in perm_mark: return
            if n in temp_mark: return
            temp_mark.add(n)
            for d in name_to_template[n].dependencies:
                if d in name_to_template:
                    visit(d)
            perm_mark.add(n)
            temp_mark.remove(n)
            ordered.append(n)
        
        for n in names:
            visit(n)
        return ordered
    
    def _simulate_task_execution(self, template: TaskTemplate, start_date: datetime,
                                params: SimulationParameters, seed: int) -> Dict:
        """V1 task execution simulation - preserved exactly with weather integration"""
        dur = np.random.triangular(template.min_duration, template.base_duration, template.max_duration)
        seasonal = self.seasonal_multipliers.get(start_date.month, 1.0)
        adjusted = dur * seasonal
        
        location_factor = self._get_location_factor(params.location)
        adjusted *= location_factor
        
        crew_eff = min(1.2, params.crew_size / max(1, template.crew_required))
        if crew_eff < 0.8:
            adjusted *= 1.25
        else:
            adjusted /= crew_eff
        
        task_delays = []
        delay_days = 0
        
        # Enhanced weather delay simulation using V2 intelligence
        if template.weather_sensitive:
            w_delay = self._simulate_enhanced_weather_delay(start_date, params, seed, template.name)
            if w_delay > 0:
                task_delays.append({
                    'type': 'weather', 
                    'days': w_delay, 
                    'description': f'Weather: {template.name}'
                })
                delay_days += w_delay
        
        # Rest of V1 delay simulation preserved
        if np.random.random() < self.delay_factors['supply_chain']['material_delay_prob']:
            s_delay = np.random.randint(*self.delay_factors['supply_chain']['material_delay_range'])
            task_delays.append({
                'type': 'supply_chain', 
                'days': s_delay, 
                'description': f'Materials: {template.name}'
            })
            delay_days += s_delay
        
        if template.name in ['Foundation', 'MEP Rough-In', 'Finishes']:
            if np.random.random() < self.delay_factors['permits']['delay_prob']:
                p_delay = np.random.randint(*self.delay_factors['permits']['delay_range'])
                task_delays.append({
                    'type': 'permit', 
                    'days': p_delay, 
                    'description': f'Permits: {template.name}'
                })
                delay_days += p_delay
        
        h_delay = self._calculate_holiday_delays(start_date, adjusted + delay_days)
        if h_delay > 0:
            task_delays.append({
                'type': 'holiday', 
                'days': h_delay, 
                'description': 'Holiday stoppage'
            })
            delay_days += h_delay
        
        total_duration = adjusted + delay_days
        end_date = start_date + timedelta(days=int(total_duration))
        
        cost_multiplier = 1.0
        if delay_days > template.base_duration * 0.2:
            cost_multiplier += 0.1
        actual_cost = template.cost * cost_multiplier
        
        return {
            'task_name': template.name,
            'start_date': start_date,
            'end_date': end_date,
            'planned_duration': template.base_duration,
            'actual_duration': float(total_duration),
            'planned_cost': template.cost,
            'actual_cost': float(actual_cost),
            'delays': task_delays,
            'critical_path': template.critical_path
        }
    
    def _simulate_enhanced_weather_delay(self, start_date: datetime, params: SimulationParameters, 
                                       seed: int, task_name: str) -> int:
        """Enhanced weather delay using V2 intelligence"""
        # Get weather intelligence for location
        weather_intel = WeatherIntelligenceEngine.get_weather_intelligence(
            params.location, start_date, 30
        )
        
        month = start_date.month
        monthly_risk = 0.3  # Default
        
        # Find risk for current month
        for monthly_data in weather_intel["monthly_risk_forecast"]:
            if monthly_data["month"] == month:
                if monthly_data["risk_category"] == "High Risk":
                    monthly_risk = 0.7
                elif monthly_data["risk_category"] == "Medium Risk":
                    monthly_risk = 0.5
                else:
                    monthly_risk = 0.3
                break
        
        # Apply weather sensitivity and task-specific factors
        adjusted_risk = monthly_risk * params.weather_sensitivity
        
        # Task-specific weather impact
        task_lower = task_name.lower()
        if any(word in task_lower for word in ['concrete', 'foundation', 'pour']):
            adjusted_risk *= 1.3  # Concrete is very weather sensitive
        elif any(word in task_lower for word in ['roofing', 'exterior']):
            adjusted_risk *= 1.2  # Roofing sensitive to wind/rain
        elif any(word in task_lower for word in ['site', 'excavation']):
            adjusted_risk *= 1.1  # Sitework sensitive to rain/mud
        
        if np.random.random() < adjusted_risk:
            return np.random.randint(1, 8)  # 1-8 day delay
        
        return 0
    
    def _get_location_factor(self, location: str) -> float:
        """V1 location factor - preserved exactly"""
        location = location.lower()
        if any(c in location for c in ['atlanta', 'dallas', 'phoenix', 'austin']): return 0.95
        if any(c in location for c in ['chicago', 'denver', 'seattle']): return 1.0
        if any(c in location for c in ['san francisco', 'new york', 'boston']): return 1.15
        return 1.0
    
    def _calculate_holiday_delays(self, start_date: datetime, duration: float) -> int:
        """V1 holiday delay calculation - preserved exactly"""
        end_date = start_date + timedelta(days=int(duration))
        holiday_days = 0
        current = start_date
        while current <= end_date:
            if current.strftime('%m-%d') in self.holiday_calendar:
                holiday_days += np.random.choice([1, 2, 3], p=[0.5, 0.3, 0.2])
            current += timedelta(days=1)
        return holiday_days
    
    def _get_task_end_date(self, tasks: List[Dict], task_name: str) -> Optional[datetime]:
        """V1 helper method - preserved exactly"""
        for t in tasks:
            if t['task_name'] == task_name:
                return t['end_date']
        return None
    
    def _analyze_simulation_results(self, results: List[Dict], params: SimulationParameters) -> Dict:
        """V1 analysis with V2 enhancements"""
        durations = [r['total_duration'] for r in results]
        costs = [r['total_cost'] for r in results]
        
        analysis = {
            'simulation_summary': {
                'scenarios_run': len(results),
                'parameters': self._params_to_dict(params)
            },
            'duration_analysis': {
                'min_duration': int(min(durations)),
                'max_duration': int(max(durations)),
                'mean_duration': float(np.mean(durations)),
                'median_duration': float(np.median(durations)),
                'std_duration': float(np.std(durations)),
                'p10_duration': float(np.percentile(durations, 10)),
                'p50_duration': float(np.percentile(durations, 50)),
                'p90_duration': float(np.percentile(durations, 90)),
            },
            'cost_analysis': {
                'min_cost': float(min(costs)),
                'max_cost': float(max(costs)),
                'mean_cost': float(np.mean(costs)),
                'median_cost': float(np.median(costs)),
                'p10_cost': float(np.percentile(costs, 10)),
                'p50_cost': float(np.percentile(costs, 50)),
                'p90_cost': float(np.percentile(costs, 90)),
            },
            'risk_analysis': self._analyze_delay_patterns(results),
            'optimization_recommendations': self._generate_recommendations(results, params),
            'scenario_percentiles': self._categorize_scenarios(results),
        }
        return analysis
    
    def _analyze_delay_patterns(self, results: List[Dict]) -> Dict:
        """V1 delay pattern analysis - preserved exactly"""
        w = [r['weather_delays'] for r in results]
        s = [r['supply_chain_delays'] for r in results]
        p = [r['permit_delays'] for r in results]
        return {
            'weather_delays': {
                'probability': float(len([d for d in w if d > 0]) / len(w)),
                'avg_when_occurs': float(np.mean([d for d in w if d > 0])) if any(w) else 0.0,
                'max_observed': int(max(w)) if len(w) else 0
            },
            'supply_chain_delays': {
                'probability': float(len([d for d in s if d > 0]) / len(s)),
                'avg_when_occurs': float(np.mean([d for d in s if d > 0])) if any(s) else 0.0,
                'max_observed': int(max(s)) if len(s) else 0
            },
            'permit_delays': {
                'probability': float(len([d for d in p if d > 0]) / len(p)),
                'avg_when_occurs': float(np.mean([d for d in p if d > 0])) if any(p) else 0.0,
                'max_observed': int(max(p)) if len(p) else 0
            }
        }
    
    def _generate_recommendations(self, results: List[Dict], params: SimulationParameters) -> List[str]:
        """V1 recommendations with V2 weather intelligence"""
        recs = []
        durations = [r['total_duration'] for r in results]
        avg_weather = float(np.mean([r['weather_delays'] for r in results]))
        
        if avg_weather > 5:
            recs.append(f"🌧️ HIGH WEATHER RISK: Average {avg_weather:.1f} weather delay days. "
                        f"Consider starting 1–2 weeks earlier or add weather buffers.")
        
        # V2 Enhanced weather recommendations using intelligence engine
        weather_intel = WeatherIntelligenceEngine.get_weather_intelligence(
            params.location, params.start_date, 180
        )
        
        for optimization in weather_intel["schedule_optimizations"]:
            recs.append(f"🌦️ WEATHER OPTIMIZATION: {optimization['recommended_action']} - "
                       f"Expected benefit: {optimization['expected_benefit']}")
        
        m = params.start_date.month
        if m in [12, 1, 2]: 
            recs.append("❄️ WINTER START: Consider a March/April start to reduce weather risk.")
        elif m in [3, 4]:   
            recs.append("🌱 MUD SEASON: Front-load indoor work during worst weeks.")
        
        median = np.median(durations)
        best = np.mean(sorted(durations)[:max(1, len(durations)//10)])
        if best < 0.9 * np.mean(durations):
            recs.append("👥 CREW OPTIMIZATION: A modest crew increase during early phases can cut duration by "
                        f"{np.mean(durations) - best:.0f} days (top decile scenarios).")
        
        if float(np.mean([r['supply_chain_delays'] for r in results])) > 3:
            recs.append("📦 SUPPLY CHAIN: Order long-lead items 2–3 weeks earlier than standard lead times.")
        
        return recs
    
    def _categorize_scenarios(self, results: List[Dict]) -> Dict:
        """V1 scenario categorization - preserved exactly"""
        s = sorted(results, key=lambda x: x['total_duration'])
        durations = [r['total_duration'] for r in results]
        costs = [r['total_cost'] for r in results]
        return {
            'best_case': {
                'duration': int(s[0]['total_duration']),
                'cost': float(s[0]['total_cost']),
                'probability': 1.0,
                'description': 'No delays, optimal conditions'
            },
            'typical_case': {
                'duration': int(np.median(durations)),
                'cost': float(np.median(costs)),
                'probability': 50.0,
                'description': 'Most likely outcome with normal variance'
            },
            'worst_case': {
                'duration': int(s[-1]['total_duration']),
                'cost': float(s[-1]['total_cost']),
                'probability': 99.0,
                'description': 'Multiple major delays'
            },
            'contingency_planning': {
                'p90_duration': float(np.percentile(durations, 90)),
                'p90_cost': float(np.percentile(costs, 90)),
                'recommendation': 'Plan contingency at P90 levels'
            }
        }
    
    def _params_to_dict(self, p: SimulationParameters) -> Dict:
        """V1 helper method - preserved exactly"""
        return {
            'location': p.location,
            'start_date': p.start_date,
            'crew_size': p.crew_size,
            'budget': p.budget,
            'project_type': p.project_type,
            'square_footage': p.square_footage,
            'weather_sensitivity': p.weather_sensitivity,
            'supply_chain_risk': p.supply_chain_risk,
            'permit_risk': p.permit_risk,
            'labor_availability': p.labor_availability
        }

# ============================================================================
# V2 SCHEDULE UPLOAD & PARSING SYSTEM
# ============================================================================

class ScheduleParser:
    """V2 Enhanced schedule parsing for P6 PDFs and various formats"""
    
    TASK_NAME_VARIATIONS = {
        'site_prep': ['site prep', 'site preparation', 'mobilization', 'laydown', 'setup'],
        'excavation': ['excavation', 'earthwork', 'grading', 'clearing', 'demo'],
        'foundation': ['foundation', 'concrete', 'footings', 'slab', 'basement'],
        'framing': ['framing', 'frame', 'structural', 'lumber', 'wood frame'],
        'roofing': ['roof', 'roofing', 'shingles', 'membrane', 'deck'],
        'mep': ['mep', 'mechanical', 'electrical', 'plumbing', 'hvac'],
        'drywall': ['drywall', 'gypsum', 'wallboard', 'interior walls'],
        'finishes': ['finish', 'flooring', 'paint', 'trim', 'final']
    }
    
    DEPENDENCY_PATTERNS = [
        r'predecessor[s]?',
        r'depends?\s*on',
        r'after',
        r'following',
        r'requires?'
    ]
    
    @classmethod
    def parse_uploaded_schedule(cls, file_content: bytes, filename: str) -> Dict[str, Any]:
        """Parse uploaded schedule file (CSV, Excel, or attempt PDF text extraction)"""
        try:
            if filename.lower().endswith('.csv'):
                return cls._parse_csv_schedule(file_content)
            elif filename.lower().endswith(('.xlsx', '.xls')):
                return cls._parse_excel_schedule(file_content)
            elif filename.lower().endswith('.pdf'):
                return cls._parse_pdf_schedule(file_content)
            else:
                raise ValueError(f"Unsupported file format: {filename}")
        
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'parsed_tasks': [],
                'warnings': []
            }
    
    @classmethod
    def _parse_csv_schedule(cls, file_content: bytes) -> Dict[str, Any]:
        """Parse CSV schedule file"""
        try:
            df = pd.read_csv(io.BytesIO(file_content))
            return cls._process_dataframe(df, 'CSV')
        except Exception as e:
            return {'success': False, 'error': f"CSV parsing failed: {str(e)}", 'parsed_tasks': [], 'warnings': []}
    
    @classmethod
    def _parse_excel_schedule(cls, file_content: bytes) -> Dict[str, Any]:
        """Parse Excel schedule file"""
        try:
            df = pd.read_excel(io.BytesIO(file_content))
            return cls._process_dataframe(df, 'Excel')
        except Exception as e:
            return {'success': False, 'error': f"Excel parsing failed: {str(e)}", 'parsed_tasks': [], 'warnings': []}
    
    @classmethod
    def _parse_pdf_schedule(cls, file_content: bytes) -> Dict[str, Any]:
        """Attempt to parse PDF schedule (basic text extraction)"""
        try:
            # Basic PDF parsing attempt - in production, would use PyPDF2 or similar
            # For now, return a placeholder structure
            return {
                'success': False,
                'error': 'PDF parsing requires additional libraries (PyPDF2, pdfplumber). Please convert to CSV/Excel.',
                'parsed_tasks': [],
                'warnings': ['PDF parsing is experimental. For best results, export to CSV or Excel format.']
            }
        except Exception as e:
            return {'success': False, 'error': f"PDF parsing failed: {str(e)}", 'parsed_tasks': [], 'warnings': []}
    
    @classmethod
    def _process_dataframe(cls, df: pd.DataFrame, source_type: str) -> Dict[str, Any]:
        """Process DataFrame to extract task information"""
        warnings = []
        parsed_tasks = []
        
        # Normalize column names
        df.columns = [col.lower().strip().replace(' ', '_') for col in df.columns]
        
        # Find required columns with fuzzy matching
        column_mapping = cls._map_columns(df.columns)
        
        if not column_mapping.get('task_name'):
            return {
                'success': False,
                'error': 'Could not identify task name column. Expected columns like: task_name, activity, description',
                'parsed_tasks': [],
                'warnings': []
            }
        
        if not column_mapping.get('duration'):
            warnings.append('Duration column not found. Using default estimates.')
        
        # Process each row
        for idx, row in df.iterrows():
            try:
                task = cls._extract_task_from_row(row, column_mapping, idx)
                if task:
                    parsed_tasks.append(task)
            except Exception as e:
                warnings.append(f"Row {idx + 1}: {str(e)}")
        
        return {
            'success': True,
            'source_type': source_type,
            'parsed_tasks': parsed_tasks,
            'warnings': warnings,
            'column_mapping': column_mapping,
            'total_tasks': len(parsed_tasks)
        }
    
    @classmethod
    def _map_columns(cls, columns: List[str]) -> Dict[str, str]:
        """Map DataFrame columns to expected fields"""
        mapping = {}
        
        # Task name mapping
        task_name_candidates = ['task_name', 'activity', 'description', 'work', 'task', 'name']
        for candidate in task_name_candidates:
            if candidate in columns:
                mapping['task_name'] = candidate
                break
        
        # Duration mapping
        duration_candidates = ['duration', 'days', 'length', 'time', 'period']
        for candidate in duration_candidates:
            if candidate in columns:
                mapping['duration'] = candidate
                break
        
        # Dependencies mapping
        dep_candidates = ['predecessor', 'depends_on', 'after', 'requirements', 'dependencies']
        for candidate in dep_candidates:
            if candidate in columns:
                mapping['dependencies'] = candidate
                break
        
        # Start/End date mapping
        start_candidates = ['start', 'start_date', 'begin', 'commence']
        for candidate in start_candidates:
            if candidate in columns:
                mapping['start_date'] = candidate
                break
        
        end_candidates = ['end', 'end_date', 'finish', 'complete']
        for candidate in end_candidates:
            if candidate in columns:
                mapping['end_date'] = candidate
                break
        
        # Cost mapping
        cost_candidates = ['cost', 'budget', 'price', 'amount', 'value']
        for candidate in cost_candidates:
            if candidate in columns:
                mapping['cost'] = candidate
                break
        
        return mapping
    
    @classmethod
    def _extract_task_from_row(cls, row: pd.Series, column_mapping: Dict[str, str], row_idx: int) -> Optional[Dict]:
        """Extract task information from a DataFrame row"""
        try:
            task_name = str(row[column_mapping['task_name']]).strip()
            if not task_name or task_name.lower() in ['nan', 'none', '']:
                return None
            
            # Extract duration
            duration = 5  # default
            if column_mapping.get('duration'):
                try:
                    duration_val = row[column_mapping['duration']]
                    if pd.notna(duration_val):
                        duration = max(1, int(float(duration_val)))
                except:
                    pass
            
            # Extract dependencies
            dependencies = []
            if column_mapping.get('dependencies'):
                dep_text = str(row[column_mapping['dependencies']])
                if dep_text and dep_text.lower() not in ['nan', 'none', '']:
                    dependencies = cls._parse_dependencies(dep_text)
            
            # Extract cost
            cost = 0.0
            if column_mapping.get('cost'):
                try:
                    cost_val = row[column_mapping['cost']]
                    if pd.notna(cost_val):
                        cost = max(0, float(str(cost_val).replace('
                , '').replace(',', '')))
                except:
                    pass
            
            # Categorize task and estimate properties
            task_category = cls._categorize_task(task_name)
            task_properties = cls._estimate_task_properties(task_name, duration, cost)
            
            return {
                'name': task_name,
                'category': task_category,
                'duration': duration,
                'dependencies': dependencies,
                'cost': cost,
                'weather_sensitive': task_properties['weather_sensitive'],
                'crew_size': task_properties['crew_size'],
                'critical_path': task_properties['critical_path'],
                'row_index': row_idx
            }
        
        except Exception as e:
            raise ValueError(f"Failed to extract task from row: {str(e)}")
    
    @classmethod
    def _parse_dependencies(cls, dep_text: str) -> List[str]:
        """Parse dependency text into list of task names"""
        if not dep_text or str(dep_text).lower() in ['nan', 'none', '']:
            return []
        
        # Split by common delimiters
        dependencies = []
        for delimiter in [',', ';', '|', '\n']:
            if delimiter in dep_text:
                parts = dep_text.split(delimiter)
                dependencies.extend([part.strip() for part in parts if part.strip()])
                break
        else:
            # No delimiter found, treat as single dependency
            dependencies = [dep_text.strip()]
        
        return [dep for dep in dependencies if dep]
    
    @classmethod
    def _categorize_task(cls, task_name: str) -> str:
        """Categorize task based on name"""
        task_lower = task_name.lower()
        
        for category, variations in cls.TASK_NAME_VARIATIONS.items():
            if any(variation in task_lower for variation in variations):
                return category.replace('_', ' ').title()
        
        # Default categorization based on common construction phases
        if any(word in task_lower for word in ['site', 'prep', 'clear']):
            return 'Sitework'
        elif any(word in task_lower for word in ['concrete', 'foundation']):
            return 'Foundation'
        elif any(word in task_lower for word in ['frame', 'structure']):
            return 'Structure'
        elif any(word in task_lower for word in ['mechanical', 'electrical', 'plumbing']):
            return 'MEP'
        elif any(word in task_lower for word in ['finish', 'interior']):
            return 'Finishes'
        else:
            return 'General'
    
    @classmethod
    def _estimate_task_properties(cls, task_name: str, duration: int, cost: float) -> Dict:
        """Estimate task properties based on name and characteristics"""
        task_lower = task_name.lower()
        
        # Weather sensitivity
        weather_sensitive = any(word in task_lower for word in [
            'site', 'excavation', 'concrete', 'foundation', 'roof', 'exterior', 'paving'
        ])
        
        # Crew size estimation
        if duration <= 3:
            crew_size = 2
        elif duration <= 7:
            crew_size = 4
        elif duration <= 14:
            crew_size = 6
        else:
            crew_size = 8
        
        # Adjust for task type
        if 'mep' in task_lower or 'electrical' in task_lower or 'plumbing' in task_lower:
            crew_size = min(crew_size, 6)
        elif 'framing' in task_lower or 'structure' in task_lower:
            crew_size = max(crew_size, 8)
        
        # Critical path estimation
        critical_path = any(word in task_lower for word in [
            'foundation', 'frame', 'structure', 'roof', 'drywall', 'final'
        ]) or duration > 10
        
        return {
            'weather_sensitive': weather_sensitive,
            'crew_size': crew_size,
            'critical_path': critical_path
        }
    
    @classmethod
    def convert_to_task_templates(cls, parsed_tasks: List[Dict]) -> Dict[str, TaskTemplate]:
        """Convert parsed tasks to TaskTemplate objects"""
        templates = {}
        
        for task in parsed_tasks:
            template_key = task['name'].lower().replace(' ', '_').replace('-', '_')
            
            # Ensure minimum and maximum durations
            base_duration = task['duration']
            min_duration = max(1, int(base_duration * 0.8))
            max_duration = max(2, int(base_duration * 1.3))
            
            # Estimate cost if not provided
            if task['cost'] <= 0:
                # Basic cost estimation based on duration and crew size
                task['cost'] = base_duration * task['crew_size'] * 800  # $800 per crew per day estimate
            
            template = TaskTemplate(
                name=task['name'],
                base_duration=base_duration,
                min_duration=min_duration,
                max_duration=max_duration,
                dependencies=task['dependencies'],
                weather_sensitive=task['weather_sensitive'],
                crew_required=task['crew_size'],
                cost=task['cost'],
                delay_probability=0.2,  # Default
                critical_path=task['critical_path']
            )
            
            templates[template_key] = template
        
        return templates

# ============================================================================
# V2 GENETIC ALGORITHM OPTIMIZER (PRESERVED FROM V1)
# ============================================================================

class GeneticScheduleOptimizer:
    """V1 GA optimizer preserved with V2 enhancements"""
    
    def __init__(self, simulator: ConstructionScenarioSimulator):
        self.simulator = simulator
    
    def optimize_schedule(self, base_params: SimulationParameters, objectives: List[str]) -> Dict:
        """V1 optimization with V2 weather intelligence"""
        population_size = 24
        generations = 20
        population = self._create_initial_population(base_params, population_size)
        
        best = None
        best_score = -1e9
        
        for generation in range(generations):
            scores = []
            for indiv in population:
                res = self.simulator.run_monte_carlo_simulation(indiv, num_scenarios=200)
                fitness = self._calculate_fitness(res, objectives, indiv)
                scores.append(fitness)
                if fitness > best_score:
                    best_score = fitness
                    best = (indiv, res)
            
            # Selection and breeding
            elite_idx = np.argsort(scores)[-max(1, population_size//3):]
            elite = [population[i] for i in elite_idx]
            
            next_pop = []
            while len(next_pop) < population_size:
                p1, p2 = random.choice(elite), random.choice(elite)
                child = self._crossover(p1, p2)
                child = self._mutate(child)
                next_pop.append(child)
            population = next_pop
        
        indiv, res = best
        return {
            'optimal_params': self.simulator._params_to_dict(indiv),
            'result_summary': res,
            'objectives': objectives,
            'fitness': float(best_score),
            'weather_optimization': self._get_weather_optimization_insights(indiv)
        }
    
    def _create_initial_population(self, base: SimulationParameters, size: int) -> List[SimulationParameters]:
        """V1 population creation with V2 weather-aware start dates"""
        pop = []
        
        # Get weather intelligence for better start date variations
        weather_intel = WeatherIntelligenceEngine.get_weather_intelligence(
            base.location, base.start_date, 180
        )
        optimal_months = weather_intel.get("optimal_start_months", [5, 6, 9, 10])
        
        for _ in range(size):
            # Weather-aware start date variations
            if random.random() < 0.3 and optimal_months:  # 30% chance to use optimal month
                target_month = random.choice(optimal_months)
                current_month = base.start_date.month
                months_diff = (target_month - current_month) % 12
                if months_diff > 6:
                    months_diff -= 12  # Go backwards if it's closer
                start_shift = months_diff * 30 + random.randint(-15, 15)
            else:
                start_shift = random.randint(-30, 45)
            
            crew = max(3, min(30, int(base.crew_size + random.randint(-3, 5))))
            
            pop.append(SimulationParameters(
                location=base.location,
                start_date=base.start_date + timedelta(days=start_shift),
                crew_size=crew,
                budget=base.budget,
                project_type=base.project_type,
                square_footage=base.square_footage,
                weather_sensitivity=base.weather_sensitivity,
                supply_chain_risk=base.supply_chain_risk,
                permit_risk=base.permit_risk,
                labor_availability=base.labor_availability
            ))
        return pop
    
    def _crossover(self, a: SimulationParameters, b: SimulationParameters) -> SimulationParameters:
        """V1 crossover - preserved exactly"""
        mid_date = a.start_date + (b.start_date - a.start_date) / 2
        crew = int((a.crew_size + b.crew_size) / 2)
        return SimulationParameters(
            location=a.location,
            start_date=mid_date,
            crew_size=crew,
            budget=a.budget,
            project_type=a.project_type,
            square_footage=a.square_footage,
            weather_sensitivity=a.weather_sensitivity,
            supply_chain_risk=a.supply_chain_risk,
            permit_risk=a.permit_risk,
            labor_availability=a.labor_availability
        )
    
    def _mutate(self, indiv: SimulationParameters) -> SimulationParameters:
        """V1 mutation - preserved exactly"""
        if random.random() < 0.5:
            indiv = SimulationParameters(
                **{**self.simulator._params_to_dict(indiv), 'crew_size': max(3, indiv.crew_size + random.randint(-2, 3))}
            )
        if random.random() < 0.5:
            shift = random.randint(-10, 10)
            indiv = SimulationParameters(
                **{**self.simulator._params_to_dict(indiv), 'start_date': indiv.start_date + timedelta(days=shift)}
            )
        return indiv
    
    def _calculate_fitness(self, result: Dict, objectives: List[str], params: SimulationParameters) -> float:
        """Enhanced fitness calculation with weather optimization bonus"""
        dur = result['duration_analysis']
        cost = result['cost_analysis']
        duration_score = 1.0 / max(1.0, dur['mean_duration'])
        cost_score = 1.0 / max(1.0, cost['mean_cost'])
        risk_score = 1.0 / max(0.1, dur['std_duration'])
        
        # Weather optimization bonus
        weather_bonus = self._calculate_weather_bonus(params)
        
        if 'minimize_duration' in objectives:
            return 0.5 * duration_score + 0.3 * cost_score + 0.15 * risk_score + 0.05 * weather_bonus
        if 'minimize_cost' in objectives:
            return 0.3 * duration_score + 0.5 * cost_score + 0.15 * risk_score + 0.05 * weather_bonus
        # minimize_risk default
        return 0.2 * duration_score + 0.3 * cost_score + 0.45 * risk_score + 0.05 * weather_bonus
    
    def _calculate_weather_bonus(self, params: SimulationParameters) -> float:
        """Calculate bonus for weather-optimized timing"""
        try:
            weather_intel = WeatherIntelligenceEngine.get_weather_intelligence(
                params.location, params.start_date, 90
            )
            
            start_month = params.start_date.month
            optimal_months = weather_intel.get("optimal_start_months", [])
            
            if start_month in optimal_months:
                return 1.0  # Maximum bonus
            else:
                # Partial bonus based on seasonal insights
                seasonal_score = weather_intel.get("seasonal_insights", {}).get("weather_risk_score", 0.5)
                return max(0.0, 1.0 - seasonal_score)
        except:
            return 0.5  # Default neutral bonus
    
    def _get_weather_optimization_insights(self, params: SimulationParameters) -> Dict:
        """Get weather optimization insights for optimized parameters"""
        try:
            return WeatherIntelligenceEngine.get_weather_intelligence(
                params.location, params.start_date, 180
            )
        except:
            return {}

# ============================================================================
# V2 PORTFOLIO OPTIMIZATION (PRESERVED FROM V1)
# ============================================================================

def portfolio_optimize(projects: List[SimulationParameters], total_crew_cap: int) -> Dict:
    """V1 portfolio optimization - preserved exactly"""
    sim = ConstructionScenarioSimulator()
    base_runs = [(p, sim.run_monte_carlo_simulation(p, 200)) for p in projects]
    
    deltas = []
    for p, res in base_runs:
        p_boost = SimulationParameters(
            **{**sim._params_to_dict(p), 'crew_size': p.crew_size + 2}
        )
        res2 = sim.run_monte_carlo_simulation(p_boost, 200)
        gain = res['duration_analysis']['mean_duration'] - res2['duration_analysis']['mean_duration']
        deltas.append((p, res, gain))
    
    deltas.sort(key=lambda x: x[2], reverse=True)
    
    remaining = max(0, total_crew_cap - sum(p.crew_size for p in projects))
    allocations = []
    for p, res, gain in deltas:
        add = min(remaining, 2) if gain > 0 else 0
        remaining -= add
        allocations.append({
            'project': sim._params_to_dict(p), 
            'add_crew': add, 
            'expected_days_saved': float(max(0, gain))
        })
    
    return {'allocations': allocations, 'crew_unassigned': remaining}

# ============================================================================
# V2 ENHANCED UI COMPONENTS
# ============================================================================

def create_sidebar_config() -> Tuple[SimulationParameters, ProjectParameters]:
    """Enhanced sidebar with both V1 and V2 parameters"""
    with st.sidebar:
        st.markdown('<div class="category-header">🔧 Project Configuration</div>', unsafe_allow_html=True)
        
        # Basic Project Information
        with st.expander("📋 Basic Information", expanded=True):
            project_name = st.text_input("Project Name", "New Office Building")
            
            project_type = st.selectbox("Project Type", [
                "Office Building", "Retail Store", "Warehouse", 
                "Apartment Complex", "Mixed Use", "Industrial"
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
        
        # Create both parameter objects
        v1_params = SimulationParameters(
            location=location,
            start_date=datetime.combine(start_date, datetime.min.time()),
            crew_size=base_crew_size,
            budget=float(budget),
            project_type=project_type,
            square_footage=square_footage,
            weather_sensitivity=weather_sensitivity,
            supply_chain_risk=supply_chain_risk,
            permit_risk=permit_complexity,
            labor_availability=labor_availability
        )
        
        v2_params = ProjectParameters(
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
        
        return v1_params, v2_params

def create_weather_intelligence_dashboard(v2_params: ProjectParameters):
    """V2 Weather Intelligence Dashboard - Key Feature"""
    st.markdown('<div class="category-header">🌦️ Weather Intelligence Dashboard</div>', unsafe_allow_html=True)
    
    # Get weather intelligence
    weather_intel = WeatherIntelligenceEngine.get_weather_intelligence(
        v2_params.location, v2_params.start_date, 180
    )
    
    # Weather Risk Overview
    col1, col2, col3 = st.columns(3)
    
    with col1:
        seasonal_insights = weather_intel["seasonal_insights"]
        risk_score = seasonal_insights["weather_risk_score"]
        risk_level = "High" if risk_score > 0.7 else "Medium" if risk_score > 0.4 else "Low"
        
        st.metric(
            "Weather Risk Score",
            f"{risk_score:.2f}",
            delta=f"{risk_level} Risk",
            delta_color="inverse"
        )
    
    with col2:
        optimal_months = weather_intel["optimal_start_months"]
        current_month = v2_params.start_date.month
        is_optimal = current_month in optimal_months
        
        st.metric(
            "Start Timing",
            "Optimal" if is_optimal else "Sub-optimal",
            delta="Good timing" if is_optimal else "Consider delay",
            delta_color="normal" if is_optimal else "inverse"
        )
    
    with col3:
        high_risk_periods = len(weather_intel["high_risk_periods"])
        st.metric(
            "Risk Periods",
            f"{high_risk_periods} identified",
            help="Number of high-risk weather periods during project"
        )
    
    # Monthly Risk Forecast Chart
    st.subheader("📅 Monthly Risk Forecast")
    
    monthly_data = weather_intel["monthly_risk_forecast"]
    months = [data["month_name"] for data in monthly_data]
    risk_levels = [data["risk_level"] for data in monthly_data]
    risk_categories = [data["risk_category"] for data in monthly_data]
    
    fig = go.Figure()
    
    # Color mapping for risk levels
    colors = []
    for category in risk_categories:
        if category == "High Risk":
            colors.append('#ff6b35')
        elif category == "Medium Risk":
            colors.append('#ffa726')
        else:
            colors.append('#4ecdc4')
    
    fig.add_trace(go.Bar(
        x=months,
        y=risk_levels,
        marker_color=colors,
        text=risk_categories,
        textposition='auto',
        name='Weather Risk'
    ))
    
    # Highlight project start month
    start_month_name = v2_params.start_date.strftime("%B")
    if start_month_name in months:
        start_idx = months.index(start_month_name)
        fig.add_vline(
            x=start_idx,
            line_dash="dash",
            line_color="red",
            annotation_text="Project Start"
        )
    
    fig.update_layout(
        title=f"Weather Risk Profile - {v2_params.location}",
        xaxis_title="Month",
        yaxis_title="Risk Level (0-1)",
        height=400,
        showlegend=False
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Weather Optimization Recommendations
    if weather_intel["schedule_optimizations"]:
        st.subheader("⚡ Weather Optimization Opportunities")
        
        for opt in weather_intel["schedule_optimizations"]:
            st.markdown(f"""
            <div class="weather-alert">
                <h4>{opt['type']}</h4>
                <p><strong>Current Risk:</strong> {opt['current_risk']}</p>
                <p><strong>Recommendation:</strong> {opt['recommended_action']}</p>
                <p><strong>Expected Benefit:</strong> {opt['expected_benefit']}</p>
                <p><strong>Trade-off:</strong> {opt['trade_off']}</p>
            </div>
            """, unsafe_allow_html=True)
    
    # High Risk Periods Detail
    if weather_intel["high_risk_periods"]:
        with st.expander("🌪️ Detailed Risk Periods"):
            for period in weather_intel["high_risk_periods"]:
                st.write(f"**{period['period']}** ({period['risk_type']})")
                st.write(f"Months: {', '.join([str(m) for m in period['months']])}")
                st.write(f"Mitigation: {period['mitigation']}")
                st.write("---")

def create_schedule_upload_section():
    """V2 Schedule Upload & Parsing Section"""
    st.markdown('<div class="category-header">📄 Schedule Upload & Analysis</div>', unsafe_allow_html=True)
    
    st.write("""
    Upload your existing project schedule in CSV, Excel, or PDF format. 
    The system will intelligently parse tasks, dependencies, and durations.
    """)
    
    # File upload
    uploaded_file = st.file_uploader(
        "Choose Schedule File",
        type=['csv', 'xlsx', 'xls', 'pdf'],
        help="Supports CSV, Excel, and PDF formats. For P6 schedules, export to CSV/Excel for best results."
    )
    
    if uploaded_file is not None:
        with st.spinner("🔄 Parsing schedule file..."):
            file_content = uploaded_file.read()
            parsed_result = ScheduleParser.parse_uploaded_schedule(file_content, uploaded_file.name)
        
        if parsed_result['success']:
            st.success(f"✅ Successfully parsed {parsed_result['total_tasks']} tasks from {parsed_result['source_type']} file!")
            
            # Display warnings if any
            if parsed_result['warnings']:
                with st.expander("⚠️ Parsing Warnings"):
                    for warning in parsed_result['warnings']:
                        st.warning(warning)
            
            # Show parsed tasks preview
            st.subheader("📋 Parsed Tasks Preview")
            
            tasks_df = pd.DataFrame(parsed_result['parsed_tasks'])
            if not tasks_df.empty:
                # Display first 10 tasks
                display_cols = ['name', 'category', 'duration', 'dependencies', 'cost', 'weather_sensitive']
                available_cols = [col for col in display_cols if col in tasks_df.columns]
                st.dataframe(tasks_df[available_cols].head(10), use_container_width=True)
                
                if len(tasks_df) > 10:
                    st.caption(f"... and {len(tasks_df) - 10} more tasks")
            
            # Convert to task templates and run simulation
            if st.button("🚀 Run Analysis with Uploaded Schedule", type="primary"):
                with st.spinner("Converting schedule to simulation templates..."):
                    task_templates = ScheduleParser.convert_to_task_templates(parsed_result['parsed_tasks'])
                
                st.success(f"✅ Created {len(task_templates)} task templates!")
                
                # Store in session state for use in simulation
                st.session_state['custom_templates'] = task_templates
                st.session_state['custom_schedule_loaded'] = True
                
                st.info("📊 Custom schedule loaded! Use the 'Run Analysis' button in other sections to simulate with your schedule.")
            
            # Show column mapping for transparency
            with st.expander("🔍 Column Mapping Details"):
                mapping_df = pd.DataFrame([
                    {"Expected Field": k, "Mapped Column": v} 
                    for k, v in parsed_result['column_mapping'].items()
                ])
                st.dataframe(mapping_df, use_container_width=True, hide_index=True)
        
        else:
            st.error(f"❌ Failed to parse schedule: {parsed_result['error']}")
            
            if 'pdf' in uploaded_file.name.lower():
                st.info("""
                💡 **PDF Parsing Tip:** For best results with P6 Primavera schedules:
                1. Export your P6 schedule to CSV or Excel format
                2. Include columns: Task Name, Duration, Predecessors, Cost (optional)
                3. Upload the exported file here
                """)

def run_v1_analysis(v1_params: SimulationParameters, num_scenarios: int = 1000):
    """Run V1 Core Analysis"""
    with st.spinner(f"🔄 Running V1 Monte Carlo Analysis ({num_scenarios:,} scenarios)..."):
        # Use custom templates if available
        if st.session_state.get('custom_schedule_loaded', False):
            custom_templates = st.session_state.get('custom_templates', {})
            simulator = ConstructionScenarioSimulator(task_templates=custom_templates)
        else:
            simulator = ConstructionScenarioSimulator()
        
        results = simulator.run_monte_carlo_simulation(v1_params, num_scenarios)
    
    st.success(f"✅ Analysis complete! Processed {num_scenarios:,} scenarios.")
    return results

def display_v1_results(results: Dict, v1_params: SimulationParameters):
    """Enhanced V1 Results Display"""
    st.markdown('<div class="category-header">📊 Core Analysis Results</div>', unsafe_allow_html=True)
    
    analysis = results
    
    # Key Metrics Overview
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Median Duration",
            f"{analysis['duration_analysis']['median_duration']:.0f} days",
            f"±{analysis['duration_analysis']['std_duration']:.0f} std"
        )
    
    with col2:
        st.metric(
            "Median Cost", 
            f"${analysis['cost_analysis']['median_cost']/1000000:.1f}M",
            f"${(analysis['cost_analysis']['median_cost'] - v1_params.budget)/1000000:+.1f}M"
        )
    
    with col3:
        on_time_prob = len([d for d in [analysis['duration_analysis']['median_duration']] if d <= analysis['duration_analysis']['median_duration']]) / 1
        st.metric(
            "Schedule Confidence",
            f"{min(100, max(0, (1.0 - analysis['duration_analysis']['std_duration']/analysis['duration_analysis']['mean_duration']) * 100)):.0f}%",
            help="Confidence in meeting median duration"
        )
    
    with col4:
        weather_impact = analysis['risk_analysis']['weather_delays']['avg_when_occurs']
        st.metric(
            "Weather Impact",
            f"{weather_impact:.1f} days avg",
            help="Average weather delays when they occur"
        )
    
    # Duration Distribution Chart
    st.subheader("📈 Duration Distribution")
    
    # Create synthetic distribution for visualization
    mean_dur = analysis['duration_analysis']['mean_duration']
    std_dur = analysis['duration_analysis']['std_duration']
    min_dur = analysis['duration_analysis']['min_duration']
    max_dur = analysis['duration_analysis']['max_duration']
    
    x_values = np.linspace(min_dur, max_dur, 100)
    y_values = np.exp(-0.5 * ((x_values - mean_dur) / max(std_dur, 1)) ** 2)
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=x_values, y=y_values,
        mode='lines', name='Duration Distribution',
        fill='tonexty', fillcolor='rgba(56, 142, 255, 0.3)',
        line=dict(color='rgb(56, 142, 255)', width=3)
    ))
    
    # Add percentile markers
    percentiles = {'P10': analysis['duration_analysis']['p10_duration'],
                   'P50': analysis['duration_analysis']['p50_duration'],
                   'P90': analysis['duration_analysis']['p90_duration']}
    
    for label, value in percentiles.items():
        fig.add_vline(
            x=value, line_dash="dash",
            annotation_text=f"{label}: {value:.0f}d",
            annotation_position="top"
        )
    
    fig.update_layout(
        title="Project Duration Probability Distribution",
        xaxis_title="Duration (Days)",
        yaxis_title="Probability Density",
        height=400,
        showlegend=False
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Risk Analysis
    st.subheader("⚠️ Risk Breakdown")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Risk categories chart
        risk_data = analysis['risk_analysis']
        categories = ['Weather', 'Supply Chain', 'Permits']
        probabilities = [
            risk_data['weather_delays']['probability'] * 100,
            risk_data['supply_chain_delays']['probability'] * 100,
            risk_data['permit_delays']['probability'] * 100
        ]
        
        fig = go.Figure(data=go.Bar(
            x=categories,
            y=probabilities,
            marker_color=['#1f77b4', '#ff7f0e', '#2ca02c'],
            text=[f"{p:.1f}%" for p in probabilities],
            textposition='auto'
        ))
        
        fig.update_layout(
            title="Delay Probability by Category",
            yaxis_title="Probability (%)",
            height=350
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Risk metrics table
        st.write("**Risk Metrics Summary**")
        
        risk_summary = []
        for risk_type, data in risk_data.items():
            if isinstance(data, dict) and 'probability' in data:
                risk_summary.append({
                    'Risk Type': risk_type.replace('_', ' ').title(),
                    'Probability': f"{data['probability']:.1%}",
                    'Avg Impact': f"{data['avg_when_occurs']:.1f} days",
                    'Max Observed': f"{data['max_observed']} days"
                })
        
        if risk_summary:
            st.dataframe(pd.DataFrame(risk_summary), use_container_width=True, hide_index=True)
    
    # Optimization Recommendations
    st.subheader("💡 Optimization Recommendations")
    
    recommendations = analysis.get('optimization_recommendations', [])
    if recommendations:
        for i, rec in enumerate(recommendations):
            if any(emoji in rec for emoji in ['🌧️', '❄️', '🌦️']):
                st.warning(f"**Weather Risk:** {rec}")
            elif any(emoji in rec for emoji in ['💰', '👥', '📦']):
                st.info(f"**Opportunity:** {rec}")
            else:
                st.success(f"**Insight:** {rec}")
    else:
        st.info("No specific recommendations generated for this scenario.")
    
    # Detailed Results Expander
    with st.expander("📋 Detailed Analysis Results"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Duration Analysis**")
            dur_data = analysis['duration_analysis']
            for key, value in dur_data.items():
                if isinstance(value, (int, float)):
                    st.write(f"- {key.replace('_', ' ').title()}: {value:.1f}")
        
        with col2:
            st.write("**Cost Analysis**") 
            cost_data = analysis['cost_analysis']
            for key, value in cost_data.items():
                if isinstance(value, (int, float)):
                    st.write(f"- {key.replace('_', ' ').title()}: ${value:,.0f}")
    
    return results

def create_v2_optimization_section(v1_params: SimulationParameters, v2_params: ProjectParameters):
    """V2 Advanced Optimization Section"""
    st.markdown('<div class="category-header">🧬 AI-Powered Optimization</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Optimization Objectives**")
        minimize_time = st.checkbox("⏱️ Minimize Duration", value=True)
        minimize_cost = st.checkbox("💰 Minimize Cost", value=False)
        minimize_risk = st.checkbox("⚠️ Minimize Risk", value=True)
        weather_optimize = st.checkbox("🌦️ Weather Optimization", value=True, 
                                     help="Use weather intelligence for timing optimization")
    
    with col2:
        st.write("**Optimization Parameters**")
        max_iterations = st.selectbox("Analysis Depth", [
            ("Quick", 10), ("Standard", 20), ("Deep", 30)
        ], format_func=lambda x: f"{x[0]} ({x[1]} iterations)")
        
        crew_flexibility = st.slider("Crew Size Flexibility (%)", 0, 50, 20)
        schedule_flexibility = st.slider("Start Date Flexibility (days)", 0, 90, 30)
    
    if st.button("🎯 Run AI Optimization", type="primary"):
        objectives = []
        if minimize_time: objectives.append('minimize_duration')
        if minimize_cost: objectives.append('minimize_cost') 
        if minimize_risk: objectives.append('minimize_risk')
        
        if not objectives:
            st.warning("Please select at least one optimization objective.")
            return
        
        with st.spinner("🤖 Running genetic algorithm optimization..."):
            # Use custom templates if available
            if st.session_state.get('custom_schedule_loaded', False):
                custom_templates = st.session_state.get('custom_templates', {})
                simulator = ConstructionScenarioSimulator(task_templates=custom_templates)
            else:
                simulator = ConstructionScenarioSimulator()
            
            ga_optimizer = GeneticScheduleOptimizer(simulator)
            optimization_result = ga_optimizer.optimize_schedule(v1_params, objectives)
        
        st.success("✅ AI optimization complete!")
        
        # Display optimization results
        st.subheader("🎯 Optimized Configuration")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Original Parameters:**")
            st.write(f"• Crew Size: {v1_params.crew_size}")
            st.write(f"• Start Date: {v1_params.start_date.strftime('%Y-%m-%d')}")
            st.write(f"• Weather Sensitivity: {v1_params.weather_sensitivity:.1f}")
        
        with col2:
            optimal = optimization_result['optimal_params']
            st.write("**Optimized Parameters:**")
            st.write(f"• Crew Size: {optimal['crew_size']}")
            st.write(f"• Start Date: {optimal['start_date'][:10] if isinstance(optimal['start_date'], str) else optimal['start_date'].strftime('%Y-%m-%d')}")
            st.write(f"• Weather Sensitivity: {optimal.get('weather_sensitivity', v1_params.weather_sensitivity):.1f}")
        
        # Performance metrics
        col1, col2, col3 = st.columns(3)
        
        original_duration = optimization_result['result_summary']['duration_analysis']['mean_duration']
        col1.metric("Fitness Score", f"{optimization_result['fitness']:.3f}")
        col2.metric("Est. Duration", f"{original_duration:.0f} days")
        
        # Weather optimization insights
        if weather_optimize and 'weather_optimization' in optimization_result:
            weather_insights = optimization_result['weather_optimization']
            if weather_insights:
                st.subheader("🌦️ Weather Optimization Insights")
                
                seasonal_insights = weather_insights.get('seasonal_insights', {})
                if seasonal_insights:
                    risk_score = seasonal_insights.get('weather_risk_score', 0.5)
                    st.metric("Weather Risk Score", f"{risk_score:.2f}", 
                             delta="Optimized timing" if risk_score < 0.5 else "Consider further adjustment")
                
                # Show optimization recommendations
                optimizations = weather_insights.get('schedule_optimizations', [])
                for opt in optimizations:
                    st.info(f"⚡ **{opt.get('type', 'Optimization')}:** {opt.get('recommended_action', 'No specific action')}")

def create_portfolio_section(v1_params: SimulationParameters):
    """V2 Portfolio Management Section"""
    st.markdown('<div class="category-header">📦 Multi-Project Portfolio</div>', unsafe_allow_html=True)
    
    st.write("Optimize crew allocation across multiple concurrent projects.")
    
    # Portfolio configuration
    num_projects = st.slider("Number of Projects", 2, 5, 3)
    total_crew_capacity = st.number_input("Total Available Crew", 20, 150, 60, 5)
    
    projects = []
    cols = st.columns(min(num_projects, 3))
    
    for i in range(num_projects):
        col_idx = i % 3
        with cols[col_idx]:
            st.subheader(f"Project {i+1}")
            
            proj_location = st.selectbox(f"Location {i+1}", [
                "Atlanta, GA", "Dallas, TX", "Phoenix, AZ", "Chicago, IL",
                "Denver, CO", "Seattle, WA", "San Francisco, CA"
            ], key=f"proj_loc_{i}")
            
            proj_start = st.date_input(f"Start Date {i+1}", 
                datetime.now().date() + timedelta(days=i*30), key=f"proj_start_{i}")
            
            proj_crew = st.slider(f"Base Crew {i+1}", 5, 25, 10, key=f"proj_crew_{i}")
            
            proj_budget = st.number_input(f"Budget ($) {i+1}", 500000, 10000000, 
                1500000 + (i * 200000), 100000, key=f"proj_budget_{i}", format="%d")
            
            proj_sqft = st.number_input(f"Sq Ft {i+1}", 5000, 100000, 
                20000 + (i * 5000), 1000, key=f"proj_sqft_{i}", format="%d")
            
            projects.append(SimulationParameters(
                location=proj_location,
                start_date=datetime.combine(proj_start, datetime.min.time()),
                crew_size=proj_crew,
                budget=float(proj_budget),
                project_type="Office Building",
                square_footage=proj_sqft,
                weather_sensitivity=v1_params.weather_sensitivity,
                supply_chain_risk=v1_params.supply_chain_risk,
                permit_risk=v1_params.permit_risk,
                labor_availability=v1_params.labor_availability
            ))
    
    if st.button("🎯 Optimize Portfolio", type="primary"):
        with st.spinner("Optimizing crew allocation across projects..."):
            portfolio_result = portfolio_optimize(projects, total_crew_capacity)
        
        st.success("✅ Portfolio optimization complete!")
        
        # Display results
        st.subheader("📊 Optimized Crew Allocation")
        
        for i, allocation in enumerate(portfolio_result['allocations']):
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                st.write(f"**Project {i+1}:** {allocation['project']['location']}")
            with col2:
                st.metric("Added Crew", allocation['add_crew'])
            with col3:
                st.metric("Days Saved", f"{allocation['expected_days_saved']:.1f}")
        
        if portfolio_result['crew_unassigned'] > 0:
            st.info(f"💡 {portfolio_result['crew_unassigned']} crew members remain unassigned and available for contingency.")

def main():
    """Main V2 Application"""
    st.markdown('<h1 class="main-header">🏗️ Construction Scenario Engine V2</h1>', unsafe_allow_html=True)
    
    st.markdown("""
    **Enhanced with Weather Intelligence • Schedule Upload • AI Optimization**
    
    Preserve all V1 core functionality while adding advanced V2 features for comprehensive construction project analysis.
    """)
    
    # Initialize session state
    if 'custom_schedule_loaded' not in st.session_state:
        st.session_state.custom_schedule_loaded = False
    
    # Create sidebar configuration
    v1_params, v2_params = create_sidebar_config()
    
    # Main application tabs - organized by feature categories
    tabs = st.tabs([
        "🚦 Quick Analysis", 
        "🌦️ Weather Intelligence", 
        "📄 Schedule Upload",
        "🧬 AI Optimization",
        "📦 Portfolio Management", 
        "💰 ROI Calculator"
    ])
    
    # Tab 1: Quick Analysis (V1 Core with V2 enhancements)
    with tabs[0]:
        st.markdown('<div class="feature-card">', unsafe_allow_html=True)
        st.subheader("⚡ Progressive Project Analysis")
        st.write("Choose your analysis depth based on project stage and time available.")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.write("**🔥 Quick Preview**")
            st.write("• 500 scenarios • ~15 seconds")
            st.write("• Basic risk assessment")
            st.write("• Key recommendations")
            if st.button("Run Quick Analysis", key="quick"):
                results = run_v1_analysis(v1_params, 500)
                display_v1_results(results, v1_params)
        
        with col2:
            st.write("**🔍 Standard Analysis**")
            st.write("• 1,500 scenarios • ~30 seconds")
            st.write("• Detailed probability curves")
            st.write("• Enhanced recommendations")
            if st.button("Run Standard Analysis", key="standard"):
                results = run_v1_analysis(v1_params, 1500)
                display_v1_results(results, v1_params)
        
        with col3:
            st.write("**🚀 Comprehensive Analysis**")
            st.write("• 5,000 scenarios • ~60 seconds")
            st.write("• Full statistical analysis")
            st.write("• Advanced optimization insights")
            if st.button("Run Comprehensive Analysis", key="comprehensive"):
                results = run_v1_analysis(v1_params, 5000)
                display_v1_results(results, v1_params)
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Custom schedule indicator
        if st.session_state.get('custom_schedule_loaded', False):
            st.success("✅ Custom schedule loaded! Analyses will use your uploaded schedule.")
    
    # Tab 2: Weather Intelligence (V2 Key Feature)
    with tabs[1]:
        create_weather_intelligence_dashboard(v2_params)
    
    # Tab 3: Schedule Upload (V2 Core Feature)  
    with tabs[2]:
        create_schedule_upload_section()
    
    # Tab 4: AI Optimization (V1 + V2 Enhanced)
    with tabs[3]:
        create_v2_optimization_section(v1_params, v2_params)
    
    # Tab 5: Portfolio Management (V1 Preserved)
    with tabs[4]:
        create_portfolio_section(v1_params)
    
    # Tab 6: ROI Calculator (V1 Enhanced)
    with tabs[5]:
        st.markdown('<div class="category-header">💰 ROI Calculator & Pricing</div>', unsafe_allow_html=True)
        
        # Pricing tiers
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("""
            <div class="feature-card">
                <h3>🥉 V2 Basic</h3>
                <h2>$299/month</h2>
                <p>✅ 1,000 scenarios/month</p>
                <p>✅ Weather intelligence</p>
                <p>✅ Schedule upload</p>
                <p>✅ Basic optimization</p>
                <p>✅ Email support</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown("""
            <div class="feature-card">
                <h3>🥈 V2 Professional</h3>
                <h2>$599/month</h2>
                <p>✅ 10,000 scenarios/month</p>
                <p>✅ Advanced weather intelligence</p>
                <p>✅ AI genetic optimization</p>
                <p>✅ Portfolio analysis</p>
                <p>✅ Priority support</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown("""
            <div class="feature-card">
                <h3>🥇 V2 Enterprise</h3>
                <h2>$1,199/month</h2>
                <p>✅ Unlimited scenarios</p>
                <p>✅ Real-time optimization</p>
                <p>✅ Custom integrations</p>
                <p>✅ API access</p>
                <p>✅ Dedicated support</p>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # ROI Calculator
        st.subheader("📈 ROI Calculator")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Current Project Metrics:**")
            current_duration = st.number_input("Typical project duration (days)", 60, 500, 180)
            current_cost = st.number_input("Average project cost ($)", 500000, 50000000, 2000000, 100000)
            projects_per_year = st.number_input("Projects per year", 1, 50, 6)
            delay_frequency = st.slider("Current delay frequency (%)", 10, 80, 40)
            avg_delay_cost = st.number_input("Average delay cost per day ($)", 1000, 50000, 5000, 500)
        
        with col2:
            st.write("**Expected Improvements with V2:**")
            duration_improvement = st.slider("Duration reduction (%)", 5, 35, 20, 
                                           help="V2 weather intelligence average: 15-25%")
            cost_reduction = st.slider("Cost reduction (%)", 3, 25, 12,
                                     help="AI optimization average: 8-18%")
            delay_reduction = st.slider("Delay frequency reduction (%)", 20, 70, 45,
                                      help="Weather intelligence reduces delays significantly")
        
        # Calculate ROI
        if st.button("💰 Calculate V2 ROI", type="primary"):
            # Current annual costs
            annual_project_cost = current_cost * projects_per_year
            annual_delay_cost = (delay_frequency / 100) * projects_per_year * (current_duration * 0.2) * avg_delay_cost
            total_annual_cost = annual_project_cost + annual_delay_cost
            
            # Improved costs with V2
            improved_duration = current_duration * (1 - duration_improvement / 100)
            improved_project_cost = current_cost * (1 - cost_reduction / 100) * projects_per_year
            improved_delay_freq = delay_frequency * (1 - delay_reduction / 100)
            improved_delay_cost = (improved_delay_freq / 100) * projects_per_year * (improved_duration * 0.2) * avg_delay_cost
            total_improved_cost = improved_project_cost + improved_delay_cost
            
            # Savings calculation
            annual_savings = total_annual_cost - total_improved_cost
            monthly_savings = annual_savings / 12
            
            # Software costs (Professional tier)
            software_cost_monthly = 599
            software_cost_annual = software_cost_monthly * 12
            
            net_savings = annual_savings - software_cost_annual
            roi_percentage = (net_savings / software_cost_annual) * 100 if software_cost_annual > 0 else 0
            
            # Display results
            st.markdown('<div class="success-card">', unsafe_allow_html=True)
            st.write("### 🎯 V2 ROI Analysis Results")
            st.markdown('</div>', unsafe_allow_html=True)
            
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Annual Savings", f"${annual_savings:,.0f}")
            col2.metric("Monthly Savings", f"${monthly_savings:,.0f}")
            col3.metric("Net Annual ROI", f"${net_savings:,.0f}")
            col4.metric("ROI Percentage", f"{roi_percentage:.0f}%")
            
            # Payback period
            if monthly_savings > software_cost_monthly:
                payback_months = software_cost_annual / monthly_savings
                st.success(f"💡 **Payback Period:** {payback_months:.1f} months")
            else:
                st.warning("⚠️ Consider higher-impact parameters or different tier")
            
            # Value proposition
            st.info("""
            **🎯 V2 Value Drivers:**
            
            🌦️ **Weather Intelligence** - 25-40% reduction in weather delays through predictive scheduling
            
            📊 **Smart Schedule Upload** - Instantly analyze any P6/Excel schedule with AI task recognition
            
            🧬 **Genetic Optimization** - AI finds optimal crew sizes and start dates automatically
            
            📈 **Portfolio Management** - Optimize resource allocation across multiple projects
            
            🔄 **Real-time Updates** - Continuously optimize as project conditions change
            """)
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666; padding: 20px;'>
        <h4>🏗️ Construction Scenario Engine V2</h4>
        <p><strong>Powered by Weather Intelligence • AI Optimization • Smart Schedule Parsing</strong></p>
        <p><em>Transform your construction scheduling with predictive analytics and intelligent automation</em></p>
        <br>
        <p style='font-size: 0.9em;'>
            <strong>V1 Core Features Preserved:</strong> Monte Carlo simulation, risk analysis, scenario planning<br>
            <strong>V2 Enhanced Features:</strong> Weather intelligence, schedule upload, genetic optimization, portfolio management
        </p>
    </div>
    """, unsafe_allow_html=True)

# ============================================================================
# CACHING AND HELPER FUNCTIONS
# ============================================================================

@st.cache_data(ttl=3600)
def cached_simulation(params_json: str, num_scenarios: int, use_custom: bool = False) -> Dict:
    """Cached simulation for performance"""
    import json
    params_dict = json.loads(params_json)
    params_dict['start_date'] = datetime.fromisoformat(params_dict['start_date'])
    params = SimulationParameters(**params_dict)
    
    if use_custom and st.session_state.get('custom_schedule_loaded', False):
        custom_templates = st.session_state.get('custom_templates', {})
        simulator = ConstructionScenarioSimulator(task_templates=custom_templates)
    else:
        simulator = ConstructionScenarioSimulator()
    
    return simulator.run_monte_carlo_simulation(params, num_scenarios)

def hash_simulation_params(params: SimulationParameters) -> str:
    """Create hash for caching"""
    param_dict = {
        'location': params.location,
        'start_date': params.start_date.isoformat(),
        'crew_size': params.crew_size,
        'budget': params.budget,
        'project_type': params.project_type,
        'square_footage': params.square_footage,
        'weather_sensitivity': params.weather_sensitivity,
        'supply_chain_risk': params.supply_chain_risk,
        'permit_risk': params.permit_risk,
        'labor_availability': params.labor_availability
    }
    return json.dumps(param_dict, sort_keys=True)

# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    # CLI mode for testing
    if len(os.sys.argv) > 1 and os.sys.argv[1] == "cli":
        print("🏗️ Construction Scenario Engine V2 - CLI Mode")
        
        # Test V1 core functionality
        params = SimulationParameters(
            location="Atlanta, GA",
            start_date=datetime(2025, 6, 1),
            crew_size=12,
            budget=1500000,
            project_type="Office Building",
            square_footage=25000
        )
        
        sim = ConstructionScenarioSimulator()
        results = sim.run_monte_carlo_simulation(params, num_scenarios=500)
        
        print(f"✅ V1 Core Test Complete:")
        print(f"   Median duration: {int(results['duration_analysis']['median_duration'])} days")
        print(f"   P90 duration: {int(results['duration_analysis']['p90_duration'])} days")
        print(f"   Median cost: ${results['cost_analysis']['median_cost']:,.0f}")
        
        # Test V2 weather intelligence
        v2_params = ProjectParameters(
            location="Atlanta, GA",
            start_date=datetime(2025, 6, 1),
            base_crew_size=12
        )
        
        weather_intel = WeatherIntelligenceEngine.get_weather_intelligence(
            v2_params.location, v2_params.start_date, 180
        )
        
        print(f"\n✅ V2 Weather Intelligence Test:")
        print(f"   Risk score: {weather_intel['seasonal_insights']['weather_risk_score']:.2f}")
        print(f"   Optimal months: {weather_intel['optimal_start_months']}")
        print(f"   High risk periods: {len(weather_intel['high_risk_periods'])}")
        
        print("\n🎉 All systems operational!")
        
    else:
        # Streamlit UI mode
        main()
