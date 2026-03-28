from pathlib import Path

import pytest

from extensions.scenario_api import (
    TimeSeries,
    default_contact_policy_mapping_profile,
    default_mask_effectiveness_profiles,
    default_mask_mapping_profile,
    default_testing_tracing_mapping_profile,
    get_default_shp_region_config,
    run_region_scenario_against_observed,
    scale_timeseries_values,
)


def test_scale_timeseries_values():
    ts = TimeSeries(
        name="x",
        times=[0, 1, 2],
        values=[1.0, 2.0, 3.0],
        variable="cases",
        source_type="simulation",
        source_name="dummy",
    )
    scaled = scale_timeseries_values(ts, factor=2.5)
    assert scaled.values == [2.5, 5.0, 7.5]
    assert scaled.metadata["scaled"] is True


def test_run_region_scenario_against_observed_smoke_with_local_files():
    repo = Path("/home/ubuntu/OpenABM-Covid19")
    bundle = run_region_scenario_against_observed(
        region_config=get_default_shp_region_config("Helsinki and Uusimaa", simulated_population=200000),
        observed_cases_path=str(repo / "data" / "processed" / "thl_cases_2020_2022_processed_daily.csv"),
        timeline_processed_path=str(repo / "data" / "processed" / "oxcgrt_finland_2020_2022_timeline.csv"),
        reference_start_date="2020-03-01",
        start_date="2020-03-01",
        end_date="2020-06-30",
        simulation_steps=122,
        mask_mapping_profile=default_mask_mapping_profile(),
        contact_mapping_profile=default_contact_policy_mapping_profile(),
        testing_tracing_mapping_profile=default_testing_tracing_mapping_profile(),
        mask_profiles=default_mask_effectiveness_profiles(),
    )

    assert bundle["metadata"]["region_name"] == "Helsinki and Uusimaa Hospital District"
    assert bundle["metadata"]["start_date"] == "2020-03-01"
    assert bundle["metadata"]["end_date"] == "2020-06-30"
    assert bundle["metadata"]["observed_points"] > 0
    assert bundle["metadata"]["simulated_scaled_points"] == 122
    assert bundle["metadata"]["timeline_events_used"] > 0


def test_run_region_scenario_against_observed_missing_region_raises():
    repo = Path("/home/ubuntu/OpenABM-Covid19")
    bad = get_default_shp_region_config("Helsinki and Uusimaa", simulated_population=200000)
    bad.name = "Missing Region"
    with pytest.raises(ValueError, match="Missing observed cases"):
        run_region_scenario_against_observed(
            region_config=bad,
            observed_cases_path=str(repo / "data" / "processed" / "thl_cases_2020_2022_processed_daily.csv"),
            timeline_processed_path=str(repo / "data" / "processed" / "oxcgrt_finland_2020_2022_timeline.csv"),
            reference_start_date="2020-03-01",
            start_date="2020-03-01",
            end_date="2020-06-30",
            simulation_steps=10,
            mask_mapping_profile=default_mask_mapping_profile(),
            contact_mapping_profile=default_contact_policy_mapping_profile(),
            testing_tracing_mapping_profile=default_testing_tracing_mapping_profile(),
            mask_profiles=default_mask_effectiveness_profiles(),
        )
