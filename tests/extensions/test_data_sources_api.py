from pathlib import Path

import pandas as pd
import pytest

from extensions.scenario_api import (
    download_and_save_thl_cases_snapshot,
    load_thl_cases_observed_dataset,
    load_raw_snapshot,
    process_thl_cases_raw_to_table,
    save_processed_table,
    save_raw_snapshot,
    thl_dataset_to_timeseries,
)


RAW_SAMPLE = """Time;Area;val
2020-02-09;Åland;1
2020-02-10;Åland;0
2020-02-11;Åland;2
2020-02-09;Helsinki and Uusimaa Hospital District;3
2020-02-10;Helsinki and Uusimaa Hospital District;1
2020-02-11;Helsinki and Uusimaa Hospital District;4
"""


def test_process_thl_cases_raw_to_table_hospital_district_daily():
    table = process_thl_cases_raw_to_table(
        RAW_SAMPLE,
        start_date="2020-01-01",
        end_date="2020-12-31",
        region_level="hospital_district",
    )
    assert set(["date", "region_level", "region", "variable", "value"]).issubset(table.columns)
    assert table["region_level"].unique().tolist() == ["hospital_district"]
    assert table["variable"].unique().tolist() == ["cases"]
    assert table["date"].min().isoformat() == "2020-02-09"
    assert table["date"].max().isoformat() == "2020-02-11"
    assert table["region"].nunique() == 2


def test_process_thl_cases_raw_to_table_country_aggregates():
    table = process_thl_cases_raw_to_table(RAW_SAMPLE, region_level="country")
    assert table["region_level"].unique().tolist() == ["country"]
    assert table["region"].unique().tolist() == ["Finland"]
    by_date = dict(zip(table["date"].astype(str), table["value"].astype(float)))
    assert by_date["2020-02-09"] == 4.0
    assert by_date["2020-02-10"] == 1.0
    assert by_date["2020-02-11"] == 6.0


def test_process_thl_cases_raw_to_table_rejects_invalid_region_level():
    with pytest.raises(ValueError, match="Invalid region_level"):
        process_thl_cases_raw_to_table(RAW_SAMPLE, region_level="municipality")


def test_observed_dataset_and_timeseries_from_processed_csv(tmp_path: Path):
    table = process_thl_cases_raw_to_table(RAW_SAMPLE, region_level="hospital_district")
    processed_path = tmp_path / "thl_processed.csv"
    save_processed_table(table, processed_path)

    dataset = load_thl_cases_observed_dataset(processed_path)
    assert dataset.metadata["source"] == "THL"
    assert "Helsinki and Uusimaa Hospital District" in dataset.metadata["available_regions"]

    single = thl_dataset_to_timeseries(
        dataset,
        variable="cases",
        region="Åland",
        region_level="hospital_district",
    )
    assert single.variable == "cases"
    assert len(single.times) == 3
    assert single.values[-1] == 2.0

    many = thl_dataset_to_timeseries(dataset, variable="cases", region_level="hospital_district")
    assert isinstance(many, list)
    assert len(many) == 2


def test_raw_snapshot_roundtrip(tmp_path: Path):
    raw_path = tmp_path / "raw.csv"
    save_raw_snapshot(RAW_SAMPLE, raw_path)
    loaded = load_raw_snapshot(raw_path)
    assert loaded == RAW_SAMPLE


def test_download_and_save_thl_cases_snapshot_with_mock(monkeypatch, tmp_path: Path):
    from extensions.scenario_api import data_sources

    monkeypatch.setattr(data_sources, "fetch_thl_cases_raw", lambda: RAW_SAMPLE)
    raw = tmp_path / "raw" / "thl_raw.csv"
    processed = tmp_path / "processed" / "thl_processed.csv"

    raw_path, processed_path = download_and_save_thl_cases_snapshot(
        raw_output_path=raw,
        processed_output_path=processed,
        start_date="2020-01-01",
        end_date="2020-12-31",
        region_level="hospital_district",
    )
    assert Path(raw_path).exists()
    assert Path(processed_path).exists()
    loaded = pd.read_csv(processed_path)
    assert not loaded.empty
