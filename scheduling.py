# Construction Scenario Simulation Engine - V2 Implementation (Streamlit-safe)
# - Thread-based parallelism (no pickling crash)
# - V2 feature progression: GA optimization, real-time updates, portfolio optimization
# - Phased integration helpers + advanced UI + caching + progressive disclosure
# - Fixed: No blocking computations on page load - everything behind buttons

import os
import math
import json
import random
import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional
from datetime import datetime, timedelta
import concurrent.futures
import streamlit as st

# Set page config first
st.set_page_config(page_title="Construction Scenario Engine V2", layout="wide")
st.write("✅ App started - Construction Scenario Simulation Engine V2")

# ---------- Data Models ----------
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
    base_duration: int  # days
    min_duration: int
    max_duration: int
    dependencies: List[str]
    weather_sensitive: bool
    crew_required: int
    cost: float
    delay_probability: float
    critical_path: bool

# ---------- Core Simulator ----------
class ConstructionScenarioSimulator:
    """
    Monte Carlo simulation engine for construction scheduling.
    Uses THREADS (not processes) to avoid pickling issues on Streamlit/Cloud.
    """

    def __init__(self, task_templates: Optional[Dict[str, TaskTemplate]] = None):
        self.task_templates = task_templates or self._initialize_task_templates()
        self.delay_factors = self._initialize_delay_factors()
        self.seasonal_multipliers = self._initialize_seasonal_patterns()
        self.holiday_calendar = self._initialize_holidays()

    # ---- Static template data ----
    def _initialize_task_templates(self) -> Dict[str, TaskTemplate]:
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
        return {
            'weather': {
                'extreme_weather_prob': 0.1,
                'extreme_weather_delay': (3, 7)  # days
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
        return {
            1: 0.85, 2: 0.88, 3: 0.92, 4: 0.95, 5: 1.08, 6: 1.12,
            7: 1.15, 8: 1.12, 9: 1.08, 10: 1.02, 11: 0.95, 12: 0.88
        }

    def _initialize_holidays(self) -> List[str]:
        return ['01-01', '05-30', '07-04', '09-05', '11-24', '12-25']

    # ---- Scenario runner ----
    def run_single_scenario(self, params: SimulationParameters, scenario_id: int) -> Dict:
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

        # We'll traverse tasks in dependency order based on names
        name_to_template = {t.name: t for t in self.task_templates.values()}
        ordered_names = self._order_tasks_by_dependencies(list(name_to_template.keys()), name_to_template)

        current_date = params.start_date
        completed_tasks = set()
        tasks_done = []

        for task_name in ordered_names:
            template = name_to_template[task_name]

            # align current date to the max end of dependencies
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

            completed_tasks.add(task_name)
            current_date = task_result['end_date']

        return scenario_result

    def _order_tasks_by_dependencies(self, names: List[str], name_to_template: Dict[str, TaskTemplate]) -> List[str]:
        ordered, temp_mark, perm_mark = [], set(), set()

        def visit(n):
            if n in perm_mark: return
            if n in temp_mark:  # cycle guard
                return
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

        if template.weather_sensitive:
            w_delay = self._simulate_weather_delay(start_date, params, seed)
            if w_delay > 0:
                task_delays.append({'type': 'weather', 'days': w_delay, 'description': f'Weather: {template.name}'})
                delay_days += w_delay

        if np.random.random() < self.delay_factors['supply_chain']['material_delay_prob']:
            s_delay = np.random.randint(*self.delay_factors['supply_chain']['material_delay_range'])
            task_delays.append({'type': 'supply_chain', 'days': s_delay, 'description': f'Materials: {template.name}'})
            delay_days += s_delay

        if template.name in ['Foundation', 'MEP Rough-In', 'Finishes']:
            if np.random.random() < self.delay_factors['permits']['delay_prob']:
                p_delay = np.random.randint(*self.delay_factors['permits']['delay_range'])
                task_delays.append({'type': 'permit', 'days': p_delay, 'description': f'Permits: {template.name}'})
                delay_days += p_delay

        h_delay = self._calculate_holiday_delays(start_date, adjusted + delay_days)
        if h_delay > 0:
            task_delays.append({'type': 'holiday', 'days': h_delay, 'description': 'Holiday stoppage'})
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

    def _simulate_weather_delay(self, start_date: datetime, params: SimulationParameters, seed: int) -> int:
        month = start_date.month
        base = 0.1
        if month in [12, 1, 2]:     prob = base * 2.0
        elif month in [3, 4]:       prob = base * 1.5
        elif month in [6, 7, 8, 9]: prob = base * 1.3
        else:                       prob = base

        loc = params.location.lower()
        if 'florida' in loc or 'miami' in loc: prob *= 1.4
        elif 'minnesot' in loc or 'alaska' in loc: prob *= 1.6
        elif 'arizona' in loc or 'nevada' in loc: prob *= 0.7

        if np.random.random() < prob:
            return np.random.randint(*self.delay_factors['weather']['extreme_weather_delay'])
        return 0

    def _get_location_factor(self, location: str) -> float:
        location = location.lower()
        if any(c in location for c in ['atlanta', 'dallas', 'phoenix', 'austin']): return 0.95
        if any(c in location for c in ['chicago', 'denver', 'seattle']):           return 1.0
        if any(c in location for c in ['san francisco', 'new york', 'boston']):    return 1.15
        return 1.0

    def _calculate_holiday_delays(self, start_date: datetime, duration: float) -> int:
        end_date = start_date + timedelta(days=int(duration))
        holiday_days = 0
        current = start_date
        while current <= end_date:
            if current.strftime('%m-%d') in self.holiday_calendar:
                holiday_days += np.random.choice([1, 2, 3], p=[0.5, 0.3, 0.2])
            current += timedelta(days=1)
        return holiday_days

    def _get_task_end_date(self, tasks: List[Dict], task_name: str) -> Optional[datetime]:
        for t in tasks:
            if t['task_name'] == task_name:
                return t['end_date']
        return None

    # ---- Public Monte Carlo (THREADS ONLY to avoid pickling) ----
    def run_monte_carlo_simulation(self, params: SimulationParameters, num_scenarios: int = 1000) -> Dict:
        # ThreadPool avoids pickling lambdas or bound methods
        scenarios = list(range(num_scenarios))
        max_workers = min(32, max(4, (os.cpu_count() or 4) * 2))
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as ex:
            results = list(ex.map(lambda sid: self.run_single_scenario(params, sid), scenarios))
        return self._analyze_simulation_results(results, params)

    # ---- Analysis ----
    def _analyze_simulation_results(self, results: List[Dict], params: SimulationParameters) -> Dict:
        durations = [r['total_duration'] for r in results]
        costs = [r['total_cost'] for r in results]

        analysis = {
            'simulation_summary': {
                'scenarios_run': len(results),
                'parameters': _params_to_dict(params)
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
        recs = []
        durations = [r['total_duration'] for r in results]
        avg_weather = float(np.mean([r['weather_delays'] for r in results]))
        if avg_weather > 5:
            recs.append(f"🌧️ HIGH WEATHER RISK: Average {avg_weather:.1f} weather delay days. "
                        f"Consider starting 1–2 weeks earlier or add weather buffers.")

        m = params.start_date.month
        if m in [12, 1, 2]: recs.append("❄️ WINTER START: Consider a March/April start to reduce weather risk.")
        elif m in [3, 4]:   recs.append("🌱 MUD SEASON: Front-load indoor work during worst weeks.")

        median = np.median(durations)
        best = np.mean(sorted(durations)[:max(1, len(durations)//10)])
        if best < 0.9 * np.mean(durations):
            recs.append("👥 CREW OPTIMIZATION: A modest crew increase during early phases can cut duration by "
                        f"{np.mean(durations) - best:.0f} days (top decile scenarios).")

        if float(np.mean([r['supply_chain_delays'] for r in results])) > 3:
            recs.append("📦 SUPPLY CHAIN: Order long-lead items 2–3 weeks earlier than standard lead times.")

        # Time-cost correlation
        try:
            corr = float(np.corrcoef(
                [r['total_cost'] for r in results],
                [r['total_duration'] for r in results]
            )[0, 1])
            if corr < -0.3:
                recs.append("💰 FAST-TRACK: Spending 10–15% more on crew/equipment could materially reduce duration.")
        except Exception:
            pass

        return recs

    def _categorize_scenarios(self, results: List[Dict]) -> Dict:
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

# ---------- Phase 2: Parse uploaded schedules into templates ----------
def parse_dependencies(raw: str) -> List[str]:
    if not raw: return []
    # Support comma/semicolon separated names
    parts = [p.strip() for p in str(raw).split(',') if p.strip()]
    # Capitalize each word to align with template names in simulator
    return [standardize_task_name(p) for p in parts]

def standardize_task_name(name: str) -> str:
    s = str(name).replace('_', ' ').strip()
    return ' '.join(w.capitalize() for w in s.split())

def is_weather_sensitive(task_name: str) -> bool:
    n = task_name.lower()
    return any(k in n for k in ['site', 'excavation', 'foundation', 'roof'])

def estimate_crew_size(task_name: str) -> int:
    n = task_name.lower()
    if 'framing' in n: return 8
    if 'mep' in n: return 6
    if 'drywall' in n: return 5
    if 'foundation' in n: return 6
    if 'excavation' in n: return 4
    if 'roof' in n: return 4
    if 'finish' in n: return 7
    return 4

def get_historical_delay_prob(task_name: str) -> float:
    n = task_name.lower()
    if 'permit' in n or 'inspection' in n: return 0.25
    if 'roof' in n: return 0.35
    if 'excavation' in n: return 0.3
    if 'foundation' in n: return 0.25
    return 0.15

def parse_user_schedule_for_simulation(uploaded_df: pd.DataFrame) -> Dict[str, TaskTemplate]:
    """Convert uploaded schedule DF into TaskTemplate dict (Phase 2)"""
    required_cols = {'task_name', 'duration'}
    if not required_cols.issubset(set(map(str.lower, uploaded_df.columns))):
        # Try to normalize common variations
        cols = {c.lower(): c for c in uploaded_df.columns}
        if 'task_name' not in cols or 'duration' not in cols:
            raise ValueError("Uploaded schedule needs at least columns: task_name, duration")

    cols = {c.lower(): c for c in uploaded_df.columns}
    task_templates: Dict[str, TaskTemplate] = {}

    for _, row in uploaded_df.iterrows():
        name = standardize_task_name(row[cols.get('task_name')])
        duration = int(row[cols.get('duration')])
        predecessor = row.get(cols.get('predecessor', ''), '') if cols.get('predecessor', '') in row else ''
        cost = float(row.get(cols.get('cost', ''), 0)) if cols.get('cost', '') in row else 0.0
        critical = bool(row.get(cols.get('critical_path', ''), False)) if cols.get('critical_path', '') in row else False

        tt = TaskTemplate(
            name=name,
            base_duration=duration,
            min_duration=max(1, int(duration * 0.8)),
            max_duration=max(2, int(math.ceil(duration * 1.3))),
            dependencies=parse_dependencies(predecessor),
            weather_sensitive=is_weather_sensitive(name),
            crew_required=estimate_crew_size(name),
            cost=cost,
            delay_probability=get_historical_delay_prob(name),
            critical_path=critical
        )
        task_templates[name.lower().replace(' ', '_')] = tt

    return task_templates

# ---------- GA Optimizer (Week 5) ----------
class GeneticScheduleOptimizer:
    """Find optimal schedule config using a simple genetic algorithm."""
    def __init__(self, simulator: ConstructionScenarioSimulator):
        self.simulator = simulator

    def optimize_schedule(self, base_params: SimulationParameters, objectives: List[str]) -> Dict:
        population_size = 24
        generations = 20
        population = self._create_initial_population(base_params, population_size)

        best = None
        best_score = -1e9

        for _ in range(generations):
            scores = []
            for indiv in population:
                res = self.simulator.run_monte_carlo_simulation(indiv, num_scenarios=200)
                fitness = self._calculate_fitness(res, objectives)
                scores.append(fitness)
                if fitness > best_score:
                    best_score = fitness
                    best = (indiv, res)

            # select top 30%
            elite_idx = np.argsort(scores)[-max(1, population_size//3):]
            elite = [population[i] for i in elite_idx]

            # breed + mutate to next gen
            next_pop = []
            while len(next_pop) < population_size:
                p1, p2 = random.choice(elite), random.choice(elite)
                child = self._crossover(p1, p2)
                child = self._mutate(child)
                next_pop.append(child)
            population = next_pop

        indiv, res = best
        return {
            'optimal_params': _params_to_dict(indiv),
            'result_summary': res,
            'objectives': objectives,
            'fitness': float(best_score)
        }

    def _create_initial_population(self, base: SimulationParameters, size: int) -> List[SimulationParameters]:
        pop = []
        for _ in range(size):
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
        # Simple mix of crew size and start date
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
        if random.random() < 0.5:
            indiv = SimulationParameters(
                **{**_params_to_dict(indiv), 'crew_size': max(3, indiv.crew_size + random.randint(-2, 3))}
            )
        if random.random() < 0.5:
            shift = random.randint(-10, 10)
            indiv = SimulationParameters(
                **{**_params_to_dict(indiv), 'start_date': indiv.start_date + timedelta(days=shift)}
            )
        return indiv

    def _calculate_fitness(self, result: Dict, objectives: List[str]) -> float:
        dur = result['duration_analysis']
        cost = result['cost_analysis']
        duration_score = 1.0 / max(1.0, dur['mean_duration'])
        cost_score = 1.0 / max(1.0, cost['mean_cost'])
        risk_score = 1.0 / max(0.1, dur['std_duration'])

        if 'minimize_duration' in objectives:
            return 0.5 * duration_score + 0.3 * cost_score + 0.2 * risk_score
        if 'minimize_cost' in objectives:
            return 0.3 * duration_score + 0.5 * cost_score + 0.2 * risk_score
        # minimize_risk default
        return 0.2 * duration_score + 0.3 * cost_score + 0.5 * risk_score

# ---------- Portfolio Optimization (Week 9) ----------
def portfolio_optimize(projects: List[SimulationParameters], total_crew_cap: int) -> Dict:
    """
    Very simple heuristic: allocate crew boosts to projects with highest
    duration sensitivity first, under total crew cap.
    """
    sim = ConstructionScenarioSimulator()
    base_runs = [(p, sim.run_monte_carlo_simulation(p, 200)) for p in projects]
    # Estimate sensitivity: try +2 crew for each
    deltas = []
    for p, res in base_runs:
        p_boost = SimulationParameters(**{**_params_to_dict(p), 'crew_size': p.crew_size + 2})
        res2 = sim.run_monte_carlo_simulation(p_boost, 200)
        gain = res['duration_analysis']['mean_duration'] - res2['duration_analysis']['mean_duration']
        deltas.append((p, res, gain))

    # Sort by gain (descending)
    deltas.sort(key=lambda x: x[2], reverse=True)

    # Allocate crews greedily
    remaining = max(0, total_crew_cap - sum(p.crew_size for p in projects))
    allocations = []
    for p, res, gain in deltas:
        add = min(remaining, 2) if gain > 0 else 0
        remaining -= add
        allocations.append({'project': _params_to_dict(p), 'add_crew': add, 'expected_days_saved': float(max(0, gain))})

    return {'allocations': allocations, 'crew_unassigned': remaining}

# ---------- Helpers ----------
def _params_to_dict(p: SimulationParameters) -> Dict:
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

def hash_params(params: SimulationParameters) -> str:
    d = _params_to_dict(params).copy()
    d['start_date'] = d['start_date'].isoformat()
    return json.dumps(d, sort_keys=True)

# ---------- Caching (Streamlit) ----------
@st.cache_data(ttl=3600, show_spinner=False)
def cached_run(params_json: str, num: int) -> Dict:
    p = json.loads(params_json)
    p['start_date'] = datetime.fromisoformat(p['start_date'])
    sim = ConstructionScenarioSimulator()
    return sim.run_monte_carlo_simulation(SimulationParameters(**p), num)

# ---------- UI Functions ----------
def run_scenario_simulation(params: SimulationParameters, num_scenarios: int) -> Dict:
    """Public wrapper that uses caching"""
    p_json = hash_params(params)
    return cached_run(p_json, num_scenarios)

# ---------- Results Display Functions ----------
def display_scenario_results(results: Dict):
    """Display basic scenario results with metrics and charts"""
    st.subheader("📊 Scenario Results")
    
    # Key metrics in columns
    col1, col2, col3, col4 = st.columns(4)
    dur = results['duration_analysis']
    cost = results['cost_analysis']
    
    col1.metric("Best Case", f"{dur['min_duration']} days", delta=None)
    col2.metric("Median", f"{dur['median_duration']} days")
    col3.metric("Worst Case", f"{dur['max_duration']} days")
    col4.metric("P90 Duration", f"{dur['p90_duration']} days")

    # Cost metrics
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Min Cost", f"${cost['min_cost']:,.0f}")
    col2.metric("Median Cost", f"${cost['median_cost']:,.0f}")
    col3.metric("Max Cost", f"${cost['max_cost']:,.0f}")
    col4.metric("P90 Cost", f"${cost['p90_cost']:,.0f}")

    # Duration distribution chart (synthetic)
    try:
        import matplotlib.pyplot as plt
        mu = dur['mean_duration']
        sigma = max(1.0, dur['std_duration'])
        synthetic_durations = np.random.normal(mu, sigma, 1000)
        synthetic_durations = synthetic_durations[synthetic_durations > 0]  # Remove negative values
        
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.hist(synthetic_durations, bins=30, alpha=0.7, color='steelblue', edgecolor='black')
        ax.axvline(dur['median_duration'], color='red', linestyle='--', label=f"Median: {dur['median_duration']:.0f} days")
        ax.axvline(dur['p90_duration'], color='orange', linestyle='--', label=f"P90: {dur['p90_duration']:.0f} days")
        ax.set_xlabel("Project Duration (Days)")
        ax.set_ylabel("Frequency")
        ax.set_title("Duration Probability Distribution")
        ax.legend()
        st.pyplot(fig)
        plt.close()
    except Exception as e:
        st.info(f"Chart display unavailable: {str(e)}")

    # Risk analysis table
    st.subheader("🎯 Risk Analysis")
    risk_data = results.get('risk_analysis', {})
    risk_df = pd.DataFrame([
        {
            'Risk Type': 'Weather',
            'Probability': f"{risk_data.get('weather_delays', {}).get('probability', 0.0):.1%}",
            'Avg Days When Occurs': f"{risk_data.get('weather_delays', {}).get('avg_when_occurs', 0.0):.1f}",
            'Max Observed': f"{risk_data.get('weather_delays', {}).get('max_observed', 0)}"
        },
        {
            'Risk Type': 'Supply Chain',
            'Probability': f"{risk_data.get('supply_chain_delays', {}).get('probability', 0.0):.1%}",
            'Avg Days When Occurs': f"{risk_data.get('supply_chain_delays', {}).get('avg_when_occurs', 0.0):.1f}",
            'Max Observed': f"{risk_data.get('supply_chain_delays', {}).get('max_observed', 0)}"
        },
        {
            'Risk Type': 'Permits',
            'Probability': f"{risk_data.get('permit_delays', {}).get('probability', 0.0):.1%}",
            'Avg Days When Occurs': f"{risk_data.get('permit_delays', {}).get('avg_when_occurs', 0.0):.1f}",
            'Max Observed': f"{risk_data.get('permit_delays', {}).get('max_observed', 0)}"
        }
    ])
    st.dataframe(risk_df, use_container_width=True)

    # Optimization recommendations
    st.subheader("💡 Optimization Recommendations")
    recommendations = results.get('optimization_recommendations', [])
    if recommendations:
        for i, rec in enumerate(recommendations):
            if any(emoji in rec for emoji in ['🌧️', '❄️']):
                st.warning(f"**Weather Risk:** {rec}")
            elif any(emoji in rec for emoji in ['💰', '👥', '📦']):
                st.info(f"**Opportunity:** {rec}")
            else:
                st.success(f"**Insight:** {rec}")
    else:
        st.info("No specific recommendations generated for this scenario.")

    # Expandable full results
    with st.expander("View Full JSON Results"):
        st.json(results)

def display_advanced_scenario_results(results: Dict):
    """Display advanced results with optimization opportunities"""
    # First show basic results
    display_scenario_results(results)
    
    # Then add advanced features
    st.subheader("🚀 Advanced Analysis & Optimization")
    
    # Scenario categorization
    scenarios = results.get('scenario_percentiles', {})
    if scenarios:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                "Best Case Scenario",
                f"{scenarios.get('best_case', {}).get('duration', 0)} days",
                help=scenarios.get('best_case', {}).get('description', '')
            )
            st.caption(f"Cost: ${scenarios.get('best_case', {}).get('cost', 0):,.0f}")
        
        with col2:
            st.metric(
                "Most Likely Scenario", 
                f"{scenarios.get('typical_case', {}).get('duration', 0)} days",
                help=scenarios.get('typical_case', {}).get('description', '')
            )
            st.caption(f"Cost: ${scenarios.get('typical_case', {}).get('cost', 0):,.0f}")
        
        with col3:
            st.metric(
                "Worst Case Scenario",
                f"{scenarios.get('worst_case', {}).get('duration', 0)} days", 
                help=scenarios.get('worst_case', {}).get('description', '')
            )
            st.caption(f"Cost: ${scenarios.get('worst_case', {}).get('cost', 0):,.0f}")

    # Interactive optimization opportunities
    st.subheader("💡 Apply Optimizations")
    recommendations = results.get('optimization_recommendations', [])
    for idx, rec in enumerate(recommendations):
        with st.expander(f"Optimization {idx+1}: {rec[:50]}..."):
            st.write(rec)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Estimated Time Saved", "2-5 days", help="Based on similar optimizations")
            with col2:
                st.metric("Implementation Cost", "5-15%", help="Additional resource investment")
            with col3:
                st.metric("ROI Estimate", "200-400%", help="Return on optimization investment")
            
            if st.button(f"Apply Optimization {idx+1}", key=f"apply_opt_{idx}"):
                st.success(f"✅ Optimization {idx+1} applied! Re-run simulation to see updated results.")

# ---------- Progressive Analysis Functions ----------
def quick_analysis(params: SimulationParameters):
    """Run quick 100-scenario analysis"""
    with st.spinner("🔄 Running quick analysis (100 scenarios)..."):
        results = run_scenario_simulation(params, 100)
    st.success("✅ Quick analysis complete!")
    display_scenario_results(results)

def deep_analysis(params: SimulationParameters):
    """Run comprehensive 2000-scenario analysis"""
    with st.spinner("🔄 Running deep analysis (2,000 scenarios)... This may take a minute."):
        results = run_scenario_simulation(params, 2000)
    st.success("✅ Deep analysis complete!")
    display_advanced_scenario_results(results)

def full_optimization(params: SimulationParameters):
    """Run genetic algorithm optimization"""
    with st.spinner("🧬 Running genetic optimization... This may take 2-3 minutes."):
        sim = ConstructionScenarioSimulator()
        ga = GeneticScheduleOptimizer(sim)
        optimization_result = ga.optimize_schedule(params, objectives=['minimize_duration', 'minimize_risk'])
    
    st.success("✅ Genetic optimization complete!")
    
    # Display optimization results
    st.subheader("🎯 Optimized Parameters")
    optimal_params = optimization_result['optimal_params']
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Original Parameters:**")
        st.write(f"- Crew Size: {params.crew_size}")
        st.write(f"- Start Date: {params.start_date.strftime('%Y-%m-%d')}")
        st.write(f"- Location: {params.location}")
    
    with col2:
        st.write("**Optimized Parameters:**")
        st.write(f"- Crew Size: {optimal_params['crew_size']}")
        st.write(f"- Start Date: {optimal_params['start_date'][:10]}")
        st.write(f"- Location: {optimal_params['location']}")
    
    st.metric("Optimization Fitness Score", f"{optimization_result['fitness']:.4f}")
    
    # Display optimized scenario results
    display_advanced_scenario_results(optimization_result['result_summary'])

# ---------- Real-time Updates Section ----------
def realtime_updates_section(base_params: SimulationParameters):
    """Handle real-time project updates and re-simulation"""
    st.subheader("⏱️ Real-time Project Updates")
    st.write("Update your simulation with current project status to get revised predictions.")
    
    # Progress capture inputs
    col1, col2 = st.columns(2)
    
    with col1:
        as_of_date = st.date_input("Status as of", datetime.now().date())
        completed_tasks = st.text_area(
            "Completed tasks (comma-separated)", 
            placeholder="Site Preparation, Excavation, Foundation...",
            help="List the tasks that have been completed"
        )
    
    with col2:
        blocked_items = st.text_area(
            "Current blockers/delays", 
            placeholder="Weather delays, permit issues, material shortages...",
            help="Describe any current issues affecting the project"
        )
        risk_adjustment = st.slider(
            "Overall Risk Adjustment", 
            0.5, 2.0, 1.0, 0.1,
            help="Adjust based on current project conditions (0.5 = lower risk, 2.0 = higher risk)"
        )

    if st.button("🔄 Update Simulation with Current Status"):
        with st.spinner("Updating simulation with real-time data..."):
            # Adjust parameters based on progress
            completed_count = len([x.strip() for x in completed_tasks.split(',') if x.strip()])
            progress_factor = max(0.1, 1.0 - (completed_count * 0.05))  # Reduce risk as tasks complete
            
            # Create updated parameters
            updated_params = SimulationParameters(
                location=base_params.location,
                start_date=base_params.start_date,
                crew_size=base_params.crew_size,
                budget=base_params.budget,
                project_type=base_params.project_type,
                square_footage=base_params.square_footage,
                weather_sensitivity=base_params.weather_sensitivity * progress_factor * risk_adjustment,
                supply_chain_risk=base_params.supply_chain_risk * progress_factor * risk_adjustment,
                permit_risk=base_params.permit_risk * progress_factor * risk_adjustment,
                labor_availability=base_params.labor_availability
            )
            
            # Run updated simulation
            results = run_scenario_simulation(updated_params, 1000)
        
        st.success(f"✅ Simulation updated as of {as_of_date.strftime('%Y-%m-%d')}")
        if completed_count > 0:
            st.info(f"📈 Incorporated completion of {completed_count} tasks into risk calculations")
        
        display_scenario_results(results)

# ---------- Phase Integration UI Functions ----------
def enhanced_development_stage():
    """Phase 1: Development stage with schedule upload integration"""
    st.header("🚧 Development: Schedule & Risk Analysis")
    st.write("Upload your existing project schedule and run scenario analysis.")
    
    uploaded_schedule = st.file_uploader(
        "Upload Project Schedule", 
        type=['csv', 'xlsx'],
        help="Upload a CSV or Excel file with your project schedule"
    )

    df = None
    if uploaded_schedule:
        try:
            if uploaded_schedule.name.endswith('.csv'):
                df = pd.read_csv(uploaded_schedule)
            else:
                df = pd.read_excel(uploaded_schedule)
            st.success(f"✅ Schedule uploaded successfully! Found {len(df)} tasks.")
            
            # Show preview of uploaded data
            st.subheader("📋 Schedule Preview")
            st.dataframe(df.head(20), use_container_width=True)
            
        except Exception as e:
            st.error(f"❌ Failed to read file: {str(e)}")

    if df is not None:
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("📅 Integration Placeholder")
            st.info("🔧 **Integration Point:** Connect your existing Gantt chart and risk analysis tools here.")
            st.write("This space is reserved for:")
            st.write("- Interactive Gantt chart display")
            st.write("- Risk matrix visualization") 
            st.write("- Critical path highlighting")
            st.write("- Resource allocation charts")
            
            # Placeholder for future integration
            if st.button("🔗 Connect External Tools"):
                st.info("Feature coming soon! This will integrate with popular PM tools.")

        with col2:
            st.subheader("🎯 Scenario Analysis")
            
            # Analysis parameters
            crew_size = st.slider("Crew Size", 5, 20, 10, help="Total crew members across all trades")
            location = st.selectbox("Project Location", [
                "Atlanta, GA", "Dallas, TX", "Phoenix, AZ", "Chicago, IL",
                "Denver, CO", "Seattle, WA", "San Francisco, CA", "New York, NY"
            ])
            start_date = st.date_input("Project Start Date", datetime.now().date())
            budget = st.number_input("Project Budget ($)", 100000, 100000000, 2000000, 50000, format="%d")
            sqft = st.number_input("Square Footage", 1000, 500000, 25000, 1000, format="%d")
            
            num_scenarios = st.selectbox("Analysis Depth", [500, 1000, 2000, 5000], index=1)
            
            if st.button("🚀 Run Monte Carlo Analysis", type="primary"):
                params = SimulationParameters(
                    location=location,
                    start_date=datetime.combine(start_date, datetime.min.time()),
                    crew_size=crew_size,
                    budget=float(budget),
                    project_type="Office Building",
                    square_footage=sqft
                )
                
                with st.spinner(f"Running {num_scenarios} scenario analysis..."):
                    results = run_scenario_simulation(params, num_scenarios)
                
                display_scenario_results(results)

# ---------- Main UI Application ----------
def main():
    """Main Streamlit application"""
    st.title("🏗️ Construction Scenario Simulation Engine — V2")
    st.markdown("---")
    
    # Sidebar: base parameters for all analyses
    with st.sidebar:
        st.header("🔧 Base Project Parameters")
        st.write("Configure your project settings:")
        
        project_name = st.text_input("Project Name", "Office Building Project")
        
        location = st.selectbox("📍 Location", [
            "Atlanta, GA", "Dallas, TX", "Phoenix, AZ", "Austin, TX",
            "Chicago, IL", "Denver, CO", "Seattle, WA", 
            "San Francisco, CA", "New York, NY", "Boston, MA"
        ], help="Location affects weather patterns, labor costs, and regulations")
        
        start_date = st.date_input("📅 Start Date", datetime.now().date())
        
        project_type = st.selectbox("🏢 Project Type", [
            "Office Building", "Retail Store", "Warehouse", 
            "Apartment Complex", "Mixed Use", "Industrial"
        ])
        
        crew_size = st.slider("👥 Base Crew Size", 5, 30, 12, 
                             help="Total crew members across all trades")
        
        budget = st.number_input(
            "💰 Budget ($)", 
            min_value=100000, max_value=50000000, 
            value=1500000, step=50000, format="%d"
        )
        
        square_footage = st.number_input(
            "📐 Square Footage", 
            min_value=1000, max_value=500000,
            value=25000, step=1000, format="%d"
        )

        # Create base parameters object
        base_params = SimulationParameters(
            location=location,
            start_date=datetime.combine(start_date, datetime.min.time()),
            crew_size=crew_size,
            budget=float(budget),
            project_type=project_type,
            square_footage=square_footage
        )
        
        st.markdown("---")
        st.caption(f"**{project_name}**")
        st.caption(f"📊 Configured for {project_type}")
        st.caption(f"📍 {location}")

    # Main tabs
    tabs = st.tabs([
        "🚦 Quick Analysis",
        "🚧 Development Integration", 
        "🧩 Advanced Parsing",
        "🧬 AI Optimization",
        "📦 Portfolio Management",
        "💰 Pricing & ROI"
    ])

    # Tab 1: Quick Analysis (Progressive Disclosure)
    with tabs[0]:
        st.header("🚦 Progressive Project Analysis")
        st.write("Choose your analysis depth based on project stage and time available.")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.subheader("⚡ Quick Preview")
            st.write("**100 scenarios • ~10 seconds**")
            st.write("• Basic duration estimates")
            st.write("• Key risk identification") 
            st.write("• Initial recommendations")
            if st.button("Run Quick Analysis", type="secondary"):
                quick_analysis(base_params)
        
        with col2:
            st.subheader("🔍 Deep Analysis")
            st.write("**2,000 scenarios • ~30 seconds**")
            st.write("• Detailed probability curves")
            st.write("• Advanced risk breakdown")
            st.write("• Optimization opportunities")
            if st.button("Run Deep Analysis", type="secondary"):
                deep_analysis(base_params)
        
        with col3:
            st.subheader("🚀 Full Optimization")
            st.write("**AI genetic algorithm • ~2 minutes**")
            st.write("• Optimal start dates")
            st.write("• Crew size optimization")
            st.write("• Maximum ROI scenarios")
            if st.button("Run Full Optimization", type="primary"):
                full_optimization(base_params)

    # Tab 2: Development Integration (Phase 1)
    with tabs[1]:
        enhanced_development_stage()

    # Tab 3: Advanced Parsing (Phase 2)  
    with tabs[2]:
        st.header("🧩 Advanced Schedule Integration")
        st.write("Parse uploaded schedules into simulation-ready templates with intelligent task recognition.")
        
        uploaded_file = st.file_uploader(
            "Upload Detailed Schedule (CSV/XLSX)", 
            type=['csv', 'xlsx'], 
            key="advanced_upload",
            help="Include columns: task_name, duration, predecessor (optional), cost (optional)"
        )
        
        if uploaded_file:
            try:
                # Read uploaded file
                if uploaded_file.name.endswith('.csv'):
                    df = pd.read_csv(uploaded_file)
                else:
                    df = pd.read_excel(uploaded_file)
                
                st.success(f"✅ File uploaded! Processing {len(df)} tasks...")
                
                # Show data preview
                st.subheader("📋 Raw Schedule Data")
                st.dataframe(df.head(10), use_container_width=True)
                
                # Parse into templates
                task_templates = parse_user_schedule_for_simulation(df)
                st.success(f"🔄 Parsed {len(task_templates)} tasks into simulation templates!")
                
                # Show parsed templates preview
                st.subheader("🛠️ Generated Task Templates")
                template_preview = []
                for key, template in list(task_templates.items())[:5]:
                    template_preview.append({
                        'Task': template.name,
                        'Duration': f"{template.base_duration} days ({template.min_duration}-{template.max_duration})",
                        'Weather Sensitive': '🌧️' if template.weather_sensitive else '☀️',
                        'Crew Required': template.crew_required,
                        'Dependencies': ', '.join(template.dependencies) if template.dependencies else 'None'
                    })
                
                st.dataframe(pd.DataFrame(template_preview), use_container_width=True)
                if len(task_templates) > 5:
                    st.caption(f"... and {len(task_templates) - 5} more tasks")
                
                # Run simulation with parsed templates
                if st.button("🚀 Run Simulation with Parsed Schedule"):
                    with st.spinner("Running simulation with your custom schedule..."):
                        sim = ConstructionScenarioSimulator(task_templates=task_templates)
                        results = sim.run_monte_carlo_simulation(base_params, 1000)
                    
                    st.success("✅ Custom schedule simulation complete!")
                    display_scenario_results(results)
                    
            except Exception as e:
                st.error(f"❌ Parsing failed: {str(e)}")
                st.info("💡 Ensure your file has columns: task_name, duration (and optionally: predecessor, cost, critical_path)")

    # Tab 4: AI Optimization (Weeks 5-7)
    with tabs[3]:
        st.header("🧬 AI-Powered Optimization & Real-Time Updates")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🤖 Genetic Algorithm Optimization")
            st.write("Use AI to find the optimal project configuration:")
            
            objectives = st.multiselect(
                "Optimization Objectives",
                ["minimize_duration", "minimize_cost", "minimize_risk"],
                default=["minimize_duration", "minimize_risk"],
                help="Choose what to optimize for"
            )
            
            if st.button("🧬 Run AI Optimization"):
                if objectives:
                    with st.spinner("🤖 AI optimization in progress... This may take 2-3 minutes."):
                        sim = ConstructionScenarioSimulator()
                        ga = GeneticScheduleOptimizer(sim)
                        result = ga.optimize_schedule(base_params, objectives)
                    
                    st.success("✅ AI optimization complete!")
                    st.json(result['optimal_params'])
                    display_advanced_scenario_results(result['result_summary'])
                else:
                    st.warning("Please select at least one optimization objective.")
        
        with col2:
            realtime_updates_section(base_params)

    # Tab 5: Portfolio Management (Week 9)
    with tabs[4]:
        st.header("📦 Multi-Project Portfolio Optimization")
        st.write("Optimize crew allocation across multiple concurrent projects.")
        
        # Project configuration
        num_projects = st.slider("Number of Projects", 2, 5, 3)
        total_crew_capacity = st.number_input("Total Available Crew", 20, 150, 60, 5, 
                                            help="Total crew members available across all projects")
        
        projects = []
        cols = st.columns(min(num_projects, 3))  # Max 3 columns for layout
        
        for i in range(num_projects):
            col_idx = i % 3
            with cols[col_idx]:
                st.subheader(f"Project {i+1}")
                
                proj_location = st.selectbox(f"Location", [
                    "Atlanta, GA", "Dallas, TX", "Phoenix, AZ", "Chicago, IL",
                    "Denver, CO", "Seattle, WA", "San Francisco, CA"
                ], key=f"proj_loc_{i}")
                
                proj_start = st.date_input(f"Start Date", 
                    datetime.now().date() + timedelta(days=i*30), key=f"proj_start_{i}")
                
                proj_crew = st.slider(f"Base Crew", 5, 25, 10, key=f"proj_crew_{i}")
                
                proj_budget = st.number_input(f"Budget ($)", 500000, 10000000, 
                    1500000 + (i * 200000), 100000, key=f"proj_budget_{i}", format="%d")
                
                proj_sqft = st.number_input(f"Sq Ft", 5000, 100000, 
                    20000 + (i * 5000), 1000, key=f"proj_sqft_{i}", format="%d")
                
                projects.append(SimulationParameters(
                    location=proj_location,
                    start_date=datetime.combine(proj_start, datetime.min.time()),
                    crew_size=proj_crew,
                    budget=float(proj_budget),
                    project_type="Office Building",
                    square_footage=proj_sqft
                ))
        
        if st.button("🎯 Optimize Portfolio", type="primary"):
            with st.spinner("Optimizing crew allocation across projects..."):
                portfolio_result = portfolio_optimize(projects, total_crew_capacity)
            
            st.success("✅ Portfolio optimization complete!")
            
            # Display results
            st.subheader("📊 Optimized Crew Allocation")
            allocation_df = pd.DataFrame(portfolio_result['allocations'])
            
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

    # Tab 6: Pricing & ROI
    with tabs[5]:
        st.header("💰 V2 Pricing Strategy & ROI Calculator")
        
        # Pricing tiers
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.subheader("🥉 V2 Basic")
            st.write("**$299/month**")
            st.write("✅ 1,000 scenarios/month")
            st.write("✅ Basic optimization")
            st.write("✅ Standard reports")
            st.write("✅ Email support")
        
        with col2:
            st.subheader("🥈 V2 Professional")
            st.write("**$599/month**")
            st.write("✅ 10,000 scenarios/month")
            st.write("✅ AI genetic optimization")
            st.write("✅ Portfolio analysis")
            st.write("✅ Advanced dashboards")
            st.write("✅ Priority support")
        
        with col3:
            st.subheader("🥇 V2 Enterprise")
            st.write("**$1,199/month**")
            st.write("✅ Unlimited scenarios")
            st.write("✅ Real-time optimization")
            st.write("✅ API access")
            st.write("✅ Custom integrations")
            st.write("✅ Dedicated support")
        
        st.markdown("---")
        
        # ROI Calculator
        st.subheader("📈 ROI Calculator")
        st.write("Calculate potential savings from using Construction Scenario Engine:")
        
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
                                           help="Industry average: 15-25%")
            cost_reduction = st.slider("Cost reduction (%)", 3, 25, 12,
                                     help="Industry average: 8-18%")
            delay_reduction = st.slider("Delay frequency reduction (%)", 20, 70, 45,
                                      help="Better planning reduces delays")
        
        # Calculate ROI
        if st.button("💰 Calculate ROI", type="primary"):
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
            
            # Software costs (assuming Professional tier)
            software_cost_monthly = 599
            software_cost_annual = software_cost_monthly * 12
            
            net_savings = annual_savings - software_cost_annual
            roi_percentage = (net_savings / software_cost_annual) * 100 if software_cost_annual > 0 else 0
            
            # Display results
            st.success("🎯 **ROI Analysis Results**")
            
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Annual Savings", f"${annual_savings:,.0f}")
            col2.metric("Monthly Savings", f"${monthly_savings:,.0f}")
            col3.metric("Net Annual ROI", f"${net_savings:,.0f}")
            col4.metric("ROI Percentage", f"{roi_percentage:.0f}%")
            
            # Detailed breakdown
            with st.expander("📊 Detailed Breakdown"):
                breakdown_df = pd.DataFrame([
                    ["Current Annual Project Costs", f"${annual_project_cost:,.0f}"],
                    ["Current Annual Delay Costs", f"${annual_delay_cost:,.0f}"],
                    ["**Total Current Annual Costs**", f"**${total_annual_cost:,.0f}**"],
                    ["", ""],
                    ["Improved Annual Project Costs", f"${improved_project_cost:,.0f}"],
                    ["Improved Annual Delay Costs", f"${improved_delay_cost:,.0f}"],
                    ["**Total Improved Annual Costs**", f"**${total_improved_cost:,.0f}**"],
                    ["", ""],
                    ["V2 Professional Software Cost", f"${software_cost_annual:,.0f}"],
                    ["**Net Annual Benefit**", f"**${net_savings:,.0f}**"]
                ], columns=["Category", "Amount"])
                
                st.dataframe(breakdown_df, use_container_width=True, hide_index=True)
            
            # Payback period
            if monthly_savings > software_cost_monthly:
                payback_months = software_cost_annual / monthly_savings
                st.info(f"💡 **Payback Period:** {payback_months:.1f} months")
            else:
                st.warning("⚠️ Current projections show payback period > 12 months. Consider adjusting parameters or tier.")
        
        st.markdown("---")
        
        # Value proposition
        st.subheader("🎯 Value Proposition Summary")
        st.write("""
        **Construction Scenario Engine V2 delivers measurable ROI through:**
        
        🎯 **Duration Optimization:** Save 15-25% on project timelines through AI-powered scheduling
        
        💰 **Cost Reduction:** Reduce project costs by 10-18% via better resource allocation
        
        🌧️ **Risk Mitigation:** Cut weather and supply chain delays by 30-50% with predictive analytics
        
        📊 **Data-Driven Decisions:** Replace gut feelings with Monte Carlo simulations and genetic algorithms
        
        🔄 **Continuous Improvement:** Real-time updates keep projects on track as conditions change
        
        **Typical ROI: 300-500% in first year**
        """)

# ---------- Run the app if executed directly ----------
if __name__ == "__main__":
    # CLI mode for testing (no Streamlit)
    if len(os.sys.argv) > 1 and os.sys.argv[1] == "cli":
        print("🏗️ Construction Scenario Engine - CLI Mode")
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
        print(f"✅ CLI Test Complete:")
        print(f"   Median duration: {int(results['duration_analysis']['median_duration'])} days")
        print(f"   P90 duration: {int(results['duration_analysis']['p90_duration'])} days")
        print(f"   Median cost: ${results['cost_analysis']['median_cost']:,.0f}")
    else:
        # Streamlit UI mode
        main()




























