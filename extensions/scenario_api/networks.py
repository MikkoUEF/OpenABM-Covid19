from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class NetworkSpec:
    """Specification for a network."""
    name: str
    kind: str
    config: Dict[str, Any]
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


def create_network_spec(name: str, kind: str, config: Dict[str, Any], metadata: Dict[str, Any] = None) -> NetworkSpec:
    """Create a network specification."""
    if not isinstance(config, dict):
        raise ValueError("config must be a dict")
    return NetworkSpec(name=name, kind=kind, config=config, metadata=metadata or {})