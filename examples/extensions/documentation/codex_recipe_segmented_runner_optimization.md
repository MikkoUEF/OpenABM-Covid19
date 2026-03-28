# Codex Recipe: Segment-Based Runner Optimization Between Timeline Events

## Goal

Implement a **small performance optimization** in the scenario runner:

instead of advancing the model one step at a time for the whole simulation, the runner should advance the model in **segments between timeline events** whenever possible.

This is an optimization of the existing architecture, not a redesign.

The main idea is:

- if no event happens between step `t` and step `t_next`
- then there is no need for Python to loop through every intermediate step
- instead, the runner should call the underlying model in one chunk up to the next event boundary

Conceptually:

```text
run until next event -> apply events -> run until next event -> apply events -> ...
```

This should reduce Python-side overhead and move more work into the underlying engine.

---

## Scope of this task

Implement only the **segment-based run optimization**.

This task should include:

- a runner path that detects event boundaries
- chunked execution between events
- preservation of existing event semantics
- notebook testing and simple timing comparison

This task should **not** include:

- changes to the scenario model
- changes to intervention semantics
- changes to network specs
- OpenABM core modifications
- result format redesign
- major refactoring of the whole runner

Keep it narrow and testable.

---

## Design principle

Preserve the existing logic:

- events still occur at exact timeline steps
- event application order must remain correct
- the scenario API stays unchanged

Only the execution strategy changes.

Current conceptual behavior:

```text
for t in range(steps):
    if t has events:
        apply events
    model.step()
```

Optimized conceptual behavior:

```text
run from current step to next event step
apply events
repeat
run final segment to end
```

Important:
- the behavior must remain equivalent
- only the runner implementation should change

---

## Main requirement

Implement the optimization so that it works in two modes:

1. **segment mode** for models that support multi-step execution
2. **fallback mode** for models that only support single-step execution

This is important because:
- the dummy runner may only support step-by-step
- the OpenABM-backed adapter may support chunked running more efficiently

The runner should detect capability explicitly, not by guessing silently.

---

## Files to update

Likely file:

```text
extensions/scenario_api/runner.py
```

Possibly also:

- `openabm_adapter.py`
- `__init__.py`

Update notebook:

```text
extensions/notebooks/scenario_api_smoke_test.ipynb
```

or create a focused notebook if that is cleaner, for example:

```text
extensions/notebooks/scenario_runner_segment_test.ipynb
```

Use whichever is cleaner.

---

## Required implementation

### 1. Detect event boundaries

Use the existing `ResolvedScenario.events_by_time`.

Implement helper logic such as:

```python
get_event_times(resolved_scenario, steps) -> list[int]
```

Behavior:
- returns sorted event times within simulation bounds
- excludes times outside the run horizon
- should be simple and explicit

---

### 2. Segment planning

Implement helper logic such as:

```python
build_run_segments(event_times, steps) -> list[tuple[int, int]]
```

Meaning:
- produce segments like `(start, end)` where `end` is the next event boundary or the final step
- use a clearly documented convention:
  - for example `[start, end)` half-open intervals

Example:
- total steps = 100
- events at 10, 30, 80

Expected segments:
- `(0, 10)`
- `(10, 30)`
- `(30, 80)`
- `(80, 100)`

The event application should happen **at the segment boundary step** before the subsequent model advance, matching current semantics.

Be explicit in code comments about the chosen timing convention.

---

### 3. Model capability handling

Implement a small explicit capability check.

Recommended approach:

- if model has something like `run_steps(n)` or `run(n)`, use that
- otherwise fall back to repeated `step()`

This should be wrapped in one helper, for example:

```python
advance_model(model, n_steps) -> None
```

Behavior:
- if `n_steps <= 0`, do nothing
- prefer chunked execution when supported
- otherwise do a simple loop of `step()`

This keeps the optimization localized.

---

### 4. Preserve event semantics

The optimized runner must preserve this meaning:

- events scheduled at time `t` are applied **before** advancing the model through step `t`

If that differs from current semantics in the existing code, preserve the existing code’s actual behavior rather than introducing a silent semantic change.

Be explicit and careful here.

---

### 5. Result collection

Preserve current result behavior as much as possible.

If the current runner collects outputs every step, then keep that behavior, but do it in the least invasive way possible.

If full per-step collection makes chunking difficult, do this honestly:

- maintain correctness first
- keep the first optimization version modest
- document any limitation

A good first version is acceptable even if:
- chunked execution is used only when per-step extraction is not required
- or chunked execution still uses periodic extraction

Do not pretend to preserve fine-grained outputs if it does not actually do so.

---

## Recommended helper functions

Implement some or all of these if they fit the current code:

```python
get_event_times(resolved_scenario, steps) -> list[int]
build_run_segments(event_times, steps) -> list[tuple[int, int]]
advance_model(model, n_steps) -> None
run_scenario_segmented(resolved_scenario, steps, model_factory=None, result_extractor=None) -> SimulationResult
```

You may also integrate the segmented logic directly into the existing `run_scenario(...)`, but only if that remains clear.

If you modify the existing runner, preserve backward compatibility.

---

## OpenABM adapter support

If the OpenABM adapter already exists, extend it minimally so that the model wrapper can expose chunked execution cleanly.

For example, if appropriate:

```python
class OpenABMModelAdapter:
    def step(self): ...
    def run_steps(self, n_steps): ...
```

Where:
- `run_steps(n_steps)` uses the most efficient real underlying call available
- if no better option exists, it may internally fall back to repeated `step()`

The important thing is to expose a clean interface to the runner.

Do not overengineer this.

---

## Notebook requirements

Add a notebook section or a dedicated notebook that demonstrates the optimization.

### Required notebook flow

#### A. Create a scenario with multiple events
Use something like:
- event at 10
- event at 30
- event at 80

#### B. Show segment planning
Print:
- event times
- computed segments

This is important for debugging.

#### C. Run with current/fallback mode
Run the scenario with the current execution path.

#### D. Run with segmented mode
Run the same scenario with segmented execution.

#### E. Compare outputs
Verify that:
- output shape matches expectations
- event timing behavior remains correct
- trajectories are identical or acceptably identical, depending on model behavior

Be explicit if the comparison is exact or approximate.

#### F. Timing comparison
Add a simple timing measurement:
- fallback / step-by-step runner
- segmented runner

Use lightweight timing only.
No need for a full benchmark framework.

Print results clearly.

---

## Validation and correctness checks

Implement or demonstrate checks for:

- zero-event scenario
- event at step 0
- event at final step boundary
- consecutive event times if supported
- no negative-length segments

Use simple tests or notebook assertions where practical.

---

## Success criteria

This task is complete when all of the following are true:

1. the runner can identify event boundaries
2. it can execute in chunks between events
3. event semantics remain correct
4. fallback step-by-step mode still works
5. OpenABM-backed execution can use chunked execution if supported
6. the notebook demonstrates:
   - event times
   - segment plan
   - correctness check
   - simple timing comparison

---

## Coding style

Requirements:

- keep the implementation small and explicit
- preserve existing APIs if possible
- add short docstrings
- add comments on timing semantics
- avoid broad refactoring
- prefer correctness over aggressive optimization

---

## What not to do in this task

Do not implement:
- asynchronous execution
- parallel scenario execution
- caching layers
- output format redesign
- scenario batching
- intervention redesign
- network rebuild logic

This is only a focused runner optimization.

---

## Final note

This optimization is valuable because it targets likely Python overhead without touching the epidemiological core.

It should be treated as a clean execution-layer improvement:
- same scenarios
- same events
- same semantics
- less Python stepping overhead
