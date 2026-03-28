# Codex Recipe: Fix Runtime Intervention Application in OpenABM + Seed Control + R Proxy Diagnostics

## Goal

Fix the current execution bridge so that mapped interventions **actually affect the OpenABM run at runtime**.

At the moment, the main problem is not missing observed data.
The main problem is that the simulation grows almost like a baseline run because intervention effects are not being applied through a runtime-supported OpenABM path.

This task must do three things together:

1. **fix runtime intervention application**
2. **expose seed infections explicitly**
3. **add R-proxy calculation and notebook visualization**

This is still **not** full calibration.
It is a focused execution-layer correction and diagnostics step.

---

## Main problem to fix

Current behavior suggests this failure mode:

- timeline events are mapped to interventions
- interventions are converted into event-style parameter updates
- those updates target a parameter like `relative_transmission`
- in the real OpenABM execution path, that parameter is **not actually applied through a supported runtime update path**
- when unsupported updates are silently ignored, the simulation runs close to baseline

So the main task is:

**connect intervention effects to the actual runtime-supported OpenABM controls**
instead of writing to parameters that are ignored in practice.

---

## Scope

Implement:

- a runtime-supported intervention application path for OpenABM
- explicit `initial_infected`
- explicit R-proxy calculation
- improved notebook plots so observed data is visible even when simulated scale is much larger
- clear notebook diagnostics

Do NOT implement:

- full calibration
- imported infections per day
- full testing/tracing realism
- GUI
- broad redesign of the whole architecture

Keep this step focused and honest.

---

## Files

Update as needed:

- `extensions/scenario_api/openabm_adapter.py`
- `extensions/scenario_api/execution_pipeline.py`
- `extensions/scenario_api/runner.py`
- `extensions/scenario_api/interventions.py`
- `extensions/scenario_api/__init__.py`

Update notebook:

- `extensions/notebooks/end_to_end_multi_shp_test.ipynb`

If a better file split exists already, adapt to it.
But keep the OpenABM-specific runtime logic centralized.

---

## 1. Fix runtime intervention application

### Required principle

Do **not** rely on writing intervention effects into a generic parameter that OpenABM does not actually honor during runtime updates.

Instead:

- inspect the real OpenABM wrapper / adapter path
- identify which runtime update methods or supported parameters are actually used by the model during stepping
- route intervention effects through those supported controls

### Required implementation task

Add a dedicated function in the adapter layer, something like:

```python
apply_runtime_interventions_to_openabm(model_adapter, compiled_effects, strict=True) -> None
```

Behavior:
- receives already compiled model-facing intervention effects
- applies them through the real supported OpenABM runtime path
- raises a clear error if an effect cannot be applied and `strict=True`
- logs or records unsupported effects explicitly if `strict=False`

### Important rule

Do **not** silently ignore unsupported runtime updates in normal debugging mode.

For this step:
- default to a strict mode or at least a very visible warning mode
- make it obvious in notebook output which intervention effects were applied and which were not

---

## 2. Introduce explicit compiled runtime effect objects

If not already present, add a small explicit representation for runtime-applicable effects.

Suggested simple structure:

```python
@dataclass
class CompiledRuntimeEffect:
    target: str
    value: float
    metadata: dict[str, object] = field(default_factory=dict)
```

Examples:
- network/contact multipliers
- transmission-related multipliers
- other runtime-supported controls

This should help separate:
- high-level intervention objects
- runtime-applicable OpenABM controls

Do not overengineer this.
Keep it small.

---

## 3. Add a compile step for runtime-supported effects

Implement or refine a helper like:

```python
compile_runtime_effects(active_interventions, t, ...) -> list[CompiledRuntimeEffect]
```

Behavior:
- combine currently active interventions
- translate them into the exact runtime controls supported by the OpenABM adapter
- do not emit generic effects that cannot actually be applied

This is the key correction.
The compiler must now target the real adapter contract, not an imaginary generic transmission knob.

---

## 4. Make unsupported effects explicit

If some intervention types are still not wired to real runtime behavior, do not fake support.

Examples likely still incomplete:
- testing policy
- contact tracing policy

For this step:
- it is acceptable to leave them as placeholders
- but the notebook and logs must clearly say they are not yet affecting the OpenABM run

Required behavior:
- if a placeholder intervention is encountered, record it explicitly
- do not pretend it was applied

Implement something like:
- `applied_effects`
- `unsupported_effects`

and return or log both.

---

## 5. Seed infections: make them explicit and used

The current default appears to come from OpenABM baseline parameters:
- `n_seed_infection = 10`
- `rng_seed = 1`

This task must expose seed infections explicitly in the current pipeline.

### Required parameter

Use:

```python
initial_infected=100
```

### Required behavior

- validate integer
- validate `initial_infected >= 0`
- pass it into the actual OpenABM initialization path
- do not leave it as a hidden baseline default

### Required notebook behavior

Print clearly for each run:
- `initial_infected`
- whether it overrides the OpenABM default successfully

If the adapter cannot confirm the override, raise a clear error or warning.

---

## 6. Metric correctness: use daily cases, not cumulative by accident

Before plotting anything, make sure the compared metric is explicit.

For this notebook comparison against THL first-wave SHP cases, use:

- observed THL **daily cases**
- simulated **daily cases**
- optionally scaled simulated daily cases
- optionally detected simulated daily cases if a detection layer already exists

Do **not** accidentally compare:
- cumulative simulated infections
against
- daily observed cases

Add explicit variable names in code and notebook prints.

Required names if practical:
- `observed_daily_cases`
- `simulated_daily_cases`
- `simulated_scaled_daily_cases`

---

## 7. R proxy calculation

Add a simple R-like proxy series for diagnostics.

### Required helper

Implement something like:

```python
compute_r_proxy_from_incidence(timeseries, generation_interval=5) -> TimeSeries
```

### Suggested formula

For day `t`:

```text
R_proxy[t] = incidence[t] / incidence[t - generation_interval]
```

### Required behavior

- safe handling when denominator is zero or very small
- use NaN or skip invalid points
- do not create meaningless huge spikes silently

### Metadata

Store at least:
- method = `"ratio_over_lagged_incidence"`
- generation_interval

This is a diagnostic proxy only, not a formal Rt estimator.

---

## 8. Notebook plotting requirements

Update:

- `extensions/notebooks/end_to_end_multi_shp_test.ipynb`

### Required date window

Keep the explicit first-wave window:

- `2020-03-01`
- `2020-06-30`

### Required notebook focus

For this diagnostics pass, focus mainly on:

- `Helsinki and Uusimaa`

You may still keep the multi-SHP structure, but the detailed debugging plots must at least be shown for HUS.

---

### Required notebook parameters near the top

Define and print clearly:

```python
reference_start_date = "2020-03-01"
end_date = "2020-06-30"
initial_infected = 100
generation_interval = 5
strict_runtime_updates = True
```

If a detection layer already exists, you may keep it, but it is not the primary target of this recipe.

---

### Required notebook diagnostic outputs

#### A. Runtime application summary
For the HUS run, print:
- number of active interventions
- number of compiled runtime effects
- number of applied effects
- number of unsupported effects

Also print a few example applied effects.

This is required.

#### B. Daily-case comparison plot
Plot:
- observed THL daily cases
- simulated daily cases or simulated scaled daily cases, whichever is the current comparison series

Make the observed series visible even if simulated magnitude is much larger.

### Required visualization improvement

Because large simulated values can flatten the observed curve visually, add one of these:

- a second plot with a log y-scale
- or two separate plots:
  - linear scale
  - log scale

At least one readability fix is required.

Do not leave the notebook in a state where the observed curve is visually unreadable.

#### C. R proxy plot
Create a separate plot:
- simulated R proxy over time
- horizontal line at `R = 1`

This is required.

#### D. Seed sensitivity mini-test
Run a small seed test for HUS, with at least:

```python
seed_values = [10, 50, 100, 500]
```

Keep everything else fixed.
Show clearly how early growth timing changes.

#### E. Runtime-effect sanity check
Add one explicit notebook cell that prints whether intervention effects actually changed across the timeline.
For example:
- first period multipliers
- lockdown-period multipliers
- later-period multipliers

The goal is to show that the model is no longer running as pure baseline.

---

## 9. Validation requirements

Implement clear errors or warnings for:

- unsupported runtime effects
- seed override failure
- invalid seed
- missing daily incidence series
- R-proxy calculation failure due to bad input

Do not fail silently.
Do not silently ignore unsupported runtime control requests in this debugging step.

---

## 10. Success criteria

This task is complete when all of the following are true:

1. interventions are compiled into runtime-supported OpenABM effects
2. those effects are actually applied during simulation
3. unsupported effects are explicitly reported
4. `initial_infected` is explicit and overrides the baseline default
5. the notebook shows visible evidence that runtime effects change over time
6. the notebook plots:
   - observed vs simulated daily cases
   - a readability-improved version (e.g. log scale)
   - R proxy over time
7. the notebook runs a small seed sensitivity test

---

## 11. Design rules

Do NOT:

- keep using a runtime parameter path that is ignored in practice
- silently swallow unsupported updates
- redesign the whole intervention architecture
- claim testing/tracing works if still placeholder
- hide the important diagnostics inside notebook-only code

Keep it:
- explicit
- runtime-realistic
- easy to debug

---

## Final note

This step is about fixing the core execution truth:

- timeline mapping may be fine
- observed data may be fine
- but if runtime intervention effects do not reach OpenABM, the simulation will look almost like baseline

So the exact purpose here is:

**make intervention effects really reach the running OpenABM model, expose seed control, and visualize epidemic growth diagnostics clearly.**
