import pytest

from extensions.scenario_api import (
    ContactReductionIntervention,
    MaskAdoptionIntervention,
    PolicyTimelineEvent,
    assign_relative_day_indices,
    default_contact_policy_mapping_profile,
    default_mask_effectiveness_profiles,
    default_mask_mapping_profile,
    default_testing_tracing_mapping_profile,
    map_timeline_events_to_interventions,
)


def test_assign_relative_day_indices():
    events = [
        PolicyTimelineEvent(
            date="2020-01-01",
            source="OxCGRT",
            region_level="country",
            region="Finland",
            event_type="school_closing",
            value=1,
        ),
        PolicyTimelineEvent(
            date="2020-01-11",
            source="OxCGRT",
            region_level="country",
            region="Finland",
            event_type="school_closing",
            value=2,
        ),
    ]
    out = assign_relative_day_indices(events, reference_start_date="2020-01-01")
    assert out[0].metadata["relative_day"] == 0
    assert out[1].metadata["relative_day"] == 10


def test_map_timeline_events_to_interventions_maps_mask_and_contact_with_intervals():
    events = [
        PolicyTimelineEvent(
            date="2020-01-01",
            source="OxCGRT",
            region_level="country",
            region="Finland",
            event_type="facial_coverings",
            value=1,
        ),
        PolicyTimelineEvent(
            date="2020-01-10",
            source="OxCGRT",
            region_level="country",
            region="Finland",
            event_type="facial_coverings",
            value=2,
        ),
        PolicyTimelineEvent(
            date="2020-01-01",
            source="OxCGRT",
            region_level="country",
            region="Finland",
            event_type="school_closing",
            value=2,
        ),
    ]

    mapped = map_timeline_events_to_interventions(
        events,
        mask_mapping_profile=default_mask_mapping_profile(),
        contact_mapping_profile=default_contact_policy_mapping_profile(),
        testing_tracing_mapping_profile=default_testing_tracing_mapping_profile(),
        mask_profiles=default_mask_effectiveness_profiles(),
        reference_start_date="2020-01-01",
    )

    assert any(isinstance(i, MaskAdoptionIntervention) for i in mapped)
    assert any(isinstance(i, ContactReductionIntervention) for i in mapped)

    fac = [i for i in mapped if isinstance(i, MaskAdoptionIntervention)]
    assert fac[0].start == 0
    assert fac[0].end == 9


def test_map_timeline_events_to_interventions_requires_reference_start_date():
    events = [
        PolicyTimelineEvent(
            date="2020-01-01",
            source="OxCGRT",
            region_level="country",
            region="Finland",
            event_type="facial_coverings",
            value=1,
        )
    ]
    with pytest.raises(ValueError, match="reference_start_date is required"):
        map_timeline_events_to_interventions(
            events,
            mask_mapping_profile=default_mask_mapping_profile(),
            contact_mapping_profile=default_contact_policy_mapping_profile(),
            mask_profiles=default_mask_effectiveness_profiles(),
        )


def test_map_timeline_events_to_interventions_rejects_unknown_type():
    events = [
        PolicyTimelineEvent(
            date="2020-01-01",
            source="OxCGRT",
            region_level="country",
            region="Finland",
            event_type="unknown_policy",
            value=1,
        )
    ]
    with pytest.raises(ValueError, match="Unknown event type"):
        map_timeline_events_to_interventions(
            events,
            mask_mapping_profile=default_mask_mapping_profile(),
            contact_mapping_profile=default_contact_policy_mapping_profile(),
            mask_profiles=default_mask_effectiveness_profiles(),
            reference_start_date="2020-01-01",
        )
