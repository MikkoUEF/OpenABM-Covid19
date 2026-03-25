from dataclasses import dataclass
from typing import Dict, Any, List, Union
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
