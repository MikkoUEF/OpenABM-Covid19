from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Union

import pandas as pd

from .results import TimeSeries


@dataclass
class ObservedDataset:
    """A dataset of observed data."""
    name: str
    data: Dict[str, Union[List[float], List[int]]]
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


def load_observed_dataset(name: str, data: Dict[str, Union[List[float], List[int]]], metadata: Dict[str, Any] = None) -> ObservedDataset:
    """Load an observed dataset."""
    return ObservedDataset(name=name, data=data, metadata=metadata or {})


def dataset_to_timeseries(dataset: ObservedDataset, variable: str, time_key: str = "time") -> TimeSeries:
    """Convert dataset to time series."""
    if variable not in dataset.data:
        raise ValueError(f"Variable {variable} not in dataset")
    if time_key not in dataset.data:
        raise ValueError(f"Time key {time_key} not in dataset")
    times = dataset.data[time_key]
    values = dataset.data[variable]
    if len(times) != len(values):
        raise ValueError(
            f"Mismatched lengths: {time_key} has {len(times)} values, "
            f"but {variable} has {len(values)} values"
        )
    return TimeSeries(
        name=f"{dataset.name}_{variable}",
        times=times,
        values=values,
        variable=variable,
        source_type="observed",
        source_name=dataset.name
    )


def smooth_timeseries_moving_average(
    timeseries: TimeSeries,
    window: int = 7,
    new_name: Optional[str] = None,
) -> TimeSeries:
    """Return trailing moving-average smoothed time series with same time axis."""
    if window <= 0:
        raise ValueError("window must be > 0")
    if timeseries is None or not getattr(timeseries, "values", None):
        raise ValueError("timeseries must contain values")

    values = pd.Series([float(v) for v in timeseries.values], dtype=float)
    smoothed = values.rolling(window=window, min_periods=1).mean()

    return TimeSeries(
        name=new_name or f"{timeseries.name}_ma{window}",
        times=list(timeseries.times),
        values=[float(v) for v in smoothed.tolist()],
        variable=timeseries.variable,
        source_type=timeseries.source_type,
        source_name=timeseries.source_name,
        metadata={
            **(timeseries.metadata or {}),
            "smoothing_method": "moving_average_trailing",
            "smoothing_window": int(window),
        },
    )
