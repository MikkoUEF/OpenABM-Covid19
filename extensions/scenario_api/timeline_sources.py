from __future__ import annotations

from datetime import date
from io import StringIO
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import pandas as pd

OXCGRT_COMPACT_CSV_URL = (
    "https://raw.githubusercontent.com/OxCGRT/covid-policy-tracker/master/data/OxCGRT_nat_latest.csv"
)
OXCGRT_FALLBACK_CSV_URLS: Tuple[str, ...] = (
    "https://raw.githubusercontent.com/OxCGRT/covid-policy-tracker/master/data/OxCGRT_nat_latest.csv",
    "https://raw.githubusercontent.com/OxCGRT/covid-policy-tracker/master/data/OxCGRT_latest.csv",
    "https://raw.githubusercontent.com/OxCGRT/covid-policy-tracker/master/data/OxCGRT_compact.csv",
    "https://raw.githubusercontent.com/OxCGRT/covid-policy-dataset/main/data/OxCGRT_nat_latest.csv",
    "https://raw.githubusercontent.com/OxCGRT/covid-policy-dataset/main/data/OxCGRT_latest.csv",
    "https://raw.githubusercontent.com/OxCGRT/covid-policy-dataset/main/data/OxCGRT_compact.csv",
)

# Explicit first-version mapping from OxCGRT policy indicators to normalized event types.
# Some source schemas may provide M/EV variants. We accept alternatives where needed.
OXCGRT_EVENT_TYPE_TO_COLUMNS: Dict[str, Tuple[str, ...]] = {
    "school_closing": ("C1M", "C1"),
    "workplace_closing": ("C2M", "C2"),
    "public_events": ("C3M", "C3"),
    "gathering_restrictions": ("C4M", "C4"),
    "public_transport": ("C5M", "C5"),
    "stay_at_home": ("C6M", "C6"),
    "internal_movement": ("C7M", "C7"),
    "international_travel": ("C8EV", "C8M", "C8"),
    "public_information": ("H1", "H1M"),
    "testing_policy": ("H2",),
    "contact_tracing": ("H3",),
    "facial_coverings": ("H6M", "H6"),
    "vaccination_policy": ("H7",),
    "elderly_protection": ("H8M", "H8"),
}


def fetch_oxcgrt_finland_raw(url: str = OXCGRT_COMPACT_CSV_URL, timeout: int = 60) -> str:
    """Fetch raw OxCGRT CSV as UTF-8 text, with fallback URLs for schema moves."""
    candidates = [url] + [u for u in OXCGRT_FALLBACK_CSV_URLS if u != url]
    errors = []
    for target in candidates:
        request = Request(target, headers={"User-Agent": "OpenABM-Covid19 timeline ingestor"})
        try:
            with urlopen(request, timeout=timeout) as response:
                payload = response.read()
            return payload.decode("utf-8")
        except (HTTPError, URLError) as exc:
            errors.append(f"{target} -> {exc}")
            continue
    raise RuntimeError("Could not fetch OxCGRT CSV from any known URL:\n" + "\n".join(errors))


def save_timeline_raw_snapshot(data: str, path: Union[str, Path]) -> str:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(data, encoding="utf-8")
    return str(output)


def load_timeline_raw_snapshot(path: Union[str, Path]) -> str:
    return Path(path).read_text(encoding="utf-8")


def _normalize_date(value: Optional[Union[str, date]]) -> Optional[date]:
    if value is None:
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except ValueError as exc:
        raise ValueError(f"Invalid date value '{value}'. Use YYYY-MM-DD format.") from exc


def _resolve_indicator_columns(frame: pd.DataFrame) -> Dict[str, str]:
    available = list(frame.columns)

    def _pick_column(candidates: Tuple[str, ...]) -> Optional[str]:
        # Prefer exact indicator code match, then code-prefixed columns
        # used by newer OxCGRT schemas (e.g. "C1M_School closing").
        for col in candidates:
            if col in available:
                return col
        for col in candidates:
            prefixed = next((name for name in available if name.startswith(f"{col}_")), None)
            if prefixed is not None:
                return prefixed
        return None

    resolved: Dict[str, str] = {}
    missing = []
    for event_type, candidates in OXCGRT_EVENT_TYPE_TO_COLUMNS.items():
        selected = _pick_column(candidates)
        if selected is None:
            missing.append(f"{event_type} ({'/'.join(candidates)})")
        else:
            resolved[event_type] = selected
    if missing:
        raise ValueError(f"Missing expected OxCGRT columns: {missing}")
    return resolved


def process_oxcgrt_finland_raw_to_events(
    raw_data: Union[str, pd.DataFrame],
    start_date: Optional[Union[str, date]] = "2020-01-01",
    end_date: Optional[Union[str, date]] = "2022-12-31",
) -> pd.DataFrame:
    """
    Normalize OxCGRT Finland policy indicators to long-format timeline events table.

    Output columns: date, source, region_level, region, event_type, value, notes, source_code
    """
    start = _normalize_date(start_date)
    end = _normalize_date(end_date)
    if start is not None and end is not None and start > end:
        raise ValueError("start_date must be <= end_date")

    frame = pd.read_csv(StringIO(raw_data)) if isinstance(raw_data, str) else raw_data.copy()
    required_base = {"Date"}
    missing_base = sorted(required_base.difference(frame.columns))
    if missing_base:
        raise ValueError(f"Missing expected OxCGRT columns: {missing_base}")

    if "CountryCode" in frame.columns:
        finland = frame[frame["CountryCode"] == "FIN"].copy()
    elif "CountryName" in frame.columns:
        finland = frame[frame["CountryName"] == "Finland"].copy()
    else:
        raise ValueError("Missing expected OxCGRT columns: ['CountryCode' or 'CountryName']")

    if finland.empty:
        raise RuntimeError("Finland subset is empty in OxCGRT raw data")

    # Keep country-level national total rows only when jurisdiction is provided.
    if "Jurisdiction" in finland.columns:
        finland = finland[finland["Jurisdiction"] == "NAT_TOTAL"].copy()
        if finland.empty:
            raise RuntimeError("Finland subset is empty after jurisdiction filtering")

    resolved_columns = _resolve_indicator_columns(finland)

    finland["date"] = pd.to_datetime(finland["Date"].astype(str), format="%Y%m%d", errors="coerce").dt.date
    finland = finland.dropna(subset=["date"]).copy()

    if start is not None:
        finland = finland[finland["date"] >= start]
    if end is not None:
        finland = finland[finland["date"] <= end]

    if finland.empty:
        raise RuntimeError("Finland subset is empty after date filtering")

    pieces = []
    for event_type, source_col in resolved_columns.items():
        subset = finland[["date", source_col]].copy()
        subset = subset.rename(columns={source_col: "value"})
        subset["value"] = pd.to_numeric(subset["value"], errors="coerce")
        subset = subset.dropna(subset=["value"]).copy()
        subset["value"] = subset["value"].astype(int)
        subset["source"] = "OxCGRT"
        subset["region_level"] = "country"
        subset["region"] = "Finland"
        subset["event_type"] = event_type
        subset["notes"] = ""
        subset["source_code"] = source_col
        pieces.append(subset)

    if not pieces:
        raise RuntimeError("Processed timeline output is empty")

    table = pd.concat(pieces, ignore_index=True)
    table = table[
        ["date", "source", "region_level", "region", "event_type", "value", "notes", "source_code"]
    ]
    table = table.sort_values(["date", "event_type"]).reset_index(drop=True)

    if table.empty:
        raise RuntimeError("Processed timeline output is empty after normalization")

    return table


def save_processed_timeline_events(table: pd.DataFrame, path: Union[str, Path]) -> str:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(output, index=False)
    return str(output)


def load_processed_timeline_events_table(path: Union[str, Path]) -> pd.DataFrame:
    frame = pd.read_csv(path)
    required = {"date", "source", "region_level", "region", "event_type", "value", "notes"}
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise ValueError(f"Processed timeline table missing required columns: {missing}")
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce").dt.date
    frame = frame.dropna(subset=["date"]).copy()
    return frame


def download_and_save_oxcgrt_finland_timeline(
    raw_output_path: Union[str, Path],
    processed_output_path: Union[str, Path],
    start_date: Optional[Union[str, date]] = "2020-01-01",
    end_date: Optional[Union[str, date]] = "2022-12-31",
    url: str = OXCGRT_COMPACT_CSV_URL,
) -> Tuple[str, str]:
    """Fetch OxCGRT, save raw snapshot, normalize Finland events, save processed CSV."""
    raw = fetch_oxcgrt_finland_raw(url=url)
    raw_path = save_timeline_raw_snapshot(raw, raw_output_path)
    table = process_oxcgrt_finland_raw_to_events(raw, start_date=start_date, end_date=end_date)
    processed_path = save_processed_timeline_events(table, processed_output_path)
    return raw_path, processed_path
