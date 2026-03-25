import pytest

from extensions.scenario_api import (
    add_block,
    create_block,
    create_event,
    create_scenario,
    dataset_to_timeseries,
    load_observed_dataset,
    resolve_scenario,
    run_scenario,
)


def test_create_event_rejects_negative_time():
    with pytest.raises(ValueError, match="non-negative int"):
        create_event(time=-1, action="set", target="x", value=1.0)


def test_add_block_does_not_alias_original_scenario_dicts():
    original = create_scenario(name="base", base_params={"k": 1.0})
    updated = add_block(original, create_block("b1", {"x": 2.0}))

    original.base_params["k"] = 999.0

    assert updated.base_params["k"] == 1.0


def test_dataset_to_timeseries_rejects_mismatched_lengths():
    dataset = load_observed_dataset(
        name="obs",
        data={"time": [0, 1, 2], "cases": [1.0, 2.0]},
    )

    with pytest.raises(ValueError, match="Mismatched lengths"):
        dataset_to_timeseries(dataset, "cases")


def test_run_scenario_uses_model_factory_and_result_extractor():
    class DummyModel:
        def __init__(self, params):
            self.params = dict(params)

        def update_params(self, params):
            self.params = dict(params)

        def step(self):
            return {"cases": self.params["k"]}

    created = {"called": False}

    def model_factory(params):
        created["called"] = True
        return DummyModel(params)

    def result_extractor(model, step_output, t, params):
        out = dict(step_output)
        out["t"] = t
        return out

    scenario = create_scenario(
        name="with_model",
        base_params={"k": 2.0},
        events=[create_event(1, "set", "k", 3.0)],
    )
    resolved = resolve_scenario(scenario)

    result = run_scenario(
        resolved,
        steps=3,
        model_factory=model_factory,
        result_extractor=result_extractor,
    )

    assert created["called"] is True
    assert result.raw_outputs["cases"] == [2.0, 3.0, 3.0]
    assert result.raw_outputs["t"] == [0.0, 1.0, 2.0]

