from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Dict, Optional, Union

import pandas as pd


def mobility_to_work_multiplier(
    mobility_value: float,
    scale: float = 1.0,
    floor: float = 0.1,
    ceiling: float = 1.0,
) -> float:
    """
    Convert workplace mobility change (%) to a transmission multiplier.

    Formula: multiplier = 1 + scale * (mobility_value / 100)
    """
    raw = 1.0 + float(scale) * (float(mobility_value) / 100.0)
    return float(min(max(raw, float(floor)), float(ceiling)))


def mobility_to_random_multiplier(
    mobility_value: float,
    scale: float = 1.0,
    floor: float = 0.1,
    ceiling: float = 1.0,
) -> float:
    """
    Convert retail/recreation mobility change (%) to a random-contact multiplier.

    Formula: multiplier = 1 + scale * (mobility_value / 100)
    """
    raw = 1.0 + float(scale) * (float(mobility_value) / 100.0)
    return float(min(max(raw, float(floor)), float(ceiling)))


def load_google_mobility_table(
    processed_path: Union[str, Path],
    region: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> pd.DataFrame:
    """
    Load a processed Google mobility CSV with at least:
    - date
    - workplace_percent_change_from_baseline
    - retail_and_recreation_percent_change_from_baseline
    Optional:
    - region
    """
    path = Path(processed_path)
    if not path.exists():
        raise ValueError(f"Mobility processed file not found: {path}")

    frame = pd.read_csv(path)
    required = {
        "date",
        "workplace_percent_change_from_baseline",
        "retail_and_recreation_percent_change_from_baseline",
    }
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"Missing required mobility columns: {sorted(missing)}")

    frame["date"] = pd.to_datetime(frame["date"]).dt.date
    if region is not None and "region" in frame.columns:
        frame = frame[frame["region"] == region].copy()
    if start_date is not None:
        frame = frame[frame["date"] >= date.fromisoformat(start_date)]
    if end_date is not None:
        frame = frame[frame["date"] <= date.fromisoformat(end_date)]
    if frame.empty:
        raise ValueError("Mobility table is empty after filtering")
    return frame.sort_values("date").reset_index(drop=True)


def build_mobility_driven_network_multipliers(
    mobility_table: pd.DataFrame,
    reference_start_date: str,
    end_date: str,
    household_scale: float = 1.0,
    work_mobility_scale: float = 1.0,
    school_scale: float = 1.0,
    random_mobility_scale: float = 1.0,
    work_multiplier_floor: float = 0.1,
    random_multiplier_floor: float = 0.1,
    multiplier_ceiling: float = 1.0,
) -> Dict[str, list[float]]:
    """Build day-aligned external multipliers for work/random networks."""
    if mobility_table is None or mobility_table.empty:
        raise ValueError("mobility_table must be a non-empty DataFrame")

    start = date.fromisoformat(reference_start_date)
    end = date.fromisoformat(end_date)
    if start > end:
        raise ValueError("reference_start_date must be <= end_date")

    dates = pd.date_range(start=start, end=end, freq="D").date
    table = mobility_table.copy()
    table["date"] = pd.to_datetime(table["date"]).dt.date
    table = table.sort_values("date").drop_duplicates(subset=["date"], keep="last")
    table = table.set_index("date").reindex(dates).ffill().bfill()
    if table.isna().any().any():
        raise ValueError("Mobility table has unresolved missing values after date alignment")

    household_values = [float(household_scale)] * len(table.index)
    work_values = []
    school_values = [float(school_scale)] * len(table.index)
    random_values = []
    for _, row in table.iterrows():
        work_values.append(
            mobility_to_work_multiplier(
                row["workplace_percent_change_from_baseline"],
                scale=work_mobility_scale,
                floor=work_multiplier_floor,
                ceiling=multiplier_ceiling,
            )
        )
        random_values.append(
            mobility_to_random_multiplier(
                row["retail_and_recreation_percent_change_from_baseline"],
                scale=random_mobility_scale,
                floor=random_multiplier_floor,
                ceiling=multiplier_ceiling,
            )
        )

    return {
        "household": [float(v) for v in household_values],
        "work": [float(v) for v in work_values],
        "school": [float(v) for v in school_values],
        "random": [float(v) for v in random_values],
    }
