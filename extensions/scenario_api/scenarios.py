from dataclasses import dataclass
from typing import Dict, Any, List, Optional
from .blocks import ParameterBlock
from .networks import NetworkSpec, validate_network_spec, validate_network_specs
from .events import TimelineEvent
from .interventions import Intervention


@dataclass
class Scenario:
    """A declarative scenario recipe."""
    name: str
    base_params: Dict[str, Any]
    blocks: List[ParameterBlock] = None
    network_specs: List[NetworkSpec] = None
    events: List[TimelineEvent] = None
    interventions: List[Intervention] = None
    parent: Optional[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.blocks is None:
            self.blocks = []
        if self.network_specs is None:
            self.network_specs = []
        if self.events is None:
            self.events = []
        if self.interventions is None:
            self.interventions = []
        if self.metadata is None:
            self.metadata = {}


def create_scenario(
    name: str,
    base_params: Dict[str, Any],
    blocks: List[ParameterBlock] = None,
    network_specs: List[NetworkSpec] = None,
    events: List[TimelineEvent] = None,
    interventions: List[Intervention] = None,
    parent: str = None,
    metadata: Dict[str, Any] = None,
) -> Scenario:
    """Create a scenario."""
    validate_network_specs(list(network_specs or []))
    return Scenario(
        name=name,
        base_params=dict(base_params),
        blocks=list(blocks or []),
        network_specs=list(network_specs or []),
        events=list(events or []),
        interventions=list(interventions or []),
        parent=parent,
        metadata=dict(metadata or {}),
    )


def add_block(scenario: Scenario, block: ParameterBlock) -> Scenario:
    """Add a block to the scenario."""
    new_blocks = scenario.blocks + [block]
    return Scenario(
        name=scenario.name,
        base_params=dict(scenario.base_params),
        blocks=new_blocks,
        network_specs=list(scenario.network_specs),
        events=list(scenario.events),
        interventions=list(scenario.interventions),
        parent=scenario.parent,
        metadata=dict(scenario.metadata),
    )


def add_event(scenario: Scenario, event: TimelineEvent) -> Scenario:
    """Add an event to the scenario."""
    new_events = scenario.events + [event]
    return Scenario(
        name=scenario.name,
        base_params=dict(scenario.base_params),
        blocks=list(scenario.blocks),
        network_specs=list(scenario.network_specs),
        events=new_events,
        interventions=list(scenario.interventions),
        parent=scenario.parent,
        metadata=dict(scenario.metadata),
    )


def add_network_spec(scenario: Scenario, network_spec: NetworkSpec) -> Scenario:
    """Add a network spec to the scenario."""
    validate_network_spec(network_spec)
    new_specs = scenario.network_specs + [network_spec]
    return Scenario(
        name=scenario.name,
        base_params=dict(scenario.base_params),
        blocks=list(scenario.blocks),
        network_specs=new_specs,
        events=list(scenario.events),
        interventions=list(scenario.interventions),
        parent=scenario.parent,
        metadata=dict(scenario.metadata),
    )


def add_intervention(scenario: Scenario, intervention: Intervention) -> Scenario:
    """Add an intervention to the scenario."""
    new_interventions = scenario.interventions + [intervention]
    return Scenario(
        name=scenario.name,
        base_params=dict(scenario.base_params),
        blocks=list(scenario.blocks),
        network_specs=list(scenario.network_specs),
        events=list(scenario.events),
        interventions=new_interventions,
        parent=scenario.parent,
        metadata=dict(scenario.metadata),
    )
