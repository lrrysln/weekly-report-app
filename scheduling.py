# Construction Scenario Simulation Engine - V2 Implementation (Streamlit-safe)
# - Thread-based parallelism (no pickling crash)
# - V2 feature progression: GA optimization, real-time updates, portfolio optimization
# - Phased integration helpers + advanced UI + caching + progressive disclosure

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
st.set_page_config(page_title="Debug Mode", layout="wide")
st.write("✅ App started")

# ---------- Streamlit (UI) ----------
try:
    import streamlit as st
except Exception:
    # Allow headless usage (e.g., CLI execution)
    class _Stub:
        def __getattr__(self, k): return lambda *a, **kw: None
    st = _Stub()

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
    base_duration: int  # days
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
                'extreme_weather_delay': (3, 7)  # days
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
        # Build a mapping from name to template and dependency names match 'name'
        name_to_template = {t.name: t for t in self.task_templates.values()}
        # Ensure a deterministic order via a simple topological-like pass
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
            if n in temp_mark:  # cycle guard
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
        if month in [12, 1, 2]:     prob = base * 2.0
        elif month in [3, 4]:       prob = base * 1.5
        elif month in [6, 7, 8, 9]: prob = base * 1.3
        else:                       prob = base

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
        if any(c in location for c in ['chicago', 'denver', 'seattle']):           return 1.0
        if any(c in location for c in ['san francisco', 'new york', 'boston']):    return 1.15
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
        elif m in [3, 4]:   recs.append("🌱 MUD SEASON: Front-load indoor work during worst weeks.")

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
if hasattr(st, "cache_data"):
    @st.cache_data(ttl=3600, show_spinner=False)
    def cached_run(params_json: str, num: int) -> Dict:
        p = json.loads(params_json)
        p['start_date'] = datetime.fromisoformat(p['start_date'])
        sim = ConstructionScenarioSimulator()
        return sim.run_monte_carlo_simulation(SimulationParameters(**p), num)
else:
    def cached_run(params_json: str, num: int) -> Dict:
        p = json.loads(params_json)
        p['start_date'] = datetime.fromisoformat(p['start_date'])
        sim = ConstructionScenarioSimulator()
        return sim.run_monte_carlo_simulation(SimulationParameters(**p), num)

# ---------- Phase 1: Drop-in Integration UI ----------
def enhanced_development_stage():
    st.header("🚧 Development: Schedule & Risk Analysis")
    uploaded_schedule = st.file_uploader("Upload Schedule (CSV/XLSX)", type=['csv', 'xlsx'])

    df = None
    if uploaded_schedule:
        try:
            if uploaded_schedule.name.endswith('.csv'):
                df = pd.read_csv(uploaded_schedule)
            else:
                df = pd.read_excel(uploaded_schedule)
            st.success("Schedule uploaded.")
            st.dataframe(df.head(20))
        except Exception as e:
            st.error(f"Failed to read file: {e}")

    if df is not None:
        col1, col2 = st.columns([2, 1])
        with col1:
            st.subheader("📅 (Placeholder) Gantt & Risk")
            st.caption("Integrate your existing Gantt/risk analysis here.")

        with col2:
            st.subheader("🎯 Scenario Analysis")
            crew_size = st.slider("Crew Size", 5, 20, 10)
            location = st.text_input("Location", "Atlanta, GA")
            start_date = st.date_input("Start Date", datetime.now().date())
            budget = st.number_input("Budget", 100000, 100000000, 2_000_000, 50000)
            sqft = st.number_input("Square Footage", 1000, 500000, 25000, 1000)
            if st.button("Run 1,000 Scenarios"):
                params = SimulationParameters(
                    location=location,
                    start_date=datetime.combine(start_date, datetime.min.time()),
                    crew_size=crew_size,
                    budget=budget,
                    project_type="Office",
                    square_footage=sqft
                )
                res = run_scenario_simulation(params, 1000)
                display_scenario_results(res)

# ---------- Phase 3: Real-time updates UI ----------
def realtime_updates_section(base_params: SimulationParameters):
    st.subheader("⏱️ Real-time Scenario Updates")
    # Simple progress capture
    as_of = st.date_input("Data as of", datetime.now().date())
    completed_tasks = st.text_area("Completed task names (comma-separated)", "")
    blocked_items = st.text_area("Blocked tasks / notes", "")

    if st.button("Re-run with Real Data"):
        # For demo: nudge risks down if lots completed; up if many blocks
        comp_count = len([x for x in completed_tasks.split(',') if x.strip()])
        risk_adj = max(0.1, 1.0 - 0.02 * comp_count)
        params2 = SimulationParameters(
            **{**_params_to_dict(base_params),
               'weather_sensitivity': base_params.weather_sensitivity * risk_adj,
               'supply_chain_risk': base_params.supply_chain_risk * risk_adj,
               'permit_risk': base_params.permit_risk * risk_adj}
        )
        res = run_scenario_simulation(params2, 1000)
        st.success(f"Updated simulation as of {as_of.isoformat()}")
        display_scenario_results(res)

# ---------- Advanced Results UI ----------
def display_scenario_results(results: Dict):
    st.subheader("📊 Scenario Results")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Best", f"{int(results['duration_analysis']['min_duration'])} days")
    col2.metric("Median", f"{int(results['duration_analysis']['median_duration'])} days")
    col3.metric("Worst", f"{int(results['duration_analysis']['max_duration'])} days")
    col4.metric("P90", f"{int(results['duration_analysis']['p90_duration'])} days")

    # Simple probability hist
    try:
        import matplotlib.pyplot as plt
        durations = []
        # Synthesize distribution from summary (rough plot)
        mu = results['duration_analysis']['mean_duration']
        sigma = max(1.0, results['duration_analysis']['std_duration'])
        durations = np.random.normal(mu, sigma, 5000)
        fig = plt.figure()
        plt.hist(durations, bins=30)
        plt.title("Duration Probability (synthetic from summary)")
        plt.xlabel("Days"); plt.ylabel("Frequency")
        st.pyplot(fig)
    except Exception:
        pass

    st.subheader("🎯 Optimization Recommendations")
    for rec in results.get('optimization_recommendations', []):
        if any(s in rec for s in ['🌧️', '❄️']): st.warning(rec)
        elif any(s in rec for s in ['💰', '👥', '📦']): st.info(rec)
        else: st.success(rec)

    with st.expander("Full JSON"):
        st.json(results)

# Advanced dashboard from spec (uses our charts + metrics)
def display_advanced_scenario_results(results: Dict):
    st.subheader("📊 Advanced Scenario Results Dashboard")

    # Chart: duration synthetic distribution (already above)
    display_scenario_results(results)

    # Risk “heatmap” proxy: simple table of probabilities
    st.markdown("#### Risk Heat Snapshot")
    ra = results.get('risk_analysis', {})
    df = pd.DataFrame([
        ['Weather', ra.get('weather_delays', {}).get('probability', 0.0),
         ra.get('weather_delays', {}).get('avg_when_occurs', 0.0)],
        ['Supply Chain', ra.get('supply_chain_delays', {}).get('probability', 0.0),
         ra.get('supply_chain_delays', {}).get('avg_when_occurs', 0.0)],
        ['Permits', ra.get('permit_delays', {}).get('probability', 0.0),
         ra.get('permit_delays', {}).get('avg_when_occurs', 0.0)],
    ], columns=['Risk', 'Probability', 'Avg Days When Occurs'])
    st.dataframe(df)

    # Sample “Apply optimization” expander (stub action)
    st.subheader("💡 Optimization Opportunities")
    for idx, rec in enumerate(results.get('optimization_recommendations', [])):
        with st.expander(f"Rec {idx+1}: {rec}"):
            c1, c2, c3 = st.columns(3)
            c1.metric("Time Saved (est)", "—")
            c2.metric("Cost Impact (est)", "—")
            c3.metric("ROI (est)", "—")
            if st.button(f"Apply Rec {idx+1}", key=f"apply_{idx}"):
                st.info("Applied (demo). Re-run scenarios with adjusted parameters in UI controls above.")

# ---------- Public wrappers ----------
def run_scenario_simulation(params: SimulationParameters, num_scenarios: int) -> Dict:
    sim = ConstructionScenarioSimulator()
    # Use cache where available
    p_json = hash_params(params)
    return cached_run(p_json, num_scenarios)

# Progressive disclosure helpers
def quick_analysis(params: SimulationParameters):
    st.info("Running quick preview (100 scenarios)…")
    res = run_scenario_simulation(params, 100)
    display_scenario_results(res)

def deep_analysis(params: SimulationParameters):
    st.info("Running deep analysis (2,000 scenarios)…")
    res = run_scenario_simulation(params, 2000)
    display_advanced_scenario_results(res)

def full_optimization(params: SimulationParameters):
    st.info("Running genetic optimization (Week 5 feature)…")
    sim = ConstructionScenarioSimulator()
    ga = GeneticScheduleOptimizer(sim)
    out = ga.optimize_schedule(params, objectives=['minimize_duration', 'minimize_risk'])
    st.success("Optimization complete.")
    st.json(out['optimal_params'])
    display_advanced_scenario_results(out['result_summary'])

# ---------- UI App ----------
def main():
    st.set_page_config(page_title="Construction Scenario Engine V2", layout="wide")
    st.title("🏗️ Construction Scenario Simulation Engine — V2")

    # Sidebar: base parameters
    with st.sidebar:
        st.header("Base Parameters")
        project_name = st.text_input("Project Name", "Office Building Project")
        location = st.selectbox("Location", [
            "Atlanta, GA", "Dallas, TX", "Phoenix, AZ", "Chicago, IL",
            "Denver, CO", "Seattle, WA", "San Francisco, CA", "New York, NY"
        ])
        start_date = st.date_input("Start Date", datetime.now().date())
        project_type = st.selectbox("Project Type", ["Office Building", "Retail", "Warehouse", "Apartment", "Mixed Use"])
        crew_size = st.slider("Crew Size", 5, 20, 10)
        budget = st.number_input("Budget ($)", 100000, 50000000, 1000000, 50000)
        square_footage = st.number_input("Square Footage", 1000, 500000, 25000, 1000)

        base_params = SimulationParameters(
            location=location,
            start_date=datetime.combine(start_date, datetime.min.time()),
            crew_size=crew_size,
            budget=budget,
            project_type=project_type,
            square_footage=square_footage
        )

    tabs = st.tabs([
        "Development (Phase 1)",
        "Advanced Integration (Phase 2)",
        "Real-Time Optimization (Week 5–7)",
        "Portfolio Optimization (Week 9)",
        "Progressive Analysis",
        "Pricing (V2)"
    ])

    # Phase 1
    with tabs[0]:
        enhanced_development_stage()

    # Phase 2
    with tabs[1]:
        st.header("🧩 Advanced Integration (Parse Schedule → Simulation Templates)")
        file2 = st.file_uploader("Upload Schedule (CSV/XLSX) to Convert", type=['csv', 'xlsx'], key="adv_upload")
        if file2:
            try:
                df2 = pd.read_csv(file2) if file2.name.endswith('.csv') else pd.read_excel(file2)
                st.dataframe(df2.head(20))
                templates = parse_user_schedule_for_simulation(df2)
                st.success(f"Parsed {len(templates)} tasks into simulation templates.")
                # Use parsed templates in a simulator
                sim = ConstructionScenarioSimulator(task_templates=templates)
                res = sim.run_monte_carlo_simulation(base_params, 1000)
                display_scenario_results(res)
            except Exception as e:
                st.error(f"Parsing failed: {e}")

    # Week 5–7
    with tabs[2]:
        st.header("🧬 Genetic Algorithm & Real-Time Updates")
        colA, colB = st.columns(2)
        with colA:
            if st.button("Run Genetic Optimization (fast)"):
                full_optimization(base_params)
        with colB:
            realtime_updates_section(base_params)

    # Week 9
    with tabs[3]:
        st.header("📦 Portfolio Optimization")
        st.caption("Provide multiple projects; we’ll suggest crew allocations under a total cap.")
        n = st.slider("Number of projects", 2, 5, 2)
        projects = []
        for i in range(n):
            with st.expander(f"Project {i+1}"):
                loc = st.selectbox(f"Location {i+1}", ["Atlanta, GA", "Dallas, TX", "Phoenix, AZ", "Chicago, IL"], key=f"loc_{i}")
                sd  = st.date_input(f"Start {i+1}", datetime.now().date(), key=f"dt_{i}")
                cs  = st.slider(f"Crew {i+1}", 5, 20, 10, key=f"crew_{i}")
                bgt = st.number_input(f"Budget {i+1}", 100000, 50000000, 1500000, 50000, key=f"bud_{i}")
                sqft= st.number_input(f"Sq Ft {i+1}", 1000, 500000, 25000, 1000, key=f"sq_{i}")
                projects.append(SimulationParameters(
                    location=loc, start_date=datetime.combine(sd, datetime.min.time()),
                    crew_size=cs, budget=bgt, project_type="Office", square_footage=sqft
                ))
        total_cap = st.number_input("Total crew capacity (sum across projects)", 5, 100, 30, 1)
        if st.button("Optimize Portfolio"):
            out = portfolio_optimize(projects, total_cap)
            st.json(out)

    # Progressive Disclosure
    with tabs[4]:
        st.header("🚦 Progressive Analysis")
        if st.button("Quick Analysis (100 scenarios)"):
            quick_analysis(base_params)
        if st.button("Deep Analysis (2,000 scenarios)"):
            deep_analysis(base_params)
        if st.button("Full Optimization (10,000 scenarios → GA)"):
            # Still thread-based; internally GA uses 200-scenario batches.
            full_optimization(base_params)

    # Pricing
    with tabs[5]:
        st.header("💰 V2 Pricing Strategy")
        st.markdown("""
**V2 Basic ($299/mo):** 1,000 scenarios/mo, basic optimization  
**V2 Professional ($599/mo):** 10,000 scenarios, genetic optimization, portfolio analysis  
**V2 Enterprise ($1,199/mo):** Unlimited scenarios, real-time optimization, API access  

**Value Prop:** Save 15–25% on duration and 10–18% on costs via AI schedule optimization. Typical ROI: 300–500% in first project.
""")

# ---------- Entrypoint ----------
if __name__ == "__main__":
    # CLI quick run (no Streamlit UI)
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
    print("Quick CLI run:")
    print(f"Median duration: {int(results['duration_analysis']['median_duration'])} days | "
          f"P90: {int(results['duration_analysis']['p90_duration'])} days")

