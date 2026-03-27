from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Any

from .interventions import MaskProfile


@dataclass
class MaskMappingProfile:
    name: str
    level_to_network_mix: Dict[int, Dict[str, Dict[str, float]]]
    mask_profile_name: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ContactPolicyMappingProfile:
    name: str
    event_type_to_level_multipliers: Dict[str, Dict[int, Dict[str, float]]]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TestingTracingMappingProfile:
    name: str
    testing_policy_levels: Dict[int, Dict[str, Any]]
    tracing_policy_levels: Dict[int, Dict[str, Any]]
    metadata: Dict[str, Any] = field(default_factory=dict)


def default_mask_effectiveness_profiles() -> Dict[str, MaskProfile]:
    return {
        "default": MaskProfile(
            name="default",
            effectiveness={
                "surgical": 0.5,
                "ffp2": 0.95,
            },
        )
    }


def default_mask_mapping_profile() -> MaskMappingProfile:
    # Level mappings are explicit editable defaults for timeline level -> adoption assumptions.
    return MaskMappingProfile(
        name="default_mask_mapping",
        mask_profile_name="default",
        level_to_network_mix={
            0: {},
            1: {
                "work": {"none": 0.50, "surgical": 0.40, "ffp2": 0.10},
                "random": {"none": 0.60, "surgical": 0.30, "ffp2": 0.10},
            },
            2: {
                "work": {"none": 0.20, "surgical": 0.50, "ffp2": 0.30},
                "random": {"none": 0.30, "surgical": 0.50, "ffp2": 0.20},
            },
            3: {
                "work": {"none": 0.15, "surgical": 0.45, "ffp2": 0.40},
                "random": {"none": 0.20, "surgical": 0.45, "ffp2": 0.35},
            },
            4: {
                "work": {"none": 0.10, "surgical": 0.40, "ffp2": 0.50},
                "random": {"none": 0.15, "surgical": 0.40, "ffp2": 0.45},
            },
        },
        metadata={"source": "recipe_default"},
    )


def default_contact_policy_mapping_profile() -> ContactPolicyMappingProfile:
    event_type_to_level_multipliers = {
        "school_closing": {
            0: {},
            1: {"school": 0.7},
            2: {"school": 0.4},
            3: {"school": 0.1},
            4: {"school": 0.05},
        },
        "workplace_closing": {
            0: {},
            1: {"work": 0.8},
            2: {"work": 0.5},
            3: {"work": 0.2},
            4: {"work": 0.1},
        },
        "gathering_restrictions": {
            0: {},
            1: {"random": 0.8},
            2: {"random": 0.5},
            3: {"random": 0.2},
            4: {"random": 0.1},
        },
        "public_events": {
            0: {},
            1: {"random": 0.8},
            2: {"random": 0.5},
            3: {"random": 0.2},
            4: {"random": 0.1},
        },
        "stay_at_home": {
            0: {},
            1: {"random": 0.8, "work": 0.9},
            2: {"random": 0.5, "work": 0.7},
            3: {"random": 0.2, "work": 0.5},
            4: {"random": 0.1, "work": 0.3},
        },
        "internal_movement": {
            0: {},
            1: {"random": 0.8},
            2: {"random": 0.5},
            3: {"random": 0.2},
            4: {"random": 0.1},
        },
    }
    return ContactPolicyMappingProfile(
        name="default_contact_policy_mapping",
        event_type_to_level_multipliers=event_type_to_level_multipliers,
        metadata={"source": "recipe_default"},
    )


def default_testing_tracing_mapping_profile() -> TestingTracingMappingProfile:
    return TestingTracingMappingProfile(
        name="default_testing_tracing_mapping",
        testing_policy_levels={
            0: {"testing_intensity": 0.0},
            1: {"testing_intensity": 0.3},
            2: {"testing_intensity": 0.6},
            3: {"testing_intensity": 1.0},
        },
        tracing_policy_levels={
            0: {"tracing_intensity": 0.0},
            1: {"tracing_intensity": 0.4},
            2: {"tracing_intensity": 0.7},
            3: {"tracing_intensity": 1.0},
        },
        metadata={"source": "recipe_default"},
    )
