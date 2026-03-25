from dataclasses import dataclass
from typing import Dict, Any, List
from .runner import SimulationResult


@dataclass
class TimeSeries:
    """A time series of values."""
    name: str
    times: List[int]
    values: List[float]
    variable: str
    source_type: str
    source_name: str
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


def result_to_timeseries(result: SimulationResult, variable: str) -> TimeSeries:
    """Convert simulation result to time series."""
    if variable not in result.raw_outputs:
        raise ValueError(f"Variable {variable} not in result")
    times = list(range(len(result.raw_outputs[variable])))
    return TimeSeries(
        name=f"{result.scenario_name}_{variable}",
        times=times,
        values=result.raw_outputs[variable],
        variable=variable,
        source_type="simulation",
        source_name=result.scenario_name
    )


def align_timeseries(series_list: List[TimeSeries]) -> List[TimeSeries]:
    """Align time series (for now, just return as is)."""
    return series_list