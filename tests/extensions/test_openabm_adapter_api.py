import pytest
import os

from extensions.scenario_api import (
    NetworkSpec,
    ResolvedScenario,
    create_openabm_runner_components,
    is_openabm_available,
    network_specs_to_openabm_config,
    resolved_params_to_openabm_params,
    run_scenario,
    supported_runtime_update_params,
)


def test_resolved_params_to_openabm_params_maps_population_size():
    translated = resolved_params_to_openabm_params(
        {"population_size": 1234, "relative_transmission": 1.1}
    )
    assert translated["n_total"] == 1234
    assert translated["relative_transmission"] == 1.1


def test_network_specs_to_openabm_config_mapping():
    specs = [
        NetworkSpec(name="households", kind="household", config={"population_size": 1000}),
        NetworkSpec(
            name="work",
            kind="activity_structured",
            config={"mean_contacts": 10, "activation_prob": 0.5},
        ),
        NetworkSpec(
            name="community",
            kind="activity_random",
            config={"mean_contacts": 4, "dispersion": 2},
        ),
    ]

    mapped = network_specs_to_openabm_config(specs)
    assert len(mapped["household"]) == 1
    assert len(mapped["occupation_like"]) == 1
    assert len(mapped["random_like"]) == 1


def test_supported_runtime_update_params_returns_list():
    params = supported_runtime_update_params()
    assert isinstance(params, list)


@pytest.mark.skipif(
    (not is_openabm_available()) or os.getenv("RUN_OPENABM_ADAPTER_TESTS") != "1",
    reason="OpenABM runtime test is opt-in (set RUN_OPENABM_ADAPTER_TESTS=1)",
)
def test_openabm_runner_components_execute_short_run():
    resolved = ResolvedScenario(
        name="openabm_smoke",
        resolved_params={"n_total": 500, "end_time": 20, "test_on_symptoms": 0},
        network_specs=[
            NetworkSpec(
                name="households",
                kind="household",
                config={"population_size": 500},
            )
        ],
        events_by_time={2: []},
        metadata={},
    )
    model_factory, result_extractor = create_openabm_runner_components(resolved)
    result = run_scenario(
        resolved,
        steps=3,
        model_factory=model_factory,
        result_extractor=result_extractor,
    )
    assert "cases" in result.raw_outputs
    assert len(result.raw_outputs["cases"]) == 3
