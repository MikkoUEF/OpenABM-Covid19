# Codex Recipe: Intervention Layer on Top of the Scenario API

## Goal

Implement the **first intervention abstraction** on top of the existing scenario/timeline interface.

The purpose of this step is to move from low-level `TimelineEvent` usage to a higher-level concept:

- users and later the UI should define **interventions**
- interventions should be converted into one or more `TimelineEvent` objects
- the runner should continue to work through events as before

In other words:

- `Scenario` remains the declarative recipe
- `Runner` still executes events step by step
- `Intervention` becomes the user-facing / API-facing way to describe policies

This step should be implemented **without changing the OpenABM core**.

---

## Scope of this task

Implement only the **first minimal intervention layer**.

Do **not** build a large hierarchy yet.
Do **not** implement UI logic.
Do **not** implement network rebuild logic.
Do **not** implement hard interventions yet, except keeping compatibility with the existing event model.

The only required intervention in this step is:

- `ParameterIntervention`

This intervention should describe a temporary parameter override over a time interval.

---

## Design principle

Use this model:

```text
Intervention -> TimelineEvent(s) -> Runner
```

An intervention must **not** modify the model directly.
An intervention must **not** know about OpenABM internals.
An intervention should only generate events.

---

## Directory / file changes

Extend the existing structure under:

```text
extensions/scenario_api/
```

Add:

```text
extensions/scenario_api/
  interventions.py
```

Update `__init__.py` accordingly.

Also update the existing notebook:

```text
extensions/notebooks/scenario_api_smoke_test.ipynb
```

so that it tests the new intervention layer.

---

## Objects to implement

Use `@dataclass` where appropriate.

### 1. `Intervention`

This is the abstract/base concept.

Fields:

- `name: str`
- `start: int`
- `end: int | None = None`
- `metadata: dict[str, object] = field(default_factory=dict)`

Behavior:

- validate that `start >= 0`
- if `end is not None`, validate `end >= start`
- expose:

```python
to_events(base_params: dict[str, object] | None = None) -> list[TimelineEvent]
```

The base class may either:
- raise `NotImplementedError`
- or be an abstract base class

Keep it simple.

---

### 2. `ParameterIntervention`

Subclass or specialization of `Intervention`.

Fields:

- inherited fields
- `params: dict[str, object]`

Meaning:

- at `start`, set the provided parameters to the intervention values
- at `end`, restore the previous values if `end` is provided

Important:
- restoration should use `base_params`
- if `end` is given and a restoration value is missing from `base_params`, raise a clear error
- if `end is None`, then the intervention becomes permanent from `start` onward

Example:

```python
ParameterIntervention(
    name="lockdown",
    start=10,
    end=30,
    params={
        "relative_transmission_work": 0.3,
        "relative_transmission_community": 0.5,
    },
)
```

This should generate events equivalent to:

- at `t=10`: set `relative_transmission_work = 0.3`
- at `t=10`: set `relative_transmission_community = 0.5`
- at `t=30`: restore `relative_transmission_work` from base params
- at `t=30`: restore `relative_transmission_community` from base params

---

## Functions to implement

### In `interventions.py`

Implement:

```python
create_parameter_intervention(
    name,
    start,
    params,
    end=None,
    metadata=None,
) -> ParameterIntervention
```

Behavior:
- validate `params` is a dict
- validate it is not empty
- return a `ParameterIntervention`

Also implement:

```python
intervention_to_events(
    intervention,
    base_params=None,
) -> list[TimelineEvent]
```

Behavior:
- convenience wrapper
- calls `intervention.to_events(...)`

Optional but recommended:

```python
interventions_to_events(
    interventions,
    base_params=None,
) -> list[TimelineEvent]
```

Behavior:
- converts a list of interventions into a flat list of events

---

## Scenario integration

Update the scenario concept so that interventions can be attached to a scenario.

There are two acceptable implementations. Use the simpler one.

### Preferred option

Extend `Scenario` with:

- `interventions: list[Intervention] = field(default_factory=list)`

and add:

```python
add_intervention(scenario, intervention) -> Scenario
```

Then update `resolve_scenario(...)` so that:

1. it resolves `base_params + blocks` into `resolved_params`
2. it converts scenario interventions to events using `resolved_params` as the restoration source
3. it combines:
   - explicit scenario events
   - intervention-generated events
4. it groups everything into `events_by_time`

This is the preferred option because interventions become part of the scenario recipe.

### Acceptable fallback

If changing `Scenario` is awkward, allow interventions to be passed into `resolve_scenario(...)`.

But prefer the first option unless the current code structure strongly resists it.

---

## Event semantics

For this task, interventions should generate only existing event types, using at least:

- `action="set"`

Do **not** invent a new runner mechanism unless absolutely necessary.

The runner should continue to work with normal `TimelineEvent` objects.

That is the key architectural constraint.

---

## Runner compatibility

Do not rewrite the runner architecture.

Only ensure that:
- existing event application still works
- intervention-generated events are handled identically to manual events

If needed, add small tests or debug prints in the notebook, but keep the code clean.

---

## `__init__.py`

Export at least:

- `Intervention`
- `ParameterIntervention`
- `create_parameter_intervention`
- `intervention_to_events`
- `interventions_to_events`
- `add_intervention` (if implemented)

---

## Notebook update

Update the notebook:

```text
extensions/notebooks/scenario_api_smoke_test.ipynb
```

Add a new section that tests the intervention layer.

### Required notebook additions

#### A. Create a `ParameterIntervention`

Example:

- name: `"lockdown"`
- start: `10`
- end: `20`
- params:
  - `relative_transmission = 0.8`
  - or a more specific transmission parameter if that is what the current dummy runner uses

#### B. Convert intervention to events

- show the generated events
- print them clearly

#### C. Attach intervention to scenario

- create a scenario using:
  - base params
  - blocks
  - one intervention
- resolve the scenario
- show that intervention-generated events are present in `events_by_time`

#### D. Run the scenario

- use the existing dummy runner or current test path
- run enough steps so that:
  - before `start`, one behavior is visible
  - between `start` and `end`, changed behavior is visible
  - after `end`, restored behavior is visible

#### E. Plot or print result

Show clearly that the intervention changes the trajectory and then restoration takes effect.

The point is not realism.
The point is to confirm that:

- intervention abstraction works
- intervention -> event conversion works
- runner stays unchanged
- restoration logic works

---

## Validation requirements

Implement clear validation errors for:

- empty `params`
- negative `start`
- `end < start`
- restore requested but missing base parameter

Use straightforward `ValueError` messages.

---

## What not to do in this task

Do not implement yet:

- hard interventions
- network rebuild logic
- network-specific intervention classes
- age-targeted interventions
- regional interventions
- vaccination intervention classes
- testing/tracing special subclasses
- UI adapters
- OpenABM-specific direct wiring beyond what already exists

This task is only the first abstraction layer.

---

## Success criteria

This task is complete when all of the following are true:

1. a `ParameterIntervention` can be created
2. it can generate `TimelineEvent` objects
3. a `Scenario` can include interventions
4. `resolve_scenario(...)` includes intervention-generated events
5. the runner can execute them without architectural changes
6. the notebook demonstrates:
   - pre-intervention phase
   - intervention-active phase
   - post-intervention restored phase

---

## Coding style

Requirements:

- keep the implementation simple
- use `dataclass`
- use type hints
- add short docstrings
- avoid overengineering
- prefer explicit code over clever abstractions
- preserve the existing architecture instead of redesigning it

---

## Final note

This is not yet the full intervention system.

This step only establishes the key architectural rule:

**interventions are high-level objects that compile into timeline events**.

If this works, later intervention types can be added without changing the runner design.
