from dataclasses import dataclass
from typing import Dict, Any, List, Callable, Optional
from numbers import Number
from .resolver import ResolvedScenario
from .events import TimelineEvent
from .interventions import InterventionSet, compile_network_multipliers
from .scenarios import create_scenario
from .resolver import resolve_scenario
from .timeline_mapper import map_timeline_events_to_interventions
from .timeline_mapper import SUPPORTED_EVENT_TYPES
from .mapping_profiles import (
    MaskMappingProfile,
    ContactPolicyMappingProfile,
    TestingTracingMappingProfile,
)
from .interventions import MaskProfile
from .region_config import RegionConfig, population_scale_factor
from .openabm_adapter import is_openabm_available, create_openabm_runner_components


@dataclass
class SimulationResult:
    """Result of a simulation run."""
    scenario_name: str
    raw_outputs: Dict[str, List[float]]
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


def apply_event_to_params(current_params: Dict[str, Any], event: TimelineEvent) -> Dict[str, Any]:
    """Apply an event to current parameters."""
    new_params = current_params.copy()
    if event.action == "set":
        new_params[event.target] = event.value
    elif event.action == "scale":
        if event.target not in new_params:
            raise ValueError(f"Cannot scale {event.target}: not in params")
        new_params[event.target] *= event.value
    return new_params


def run_scenario(resolved_scenario: ResolvedScenario, steps: int, model_factory: Optional[Callable] = None, result_extractor: Optional[Callable] = None) -> SimulationResult:
    """Run a resolved scenario for a number of steps."""
    current_params = resolved_scenario.resolved_params.copy()
    raw_outputs: Dict[str, List[float]] = {"cases": []}
    model = None
    if model_factory is not None:
        try:
            model = model_factory(current_params.copy(), resolved_scenario)
        except TypeError:
            model = model_factory(current_params.copy())
    dummy_cases = 1.0

    for t in range(steps):
        # Apply events at this time
        if t in resolved_scenario.events_by_time:
            for event in resolved_scenario.events_by_time[t]:
                current_params = apply_event_to_params(current_params, event)
            if model is not None and hasattr(model, "update_params"):
                model.update_params(current_params.copy())

        if model is None:
            # Dummy simulation logic for smoke tests when no real model is provided.
            dummy_cases = dummy_cases * float(current_params.get("relative_transmission", 1.0))
            reported_cases = dummy_cases * float(current_params.get("testing_rate", 1.0))
            raw_outputs["cases"].append(float(reported_cases))
            continue

        step_output = model.step() if hasattr(model, "step") else None

        if result_extractor is not None:
            extracted = result_extractor(model, step_output, t, current_params.copy())
        elif isinstance(step_output, dict):
            extracted = step_output
        elif isinstance(step_output, Number):
            extracted = {"cases": float(step_output)}
        elif hasattr(model, "get_outputs"):
            extracted = model.get_outputs()
        else:
            raise ValueError(
                "Could not extract outputs from model. Provide result_extractor "
                "or return dict/number from model.step()."
            )

        if not isinstance(extracted, dict):
            raise ValueError("result_extractor must return a dict[str, float]-like object")

        for key, value in extracted.items():
            raw_outputs.setdefault(key, []).append(float(value))

    return SimulationResult(
        scenario_name=resolved_scenario.name,
        raw_outputs=raw_outputs,
        metadata={"steps": steps, "final_params": current_params.copy()},
    )


def _aggregate_network_multiplier(
    network_multipliers: Dict[str, float],
    network_weights: Optional[Dict[str, float]] = None,
) -> float:
    # Explicit first-pass default weights for converting network multipliers into
    # one relative_transmission multiplier for the single-SHP bridge mode.
    weights = network_weights or {"work": 0.35, "school": 0.15, "random": 0.50}
    total_weight = 0.0
    total_value = 0.0
    for network, weight in weights.items():
        if weight <= 0:
            continue
        total_weight += float(weight)
        total_value += float(weight) * float(network_multipliers.get(network, 1.0))
    if total_weight <= 0:
        return 1.0
    return total_value / total_weight


def _scale_timeseries_values(series: Any, factor: float, name_suffix: str = "scaled") -> Any:
    from .results import TimeSeries

    return TimeSeries(
        name=f"{series.name}_{name_suffix}",
        times=list(series.times),
        values=[float(v) * float(factor) for v in series.values],
        variable=series.variable,
        source_type=series.source_type,
        source_name=series.source_name,
        metadata={**(series.metadata or {}), "scaled": True, "scale_factor": float(factor)},
    )


def run_single_shp_cases_scenario(
    region_config: RegionConfig,
    timeline_events: List[Any],
    mask_mapping_profile: MaskMappingProfile,
    contact_mapping_profile: ContactPolicyMappingProfile,
    testing_tracing_mapping_profile: Optional[TestingTracingMappingProfile] = None,
    mask_profiles: Optional[Dict[str, MaskProfile]] = None,
    reference_start_date: str = "2020-01-01",
    simulation_steps: Optional[int] = None,
    use_openabm: bool = False,
    network_weights: Optional[Dict[str, float]] = None,
) -> tuple[SimulationResult, Any]:
    """Run one independent SHP scenario and return raw result plus scaled simulated cases."""
    if region_config.simulated_population <= 0:
        raise ValueError("simulated_population must be > 0")
    if region_config.real_population <= 0:
        raise ValueError("real_population must be > 0")

    supported_events = [e for e in timeline_events if getattr(e, "event_type", None) in SUPPORTED_EVENT_TYPES]
    skipped_events = len(timeline_events) - len(supported_events)

    mapped_interventions = map_timeline_events_to_interventions(
        events=supported_events,
        mask_mapping_profile=mask_mapping_profile,
        contact_mapping_profile=contact_mapping_profile,
        testing_tracing_mapping_profile=testing_tracing_mapping_profile,
        mask_profiles=mask_profiles,
        reference_start_date=reference_start_date,
    )
    if not mapped_interventions:
        raise ValueError("Timeline mapping produced no interventions for single SHP run")

    max_end = max(int(i.end) for i in mapped_interventions if i.end is not None)
    steps = int(simulation_steps) if simulation_steps is not None else max_end
    if steps <= 0:
        raise ValueError("simulation_steps must be > 0")

    intervention_set = InterventionSet(mapped_interventions)
    transmission_events: List[TimelineEvent] = []
    for t in range(steps):
        multipliers = compile_network_multipliers(intervention_set, t=t)
        agg = _aggregate_network_multiplier(multipliers, network_weights=network_weights)
        transmission_events.append(
            TimelineEvent(
                time=t,
                action="set",
                target="relative_transmission",
                value=float(agg),
                metadata={"derived_from": "timeline_interventions"},
            )
        )

    scenario = create_scenario(
        name=f"single_shp_{region_config.name.replace(' ', '_')}",
        base_params={
            "relative_transmission": 1.0,
            "testing_rate": 1.0,
        },
        events=transmission_events,
    )
    resolved = resolve_scenario(scenario)

    model_factory = None
    result_extractor = None
    openabm_used = False
    if use_openabm and is_openabm_available():
        model_factory, result_extractor = create_openabm_runner_components(resolved)
        openabm_used = True

    result = run_scenario(
        resolved_scenario=resolved,
        steps=steps,
        model_factory=model_factory,
        result_extractor=result_extractor,
    )
    result.metadata = result.metadata or {}
    result.metadata.update(
        {
            "region_name": region_config.name,
            "region_level": region_config.region_level,
            "simulated_population": region_config.simulated_population,
            "real_population": region_config.real_population,
            "timeline_events_input": len(timeline_events),
            "timeline_events_supported": len(supported_events),
            "timeline_events_skipped": skipped_events,
            "mapped_interventions": len(mapped_interventions),
            "openabm_used": openabm_used,
        }
    )

    from .results import result_to_timeseries

    simulated_cases = result_to_timeseries(result, variable="cases")
    factor = population_scale_factor(region_config)
    scaled_cases = _scale_timeseries_values(simulated_cases, factor=factor, name_suffix="scaled_to_real_population")
    scaled_cases.metadata.update(
        {
            "region_name": region_config.name,
            "region_level": region_config.region_level,
            "scaling_rule": "scaled_cases = simulated_cases * (real_population / simulated_population)",
        }
    )
    return result, scaled_cases
