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

    def apply(self, context):
        raise NotImplementedError("apply must be implemented by intervention subclasses")

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


@dataclass
class MaskProfile:
    name: str
    effectiveness: Dict[str, float]

    def __post_init__(self):
        if not isinstance(self.effectiveness, dict) or not self.effectiveness:
            raise ValueError("effectiveness must be a non-empty dict")
        for mask_type, value in self.effectiveness.items():
            if not isinstance(mask_type, str) or not mask_type:
                raise ValueError("mask type names must be non-empty strings")
            if not isinstance(value, (int, float)):
                raise ValueError("mask effectiveness values must be numeric")
            if not 0.0 <= float(value) <= 1.0:
                raise ValueError("mask effectiveness values must be in [0,1]")


@dataclass
class MaskAdoptionIntervention(Intervention):
    network_mix: Dict[str, Dict[str, float]] = field(default_factory=dict)
    mask_profile: MaskProfile = None

    def __post_init__(self):
        super().__post_init__()
        if self.mask_profile is None or not isinstance(self.mask_profile, MaskProfile):
            raise ValueError("mask_profile must be a MaskProfile")
        if not isinstance(self.network_mix, dict) or not self.network_mix:
            raise ValueError("network_mix must be a non-empty dict")

        for network, mix in self.network_mix.items():
            if not isinstance(network, str) or not network:
                raise ValueError("network names must be non-empty strings")
            if not isinstance(mix, dict) or not mix:
                raise ValueError("each network mix must be a non-empty dict")
            if "none" not in mix:
                raise ValueError(f"network '{network}' mix must include 'none'")

            total = 0.0
            for mask_type, fraction in mix.items():
                if not isinstance(fraction, (int, float)):
                    raise ValueError("mask adoption fractions must be numeric")
                fraction = float(fraction)
                if not 0.0 <= fraction <= 1.0:
                    raise ValueError("mask adoption fractions must be in [0,1]")
                total += fraction

                if mask_type != "none" and mask_type not in self.mask_profile.effectiveness:
                    raise ValueError(
                        f"mask type '{mask_type}' in network '{network}' not found in mask profile"
                    )

            if abs(total - 1.0) > 1e-6:
                raise ValueError(f"mask mix for network '{network}' must sum to 1.0 ± 1e-6")

    def compute_multiplier(self, network: str) -> float:
        if network not in self.network_mix:
            raise ValueError(f"network '{network}' not found in network_mix")

        mix = self.network_mix[network]
        eff = self.mask_profile.effectiveness

        weighted = 0.0
        for mask_type, fraction in mix.items():
            if mask_type == "none":
                continue
            weighted += float(fraction) * float(eff[mask_type])

        multiplier = 1.0 - weighted
        if not 0.0 <= multiplier <= 1.0:
            raise ValueError("computed mask multiplier must be in [0,1]")
        return multiplier


@dataclass
class ContactReductionIntervention(Intervention):
    multipliers: Dict[str, float] = field(default_factory=dict)

    def __post_init__(self):
        super().__post_init__()
        if not isinstance(self.multipliers, dict) or not self.multipliers:
            raise ValueError("multipliers must be a non-empty dict")

        for network, value in self.multipliers.items():
            if not isinstance(network, str) or not network:
                raise ValueError("network names must be non-empty strings")
            if not isinstance(value, (int, float)):
                raise ValueError("multiplier values must be numeric")
            if not 0.0 <= float(value) <= 1.0:
                raise ValueError("multiplier values must be in [0,1]")


@dataclass
class InterventionSet:
    interventions: List[Intervention] = field(default_factory=list)

    def active_at(self, t: int) -> List[Intervention]:
        return [i for i in self.interventions if i.start <= t < (i.end if i.end is not None else t + 1)]


@dataclass
class CompiledRuntimeEffect:
    target: str
    value: float
    metadata: Dict[str, Any] = field(default_factory=dict)


def compile_network_multipliers(interventions: InterventionSet, t: int) -> Dict[str, float]:
    multipliers: Dict[str, float] = {}
    active = interventions.active_at(t)

    for intervention in active:
        if isinstance(intervention, ContactReductionIntervention):
            for network, value in intervention.multipliers.items():
                multipliers[network] = multipliers.get(network, 1.0) * float(value)

        elif isinstance(intervention, MaskAdoptionIntervention):
            for network in intervention.network_mix.keys():
                multiplier = intervention.compute_multiplier(network)
                multipliers[network] = multipliers.get(network, 1.0) * float(multiplier)

    for network, value in multipliers.items():
        if not 0.0 <= value <= 1.0:
            raise ValueError(f"compiled multiplier for network '{network}' must be in [0,1]")

    return multipliers


def compile_runtime_effects(
    interventions: InterventionSet,
    t: int,
    school_weight_in_occupation: float = 0.3,
) -> Dict[str, List[CompiledRuntimeEffect]]:
    """
    Compile active interventions into OpenABM runtime-applicable effect objects.

    Returns a dict with:
    - applied_effects: list of runtime-targeted effects
    - unsupported_effects: list of explicitly unsupported/placeholder effects
    """
    active = interventions.active_at(t)
    multipliers = compile_network_multipliers(interventions, t=t)
    work = float(multipliers.get("work", 1.0))
    school = float(multipliers.get("school", 1.0))
    random = float(multipliers.get("random", 1.0))

    occupation = work
    if "school" in multipliers:
        sw = float(school_weight_in_occupation)
        occupation = (1.0 - sw) * work + sw * school

    applied_effects = [
        CompiledRuntimeEffect(
            target="relative_transmission_occupation",
            value=float(occupation),
            metadata={"t": t, "source": "compiled_from_interventions"},
        ),
        CompiledRuntimeEffect(
            target="relative_transmission_random",
            value=float(random),
            metadata={"t": t, "source": "compiled_from_interventions"},
        ),
    ]

    unsupported_effects: List[CompiledRuntimeEffect] = []
    for intervention in active:
        cls_name = intervention.__class__.__name__
        if cls_name == "TestingIntensityIntervention":
            unsupported_effects.append(
                CompiledRuntimeEffect(
                    target="unsupported:testing_policy",
                    value=0.0,
                    metadata={"t": t, "intervention_name": intervention.name},
                )
            )
        elif cls_name == "TracingIntensityIntervention":
            unsupported_effects.append(
                CompiledRuntimeEffect(
                    target="unsupported:contact_tracing",
                    value=0.0,
                    metadata={"t": t, "intervention_name": intervention.name},
                )
            )

    return {
        "applied_effects": applied_effects,
        "unsupported_effects": unsupported_effects,
    }


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
