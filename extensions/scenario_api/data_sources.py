from __future__ import annotations

from datetime import date
from io import StringIO
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit
from urllib.request import urlopen
import re

import pandas as pd

from .data import ObservedDataset
from .results import TimeSeries


THL_DAILY_SUMMARY_PAGE_URL = (
    "https://sampo.thl.fi/pivot/prod/en/epirapo/covid19case/summary_tshcddaily"
)
THL_CASES_MEASURE_SID = 444833
THL_DEATHS_MEASURE_SID = 492118
THL_HOSPITAL_DISTRICT_ROW_CODE = "hcdmunicipality2020-445222"
SUPPORTED_REGION_LEVELS = {"hospital_district", "country"}


def _validate_region_level(region_level: str) -> None:
    if region_level not in SUPPORTED_REGION_LEVELS:
        raise ValueError(
            f"Invalid region_level '{region_level}'. "
            f"Supported values: {sorted(SUPPORTED_REGION_LEVELS)}"
        )


def _normalize_date(value: Optional[Union[str, date]]) -> Optional[date]:
    if value is None:
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except ValueError as exc:
        raise ValueError(f"Invalid date value '{value}'. Use YYYY-MM-DD format.") from exc


def _resolve_summary_daily_csv_url(timeout: int = 60) -> str:
    with urlopen(THL_DAILY_SUMMARY_PAGE_URL, timeout=timeout) as response:
        html = response.read().decode("utf-8")
    match = re.search(r'href=\"(fact_epirapo_covid19case\.csv\?[^"]+)\"', html)
    if not match:
        raise RuntimeError("Could not resolve THL daily summary CSV export URL")
    return urljoin(THL_DAILY_SUMMARY_PAGE_URL, match.group(1))


def _resolve_daily_date_token(timeout: int = 60) -> str:
    """Resolve encoded daily date token from THL daily summary export URL."""
    csv_url = _resolve_summary_daily_csv_url(timeout=timeout)
    split = urlsplit(csv_url)
    params = parse_qsl(split.query, keep_blank_values=True)
    for key, value in params:
        if key == "row" and value.startswith("dateweek20200101-"):
            return value
    raise RuntimeError("Could not resolve THL daily date row token")


def _build_daily_measure_csv_url(measure_sid: int, timeout: int = 60) -> str:
    """
    Build a daily CSV URL for a specific measure based on THL summary export query.

    Build a query using:
    - row: all hospital districts
    - column: encoded daily date token
    - filter: chosen measure
    """
    date_token = _resolve_daily_date_token(timeout=timeout)
    base = (
        "https://sampo.thl.fi/pivot/prod/en/epirapo/covid19case/"
        "fact_epirapo_covid19case.csv"
    )
    query = urlencode(
        [
            ("row", THL_HOSPITAL_DISTRICT_ROW_CODE),
            ("column", date_token),
            ("filter", f"measure-{measure_sid}"),
        ],
        doseq=True,
    )
    split = urlsplit(base)
    return urlunsplit((split.scheme, split.netloc, split.path, query, ""))


def fetch_thl_cases_raw(url: Optional[str] = None, timeout: int = 60) -> str:
    """Fetch raw THL daily cases export as text."""
    target_url = url or _build_daily_measure_csv_url(THL_CASES_MEASURE_SID, timeout=timeout)
    with urlopen(target_url, timeout=timeout) as response:
        payload = response.read()
    return payload.decode("utf-8")


def fetch_thl_deaths_raw(url: Optional[str] = None, timeout: int = 60) -> str:
    """Fetch raw THL daily deaths export as text (country-level source path)."""
    target_url = url or _build_daily_measure_csv_url(THL_DEATHS_MEASURE_SID, timeout=timeout)
    with urlopen(target_url, timeout=timeout) as response:
        payload = response.read()
    return payload.decode("utf-8")


def save_raw_snapshot(data: str, path: Union[str, Path]) -> str:
    """Save raw text snapshot to disk."""
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(data, encoding="utf-8")
    return str(output)


def load_raw_snapshot(path: Union[str, Path]) -> str:
    """Load raw text snapshot from disk."""
    target = Path(path)
    return target.read_text(encoding="utf-8")


def process_thl_cases_raw_to_table(
    raw_data: str,
    start_date: Optional[Union[str, date]] = None,
    end_date: Optional[Union[str, date]] = None,
    region_level: str = "hospital_district",
    source: str = "THL",
) -> pd.DataFrame:
    """
    Normalize THL raw CSV into long-format table:
    date, region_level, region, variable, value, source.
    """
    _validate_region_level(region_level)
    start = _normalize_date(start_date)
    end = _normalize_date(end_date)
    if start is not None and end is not None and start > end:
        raise ValueError("start_date must be <= end_date")

    frame = pd.read_csv(StringIO(raw_data), sep=";")
    required = {"Time", "Area", "val"}
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise ValueError(f"Missing expected THL columns: {missing}")

    frame = frame.rename(columns={"Time": "time", "Area": "region", "val": "value"})
    frame["value"] = (
        frame["value"]
        .replace({"..": 0, "": 0})
        .fillna(0)
    )
    frame["value"] = pd.to_numeric(frame["value"], errors="coerce")
    frame = frame.dropna(subset=["value"]).copy()
    frame["date"] = pd.to_datetime(frame["time"], format="%Y-%m-%d", errors="coerce").dt.date
    frame = frame.dropna(subset=["date"]).copy()

    if start is not None:
        frame = frame[frame["date"] >= start]
    if end is not None:
        frame = frame[frame["date"] <= end]

    if region_level == "country":
        grouped = frame.groupby("date", as_index=False)["value"].sum()
        grouped["region_level"] = "country"
        grouped["region"] = "Finland"
        grouped["variable"] = "cases"
        grouped["source"] = source
        table = grouped[["date", "region_level", "region", "variable", "value", "source"]]
    else:
        frame["region_level"] = "hospital_district"
        frame["variable"] = "cases"
        frame["source"] = source
        table = frame[["date", "region_level", "region", "variable", "value", "source"]]

    if table.empty:
        raise ValueError("Processed THL dataset is empty after filtering")

    table = table.sort_values(["date", "region"]).reset_index(drop=True)
    return table


def save_processed_table(table: pd.DataFrame, path: Union[str, Path]) -> str:
    """Save normalized processed table to CSV."""
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(output, index=False)
    return str(output)


def load_processed_table(path: Union[str, Path]) -> pd.DataFrame:
    """Load processed table CSV."""
    frame = pd.read_csv(path)
    required = {"date", "region_level", "region", "variable", "value"}
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise ValueError(f"Processed table missing required columns: {missing}")
    frame["date"] = pd.to_datetime(frame["date"]).dt.date
    return frame


def download_and_save_thl_cases_snapshot(
    raw_output_path: Union[str, Path],
    processed_output_path: Union[str, Path],
    start_date: Optional[Union[str, date]] = "2020-01-01",
    end_date: Optional[Union[str, date]] = "2022-12-31",
    region_level: str = "hospital_district",
) -> Tuple[str, str]:
    """Fetch THL data, save raw snapshot and processed local table."""
    raw = fetch_thl_cases_raw()
    raw_path = save_raw_snapshot(raw, raw_output_path)
    table = process_thl_cases_raw_to_table(
        raw,
        start_date=start_date,
        end_date=end_date,
        region_level=region_level,
    )
    processed_path = save_processed_table(table, processed_output_path)
    return raw_path, processed_path


def load_thl_cases_observed_dataset(
    processed_path: Union[str, Path],
    metadata: Optional[Dict[str, Any]] = None,
) -> ObservedDataset:
    """Load processed THL CSV and convert into ObservedDataset."""
    frame = load_processed_table(processed_path)
    data = {
        "date": [d.isoformat() for d in frame["date"].tolist()],
        "region_level": frame["region_level"].astype(str).tolist(),
        "region": frame["region"].astype(str).tolist(),
        "variable": frame["variable"].astype(str).tolist(),
        "value": frame["value"].astype(float).tolist(),
        "cases": frame["value"].astype(float).tolist(),
    }
    default_metadata: Dict[str, Any] = {
        "source": "THL",
        "available_regions": sorted(frame["region"].astype(str).unique().tolist()),
        "available_region_levels": sorted(frame["region_level"].astype(str).unique().tolist()),
        "available_variables": sorted(frame["variable"].astype(str).unique().tolist()),
        "date_min": frame["date"].min().isoformat(),
        "date_max": frame["date"].max().isoformat(),
    }
    merged_metadata = {**default_metadata, **(metadata or {})}
    return ObservedDataset(name="thl_cases", data=data, metadata=merged_metadata)


def thl_dataset_to_timeseries(
    dataset: ObservedDataset,
    variable: str = "cases",
    region: Optional[str] = None,
    region_level: Optional[str] = None,
) -> Union[TimeSeries, List[TimeSeries]]:
    """Convert THL ObservedDataset into one or more TimeSeries objects."""
    frame = pd.DataFrame(dataset.data)
    required = {"date", "region_level", "region", "variable", "value"}
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise ValueError(f"Dataset is missing THL normalized columns: {missing}")

    selected = frame[frame["variable"] == variable].copy()
    if region_level is not None:
        _validate_region_level(region_level)
        selected = selected[selected["region_level"] == region_level]

    if selected.empty:
        raise ValueError(f"No rows found for variable '{variable}' with given filters")

    def _to_series(region_name: str, rows: pd.DataFrame) -> TimeSeries:
        rows = rows.sort_values("date")
        return TimeSeries(
            name=f"{dataset.name}_{variable}_{region_name}",
            times=rows["date"].astype(str).tolist(),
            values=rows["value"].astype(float).tolist(),
            variable=variable,
            source_type="observed",
            source_name=dataset.name,
        )

    if region is not None:
        filtered = selected[selected["region"] == region]
        if filtered.empty:
            raise ValueError(f"Requested region '{region}' not found")
        return _to_series(region, filtered)

    series_list: List[TimeSeries] = []
    for region_name, rows in selected.groupby("region"):
        series_list.append(_to_series(str(region_name), rows))
    if not series_list:
        raise ValueError("No time series could be created from dataset")
    return sorted(series_list, key=lambda ts: ts.name)
