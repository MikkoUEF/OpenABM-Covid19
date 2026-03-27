from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Dict, List, Optional, Sequence

from .interventions import (
    ContactReductionIntervention,
    Intervention,
    MaskAdoptionIntervention,
    MaskProfile,
)
from .mapping_profiles import (
    ContactPolicyMappingProfile,
    MaskMappingProfile,
    TestingTracingMappingProfile,
)
from .timeline import TimelineEvent


SUPPORTED_EVENT_TYPES = {
    "facial_coverings",
    "school_closing",
    "workplace_closing",
    "gathering_restrictions",
    "stay_at_home",
    "public_events",
    "internal_movement",
    "testing_policy",
    "contact_tracing",
}


@dataclass
class TestingIntensityIntervention(Intervention):
    config: Dict[str, Any] = None


@dataclass
class TracingIntensityIntervention(Intervention):
    config: Dict[str, Any] = None


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


def assign_relative_day_indices(
    events: Sequence[TimelineEvent],
    reference_start_date: str,
) -> List[TimelineEvent]:
    ref = _parse_date(reference_start_date)
    out: List[TimelineEvent] = []
    for event in events:
        day = (_parse_date(event.date) - ref).days
        metadata = dict(event.metadata or {})
        metadata["relative_day"] = day
        out.append(
            TimelineEvent(
                date=event.date,
                source=event.source,
                region_level=event.region_level,
                region=event.region,
                event_type=event.event_type,
                value=event.value,
                notes=event.notes,
                metadata=metadata,
            )
        )
    return out


def _to_level(value: Any) -> int:
    try:
        return int(float(value))
    except (ValueError, TypeError) as exc:
        raise ValueError(f"Timeline event value '{value}' is not a valid level") from exc


def _get_start_end_days(event: TimelineEvent) -> tuple[int, int]:
    start = (event.metadata or {}).get("start_day")
    end = (event.metadata or {}).get("end_day")
    if start is None or end is None:
        raise ValueError("Missing relative day conversion (start_day/end_day) in event metadata")
    return int(start), int(end)


def map_timeline_event_to_interventions(
    event: TimelineEvent,
    mask_mapping_profile: MaskMappingProfile,
    contact_mapping_profile: ContactPolicyMappingProfile,
    testing_tracing_mapping_profile: Optional[TestingTracingMappingProfile] = None,
    mask_profiles: Optional[Dict[str, MaskProfile]] = None,
) -> List[Intervention]:
    if event.event_type not in SUPPORTED_EVENT_TYPES:
        raise ValueError(f"Unknown event type '{event.event_type}'")

    level = _to_level(event.value)
    start_day, end_day = _get_start_end_days(event)

    if start_day >= end_day:
        return []

    if event.event_type == "facial_coverings":
        if level not in mask_mapping_profile.level_to_network_mix:
            raise ValueError(f"Unknown level {level} for facial_coverings in mask mapping profile")
        network_mix = mask_mapping_profile.level_to_network_mix[level]
        if not network_mix:
            return []
        if not mask_profiles or mask_mapping_profile.mask_profile_name not in mask_profiles:
            raise ValueError(
                f"Missing mask profile '{mask_mapping_profile.mask_profile_name}' referenced by mapping profile"
            )
        mask_profile = mask_profiles[mask_mapping_profile.mask_profile_name]
        return [
            MaskAdoptionIntervention(
                name=f"timeline_facial_coverings_l{level}",
                start=start_day,
                end=end_day,
                network_mix=network_mix,
                mask_profile=mask_profile,
                metadata={"source_event_date": event.date, "event_type": event.event_type, "level": level},
            )
        ]

    if event.event_type in {
        "school_closing",
        "workplace_closing",
        "gathering_restrictions",
        "stay_at_home",
        "public_events",
        "internal_movement",
    }:
        by_type = contact_mapping_profile.event_type_to_level_multipliers.get(event.event_type)
        if by_type is None:
            raise ValueError(f"Unknown event type '{event.event_type}' in contact mapping profile")
        if level not in by_type:
            raise ValueError(f"Unknown level {level} for event type '{event.event_type}'")
        multipliers = by_type[level]
        if not multipliers:
            return []
        return [
            ContactReductionIntervention(
                name=f"timeline_{event.event_type}_l{level}",
                start=start_day,
                end=end_day,
                multipliers=multipliers,
                metadata={"source_event_date": event.date, "event_type": event.event_type, "level": level},
            )
        ]

    if event.event_type == "testing_policy":
        if testing_tracing_mapping_profile is None:
            return []
        if level not in testing_tracing_mapping_profile.testing_policy_levels:
            raise ValueError(f"Unknown level {level} for testing_policy")
        config = testing_tracing_mapping_profile.testing_policy_levels[level]
        if not config:
            return []
        return [
            TestingIntensityIntervention(
                name=f"timeline_testing_policy_l{level}",
                start=start_day,
                end=end_day,
                config=config,
                metadata={"source_event_date": event.date, "event_type": event.event_type, "level": level},
            )
        ]

    if event.event_type == "contact_tracing":
        if testing_tracing_mapping_profile is None:
            return []
        if level not in testing_tracing_mapping_profile.tracing_policy_levels:
            raise ValueError(f"Unknown level {level} for contact_tracing")
        config = testing_tracing_mapping_profile.tracing_policy_levels[level]
        if not config:
            return []
        return [
            TracingIntensityIntervention(
                name=f"timeline_contact_tracing_l{level}",
                start=start_day,
                end=end_day,
                config=config,
                metadata={"source_event_date": event.date, "event_type": event.event_type, "level": level},
            )
        ]

    raise ValueError(f"Unknown event type '{event.event_type}'")


def map_timeline_events_to_interventions(
    events: Sequence[TimelineEvent],
    mask_mapping_profile: MaskMappingProfile,
    contact_mapping_profile: ContactPolicyMappingProfile,
    testing_tracing_mapping_profile: Optional[TestingTracingMappingProfile] = None,
    mask_profiles: Optional[Dict[str, MaskProfile]] = None,
    reference_start_date: Optional[str] = None,
) -> List[Intervention]:
    if reference_start_date is None:
        raise ValueError("reference_start_date is required for relative day conversion")

    enriched = assign_relative_day_indices(events, reference_start_date)

    by_type: Dict[str, List[TimelineEvent]] = {}
    for event in enriched:
        by_type.setdefault(event.event_type, []).append(event)

    with_intervals: List[TimelineEvent] = []
    for event_type, group in by_type.items():
        ordered = sorted(group, key=lambda e: (e.date, e.metadata.get("relative_day", 0)))
        for idx, event in enumerate(ordered):
            start_day = int(event.metadata["relative_day"])
            if idx + 1 < len(ordered):
                end_day = int(ordered[idx + 1].metadata["relative_day"])
            else:
                end_day = start_day + 1

            metadata = dict(event.metadata or {})
            metadata["start_day"] = start_day
            metadata["end_day"] = end_day
            with_intervals.append(
                TimelineEvent(
                    date=event.date,
                    source=event.source,
                    region_level=event.region_level,
                    region=event.region,
                    event_type=event.event_type,
                    value=event.value,
                    notes=event.notes,
                    metadata=metadata,
                )
            )

    output: List[Intervention] = []
    for event in sorted(with_intervals, key=lambda e: (e.metadata["start_day"], e.event_type)):
        output.extend(
            map_timeline_event_to_interventions(
                event=event,
                mask_mapping_profile=mask_mapping_profile,
                contact_mapping_profile=contact_mapping_profile,
                testing_tracing_mapping_profile=testing_tracing_mapping_profile,
                mask_profiles=mask_profiles,
            )
        )
    return output


def load_finland_timeline_interventions(
    processed_timeline_path: str,
    reference_start_date: str,
    mask_mapping_profile: MaskMappingProfile,
    contact_mapping_profile: ContactPolicyMappingProfile,
    testing_tracing_mapping_profile: Optional[TestingTracingMappingProfile] = None,
    mask_profiles: Optional[Dict[str, MaskProfile]] = None,
    event_types: Optional[Sequence[str]] = None,
) -> List[Intervention]:
    """Load normalized Finland timeline rows from local processed file and map to interventions."""
    from .timeline import load_timeline_events_from_processed

    events = load_timeline_events_from_processed(processed_timeline_path)
    if event_types:
        event_type_set = set(event_types)
        events = [e for e in events if e.event_type in event_type_set]
    return map_timeline_events_to_interventions(
        events=events,
        mask_mapping_profile=mask_mapping_profile,
        contact_mapping_profile=contact_mapping_profile,
        testing_tracing_mapping_profile=testing_tracing_mapping_profile,
        mask_profiles=mask_profiles,
        reference_start_date=reference_start_date,
    )
