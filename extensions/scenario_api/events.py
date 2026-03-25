from dataclasses import dataclass
from typing import Dict, Any, List
from collections import defaultdict


@dataclass
class TimelineEvent:
    """An event on the timeline."""
    time: int
    action: str
    target: str
    value: Any
    event_type: str = "soft"
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


def create_event(time: int, action: str, target: str, value: Any, event_type: str = "soft", metadata: Dict[str, Any] = None) -> TimelineEvent:
    """Create a timeline event with validation."""
    if not isinstance(time, int) or time < 0:
        raise ValueError("time must be a non-negative int")
    if action not in ["set", "scale"]:
        raise ValueError("action must be 'set' or 'scale'")
    if event_type not in ["soft", "hard"]:
        raise ValueError("event_type must be 'soft' or 'hard'")
    return TimelineEvent(time=time, action=action, target=target, value=value, event_type=event_type, metadata=metadata or {})


def group_events_by_time(events: List[TimelineEvent]) -> Dict[int, List[TimelineEvent]]:
    """Group events by time."""
    grouped = defaultdict(list)
    for event in events:
        grouped[event.time].append(event)
    return dict(grouped)
