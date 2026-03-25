from dataclasses import dataclass
from numbers import Number
from typing import Any, Dict, List


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


SUPPORTED_NETWORK_KINDS = {
    "household",
    "activity_structured",
    "activity_random",
}


def _ensure_non_empty_name(name: str) -> None:
    if not isinstance(name, str) or not name.strip():
        raise ValueError("name must be a non-empty string")


def _ensure_supported_kind(kind: str) -> None:
    if kind not in SUPPORTED_NETWORK_KINDS:
        raise ValueError(
            "kind must be one of: household, activity_structured, activity_random"
        )


def _validate_household_config(config: Dict[str, Any]) -> None:
    if "population_size" not in config:
        raise ValueError("household config requires 'population_size'")
    population_size = config["population_size"]
    if not isinstance(population_size, int) or population_size <= 0:
        raise ValueError("household 'population_size' must be a positive integer")


def _validate_activity_structured_config(config: Dict[str, Any]) -> None:
    if "mean_contacts" not in config:
        raise ValueError("activity_structured config requires 'mean_contacts'")
    if "activation_prob" not in config:
        raise ValueError("activity_structured config requires 'activation_prob'")

    mean_contacts = config["mean_contacts"]
    if not isinstance(mean_contacts, Number) or mean_contacts < 0:
        raise ValueError("activity_structured 'mean_contacts' must be a non-negative number")

    activation_prob = config["activation_prob"]
    if (
        not isinstance(activation_prob, Number)
        or activation_prob < 0
        or activation_prob > 1
    ):
        raise ValueError(
            "activity_structured 'activation_prob' must be between 0 and 1"
        )


def _validate_activity_random_config(config: Dict[str, Any]) -> None:
    if "mean_contacts" not in config:
        raise ValueError("activity_random config requires 'mean_contacts'")

    mean_contacts = config["mean_contacts"]
    if not isinstance(mean_contacts, Number) or mean_contacts < 0:
        raise ValueError("activity_random 'mean_contacts' must be a non-negative number")

    if "dispersion" in config:
        dispersion = config["dispersion"]
        if not isinstance(dispersion, Number) or dispersion <= 0:
            raise ValueError("activity_random 'dispersion' must be a positive number")


def validate_network_spec(spec: NetworkSpec) -> None:
    """Validate one NetworkSpec and raise ValueError on invalid input."""
    if not isinstance(spec, NetworkSpec):
        raise ValueError("spec must be a NetworkSpec")
    _ensure_non_empty_name(spec.name)
    _ensure_supported_kind(spec.kind)
    if not isinstance(spec.config, dict):
        raise ValueError("config must be a dict")

    if spec.kind == "household":
        _validate_household_config(spec.config)
    elif spec.kind == "activity_structured":
        _validate_activity_structured_config(spec.config)
    elif spec.kind == "activity_random":
        _validate_activity_random_config(spec.config)


def validate_network_specs(specs: List[NetworkSpec]) -> None:
    """Validate a list of network specs and raise on the first invalid spec."""
    for spec in specs:
        validate_network_spec(spec)


def network_spec_to_dict(spec: NetworkSpec) -> Dict[str, Any]:
    """Convert a NetworkSpec into a plain dictionary for inspection/serialization."""
    validate_network_spec(spec)
    return {
        "name": spec.name,
        "kind": spec.kind,
        "config": dict(spec.config),
        "metadata": dict(spec.metadata or {}),
    }


def group_network_specs_by_kind(specs: List[NetworkSpec]) -> Dict[str, List[NetworkSpec]]:
    """Group validated network specs by kind."""
    validate_network_specs(specs)
    grouped: Dict[str, List[NetworkSpec]] = {}
    for spec in specs:
        grouped.setdefault(spec.kind, []).append(spec)
    return grouped


def create_network_spec(name: str, kind: str, config: Dict[str, Any], metadata: Dict[str, Any] = None) -> NetworkSpec:
    """Create and validate a network specification."""
    spec = NetworkSpec(name=name, kind=kind, config=config, metadata=metadata or {})
    validate_network_spec(spec)
    return spec
