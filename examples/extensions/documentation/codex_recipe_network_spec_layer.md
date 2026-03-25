# Codex Recipe: Network Specification Layer for the Scenario API

## Goal

Implement the **first network specification layer** on top of the current scenario API.

At this stage, the purpose is **not** to build actual dynamic networks and **not** to modify the OpenABM core.
The purpose is to make networks a **first-class declarative concept** in scenarios, in the same way that:

- parameter blocks describe parameter sets
- interventions describe policy changes over time
- network specs should describe which network structures a scenario uses

This step should define a clean API for network descriptions that can later be translated into:

- default OpenABM network initialization
- custom user-defined networks
- future network rebuild logic
- future UI-level scenario editing

For now, keep the implementation simple, explicit, and easy to debug.

---

## Scope of this task

Implement only the **declarative network specification layer**.

This task should include:

- a stronger `NetworkSpec` model
- validation rules for supported network kinds
- scenario integration for network specifications
- a resolver output that preserves validated network specs
- notebook tests showing that network specs can be created, attached to scenarios, resolved, and inspected

This task should **not** include:

- actual network generation
- OpenABM core modifications
- dynamic rewiring
- hard-event rebuild logic
- regional network logic
- postcode-level household sampling
- custom graph algorithms

---

## Design principle

Use this separation:

```text
NetworkSpec -> validated declarative network description
NetworkBuilder (later) -> actual network construction
Runner (current) -> does not yet build real networks from specs
```

The current task is only about the **specification layer**, not the builder layer.

A `NetworkSpec` should be:

- explicit
- typed by network kind
- validated
- scenario-friendly
- future-proof enough for later extensions

---

## Supported network kinds in this task

Implement support for exactly these kinds for now:

1. `household`
2. `activity_structured`
3. `activity_random`

These are intentionally generic.

### Meaning of the kinds

#### `household`
Represents household-based persistent contact structure.

#### `activity_structured`
Represents a persistent-but-partially-activated contact structure, analogous to the OpenABM occupation network idea:
- work
- school
- daycare
- elderly daytime social network
- potentially later also recurring retail/social activity structures

#### `activity_random`
Represents transient / resampled contact opportunities, analogous to random/community contacts.

Do not add more kinds yet.

---

## File changes

Update and extend under:

```text
extensions/scenario_api/
```

Relevant files:
- `networks.py`
- `scenarios.py`
- `resolver.py`
- `__init__.py`

Also update the notebook:

```text
extensions/notebooks/scenario_api_smoke_test.ipynb
```

to include network spec tests.

---

## Object design

### `NetworkSpec`

If a `NetworkSpec` already exists, refine it instead of replacing it unnecessarily.

Use `@dataclass`.

Required fields:

- `name: str`
- `kind: str`
- `config: dict[str, object]`
- `metadata: dict[str, object] = field(default_factory=dict)`

Behavior:
- validate `name` is non-empty
- validate `kind` is one of:
  - `household`
  - `activity_structured`
  - `activity_random`
- validate `config` is a dict
- expose a validation function or method

Recommended:
- keep validation external as a function if that fits the current code better
- but explicit validation must exist

---

## Validation rules by kind

Implement lightweight but meaningful validation.

### 1. `household`

Required config keys:
- `population_size`

Optional keys:
- `household_size_distribution`
- `age_profile_source`
- `reference_panel`
- `notes`

Validation:
- `population_size` must exist
- `population_size` must be a positive integer

Do not validate the detailed structure of optional fields yet.

---

### 2. `activity_structured`

Required config keys:
- `mean_contacts`
- `activation_prob`

Optional keys:
- `group`
- `age_range`
- `rewiring_hint`
- `label`
- `notes`

Validation:
- `mean_contacts` must exist and be non-negative number
- `activation_prob` must exist and satisfy `0 <= activation_prob <= 1`

Do not implement rewiring logic.
Just validate the field if present only loosely.

---

### 3. `activity_random`

Required config keys:
- `mean_contacts`

Optional keys:
- `dispersion`
- `group`
- `label`
- `notes`

Validation:
- `mean_contacts` must exist and be non-negative number
- if `dispersion` is present, it must be positive number

---

## Functions to implement

### In `networks.py`

Implement or refine:

```python
create_network_spec(name, kind, config, metadata=None) -> NetworkSpec
```

Behavior:
- validates basic structure
- validates config according to kind
- returns `NetworkSpec`

Implement:

```python
validate_network_spec(spec) -> None
```

Behavior:
- raises `ValueError` on invalid specs
- returns nothing on success

Implement:

```python
validate_network_specs(specs) -> None
```

Behavior:
- validates a list of specs
- raises on first invalid spec

Optional but recommended:

```python
network_spec_to_dict(spec) -> dict
```

This can help notebook inspection and future serialization.

---

## Scenario integration

Ensure that `Scenario` cleanly supports network specs as a first-class list.

If not already present, keep:

- `network_specs: list[NetworkSpec] = field(default_factory=list)`

Ensure this helper exists and works:

```python
add_network_spec(scenario, network_spec) -> Scenario
```

Behavior:
- validates the spec before attaching
- returns updated scenario

If the current architecture mutates the scenario in place, keep that consistent.
If it uses copy/return semantics, keep that consistent.
Do not redesign the whole style.

---

## Resolver integration

Update `resolve_scenario(...)` so that:

- network specs are validated during resolve
- validated specs are preserved in the `ResolvedScenario`
- they remain available for future builder logic

Important:
- do not attempt actual network construction here
- do not collapse them into flat params
- keep them as typed specs

If helpful, add a field in `ResolvedScenario.metadata` summarizing network names and kinds, but this is optional.

---

## Optional categorization helper

Recommended but optional:

Implement in `networks.py`:

```python
group_network_specs_by_kind(specs) -> dict[str, list[NetworkSpec]]
```

This is only for inspection / debugging convenience.
Do not overengineer it.

---

## Notebook updates

Update:

```text
extensions/notebooks/scenario_api_smoke_test.ipynb
```

Add a new section that tests the network spec layer.

### Required notebook additions

#### A. Create example specs

Create at least three specs:

1. household example:
- name: `"households"`
- kind: `"household"`
- config:
  - `population_size = 1000`

2. activity structured example:
- name: `"work"`
- kind: `"activity_structured"`
- config:
  - `mean_contacts = 10`
  - `activation_prob = 0.5`
  - maybe `group = "working_age"`

3. activity random example:
- name: `"community"`
- kind: `"activity_random"`
- config:
  - `mean_contacts = 4`
  - optionally `dispersion = 2`

Print the objects.

#### B. Validate them

Run the explicit validation functions and show success.

#### C. Add them to a scenario

Create or reuse a scenario and attach the network specs.
Print scenario contents.

#### D. Resolve the scenario

Run `resolve_scenario(...)` and show that:
- network specs are preserved
- the resolved scenario contains validated network specs

#### E. Optional invalid-case smoke test

Include one deliberately invalid example in a small try/except block, for example:
- `activity_structured` with `activation_prob = 1.5`

Print the error message clearly.

Do not let the notebook fail permanently because of this test.

#### F. Existing runner compatibility

You do not need to make the runner use real network specs yet.
But verify that the presence of network specs does not break the existing scenario resolve/run flow.

A simple smoke test is enough.

---

## Success criteria

This task is complete when all of the following are true:

1. `NetworkSpec` supports the three defined kinds
2. kind-specific validation exists
3. invalid specs fail with clear errors
4. scenarios can include validated network specs
5. `resolve_scenario(...)` preserves validated specs
6. the notebook demonstrates:
   - creation
   - validation
   - scenario attachment
   - resolution
   - invalid-case handling
   - no regression in the existing flow

---

## Coding style

Requirements:

- use `dataclass`
- use type hints
- keep functions small
- add short docstrings
- keep validation explicit
- avoid overengineering
- do not introduce unnecessary dependencies
- preserve the current architecture rather than redesigning it

---

## What not to do in this task

Do not implement:
- actual network generation
- graph libraries
- dynamic topology changes
- network interventions
- hard-event rebuilds
- postcode-level data integration
- OpenABM-specific low-level network adapters

Those come later.

---

## Final note

The purpose of this step is to make network structure a clean declarative part of the scenario model.

After this step, the scenario API should have three stable layers:

- parameter blocks
- interventions
- network specifications

That gives a strong base for the later network builder and data integration work.
