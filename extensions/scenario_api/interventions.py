from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .events import TimelineEvent, create_event


@dataclass
class Intervention:
    """Base class for high-level interventions that compile to timeline events."""

    name: str
    start: int
    end: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not isinstance(self.start, int) or self.start < 0:
            raise ValueError("start must be a non-negative int")
        if self.end is not None and (not isinstance(self.end, int) or self.end < self.start):
            raise ValueError("end must be >= start when provided")

    def to_events(self, base_params: Dict[str, Any] = None) -> List[TimelineEvent]:
        """Compile this intervention into timeline events."""
        raise NotImplementedError("to_events must be implemented by intervention subclasses")


@dataclass
class ParameterIntervention(Intervention):
    """Temporary or permanent parameter override represented as set events."""

    params: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        super().__post_init__()
        if not isinstance(self.params, dict):
            raise ValueError("params must be a dict")
        if not self.params:
            raise ValueError("params must not be empty")

    def to_events(self, base_params: Dict[str, Any] = None) -> List[TimelineEvent]:
        """Create start override events and optional end-time restoration events."""
        events: List[TimelineEvent] = []

        for key, value in self.params.items():
            events.append(
                create_event(
                    time=self.start,
                    action="set",
                    target=key,
                    value=value,
                    metadata={"intervention": self.name, "phase": "start"},
                )
            )

        if self.end is not None:
            base = base_params or {}
            for key in self.params:
                if key not in base:
                    raise ValueError(
                        f"Cannot restore parameter '{key}' for intervention '{self.name}': "
                        "missing in base_params"
                    )
                events.append(
                    create_event(
                        time=self.end,
                        action="set",
                        target=key,
                        value=base[key],
                        metadata={"intervention": self.name, "phase": "end_restore"},
                    )
                )

        return events


def create_parameter_intervention(
    name: str,
    start: int,
    params: Dict[str, Any],
    end: Optional[int] = None,
    metadata: Dict[str, Any] = None,
) -> ParameterIntervention:
    """Create a ParameterIntervention with validation."""
    if not isinstance(params, dict):
        raise ValueError("params must be a dict")
    if not params:
        raise ValueError("params must not be empty")
    return ParameterIntervention(
        name=name,
        start=start,
        end=end,
        params=params,
        metadata=metadata or {},
    )


def intervention_to_events(
    intervention: Intervention,
    base_params: Dict[str, Any] = None,
) -> List[TimelineEvent]:
    """Convert a single intervention into timeline events."""
    return intervention.to_events(base_params=base_params)


def interventions_to_events(
    interventions: List[Intervention],
    base_params: Dict[str, Any] = None,
) -> List[TimelineEvent]:
    """Convert interventions into a flat list of timeline events."""
    events: List[TimelineEvent] = []
    for intervention in interventions:
        events.extend(intervention_to_events(intervention, base_params=base_params))
    return events
