# Construction Scenario Simulation Engine - V2 Implementation
import numpy as np
import pandas as pd
import random
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import List, Dict, Tuple
import concurrent.futures
from multiprocessing import Pool
import json

@dataclass
class SimulationParameters:
    """Configuration for scenario simulation"""
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
    """Template for construction tasks with uncertainty ranges"""
    name: str
    base_duration: int  # days
    min_duration: int
    max_duration: int
    dependencies: List[str]
    weather_sensitive: bool
    crew_required: int
    cost: float
    delay_probability: float
    critical_path: bool

class ConstructionScenarioSimulator:
    """
    Monte Carlo simulation engine for construction scheduling
    Runs thousands of scenarios to find optimal schedules
    """
    
    def __init__(self):
        self.task_templates = self._initialize_task_templates()
        self.delay_factors = self._initialize_delay_factors()
        self.seasonal_multipliers = self._initialize_seasonal_patterns()
        self.holiday_calendar = self._initialize_holidays()
    
    def _initialize_task_templates(self) -> Dict[str, TaskTemplate]:
        """Standard construction task templates with uncertainty ranges"""
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
                dependencies=['site_prep'], weather_sensitive=True, crew_required=4,
                cost=45000, delay_probability=0.3, critical_path=True
            ),
            'foundation': TaskTemplate(
                name='Foundation',
                base_duration=10, min_duration=8, max_duration=15,
                dependencies=['excavation'], weather_sensitive=True, crew_required=6,
                cost=85000, delay_probability=0.25, critical_path=True
            ),
            'framing': TaskTemplate(
                name='Framing',
                base_duration=20, min_duration=15, max_duration=28,
                dependencies=['foundation'], weather_sensitive=False, crew_required=8,
                cost=120000, delay_probability=0.15, critical_path=True
            ),
            'roofing': TaskTemplate(
                name='Roofing',
                base_duration=8, min_duration=6, max_duration=12,
                dependencies=['framing'], weather_sensitive=True, crew_required=4,
                cost=65000, delay_probability=0.35, critical_path=False
            ),
            'mep_rough': TaskTemplate(
                name='MEP Rough-In',
                base_duration=15, min_duration=12, max_duration=20,
                dependencies=['framing'], weather_sensitive=False, crew_required=6,
                cost=95000, delay_probability=0.2, critical_path=False
            ),
            'drywall': TaskTemplate(
                name='Drywall',
                base_duration=12, min_duration=10, max_duration=16,
                dependencies=['mep_rough'], weather_sensitive=False, crew_required=5,
                cost=55000, delay_probability=0.1, critical_path=True
            ),
            'finishes': TaskTemplate(
                name='Finishes',
                base_duration=18, min_duration=15, max_duration=25,
                dependencies=['drywall'], weather_sensitive=False, crew_required=7,
                cost=110000, delay_probability=0.2, critical_path=True
            )
        }
    
    def _initialize_delay_factors(self) -> Dict[str, Dict]:
        """Common delay factors with probability distributions"""
        return {
            'weather': {
                'winter_multiplier': 1.4,
                'spring_multiplier': 1.2,
                'summer_multiplier': 1.1,
                'fall_multiplier': 1.15,
                'extreme_weather_prob': 0.1,
                'extreme_weather_delay': (3, 7)  # days range
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
        """Seasonal productivity multipliers by month"""
        return {
            1: 0.85,   # January - winter slowdown
            2: 0.88,   # February
            3: 0.92,   # March - mud season
            4: 0.95,   # April
            5: 1.08,   # May - peak season
            6: 1.12,   # June
            7: 1.15,   # July - peak productivity
            8: 1.12,   # August
            9: 1.08,   # September
            10: 1.02,  # October
            11: 0.95,  # November - weather turning
            12: 0.88   # December - holidays
        }
    
    def _initialize_holidays(self) -> List[str]:
        """Major construction holidays (work stoppages)"""
        return [
            '01-01',  # New Year's Day
            '05-30',  # Memorial Day
            '07-04',  # Independence Day
            '09-05',  # Labor Day
            '11-24',  # Thanksgiving
            '12-25'   # Christmas
        ]
    
    def run_single_scenario(self, params: SimulationParameters, scenario_id: int) -> Dict:
        """Run a single construction scenario simulation"""
        np.random.seed(scenario_id)  # Reproducible randomness
        
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
        
        current_date = params.start_date
        completed_tasks = set()
        
        # Simulate each task
        for task_name, template in self.task_templates.items():
            # Check dependencies
            if not all(dep in completed_tasks for dep in template.dependencies):
                # Calculate dependency delay
                max_dependency_end = current_date
                for dep in template.dependencies:
                    dep_end = self._get_task_end_date(scenario_result['tasks'], dep)
                    if dep_end and dep_end > max_dependency_end:
                        max_dependency_end = dep_end
                current_date = max_dependency_end
            
            # Simulate task execution
            task_result = self._simulate_task_execution(
                template, current_date, params, scenario_id
            )
            
            scenario_result['tasks'].append(task_result)
            scenario_result['total_cost'] += task_result['actual_cost']
            scenario_result['total_duration'] = (task_result['end_date'] - params.start_date).days
            
            # Accumulate delays
            for delay in task_result['delays']:
                scenario_result['delay_events'].append(delay)
                if delay['type'] == 'weather':
                    scenario_result['weather_delays'] += delay['days']
                elif delay['type'] == 'supply_chain':
                    scenario_result['supply_chain_delays'] += delay['days']
                elif delay['type'] == 'permit':
                    scenario_result['permit_delays'] += delay['days']
            
            completed_tasks.add(task_name)
            current_date = task_result['end_date']
        
        return scenario_result
    
    def _simulate_task_execution(self, template: TaskTemplate, start_date: datetime, 
                                params: SimulationParameters, seed: int) -> Dict:
        """Simulate execution of a single task with all uncertainty factors"""
        
        # Base duration with uncertainty
        duration_uncertainty = np.random.triangular(
            template.min_duration, 
            template.base_duration, 
            template.max_duration
        )
        
        # Apply seasonal multiplier
        seasonal_factor = self.seasonal_multipliers.get(start_date.month, 1.0)
        adjusted_duration = duration_uncertainty * seasonal_factor
        
        # Apply location-specific factors
        location_factor = self._get_location_factor(params.location)
        adjusted_duration *= location_factor
        
        # Apply crew size factor
        crew_efficiency = min(1.2, params.crew_size / template.crew_required)
        if crew_efficiency < 0.8:  # Understaffed penalty
            adjusted_duration *= 1.25
        else:
            adjusted_duration /= crew_efficiency
        
        task_delays = []
        delay_days = 0
        
        # Weather delays
        if template.weather_sensitive:
            weather_delay = self._simulate_weather_delay(start_date, params, seed)
            if weather_delay > 0:
                task_delays.append({
                    'type': 'weather',
                    'days': weather_delay,
                    'description': f'Weather delay during {template.name}'
                })
                delay_days += weather_delay
        
        # Supply chain delays
        if np.random.random() < self.delay_factors['supply_chain']['material_delay_prob']:
            supply_delay = np.random.randint(*self.delay_factors['supply_chain']['material_delay_range'])
            task_delays.append({
                'type': 'supply_chain',
                'days': supply_delay,
                'description': f'Material delivery delay for {template.name}'
            })
            delay_days += supply_delay
        
        # Permit delays
        if template.name in ['Foundation', 'MEP Rough-In', 'Finishes']:
            if np.random.random() < self.delay_factors['permits']['delay_prob']:
                permit_delay = np.random.randint(*self.delay_factors['permits']['delay_range'])
                task_delays.append({
                    'type': 'permit',
                    'days': permit_delay,
                    'description': f'Permit/inspection delay for {template.name}'
                })
                delay_days += permit_delay
        
        # Holiday delays
        holiday_delay = self._calculate_holiday_delays(start_date, adjusted_duration + delay_days)
        if holiday_delay > 0:
            task_delays.append({
                'type': 'holiday',
                'days': holiday_delay,
                'description': 'Holiday work stoppage'
            })
            delay_days += holiday_delay
        
        # Calculate final dates and costs
        total_duration = adjusted_duration + delay_days
        end_date = start_date + timedelta(days=int(total_duration))
        
        # Cost adjustments for delays and efficiency
        cost_multiplier = 1.0
        if delay_days > template.base_duration * 0.2:  # If delays > 20% of base duration
            cost_multiplier += 0.1  # 10% cost overrun
        
        actual_cost = template.cost * cost_multiplier
        
        return {
            'task_name': template.name,
            'start_date': start_date,
            'end_date': end_date,
            'planned_duration': template.base_duration,
            'actual_duration': total_duration,
            'planned_cost': template.cost,
            'actual_cost': actual_cost,
            'delays': task_delays,
            'critical_path': template.critical_path
        }
    
    def _simulate_weather_delay(self, start_date: datetime, params: SimulationParameters, seed: int) -> int:
        """Simulate weather-related delays based on season and location"""
        month = start_date.month
        base_weather_prob = 0.1
        
        # Seasonal weather risk
        if month in [12, 1, 2]:  # Winter
            weather_prob = base_weather_prob * 2.0
        elif month in [3, 4]:  # Spring (mud season)
            weather_prob = base_weather_prob * 1.5
        elif month in [6, 7, 8, 9]:  # Hurricane/thunderstorm season
            weather_prob = base_weather_prob * 1.3
        else:
            weather_prob = base_weather_prob
        
        # Apply location factors
        if 'florida' in params.location.lower() or 'miami' in params.location.lower():
            weather_prob *= 1.4  # Hurricane risk
        elif 'minnesot' in params.location.lower() or 'alaska' in params.location.lower():
            weather_prob *= 1.6  # Winter weather
        elif 'arizona' in params.location.lower() or 'nevada' in params.location.lower():
            weather_prob *= 0.7  # Less weather risk
        
        if np.random.random() < weather_prob:
            return np.random.randint(*self.delay_factors['weather']['extreme_weather_delay'])
        
        return 0
    
    def _get_location_factor(self, location: str) -> float:
        """Get productivity multiplier based on location"""
        location = location.lower()
        
        # High-productivity regions
        if any(city in location for city in ['atlanta', 'dallas', 'phoenix', 'austin']):
            return 0.95  # 5% faster
        
        # Average productivity
        elif any(city in location for city in ['chicago', 'denver', 'seattle']):
            return 1.0
        
        # Lower productivity (high cost, regulations, weather)
        elif any(city in location for city in ['san francisco', 'new york', 'boston']):
            return 1.15  # 15% slower
        
        return 1.0  # Default
    
    def _calculate_holiday_delays(self, start_date: datetime, duration: float) -> int:
        """Calculate delays due to holidays during task execution"""
        end_date = start_date + timedelta(days=int(duration))
        holiday_days = 0
        
        current = start_date
        while current <= end_date:
            date_str = current.strftime('%m-%d')
            if date_str in self.holiday_calendar:
                # Add holiday + potential extended weekend
                holiday_days += np.random.choice([1, 2, 3], p=[0.5, 0.3, 0.2])
            current += timedelta(days=1)
        
        return holiday_days
    
    def _get_task_end_date(self, tasks: List[Dict], task_name: str) -> datetime:
        """Get end date of a specific task from completed tasks"""
        for task in tasks:
            if task['task_name'] == task_name:
                return task['end_date']
        return None
    
    def run_monte_carlo_simulation(self, params: SimulationParameters, 
                                  num_scenarios: int = 1000) -> Dict:
        """
        Run thousands of scenarios to find optimal scheduling strategies
        """
        print(f"Running {num_scenarios} construction scenarios...")
        
        # Run scenarios in parallel for speed
        with concurrent.futures.ProcessPoolExecutor() as executor:
            scenarios = list(range(num_scenarios))
            results = list(executor.map(
                lambda scenario_id: self.run_single_scenario(params, scenario_id),
                scenarios
            ))
        
        # Analyze results
        return self._analyze_simulation_results(results, params)
    
    def _analyze_simulation_results(self, results: List[Dict], 
                                   params: SimulationParameters) -> Dict:
        """Analyze simulation results to extract insights and recommendations"""
        
        durations = [r['total_duration'] for r in results]
        costs = [r['total_cost'] for r in results]
        
        # Statistical analysis
        analysis = {
            'simulation_summary': {
                'scenarios_run': len(results),
                'parameters': params.__dict__
            },
            'duration_analysis': {
                'min_duration': int(min(durations)),
                'max_duration': int(max(durations)),
                'mean_duration': int(np.mean(durations)),
                'median_duration': int(np.median(durations)),
                'std_duration': int(np.std(durations)),
                'p10_duration': int(np.percentile(durations, 10)),
                'p50_duration': int(np.percentile(durations, 50)),
                'p90_duration': int(np.percentile(durations, 90))
            },
            'cost_analysis': {
                'min_cost': int(min(costs)),
                'max_cost': int(max(costs)),
                'mean_cost': int(np.mean(costs)),
                'median_cost': int(np.median(costs)),
                'p10_cost': int(np.percentile(costs, 10)),
                'p50_cost': int(np.percentile(costs, 50)),
                'p90_cost': int(np.percentile(costs, 90))
            },
            'risk_analysis': self._analyze_delay_patterns(results),
            'optimization_recommendations': self._generate_recommendations(results, params),
            'scenario_percentiles': self._categorize_scenarios(results)
        }
        
        return analysis
    
    def _analyze_delay_patterns(self, results: List[Dict]) -> Dict:
        """Analyze delay patterns across all scenarios"""
        all_weather_delays = [r['weather_delays'] for r in results]
        all_supply_delays = [r['supply_chain_delays'] for r in results]
        all_permit_delays = [r['permit_delays'] for r in results]
        
        return {
            'weather_delays': {
                'probability': len([d for d in all_weather_delays if d > 0]) / len(results),
                'avg_when_occurs': np.mean([d for d in all_weather_delays if d > 0]) if any(all_weather_delays) else 0,
                'max_observed': max(all_weather_delays)
            },
            'supply_chain_delays': {
                'probability': len([d for d in all_supply_delays if d > 0]) / len(results),
                'avg_when_occurs': np.mean([d for d in all_supply_delays if d > 0]) if any(all_supply_delays) else 0,
                'max_observed': max(all_supply_delays)
            },
            'permit_delays': {
                'probability': len([d for d in all_permit_delays if d > 0]) / len(results),
                'avg_when_occurs': np.mean([d for d in all_permit_delays if d > 0]) if any(all_permit_delays) else 0,
                'max_observed': max(all_permit_delays)
            }
        }
    
    def _generate_recommendations(self, results: List[Dict], 
                                params: SimulationParameters) -> List[str]:
        """Generate actionable recommendations based on simulation results"""
        recommendations = []
        
        # Analyze best performing scenarios
        sorted_results = sorted(results, key=lambda x: x['total_duration'])
        best_10_percent = sorted_results[:len(results)//10]
        
        # Weather recommendations
        weather_delays = [r['weather_delays'] for r in results]
        avg_weather_delay = np.mean(weather_delays)
        if avg_weather_delay > 5:
            recommendations.append(
                f"🌧️ HIGH WEATHER RISK: Average {avg_weather_delay:.1f} days weather delays. "
                f"Consider starting 1-2 weeks earlier or adding weather buffers."
            )
        
        # Seasonal recommendations
        start_month = params.start_date.month
        if start_month in [12, 1, 2]:
            recommendations.append(
                "❄️ WINTER START: Consider delaying start to March-April to avoid winter weather delays."
            )
        elif start_month in [3, 4]:
            recommendations.append(
                "🌱 MUD SEASON: Schedule indoor work (MEP, drywall) during worst weather periods."
            )
        
        # Crew size optimization
        best_scenarios_avg_duration = np.mean([r['total_duration'] for r in best_10_percent])
        if best_scenarios_avg_duration < np.mean([r['total_duration'] for r in results]) * 0.9:
            recommendations.append(
                f"👥 CREW OPTIMIZATION: Increasing crew size to {params.crew_size + 2} could reduce "
                f"project duration by {np.mean([r['total_duration'] for r in results]) - best_scenarios_avg_duration:.0f} days."
            )
        
        # Supply chain recommendations
        supply_delays = [r['supply_chain_delays'] for r in results]
        if np.mean(supply_delays) > 3:
            recommendations.append(
                "📦 SUPPLY CHAIN RISK: Order materials 2-3 weeks earlier than standard lead times."
            )
        
        # Cost-time tradeoff
        cost_duration_correlation = np.corrcoef(
            [r['total_cost'] for r in results],
            [r['total_duration'] for r in results]
        )[0,1]
        
        if cost_duration_correlation < -0.3:
            recommendations.append(
                "💰 FAST-TRACK OPPORTUNITY: Spending 10-15% more on crew/equipment could "
                "significantly reduce project duration."
            )
        
        return recommendations
    
    def _categorize_scenarios(self, results: List[Dict]) -> Dict:
        """Categorize scenarios into best, worst, and typical cases"""
        sorted_by_duration = sorted(results, key=lambda x: x['total_duration'])
        
        return {
            'best_case': {
                'duration': sorted_by_duration[0]['total_duration'],
                'cost': sorted_by_duration[0]['total_cost'],
                'probability': 1.0,  # Best case scenario
                'description': 'Everything goes perfectly - no delays, optimal weather'
            },
            'typical_case': {
                'duration': sorted_by_duration[len(results)//2]['total_duration'],
                'cost': sorted_by_duration[len(results)//2]['total_cost'],
                'probability': 50.0,
                'description': 'Most likely outcome with normal delays and issues'
            },
            'worst_case': {
                'duration': sorted_by_duration[-1]['total_duration'],
                'cost': sorted_by_duration[-1]['total_cost'],
                'probability': 99.0,  # 99th percentile
                'description': 'Multiple major delays - weather, permits, supply chain'
            },
            'contingency_planning': {
                'p90_duration': int(np.percentile([r['total_duration'] for r in results], 90)),
                'p90_cost': int(np.percentile([r['total_cost'] for r in results], 90)),
                'recommendation': 'Plan for P90 scenario - 90% chance of completing within these parameters'
            }
        }

# Example usage and Streamlit integration
def create_scenario_simulation_ui():
    """Streamlit UI for the scenario simulation engine"""
    import streamlit as st
    
    st.header("🎯 Construction Scenario Simulation Engine")
    st.caption("Run thousands of scenarios to optimize your construction schedule")
    
    # Input parameters
    col1, col2 = st.columns(2)
    
    with col1:
        project_name = st.text_input("Project Name", "Office Building Project")
        location = st.selectbox("Location", [
            "Atlanta, GA", "Dallas, TX", "Phoenix, AZ", "Chicago, IL",
            "Denver, CO", "Seattle, WA", "San Francisco, CA", "New York, NY"
        ])
        start_date = st.date_input("Project Start Date", datetime.now().date())
        project_type = st.selectbox("Project Type", [
            "Office Building", "Retail", "Warehouse", "Apartment", "Mixed Use"
        ])
    
    with col2:
        crew_size = st.slider("Crew Size", 5, 20, 10)
        budget = st.number_input("Budget ($)", 100000, 50000000, 1000000, 50000)
        square_footage = st.number_input("Square Footage", 1000, 500000, 25000, 1000)
        num_scenarios = st.slider("Number of Scenarios", 100, 5000, 1000, 100)
    
    if st.button("🚀 Run Simulation", type="primary"):
        # Create simulation parameters
        params = SimulationParameters(
            location=location,
            start_date=datetime.combine(start_date, datetime.min.time()),
            crew_size=crew_size,
            budget=budget,
            project_type=project_type,
            square_footage=square_footage
        )
        
        # Run simulation
        simulator = ConstructionScenarioSimulator()
        
        with st.spinner(f"Running {num_scenarios} scenarios..."):
            results = simulator.run_monte_carlo_simulation(params, num_scenarios)
        
        # Display results
        st.success("Simulation Complete!")
        
        # Key metrics
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Best Case", f"{results['duration_analysis']['min_duration']} days")
        col2.metric("Most Likely", f"{results['duration_analysis']['median_duration']} days")
        col3.metric("Worst Case", f"{results['duration_analysis']['max_duration']} days")
        col4.metric("90% Confidence", f"{results['duration_analysis']['p90_duration']} days")
        
        # Recommendations
        st.subheader("🎯 Optimization Recommendations")
        for rec in results['optimization_recommendations']:
            if "🌧️" in rec or "❄️" in rec:
                st.warning(rec)
            elif "💰" in rec or "👥" in rec:
                st.info(rec)
            else:
                st.success(rec)
        
        # Detailed analysis
        with st.expander("📊 Detailed Analysis"):
            st.json(results)

if __name__ == "__main__":
    # Example usage
    params = SimulationParameters(
        location="Atlanta, GA",
        start_date=datetime(2025, 6, 1),
        crew_size=12,
        budget=1500000,
        project_type="Office Building",
        square_footage=25000
    )
    
    simulator = ConstructionScenarioSimulator()
    results = simulator.run_monte_carlo_simulation(params, num_scenarios=1000)
    
    print("Simulation Results:")
    print(f"Duration range: {results['duration_analysis']['min_duration']} - {results['duration_analysis']['max_duration']} days")
    print(f"Most likely duration: {results['duration_analysis']['median_duration']} days")
    print(f"90% confidence: {results['duration_analysis']['p90_duration']} days")
    print("\nRecommendations:")
    for rec in results['optimization_recommendations']:
        print(f"• {rec}")
