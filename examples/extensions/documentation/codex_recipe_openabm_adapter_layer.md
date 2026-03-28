# Codex Recipe: First OpenABM Adapter / Builder Layer

## Goal

Implement the **first adapter / builder layer** that connects the current scenario API to an actual OpenABM run.

At this point, the project already has a declarative API with:

- parameter blocks
- scenarios
- interventions
- network specifications

The next step is to build the **first explicit bridge** between that API and the real OpenABM execution layer.

The key idea is:

```text
Scenario -> ResolvedScenario -> OpenABM Adapter -> OpenABM model run
```

This step should not redesign the current architecture.
It should add a clean integration layer so that the declarative scenario model can drive a real OpenABM simulation.

---

## Scope of this task

Implement only the **first integration layer**.

This task should include:

- an adapter module that translates resolved scenario data into OpenABM-facing inputs
- a builder/factory function that creates an OpenABM-backed model runner
- a minimal execution path that runs a real scenario using the existing step-by-step logic where possible
- notebook coverage that demonstrates the adapter path

This task should **not** include:

- OpenABM core modifications
- network rebuild logic
- dynamic rewiring
- postcode-level localization
- waning immunity core changes
- full calibration workflow
- a broad refactor of the current runner design

Keep the implementation narrow, explicit, and easy to debug.

---

## Design principle

Preserve the current architecture:

- `Scenario` is declarative
- `ResolvedScenario` is the resolved recipe
- `Runner` executes step-by-step
- the new adapter layer translates current API concepts into OpenABM-compatible calls

The adapter should be a **boundary layer**.
It should isolate OpenABM-specific details from the higher-level scenario API.

That means:

- higher-level objects should remain OpenABM-agnostic
- OpenABM naming / wiring should be localized in the adapter layer

---

## File changes

Extend under:

```text
extensions/scenario_api/
```

Add:

```text
extensions/scenario_api/
  openabm_adapter.py
```

You may also update, if needed:

- `runner.py`
- `resolver.py`
- `__init__.py`

Also update the notebook:

```text
extensions/notebooks/scenario_api_smoke_test.ipynb
```

Add a new section that exercises the OpenABM adapter path.

If the existing smoke test notebook becomes too cluttered, it is acceptable to instead create:

```text
extensions/notebooks/scenario_api_openabm_adapter_test.ipynb
```

Choose whichever is cleaner, but keep the notebook focused and runnable.

---

## Main architectural requirement

Do **not** spread OpenABM-specific logic across all modules.

Centralize it in the new adapter module as much as reasonably possible.

The higher-level API should still work in dummy mode without OpenABM.

---

## Adapter responsibilities

Implement a minimal but clear set of responsibilities.

### 1. Parameter translation

Translate:

- `ResolvedScenario.resolved_params`

into a validated dictionary suitable for OpenABM initialization and/or runtime parameter updates.

At this stage, the translation may be simple if current parameter names are already close to OpenABM names.

But make the translation step explicit, even if it currently behaves mostly like pass-through.

Implement a function like:

```python
resolved_params_to_openabm_params(resolved_params) -> dict
```

Behavior:
- returns a new dict
- may currently pass through keys unchanged
- should be the single obvious place for future name mapping or normalization

---

### 2. Network spec translation

Translate current generic network specs into an OpenABM-facing network configuration description.

Implement a function like:

```python
network_specs_to_openabm_config(network_specs) -> dict
```

Behavior:
- takes validated `NetworkSpec` objects
- returns a simple OpenABM-facing config summary
- does **not** need to construct real graphs yet
- should make explicit how the three supported generic kinds map conceptually to OpenABM categories

For now, support this conceptual mapping:

- `household` -> household-related initialization config
- `activity_structured` -> occupation-like config
- `activity_random` -> random/community-like config

This can initially produce a summary dict or similar intermediate structure if direct low-level wiring is not yet stable.

The important thing is to establish the adapter boundary clearly.

---

### 3. OpenABM model factory

Implement a model factory function like:

```python
create_openabm_model(resolved_scenario, **kwargs)
```

Behavior:
- translates params
- translates network specs
- initializes the OpenABM model if the required OpenABM objects are available
- raises a clear error if OpenABM is not available in the current environment
- returns an object usable by the existing runner path, or returns a small wrapper object

Keep this practical rather than elegant.

---

## Wrapper object (recommended)

Recommended: define a small wrapper class in `openabm_adapter.py`, for example:

```python
class OpenABMModelAdapter:
    ...
```

Possible responsibilities:
- hold the underlying OpenABM model instance
- expose:
  - `step()`
  - `apply_params(params)` or similar
  - `extract_outputs()` or similar

This is recommended because it gives the existing runner a stable interface without forcing the higher-level runner to know OpenABM internals.

If the current runner already expects a factory + extractor pattern, preserve that pattern and make the wrapper fit it.

---

## Runner integration

Update the runner only as much as needed to support the adapter path.

The current runner likely already supports:
- dummy mode
- event application
- result extraction

Preserve that.

Add a minimal integration path so that:

- a resolved scenario can be run with a real OpenABM-backed model factory
- event-driven parameter changes still go through the same event mechanism where possible

Important:
- do not rewrite the event system
- do not rewrite the scenario model
- do not collapse everything into OpenABM-specific code

If some parameter updates cannot yet be applied live to the real model, do this honestly:
- document the limitation in code comments
- either raise a clear error
- or apply only the supported subset in this first version

Do not fake support for runtime updates that do not actually work.

---

## Output extraction

Implement a minimal extraction path from the OpenABM-backed model into the existing `SimulationResult` format.

Implement something like:

```python
extract_openabm_outputs(model_adapter) -> dict[str, list[float]]
```

or a method on the wrapper.

At minimum, collect one or more simple series that are actually available and stable in the current OpenABM setup.

Choose a small stable subset.
Do not attempt to expose every metric.

If exact OpenABM result access is slightly awkward, keep the first version narrow and explicit.

---

## Suggested functions in `openabm_adapter.py`

Implement at least these, or close equivalents:

```python
resolved_params_to_openabm_params(resolved_params) -> dict
network_specs_to_openabm_config(network_specs) -> dict
create_openabm_model(resolved_scenario, **kwargs)
create_openabm_runner_components(resolved_scenario, **kwargs) -> tuple
```

Recommended additional class:

```python
class OpenABMModelAdapter:
    ...
```

And optionally:

```python
is_openabm_available() -> bool
```

This can help produce clean notebook behavior.

---

## Practical constraint

Be guided by what the local repo and environment actually support.

Do not invent a fake OpenABM API.

Inspect the current codebase and use the real available model creation path already present in the repository.

If the real API differs from the function names suggested here, adapt to reality.
The important part is the architectural role, not the exact names.

---

## Notebook requirements

Update or create a notebook to test the adapter layer.

### Required notebook flow

#### A. Imports
- import the scenario API
- import the OpenABM adapter functions
- handle the case where OpenABM is unavailable with a clear message

#### B. Create a simple scenario
Use:
- base params
- at least one parameter block
- at least one intervention
- at least one network spec of each supported kind if practical, or at least a representative subset

#### C. Resolve the scenario
- print resolved params
- print network specs
- print generated events

#### D. Adapter translation inspection
- show output of:
  - `resolved_params_to_openabm_params(...)`
  - `network_specs_to_openabm_config(...)`

Print these clearly.

#### E. Create OpenABM-backed model
- build the real adapter/model if available
- show that initialization succeeds

#### F. Run a short real simulation
- run a small number of steps
- keep it lightweight
- extract outputs into `SimulationResult`

#### G. Convert to `TimeSeries`
- use the existing result conversion path if possible
- print and/or plot at least one series

#### H. Graceful fallback
If the environment does not support a real OpenABM run, the notebook should:
- clearly explain that
- still demonstrate the adapter translation layer
- not fail in a confusing way

But since this repository should already be set up, prefer actually exercising the real model path if possible.

---

## Validation and error behavior

Implement clear errors for:

- OpenABM package/module not available
- unsupported runtime parameter update requests
- unsupported network mapping situations in this first version

Use direct `ValueError` / `RuntimeError` messages.
Do not hide failures.

---

## Success criteria

This task is complete when all of the following are true:

1. there is a dedicated OpenABM adapter module
2. parameter translation is explicit
3. network spec translation is explicit
4. the current scenario API can be connected to a real OpenABM-backed execution path
5. the runner architecture is preserved rather than rewritten
6. the notebook demonstrates:
   - scenario creation
   - scenario resolution
   - adapter translation
   - real or gracefully-failed OpenABM initialization
   - short execution path
   - output extraction

---

## Coding style

Requirements:

- keep the implementation explicit
- use type hints
- add short docstrings
- centralize OpenABM-specific logic
- avoid broad refactoring
- preserve compatibility with the existing dummy path
- prefer small honest limitations over pretending full support

---

## What not to do in this task

Do not implement:
- new epidemiological model states
- waning immunity
- network rebuild engine
- calibration machinery
- postcode-level household generation
- UI adapters
- full scenario serialization framework

This task is only the first real execution bridge.

---

## Final note

This is the point where the project stops being only a declarative API and becomes a real layered system:

- high-level scenario API
- intervention layer
- network specification layer
- OpenABM execution adapter

That bridge is the goal of this step.
