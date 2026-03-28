from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from .networks import NetworkSpec, validate_network_specs
from .resolver import ResolvedScenario


def is_openabm_available() -> bool:
    """Return True when the local environment can import the OpenABM Python API."""
    try:
        from COVID19.model import Model, Parameters  # noqa: F401
        return True
    except Exception:
        return False


def supported_runtime_update_params() -> List[str]:
    """Return OpenABM parameter names that are safe to update during runtime."""
    if not is_openabm_available():
        return []
    from COVID19.model import PYTHON_SAFE_UPDATE_PARAMS

    return sorted(list(PYTHON_SAFE_UPDATE_PARAMS))


def resolved_params_to_openabm_params(resolved_params: Dict[str, Any]) -> Dict[str, Any]:
    """Translate resolved scenario parameters into OpenABM-facing parameter names."""
    translated = dict(resolved_params)
    if "population_size" in translated and "n_total" not in translated:
        translated["n_total"] = translated["population_size"]
    if "initial_infected" in translated and "n_seed_infection" not in translated:
        try:
            translated["n_seed_infection"] = int(translated["initial_infected"])
        except (TypeError, ValueError) as exc:
            raise ValueError("initial_infected must be an integer") from exc
    translated.pop("initial_infected", None)
    return translated


def network_specs_to_openabm_config(network_specs: List[NetworkSpec]) -> Dict[str, Any]:
    """Translate generic network specs into a simple OpenABM-facing config summary."""
    validate_network_specs(network_specs)
    config: Dict[str, Any] = {
        "household": [],
        "occupation_like": [],
        "random_like": [],
    }
    for spec in network_specs:
        payload = {
            "name": spec.name,
            "kind": spec.kind,
            "config": dict(spec.config),
            "metadata": dict(spec.metadata or {}),
        }
        if spec.kind == "household":
            config["household"].append(payload)
        elif spec.kind == "activity_structured":
            config["occupation_like"].append(payload)
        elif spec.kind == "activity_random":
            config["random_like"].append(payload)
    return config


@dataclass
class OpenABMModelAdapter:
    """Thin wrapper that exposes a stable interface for runner integration."""

    model: Any
    applied_params: Dict[str, Any] = field(default_factory=dict)
    outputs_history: Dict[str, List[float]] = field(
        default_factory=lambda: {"cases": [], "infected": [], "deaths": [], "cases_cumulative": []}
    )
    strict_runtime_updates: bool = True
    _last_total_case: Optional[float] = None

    def update_params(self, params: Dict[str, Any]) -> None:
        """Apply runtime-updatable parameter changes to the running OpenABM model."""
        allowed = set(supported_runtime_update_params())
        for key, value in params.items():
            if self.applied_params.get(key) == value:
                continue
            if allowed and key not in allowed:
                message = (
                    f"Unsupported runtime parameter update for '{key}' in OpenABM adapter. "
                    "Parameter is not in PYTHON_SAFE_UPDATE_PARAMS."
                )
                if self.strict_runtime_updates:
                    raise RuntimeError(message)
                continue
            try:
                self.model.update_running_params(key, value)
                self.applied_params[key] = value
            except Exception as exc:
                raise RuntimeError(
                    f"Unsupported runtime parameter update for '{key}' in OpenABM adapter: {exc}"
                ) from exc

    def step(self) -> Dict[str, float]:
        """Advance one simulation step and return one-step extracted outputs."""
        self.model.one_time_step()
        results = self.model.one_time_step_results()
        total_case = float(results.get("total_case", 0.0))
        if self._last_total_case is None:
            daily_cases = total_case
        else:
            daily_cases = total_case - float(self._last_total_case)
        self._last_total_case = total_case
        if daily_cases < 0:
            daily_cases = 0.0
        step_data = {
            "cases": float(daily_cases),
            "cases_cumulative": float(total_case),
            "infected": float(results.get("total_infected", 0.0)),
            "deaths": float(results.get("total_death", 0.0)),
        }
        for key, value in step_data.items():
            self.outputs_history.setdefault(key, []).append(float(value))
        return step_data

    def get_outputs(self) -> Dict[str, List[float]]:
        """Return collected output time series from adapter-managed steps."""
        return {key: list(values) for key, values in self.outputs_history.items()}


def create_openabm_model(
    resolved_scenario: ResolvedScenario,
    initial_params: Optional[Dict[str, Any]] = None,
    model_kwargs: Optional[Dict[str, Any]] = None,
    strict_runtime_updates: bool = True,
) -> OpenABMModelAdapter:
    """Create an OpenABM-backed model adapter for the given resolved scenario."""
    if not is_openabm_available():
        raise RuntimeError("OpenABM Python API is not available in this environment")

    from COVID19.model import Model, Parameters

    base_params = initial_params if initial_params is not None else resolved_scenario.resolved_params
    openabm_params = resolved_params_to_openabm_params(base_params)
    _ = network_specs_to_openabm_config(resolved_scenario.network_specs)

    params_obj = Parameters()
    default_n_total = params_obj.get_param("n_total")
    applied: Dict[str, Any] = {}
    skipped: Dict[str, Any] = {}
    for key, value in openabm_params.items():
        if key == "n_total" and value != default_n_total:
            raise RuntimeError(
                "Setting n_total through the first adapter layer is currently unsupported "
                "because the default household-demographics source is not rebuilt here. "
                "Use the default n_total for now."
            )
        try:
            params_obj.set_param(key, value)
            applied[key] = value
        except Exception:
            skipped[key] = value

    kwargs = dict(model_kwargs or {})
    model = Model(params_object=params_obj, **kwargs)

    _ = skipped
    return OpenABMModelAdapter(
        model=model,
        applied_params=applied,
        strict_runtime_updates=strict_runtime_updates,
    )


def extract_openabm_outputs(model_adapter: OpenABMModelAdapter) -> Dict[str, List[float]]:
    """Extract accumulated outputs from an OpenABM adapter instance."""
    return model_adapter.get_outputs()


def apply_runtime_interventions_to_openabm(
    model_adapter: OpenABMModelAdapter,
    compiled_effects: Dict[str, Any],
    strict: bool = True,
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Apply already-compiled runtime effects through OpenABM's supported runtime API.

    Returns a diagnostics dict with applied and unsupported effects.
    """
    allowed = set(supported_runtime_update_params())
    applied: List[Dict[str, Any]] = []
    unsupported: List[Dict[str, Any]] = []

    for effect in compiled_effects.get("applied_effects", []):
        target = getattr(effect, "target", None)
        value = getattr(effect, "value", None)
        metadata = dict(getattr(effect, "metadata", {}) or {})

        if not isinstance(target, str) or target == "":
            message = "Invalid runtime effect target"
            if strict:
                raise RuntimeError(message)
            unsupported.append({"target": str(target), "value": value, "metadata": metadata, "reason": message})
            continue

        if allowed and target not in allowed:
            message = f"Unsupported runtime effect target '{target}'"
            if strict:
                raise RuntimeError(message)
            unsupported.append({"target": target, "value": value, "metadata": metadata, "reason": message})
            continue

        try:
            model_adapter.model.update_running_params(target, value)
            model_adapter.applied_params[target] = value
            applied.append({"target": target, "value": float(value), "metadata": metadata})
        except Exception as exc:
            message = f"Failed to apply runtime effect '{target}': {exc}"
            if strict:
                raise RuntimeError(message) from exc
            unsupported.append({"target": target, "value": value, "metadata": metadata, "reason": message})

    for effect in compiled_effects.get("unsupported_effects", []):
        unsupported.append(
            {
                "target": getattr(effect, "target", None),
                "value": getattr(effect, "value", None),
                "metadata": dict(getattr(effect, "metadata", {}) or {}),
                "reason": "placeholder_not_runtime_wired",
            }
        )

    return {
        "applied_effects": applied,
        "unsupported_effects": unsupported,
    }


def create_openabm_runner_components(
    resolved_scenario: ResolvedScenario,
    model_kwargs: Optional[Dict[str, Any]] = None,
    strict_runtime_updates: bool = True,
) -> Tuple[Callable[..., OpenABMModelAdapter], Callable[..., Dict[str, float]]]:
    """Create model factory and extractor compatible with run_scenario(...)."""

    def model_factory(initial_params: Dict[str, Any], scenario: ResolvedScenario = None) -> OpenABMModelAdapter:
        target = scenario if scenario is not None else resolved_scenario
        return create_openabm_model(
            resolved_scenario=target,
            initial_params=initial_params,
            model_kwargs=model_kwargs,
            strict_runtime_updates=strict_runtime_updates,
        )

    def result_extractor(
        model: OpenABMModelAdapter,
        step_output: Optional[Dict[str, float]],
        t: int,
        params: Dict[str, Any],
    ) -> Dict[str, float]:
        if isinstance(step_output, dict):
            return step_output
        outputs = model.get_outputs()
        return {key: values[-1] for key, values in outputs.items() if values}

    return model_factory, result_extractor
