from dataclasses import dataclass
from typing import Dict, Any, List
from .scenarios import Scenario
from .networks import NetworkSpec
from .events import TimelineEvent, group_events_by_time
from .blocks import merge_blocks


@dataclass
class ResolvedScenario:
    """A resolved scenario ready for execution."""
    name: str
    resolved_params: Dict[str, Any]
    network_specs: List[NetworkSpec]
    events_by_time: Dict[int, List[TimelineEvent]]
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


def resolve_scenario(scenario: Scenario) -> ResolvedScenario:
    """Resolve a scenario into an executable form."""
    resolved_params = scenario.base_params.copy()
    merged_block_params = merge_blocks(scenario.blocks)
    resolved_params.update(merged_block_params)
    events_by_time = group_events_by_time(scenario.events)
    return ResolvedScenario(
        name=scenario.name,
        resolved_params=resolved_params,
        network_specs=scenario.network_specs,
        events_by_time=events_by_time,
        metadata=scenario.metadata
    )