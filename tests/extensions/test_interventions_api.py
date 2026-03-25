import pytest

from extensions.scenario_api import (
    add_intervention,
    create_parameter_intervention,
    create_scenario,
    intervention_to_events,
    interventions_to_events,
    resolve_scenario,
    run_scenario,
)


def test_parameter_intervention_validates_empty_params():
    with pytest.raises(ValueError, match="must not be empty"):
        create_parameter_intervention("lockdown", start=5, params={})


def test_parameter_intervention_validates_start_and_end():
    with pytest.raises(ValueError, match="non-negative int"):
        create_parameter_intervention("x", start=-1, params={"p": 1.0})

    with pytest.raises(ValueError, match="end must be >= start"):
        create_parameter_intervention("x", start=3, end=2, params={"p": 1.0})


def test_parameter_intervention_generates_restore_events():
    intervention = create_parameter_intervention(
        name="lockdown",
        start=10,
        end=20,
        params={"relative_transmission": 0.8, "testing_rate": 0.3},
    )

    events = intervention_to_events(
        intervention,
        base_params={"relative_transmission": 1.2, "testing_rate": 0.1},
    )

    assert len(events) == 4
    assert [(e.time, e.target, e.value) for e in events] == [
        (10, "relative_transmission", 0.8),
        (10, "testing_rate", 0.3),
        (20, "relative_transmission", 1.2),
        (20, "testing_rate", 0.1),
    ]


def test_parameter_intervention_restore_requires_base_param():
    intervention = create_parameter_intervention(
        name="restore_missing",
        start=1,
        end=2,
        params={"unknown_param": 0.0},
    )

    with pytest.raises(ValueError, match="missing in base_params"):
        intervention_to_events(intervention, base_params={})


def test_interventions_to_events_flattens_list():
    first = create_parameter_intervention("a", start=1, params={"x": 2.0})
    second = create_parameter_intervention("b", start=2, params={"y": 3.0})

    events = interventions_to_events([first, second], base_params={"x": 1.0, "y": 1.0})
    assert [(e.time, e.target, e.value) for e in events] == [
        (1, "x", 2.0),
        (2, "y", 3.0),
    ]


def test_scenario_resolve_and_runner_with_intervention():
    intervention = create_parameter_intervention(
        name="temporary_transmission_cut",
        start=2,
        end=4,
        params={"relative_transmission": 0.5},
    )

    scenario = create_scenario(
        name="with_intervention",
        base_params={"relative_transmission": 1.2, "testing_rate": 1.0},
        interventions=[intervention],
    )
    # Also verify add_intervention API while preserving immutable style.
    scenario = add_intervention(
        create_scenario(
            name=scenario.name,
            base_params=scenario.base_params,
            interventions=[],
        ),
        intervention,
    )

    resolved = resolve_scenario(scenario)
    assert 2 in resolved.events_by_time
    assert 4 in resolved.events_by_time
    assert [e.value for e in resolved.events_by_time[2] if e.target == "relative_transmission"] == [0.5]
    assert [e.value for e in resolved.events_by_time[4] if e.target == "relative_transmission"] == [1.2]

    result = run_scenario(resolved, steps=6)
    assert len(result.raw_outputs["cases"]) == 6

