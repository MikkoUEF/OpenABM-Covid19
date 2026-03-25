import pytest

from extensions.scenario_api import (
    create_network_spec,
    create_scenario,
    group_network_specs_by_kind,
    network_spec_to_dict,
    resolve_scenario,
)


def test_create_network_spec_supports_required_kinds():
    household = create_network_spec(
        name="households",
        kind="household",
        config={"population_size": 1000},
    )
    structured = create_network_spec(
        name="work",
        kind="activity_structured",
        config={"mean_contacts": 10, "activation_prob": 0.5},
    )
    random = create_network_spec(
        name="community",
        kind="activity_random",
        config={"mean_contacts": 4, "dispersion": 2},
    )

    assert household.kind == "household"
    assert structured.kind == "activity_structured"
    assert random.kind == "activity_random"


def test_create_network_spec_rejects_invalid_kind():
    with pytest.raises(ValueError, match="kind must be one of"):
        create_network_spec(name="x", kind="community", config={"mean_contacts": 3})


def test_household_requires_positive_population_size():
    with pytest.raises(ValueError, match="population_size"):
        create_network_spec(name="hh", kind="household", config={})
    with pytest.raises(ValueError, match="positive integer"):
        create_network_spec(name="hh", kind="household", config={"population_size": 0})


def test_activity_structured_validation():
    with pytest.raises(ValueError, match="requires 'activation_prob'"):
        create_network_spec(
            name="work",
            kind="activity_structured",
            config={"mean_contacts": 10},
        )
    with pytest.raises(ValueError, match="between 0 and 1"):
        create_network_spec(
            name="work",
            kind="activity_structured",
            config={"mean_contacts": 10, "activation_prob": 1.5},
        )


def test_activity_random_validation():
    with pytest.raises(ValueError, match="requires 'mean_contacts'"):
        create_network_spec(name="rnd", kind="activity_random", config={})
    with pytest.raises(ValueError, match="positive number"):
        create_network_spec(
            name="rnd",
            kind="activity_random",
            config={"mean_contacts": 3, "dispersion": 0},
        )


def test_scenario_resolve_preserves_validated_network_specs():
    specs = [
        create_network_spec("households", "household", {"population_size": 1000}),
        create_network_spec(
            "work", "activity_structured", {"mean_contacts": 10, "activation_prob": 0.5}
        ),
        create_network_spec("community", "activity_random", {"mean_contacts": 4}),
    ]
    scenario = create_scenario(
        name="networked",
        base_params={"relative_transmission": 1.0, "testing_rate": 1.0},
        network_specs=specs,
    )

    resolved = resolve_scenario(scenario)
    assert [s.name for s in resolved.network_specs] == ["households", "work", "community"]

    grouped = group_network_specs_by_kind(resolved.network_specs)
    assert set(grouped.keys()) == {"household", "activity_structured", "activity_random"}

    as_dict = network_spec_to_dict(resolved.network_specs[0])
    assert as_dict["name"] == "households"
    assert as_dict["kind"] == "household"

