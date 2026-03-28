from __future__ import annotations

import math
from datetime import date
from typing import Any, Dict, Optional, Sequence

from .data_sources import load_observed_cases_timeseries_for_region
from .data import smooth_timeseries_moving_average
from .mapping_profiles import (
    ContactPolicyMappingProfile,
    MaskMappingProfile,
    TestingTracingMappingProfile,
)
from .region_config import RegionConfig, population_scale_factor
from .results import TimeSeries, result_to_timeseries
from .runner import run_single_shp_cases_scenario
from .timeline import TimelineEvent, load_timeline_events_from_processed
from .timeline_mapper import SUPPORTED_EVENT_TYPES, map_timeline_events_to_interventions
from .interventions import MaskProfile


def _parse_iso_date(value: str) -> date:
    return date.fromisoformat(value)


def _filter_timeline_events_window(
    events: Sequence[TimelineEvent],
    start_date: str,
    end_date: str,
) -> list[TimelineEvent]:
    start = _parse_iso_date(start_date)
    end = _parse_iso_date(end_date)
    if start > end:
        raise ValueError("start_date must be <= end_date")
    filtered = [e for e in events if start <= _parse_iso_date(e.date) <= end]
    if not filtered:
        raise RuntimeError("No timeline events after filtering to requested date window")
    return filtered


def scale_timeseries_values(
    timeseries: TimeSeries,
    factor: float,
    new_name: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> TimeSeries:
    if factor <= 0:
        raise ValueError("scale factor must be > 0")
    merged_metadata = {
        **(timeseries.metadata or {}),
        "scaled": True,
        "scale_factor": float(factor),
        **(metadata or {}),
    }
    return TimeSeries(
        name=new_name or f"{timeseries.name}_scaled",
        times=list(timeseries.times),
        values=[float(v) * float(factor) for v in timeseries.values],
        variable=timeseries.variable,
        source_type=timeseries.source_type,
        source_name=timeseries.source_name,
        metadata=merged_metadata,
    )


def run_region_scenario_against_observed(
    region_config: RegionConfig,
    observed_cases_path: str,
    timeline_processed_path: str,
    reference_start_date: str,
    simulation_steps: int,
    mask_mapping_profile: MaskMappingProfile,
    contact_mapping_profile: ContactPolicyMappingProfile,
    testing_tracing_mapping_profile: Optional[TestingTracingMappingProfile] = None,
    mask_profiles: Optional[Dict[str, MaskProfile]] = None,
    model_factory: Optional[Any] = None,
    result_variable: str = "cases",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    use_openabm: bool = True,
    initial_infected: int = 100,
    strict_runtime_updates: bool = True,
) -> Dict[str, Any]:
    if simulation_steps <= 0:
        raise ValueError("simulation_steps must be > 0")
    if region_config.simulated_population <= 0:
        raise ValueError("simulated_population must be > 0")
    if region_config.real_population <= 0:
        raise ValueError("real_population must be > 0")

    observed_ts = load_observed_cases_timeseries_for_region(
        processed_path=observed_cases_path,
        region=region_config.name,
        region_level=region_config.region_level,
        start_date=start_date,
        end_date=end_date,
    )

    timeline_events_all = load_timeline_events_from_processed(timeline_processed_path)
    if start_date is not None and end_date is not None:
        timeline_events_all = _filter_timeline_events_window(
            timeline_events_all,
            start_date=start_date,
            end_date=end_date,
        )
    timeline_events_supported = [e for e in timeline_events_all if e.event_type in SUPPORTED_EVENT_TYPES]
    if not timeline_events_supported:
        raise RuntimeError("No supported timeline events found for mapping")
    interventions = map_timeline_events_to_interventions(
        events=timeline_events_supported,
        mask_mapping_profile=mask_mapping_profile,
        contact_mapping_profile=contact_mapping_profile,
        testing_tracing_mapping_profile=testing_tracing_mapping_profile,
        mask_profiles=mask_profiles,
        reference_start_date=reference_start_date,
    )
    if not interventions:
        raise RuntimeError("No interventions created after timeline mapping")

    selected_factory = None
    selected_extractor = None
    if isinstance(model_factory, tuple) and len(model_factory) == 2:
        selected_factory, selected_extractor = model_factory
    else:
        selected_factory = model_factory
    use_openabm_flag = bool(use_openabm or selected_factory is not None)
    result, _scaled_ts = run_single_shp_cases_scenario(
        region_config=region_config,
        timeline_events=timeline_events_supported,
        mask_mapping_profile=mask_mapping_profile,
        contact_mapping_profile=contact_mapping_profile,
        testing_tracing_mapping_profile=testing_tracing_mapping_profile,
        mask_profiles=mask_profiles,
        reference_start_date=reference_start_date,
        simulation_steps=simulation_steps,
        use_openabm=use_openabm_flag,
        model_factory=selected_factory,
        result_extractor=selected_extractor,
        initial_infected=initial_infected,
        strict_runtime_updates=strict_runtime_updates,
    )
    if bool(result.metadata.get("openabm_used", False)) and not bool(
        result.metadata.get("seed_override_applied", False)
    ):
        raise RuntimeError(
            "OpenABM seed override failed: expected n_seed_infection to match initial_infected."
        )

    simulated_raw_ts = result_to_timeseries(result, variable=result_variable)
    scale_factor = population_scale_factor(region_config)
    simulated_scaled_ts = scale_timeseries_values(
        simulated_raw_ts,
        factor=scale_factor,
        new_name=f"{simulated_raw_ts.name}_scaled_{region_config.name.replace(' ', '_')}",
        metadata={
            "region_name": region_config.name,
            "region_level": region_config.region_level,
            "reference_start_date": reference_start_date,
            "start_date": start_date or observed_ts.metadata.get("date_min"),
            "end_date": end_date or observed_ts.metadata.get("date_max"),
            "scaling_rule": "scaled_cases = simulated_cases * (real_population / simulated_population)",
        },
    )

    return {
        "region_config": region_config,
        "observed_timeseries": observed_ts,
        "simulated_raw_timeseries": simulated_raw_ts,
        "simulated_scaled_timeseries": simulated_scaled_ts,
        "timeline_events": timeline_events_supported,
        "interventions": interventions,
        "interventions_count": len(interventions),
        "metadata": {
            "region_name": region_config.name,
            "real_population": region_config.real_population,
            "simulated_population": region_config.simulated_population,
            "scale_factor": scale_factor,
            "reference_start_date": reference_start_date,
            "start_date": start_date or observed_ts.metadata.get("date_min"),
            "end_date": end_date or observed_ts.metadata.get("date_max"),
            "timeline_events_used": len(timeline_events_supported),
            "interventions_created": len(interventions),
            "observed_points": len(observed_ts.values),
            "simulated_raw_points": len(simulated_raw_ts.values),
            "simulated_scaled_points": len(simulated_scaled_ts.values),
            "openabm_used": bool(result.metadata.get("openabm_used", False)),
            "initial_infected": int(initial_infected),
            "seed_override_applied": bool(result.metadata.get("seed_override_applied", False)),
            "openabm_n_seed_infection": result.metadata.get("openabm_n_seed_infection"),
            "runtime_diagnostics": dict(result.metadata.get("runtime_diagnostics", {})),
        },
        "runtime_diagnostics": dict(result.metadata.get("runtime_diagnostics", {})),
    }


def compute_r_proxy_from_incidence(
    timeseries: TimeSeries,
    generation_interval: int = 5,
    epsilon: float = 1e-9,
    new_name: Optional[str] = None,
) -> TimeSeries:
    """
    Compute a simple R-like diagnostic proxy from incidence values.

    R_proxy[t] = incidence[t] / incidence[t - generation_interval]
    """
    if generation_interval <= 0:
        raise ValueError("generation_interval must be > 0")
    if timeseries is None or not getattr(timeseries, "values", None):
        raise ValueError("timeseries must contain incidence values")

    values = [float(v) for v in timeseries.values]
    out: list[float] = []
    valid_ratio_count = 0
    for idx, numerator in enumerate(values):
        lag_idx = idx - generation_interval
        if lag_idx < 0:
            out.append(float("nan"))
            continue
        denominator = float(values[lag_idx])
        if math.isnan(denominator) or abs(denominator) <= epsilon:
            out.append(float("nan"))
            continue
        out.append(float(numerator) / denominator)
        valid_ratio_count += 1

    if valid_ratio_count == 0:
        raise ValueError(
            "R proxy calculation failed: no valid lagged-incidence denominators "
            f"(generation_interval={generation_interval}, epsilon={epsilon})."
        )

    return TimeSeries(
        name=new_name or f"{timeseries.name}_r_proxy_gi{generation_interval}",
        times=list(timeseries.times),
        values=out,
        variable="r_proxy",
        source_type=timeseries.source_type,
        source_name=timeseries.source_name,
        metadata={
            **(timeseries.metadata or {}),
            "method": "ratio_over_lagged_incidence",
            "generation_interval": int(generation_interval),
            "input_variable": timeseries.variable,
        },
    )


def compute_smoothed_r_proxy(
    timeseries: TimeSeries,
    generation_interval: int = 5,
    smoothing_window: int = 7,
    new_name: Optional[str] = None,
) -> TimeSeries:
    """Compute lag-ratio R proxy and apply moving-average smoothing."""
    raw = compute_r_proxy_from_incidence(
        timeseries=timeseries,
        generation_interval=generation_interval,
    )
    smoothed = smooth_timeseries_moving_average(
        raw,
        window=smoothing_window,
        new_name=new_name or f"{raw.name}_smoothed_ma{smoothing_window}",
    )
    smoothed.metadata = {
        **(smoothed.metadata or {}),
        "input_variable": timeseries.variable,
        "generation_interval": int(generation_interval),
        "smoothing_window": int(smoothing_window),
    }
    return smoothed
