import pytest

from extensions.scenario_api import (
    ContactReductionIntervention,
    InterventionSet,
    MaskAdoptionIntervention,
    MaskProfile,
    compile_network_multipliers,
)


def test_mask_adoption_requires_none_in_each_network_mix():
    profile = MaskProfile(name="default", effectiveness={"surgical": 0.5})
    with pytest.raises(ValueError, match="must include 'none'"):
        MaskAdoptionIntervention(
            name="masks",
            start=0,
            end=10,
            network_mix={"work": {"surgical": 1.0}},
            mask_profile=profile,
        )


def test_mask_adoption_requires_mix_sum_one():
    profile = MaskProfile(name="default", effectiveness={"surgical": 0.5})
    with pytest.raises(ValueError, match="must sum to 1.0"):
        MaskAdoptionIntervention(
            name="masks",
            start=0,
            end=10,
            network_mix={"work": {"none": 0.4, "surgical": 0.5}},
            mask_profile=profile,
        )


def test_mask_adoption_requires_known_mask_types():
    profile = MaskProfile(name="default", effectiveness={"surgical": 0.5})
    with pytest.raises(ValueError, match="not found in mask profile"):
        MaskAdoptionIntervention(
            name="masks",
            start=0,
            end=10,
            network_mix={"work": {"none": 0.3, "ffp2": 0.7}},
            mask_profile=profile,
        )


def test_contact_reduction_multiplier_must_be_in_range():
    with pytest.raises(ValueError, match="must be in \[0,1\]"):
        ContactReductionIntervention(
            name="contacts",
            start=0,
            end=10,
            multipliers={"work": 1.2},
        )


def test_compile_network_multipliers_combines_mask_and_contact_multiplicatively():
    profile = MaskProfile(
        name="default",
        effectiveness={"surgical": 0.5, "ffp2": 0.95, "ffp3": 0.99},
    )
    masks = MaskAdoptionIntervention(
        name="mask_adoption",
        start=100,
        end=200,
        network_mix={
            "work": {"none": 0.3, "surgical": 0.5, "ffp2": 0.15, "ffp3": 0.05},
            "random": {"none": 0.4, "surgical": 0.4, "ffp2": 0.15, "ffp3": 0.05},
        },
        mask_profile=profile,
    )
    contacts = ContactReductionIntervention(
        name="contact_reduction",
        start=100,
        end=200,
        multipliers={"work": 0.5, "random": 0.3},
    )

    multipliers = compile_network_multipliers(InterventionSet([masks, contacts]), t=120)

    # work mask multiplier = 1 - (0.5*0.5 + 0.15*0.95 + 0.05*0.99) = 0.558
    # random mask multiplier = 1 - (0.4*0.5 + 0.15*0.95 + 0.05*0.99) = 0.608
    assert multipliers["work"] == pytest.approx(0.558 * 0.5)
    assert multipliers["random"] == pytest.approx(0.608 * 0.3)


def test_intervention_set_active_at_respects_time_window():
    profile = MaskProfile(name="default", effectiveness={"surgical": 0.5})
    masks = MaskAdoptionIntervention(
        name="masks",
        start=10,
        end=20,
        network_mix={"work": {"none": 0.4, "surgical": 0.6}},
        mask_profile=profile,
    )
    interventions = InterventionSet([masks])

    assert interventions.active_at(9) == []
    assert interventions.active_at(10) == [masks]
    assert interventions.active_at(19) == [masks]
    assert interventions.active_at(20) == []
