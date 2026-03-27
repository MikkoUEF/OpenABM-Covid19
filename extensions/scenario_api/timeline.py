from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import pandas as pd


@dataclass
class TimelineEvent:
    date: str
    source: str
    region_level: str
    region: str
    event_type: str
    value: Any
    notes: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        try:
            date.fromisoformat(str(self.date))
        except ValueError as exc:
            raise ValueError(f"date must be ISO YYYY-MM-DD, got '{self.date}'") from exc
        for field_name in ["source", "region_level", "region", "event_type"]:
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must be a non-empty string")
        if not isinstance(self.notes, str):
            raise ValueError("notes must be a string")
        if not isinstance(self.metadata, dict):
            raise ValueError("metadata must be a dict")


def load_timeline_events_from_processed(path: Union[str, Path]) -> List[TimelineEvent]:
    frame = pd.read_csv(path)
    required = {
        "date",
        "source",
        "region_level",
        "region",
        "event_type",
        "value",
        "notes",
    }
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise ValueError(f"Processed timeline file missing required columns: {missing}")

    events: List[TimelineEvent] = []
    for row in frame.to_dict(orient="records"):
        metadata = {}
        if "source_code" in row and pd.notna(row.get("source_code")):
            metadata["source_code"] = row["source_code"]
        events.append(
            TimelineEvent(
                date=str(row["date"]),
                source=str(row["source"]),
                region_level=str(row["region_level"]),
                region=str(row["region"]),
                event_type=str(row["event_type"]),
                value=row["value"],
                notes="" if pd.isna(row.get("notes")) else str(row.get("notes", "")),
                metadata=metadata,
            )
        )
    return events


def timeline_events_to_table(events: List[TimelineEvent]) -> pd.DataFrame:
    rows = []
    for event in events:
        row = asdict(event)
        source_code = row.get("metadata", {}).get("source_code", "")
        row["source_code"] = source_code
        rows.append(row)
    frame = pd.DataFrame(rows)
    if frame.empty:
        return pd.DataFrame(
            columns=[
                "date",
                "source",
                "region_level",
                "region",
                "event_type",
                "value",
                "notes",
                "source_code",
                "metadata",
            ]
        )
    return frame


def filter_timeline_events(
    events: List[TimelineEvent],
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    event_type: Optional[str] = None,
) -> List[TimelineEvent]:
    start = date.fromisoformat(start_date) if start_date else None
    end = date.fromisoformat(end_date) if end_date else None
    if start and end and start > end:
        raise ValueError("start_date must be <= end_date")

    filtered = events
    if start is not None:
        filtered = [e for e in filtered if date.fromisoformat(e.date) >= start]
    if end is not None:
        filtered = [e for e in filtered if date.fromisoformat(e.date) <= end]
    if event_type is not None:
        filtered = [e for e in filtered if e.event_type == event_type]
    return filtered
