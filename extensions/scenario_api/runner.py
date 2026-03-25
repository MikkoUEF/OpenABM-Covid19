from dataclasses import dataclass
from typing import Dict, Any, List, Callable, Optional
from numbers import Number
from .resolver import ResolvedScenario
from .events import TimelineEvent


@dataclass
class SimulationResult:
    """Result of a simulation run."""
    scenario_name: str
    raw_outputs: Dict[str, List[float]]
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


def apply_event_to_params(current_params: Dict[str, Any], event: TimelineEvent) -> Dict[str, Any]:
    """Apply an event to current parameters."""
    new_params = current_params.copy()
    if event.action == "set":
        new_params[event.target] = event.value
    elif event.action == "scale":
        if event.target not in new_params:
            raise ValueError(f"Cannot scale {event.target}: not in params")
        new_params[event.target] *= event.value
    return new_params


def run_scenario(resolved_scenario: ResolvedScenario, steps: int, model_factory: Optional[Callable] = None, result_extractor: Optional[Callable] = None) -> SimulationResult:
    """Run a resolved scenario for a number of steps."""
    current_params = resolved_scenario.resolved_params.copy()
    raw_outputs: Dict[str, List[float]] = {"cases": []}
    model = None
    if model_factory is not None:
        try:
            model = model_factory(current_params.copy(), resolved_scenario)
        except TypeError:
            model = model_factory(current_params.copy())
    dummy_cases = 1.0

    for t in range(steps):
        # Apply events at this time
        if t in resolved_scenario.events_by_time:
            for event in resolved_scenario.events_by_time[t]:
                current_params = apply_event_to_params(current_params, event)
            if model is not None and hasattr(model, "update_params"):
                model.update_params(current_params.copy())

        if model is None:
            # Dummy simulation logic for smoke tests when no real model is provided.
            dummy_cases = dummy_cases * float(current_params.get("relative_transmission", 1.0))
            reported_cases = dummy_cases * float(current_params.get("testing_rate", 1.0))
            raw_outputs["cases"].append(float(reported_cases))
            continue

        step_output = model.step() if hasattr(model, "step") else None

        if result_extractor is not None:
            extracted = result_extractor(model, step_output, t, current_params.copy())
        elif isinstance(step_output, dict):
            extracted = step_output
        elif isinstance(step_output, Number):
            extracted = {"cases": float(step_output)}
        elif hasattr(model, "get_outputs"):
            extracted = model.get_outputs()
        else:
            raise ValueError(
                "Could not extract outputs from model. Provide result_extractor "
                "or return dict/number from model.step()."
            )

        if not isinstance(extracted, dict):
            raise ValueError("result_extractor must return a dict[str, float]-like object")

        for key, value in extracted.items():
            raw_outputs.setdefault(key, []).append(float(value))

    return SimulationResult(
        scenario_name=resolved_scenario.name,
        raw_outputs=raw_outputs,
        metadata={"steps": steps, "final_params": current_params.copy()},
    )
