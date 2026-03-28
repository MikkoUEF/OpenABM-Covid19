# Codex Recipe: Timeline-to-Intervention Default Mapping Profiles

## Goal

Implement the **first default mapping layer** from normalized historical timeline events to model-facing interventions.

This layer should sit between:

- normalized `TimelineEvent` objects
- the intervention layer

The purpose is to support:

1. historical calibration workflows
   - use OxCGRT timeline events as the policy backbone

2. future GUI editing
   - provide editable default assumptions
   - allow users to modify the assumptions later in the intervention editor

This task should create **default mapping profiles**, not an LLM assistant and not a final policy interpretation system.

---

## Main architectural rule

Keep these layers separate:

timeline source data
-> normalized TimelineEvent
-> default mapping profile
-> Intervention objects
-> OpenABM-facing compiled multipliers / settings

Do **not** collapse timeline ingestion and intervention semantics into one module.

---

## Scope

Implement:

- default mapping profile objects
- explicit mapping functions from `TimelineEvent` to intervention objects
- support for at least mask and contact-related policy classes
- notebook tests showing the mapping pipeline

Do NOT implement:

- LLM assistance
- GUI
- calibration logic
- automatic realism scoring
- multi-country tuning
- full vaccination mapping yet
- THL/STM ingestion in this step

Keep this version explicit, deterministic, and editable.

---

## Files

Add these modules under:

extensions/scenario_api/

Create:

- extensions/scenario_api/timeline_mapper.py
- extensions/scenario_api/mapping_profiles.py

Update if needed:

- extensions/scenario_api/__init__.py

Notebook:

- extensions/notebooks/timeline_to_intervention_mapping_test.ipynb

---

## Input assumptions

Assume these already exist and should be reused:

- `TimelineEvent`
- `MaskProfile`
- `MaskAdoptionIntervention`
- `ContactReductionIntervention`
- possibly `InterventionSet`

If the current code uses slightly different names, adapt carefully, but preserve the architecture.

---

## Initial supported timeline event types

Implement first-version default mappings for exactly these normalized event types:

1. `facial_coverings`
2. `school_closing`
3. `workplace_closing`
4. `gathering_restrictions`
5. `stay_at_home`
6. `public_events`
7. `internal_movement`
8. `testing_policy`
9. `contact_tracing`

You do not need to make all of them equally detailed.
But they must at least map to something explicit.

---

## Design principle for mapping

A timeline event does **not** directly equal a model parameter.

Example:

`facial_coverings = 2`

does NOT mean:
- 80% mask use
- or any single multiplier directly

Instead, it should map through a default profile assumption such as:

level 2 facial coverings
-> stronger mask adoption in work + random networks
-> specific usage mix by network
-> mask profile defines effectiveness

This is the whole point of the mapping layer.

---

## 1. Mapping profile objects

In `mapping_profiles.py`, implement explicit dataclasses for default mappings.

### A. `MaskMappingProfile`

Suggested structure:

```python
@dataclass
class MaskMappingProfile:
    name: str
    level_to_network_mix: dict[int, dict[str, dict[str, float]]]
    mask_profile_name: str
    metadata: dict[str, object] = field(default_factory=dict)
```

Meaning:
- key = timeline level, e.g. 0 / 1 / 2
- value = per-network usage mix
- these are the default assumptions the GUI can later expose and edit

### Required first profile

Provide one built-in default mask profile mapping, e.g.:

- level 0 -> no mask intervention
- level 1 -> moderate adoption
- level 2 -> stronger adoption

Use explicit network mixes.

At minimum support:
- `work`
- `random`

Optional:
- `school`

Do not overexpand.

---

### B. `ContactPolicyMappingProfile`

Suggested structure:

```python
@dataclass
class ContactPolicyMappingProfile:
    name: str
    event_type_to_level_multipliers: dict[str, dict[int, dict[str, float]]]
    metadata: dict[str, object] = field(default_factory=dict)
```

Meaning:
- event type -> level -> network multipliers

This is for policy classes such as:
- school closing
- workplace closing
- gathering restrictions
- stay at home
- public events
- internal movement

### Required first built-in assumptions

Define explicit defaults such as:

- `school_closing`
  - level 0 -> no effect
  - level 1 -> mild school reduction
  - level 2 -> strong school reduction
  - level 3 -> near closure

- `workplace_closing`
  - level 0 -> no effect
  - level 1 -> mild work reduction
  - level 2 -> stronger work reduction
  - level 3 -> strong work reduction

- `gathering_restrictions`, `public_events`, `stay_at_home`, `internal_movement`
  - map mainly to reductions in `random`
  - optionally also modest effects on `work`

These should be simple, hand-coded defaults.

Do not try to infer them from the web in this step.

---

### C. `TestingTracingMappingProfile`

Keep this minimal.

Suggested structure:

```python
@dataclass
class TestingTracingMappingProfile:
    name: str
    testing_policy_levels: dict[int, dict[str, object]]
    tracing_policy_levels: dict[int, dict[str, object]]
    metadata: dict[str, object] = field(default_factory=dict)
```

Meaning:
- level codes map to simple model-facing assumptions

Because testing/tracing OpenABM wiring may still be evolving, keep the first version modest and explicit.

For example:
- testing policy -> testing intensity level
- tracing policy -> tracing intensity level

This may initially produce placeholder/simple intervention objects or plain config objects if needed.
Be honest about limitations.

---

## 2. Mapping functions

In `timeline_mapper.py`, implement the actual mapping logic.

### Required public functions

```python
map_timeline_event_to_interventions(
    event,
    mask_mapping_profile,
    contact_mapping_profile,
    testing_tracing_mapping_profile=None,
    mask_profiles=None,
) -> list
```

Behavior:
- takes one normalized `TimelineEvent`
- returns one or more intervention objects
- returns an empty list if level 0 means “no intervention”
- raises a clear error for unsupported event types if that is the chosen behavior
- or returns empty list only if explicitly documented

Use explicit logic by `event.event_type`.

### Additional convenience function

```python
map_timeline_events_to_interventions(
    events,
    mask_mapping_profile,
    contact_mapping_profile,
    testing_tracing_mapping_profile=None,
    mask_profiles=None,
) -> list
```

Behavior:
- maps a list of events
- flattens the result

---

## 3. Time interval handling

This is important.

Timeline events are usually observed as changes in policy state over time.
The mapper must therefore support interval logic, not just point events.

Recommended first approach:

- sort timeline events by `event_type` and `date`
- for each event:
  - start = current event date
  - end = next event date for the same event_type
- produce an intervention active on `[start, end)`

Because the current intervention layer likely uses integer time steps instead of dates, you need a simple first bridge.

### Required for this step

Implement a helper such as:

```python
assign_relative_day_indices(events, reference_start_date) -> list
```

Behavior:
- converts ISO dates to integer offsets from a reference start date
- stores or returns corresponding integer day values

This keeps the mapping explicit and testable.

Do not overengineer calendar handling.

---

## 4. Required explicit default assumptions

Use explicit, hard-coded defaults in code comments and data structures.

### A. Facial coverings

Implement at least:

- level 0 -> no mask intervention
- level 1 -> moderate mask adoption
- level 2 -> stronger mask adoption

Suggested exact default mixes for the first version:

### Level 1
```python
{
    "work":   {"none": 0.50, "surgical": 0.40, "ffp2": 0.10},
    "random": {"none": 0.60, "surgical": 0.30, "ffp2": 0.10},
}
```

### Level 2
```python
{
    "work":   {"none": 0.20, "surgical": 0.50, "ffp2": 0.30},
    "random": {"none": 0.30, "surgical": 0.50, "ffp2": 0.20},
}
```

Do not include FFP3 unless the current mask intervention code already supports it cleanly.
Keep the first default profile simple.

### B. School closing

Suggested first defaults:

- level 0 -> no effect
- level 1 -> `{"school": 0.7}`
- level 2 -> `{"school": 0.4}`
- level 3 -> `{"school": 0.1}`

### C. Workplace closing

Suggested first defaults:

- level 0 -> no effect
- level 1 -> `{"work": 0.8}`
- level 2 -> `{"work": 0.5}`
- level 3 -> `{"work": 0.2}`

### D. Gathering restrictions / public events / stay at home / internal movement

Map mainly to `random`.

Suggested first defaults:

- mild -> `{"random": 0.8}`
- moderate -> `{"random": 0.5}`
- strong -> `{"random": 0.2}`

If needed, assign exact levels per event type explicitly.
Do not leave them vague.

### E. Testing / tracing

If the current intervention layer does not yet have strong dedicated intervention classes for these, it is acceptable in this first step to map them to simple placeholder intervention/config objects, for example:

- `TestingIntensityIntervention`
- `TracingIntensityIntervention`

or similar small classes.

If you create them, keep them minimal and explicit.
Do not let this task explode in scope.

---

## 5. Validation requirements

Implement clear validation for:

- unknown event type
- unknown level in the selected profile
- missing mask profile referenced by the mask mapping profile
- invalid network mixes
- missing relative day conversion when required

Raise `ValueError` with explicit messages.

---

## 6. Notebook

Create:

- extensions/notebooks/timeline_to_intervention_mapping_test.ipynb

### Required notebook flow

#### A. Imports
Import:
- timeline loading helpers
- mapping profile objects
- mapping functions
- intervention objects

#### B. Load processed timeline file
Use the processed Finland 2020-2022 OxCGRT timeline file created earlier.

#### C. Filter a few event types
At minimum:
- `facial_coverings`
- `school_closing`
- `workplace_closing`

Print a few rows.

#### D. Convert dates to relative days
Choose a reference start date, for example:
- `2020-01-01`

Show the relative day mapping clearly.

#### E. Create default mapping profiles
Instantiate:
- default mask mapping profile
- default contact policy mapping profile
- testing/tracing profile if implemented

#### F. Map events to interventions
Run the mapping and print example resulting interventions.

Print enough detail to confirm:
- start
- end
- intervention type
- network-specific parameters

#### G. Inspect one full event type
For example:
- map all `facial_coverings` events
- print resulting mask interventions over time

#### H. Inspect one contact policy type
For example:
- map all `school_closing` events
- print resulting contact reduction interventions

#### I. Simple summary
At the end, print a summary such as:
- counts of intervention objects by type
- unique active intervals
- example compiled multipliers for a selected day

Do NOT yet run the full epidemic model in this notebook.
This notebook is about the mapping layer only.

---

## 7. Success criteria

This task is complete when all of the following are true:

1. there is a dedicated timeline mapping layer
2. default mapping profiles exist as editable objects
3. `facial_coverings` maps to mask adoption interventions
4. school/work/gathering-style policies map to contact reduction interventions
5. date-to-relative-day conversion works
6. the notebook demonstrates:
   - loading normalized timeline data
   - creating default mapping profiles
   - mapping events to intervention objects
   - printing and inspecting the resulting interventions

---

## 8. Design rules

Do NOT:

- fetch THL/STM here
- connect this directly to the GUI yet
- add LLM assistance yet
- bury assumptions inside notebook cells
- hardcode OpenABM internals into the timeline mapper

Keep assumptions:
- explicit
- centralized
- editable later by the GUI

---

## Final note

This layer should produce editable default assumptions.

That is the key requirement:
- historical timeline data gives the backbone
- default mapping profiles give the first interpretation
- later the GUI can let users edit those assumptions directly

This is exactly the right bridge between:
- historical policy timeline
- flexible future scenario editing
