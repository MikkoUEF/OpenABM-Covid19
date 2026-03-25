from dataclasses import dataclass
from typing import Dict, List, Any


@dataclass
class ParameterBlock:
    """A block of parameters."""
    name: str
    params: Dict[str, Any]
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


def create_block(name: str, params: Dict[str, Any], metadata: Dict[str, Any] = None) -> ParameterBlock:
    """Create a parameter block with validation."""
    if not isinstance(params, dict):
        raise ValueError("params must be a dict")
    return ParameterBlock(name=name, params=params, metadata=metadata or {})


def merge_blocks(blocks: List[ParameterBlock]) -> Dict[str, Any]:
    """Merge parameter blocks, later blocks override earlier ones."""
    merged = {}
    for block in blocks:
        merged.update(block.params)
    return merged