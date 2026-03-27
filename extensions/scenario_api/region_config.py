from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class RegionConfig:
    name: str
    region_level: str
    real_population: int
    simulated_population: int
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.region_level != "hospital_district":
            raise ValueError("region_level must be 'hospital_district' for single-SHP mode")
        if not isinstance(self.real_population, int) or self.real_population <= 0:
            raise ValueError("real_population must be a positive integer")
        if not isinstance(self.simulated_population, int) or self.simulated_population <= 0:
            raise ValueError("simulated_population must be a positive integer")


# Small explicit first default set. Values are approximate and editable.
_DEFAULT_SHP_POPULATIONS: Dict[str, int] = {
    "Helsinki and Uusimaa Hospital District": 1707216,
    "Pirkanmaa Hospital District": 540000,
    "Northern Ostrobothnia Hospital District": 413000,
}


def population_scale_factor(region_config: RegionConfig) -> float:
    if region_config.simulated_population <= 0:
        raise ValueError("simulated_population must be > 0 for scaling")
    if region_config.real_population <= 0:
        raise ValueError("real_population must be > 0 for scaling")
    return float(region_config.real_population) / float(region_config.simulated_population)


def get_default_shp_region_config(name: str, simulated_population: int) -> RegionConfig:
    if name not in _DEFAULT_SHP_POPULATIONS:
        known = sorted(_DEFAULT_SHP_POPULATIONS.keys())
        raise ValueError(f"Unknown SHP name '{name}'. Known defaults: {known}")
    return RegionConfig(
        name=name,
        region_level="hospital_district",
        real_population=int(_DEFAULT_SHP_POPULATIONS[name]),
        simulated_population=int(simulated_population),
        metadata={"source": "built_in_default"},
    )

