from pathlib import Path

import pandas as pd
import pytest

from extensions.scenario_api import (
    PolicyTimelineEvent,
    get_default_shp_region_config,
    load_observed_cases_timeseries_for_region,
    population_scale_factor,
    default_mask_mapping_profile,
    default_contact_policy_mapping_profile,
    default_testing_tracing_mapping_profile,
    default_mask_effectiveness_profiles,
    run_single_shp_cases_scenario,
)


def test_get_default_shp_region_config_and_scale_factor():
    region = get_default_shp_region_config(
        name="Helsinki and Uusimaa Hospital District",
        simulated_population=200000,
    )
    assert region.region_level == "hospital_district"
    factor = population_scale_factor(region)
    assert factor > 1.0


def test_get_default_shp_region_config_unknown_raises():
    with pytest.raises(ValueError, match="Unknown SHP name"):
        get_default_shp_region_config("Unknown SHP", simulated_population=100000)


def test_load_observed_cases_timeseries_for_region(tmp_path: Path):
    table = pd.DataFrame(
        {
            "date": ["2020-01-01", "2020-01-02", "2020-01-01"],
            "region_level": ["hospital_district", "hospital_district", "hospital_district"],
            "region": [
                "Helsinki and Uusimaa Hospital District",
                "Helsinki and Uusimaa Hospital District",
                "Pirkanmaa Hospital District",
            ],
            "variable": ["cases", "cases", "cases"],
            "value": [10, 11, 3],
            "source": ["THL", "THL", "THL"],
        }
    )
    p = tmp_path / "thl_processed.csv"
    table.to_csv(p, index=False)

    ts = load_observed_cases_timeseries_for_region(
        processed_path=p,
        region="Helsinki and Uusimaa Hospital District",
        region_level="hospital_district",
    )
    assert ts.variable == "cases"
    assert len(ts.values) == 2


def test_run_single_shp_cases_scenario_returns_scaled_series():
    region = get_default_shp_region_config(
        name="Helsinki and Uusimaa Hospital District",
        simulated_population=200000,
    )
    events = [
        PolicyTimelineEvent(
            date="2020-01-01",
            source="OxCGRT",
            region_level="country",
            region="Finland",
            event_type="facial_coverings",
            value=1,
        ),
        PolicyTimelineEvent(
            date="2020-01-10",
            source="OxCGRT",
            region_level="country",
            region="Finland",
            event_type="facial_coverings",
            value=2,
        ),
        PolicyTimelineEvent(
            date="2020-01-01",
            source="OxCGRT",
            region_level="country",
            region="Finland",
            event_type="school_closing",
            value=2,
        ),
    ]

    result, scaled = run_single_shp_cases_scenario(
        region_config=region,
        timeline_events=events,
        mask_mapping_profile=default_mask_mapping_profile(),
        contact_mapping_profile=default_contact_policy_mapping_profile(),
        testing_tracing_mapping_profile=default_testing_tracing_mapping_profile(),
        mask_profiles=default_mask_effectiveness_profiles(),
        reference_start_date="2020-01-01",
        simulation_steps=20,
        use_openabm=False,
    )

    assert len(result.raw_outputs["cases"]) == 20
    assert len(scaled.values) == 20
    assert scaled.metadata.get("scaled") is True
