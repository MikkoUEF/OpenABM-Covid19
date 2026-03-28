# Codex Recipe: Calibration Phases 1-2 (Baseline R0 and Reff via Mobility) with Explicit Notebook Controls

## Goal

Implement the **first two calibration phases** only:

1. **Phase 1: baseline R0 calibration**
2. **Phase 2: time-varying Reff calibration using mobility-driven network multipliers**

Do **not** implement full case-level calibration yet.
Do **not** implement automatic optimization yet.
Do **not** implement the virus library yet.

This step is meant to establish a practical manual calibration workflow.

---

## Main calibration principle

Calibrate in this order:

Phase 1: baseline R0  
Phase 2: Reff(t)

Do **not** start from absolute case counts.

The purpose is to get:
- the baseline epidemic growth right first
- then the intervention response over time right

Only after that should level / detection fitting be refined.

---

## Scope

Implement:

- baseline no-intervention calibration path
- mobility-driven multiplier calibration path
- reusable helpers for R proxy comparison
- notebook sections for Phase 1 and Phase 2
- explicit notebook controls for:
  - `initial_infected`
  - `simulated_population`

Do NOT implement:

- automatic parameter search
- detection-rate calibration as the main target
- virus library / variant library
- full calibration optimizer
- GUI
- postcode-level population modeling

Keep this step explicit and manual.

---

## Files

Update as needed:

- `extensions/scenario_api/execution_pipeline.py`
- `extensions/scenario_api/openabm_adapter.py`
- `extensions/scenario_api/data.py`
- `extensions/scenario_api/__init__.py`

If not already present, add a small mobility helper module if useful:

- `extensions/scenario_api/mobility.py`

Update notebook:

- `extensions/notebooks/end_to_end_multi_shp_test.ipynb`

Do not create a separate notebook unless the current one becomes unreadable.
Prefer adding clearly labeled calibration sections to the end of the latest notebook.

---

## Phase 1: Baseline R0 calibration

### Goal

Calibrate the baseline transmission level so that the model gives approximately:

`R0_target = 2.3`

for the early Finland / HUS context before major interventions.

### Important modeling interpretation

For this phase, the main calibration knob is:

- `infectious_rate`

Do **not** start by tuning many other parameters.

Keep:
- asymptomatic fractions fixed at current OpenABM defaults
- intervention mapping out of the way for this phase if possible

### Required implementation

Add or expose a clear execution path for a **no-intervention baseline run**.

Suggested helper:

```python
run_baseline_r0_calibration_scenario(
    region_config,
    simulation_steps,
    initial_infected,
    infectious_rate,
    model_factory=None,
) -> dict
```

Behavior:
- no timeline-driven interventions
- no mobility multipliers
- explicit `initial_infected`
- explicit `infectious_rate`
- returns:
  - simulated daily incidence
  - R-agent proxy
  - metadata

### Required notebook behavior for Phase 1

Near the top of the calibration section, define explicitly:

```python
R0_target = 2.3
initial_infected = 100
simulated_population = 200000
```

These parameters must be printed clearly.

Also define an explicit test grid for `infectious_rate`, for example:

```python
infectious_rate_grid = [4.0, 5.0, 5.8, 6.5, 7.0]
```

Adjust if needed, but keep it explicit.

For each tested `infectious_rate`:
- run the baseline scenario
- compute `R_agent`
- compute a smoothed `R_agent` (7-day MA)
- summarize the early-period R level

### Required Phase 1 output

At minimum produce:

1. one plot with smoothed `R_agent` for each tested `infectious_rate`
2. a compact summary table with:
   - infectious_rate
   - initial_infected
   - simulated_population
   - estimated early R level
   - short note on whether it is below / near / above the `R0_target`

### Required Phase 1 interpretation

At the end of Phase 1 in the notebook, print a short summary identifying:
- which `infectious_rate` seems closest to `R0_target = 2.3`

This can be manual / visual.
No optimizer required.

---

## Phase 2: Reff(t) calibration using mobility

### Goal

After selecting a baseline `infectious_rate`, calibrate the time-varying intervention response so that:

`R_agent(t) ≈ R_obs(t)`

at least directionally over the first-wave window.

### Main idea

Use Google mobility data as a driver for network multipliers.

This should be an **approximate calibration helper**, not a claim of exact causal truth.

### Required mapping concept

At minimum support:

- workplace mobility -> work network multiplier
- retail/recreation or similar mobility -> random network multiplier

If residential mobility is included, treat it cautiously.
It is acceptable to leave household unchanged in this first version.

### Required implementation

Add explicit mobility-to-multiplier helpers, for example:

```python
mobility_to_work_multiplier(mobility_value, scale=1.0, floor=0.1, ceiling=1.0) -> float
mobility_to_random_multiplier(mobility_value, scale=1.0, floor=0.1, ceiling=1.0) -> float
```

Behavior:
- convert mobility changes into multipliers
- keep this explicit and simple
- document the formula clearly in code comments

It is acceptable to start with a simple linear rule, for example conceptually:

`multiplier = 1 + scale * mobility_change_fraction`

with clipping to a sensible interval.

Do not hide the formula.

### Required calibration parameters for Phase 2

Expose a small set of manual calibration knobs such as:

- `work_mobility_scale`
- `random_mobility_scale`

Optional:
- `work_multiplier_floor`
- `random_multiplier_floor`

Do not introduce many knobs at once.

### Required helper

Implement something like:

```python
build_mobility_driven_network_multipliers(
    mobility_table,
    work_mobility_scale,
    random_mobility_scale,
    ...
) -> object
```

This helper should produce time-varying multipliers aligned to the simulation day index.

### Required execution path

Implement or refine a helper like:

```python
run_reff_calibration_scenario(
    region_config,
    observed_cases_path,
    timeline_processed_path,
    mobility_processed_path,
    reference_start_date,
    end_date,
    initial_infected,
    simulated_population,
    infectious_rate,
    work_mobility_scale,
    random_mobility_scale,
    ...
) -> dict
```

Behavior:
- load observed THL daily cases
- compute `R_obs`
- load timeline events and map them to interventions
- load mobility data and build mobility-based network multipliers
- run the simulation
- compute `R_agent`
- return all relevant series and metadata

### Important rule

Do not let mobility silently override all intervention logic.

For this phase, the intended interpretation is:
- baseline interventions still exist
- mobility helps calibrate the magnitude of network reduction

Be explicit in code comments about how these effects are combined.

---

## Notebook behavior for Phase 2

Keep the same explicit date window already in use:

```python
reference_start_date = "2020-03-01"
end_date = "2020-06-30"
```

For the first version, focus mainly on:

- `Helsinki and Uusimaa`

### Required notebook parameters near the top of Phase 2

Print explicitly:

```python
initial_infected = ...
simulated_population = ...
infectious_rate = ...
work_mobility_scale = ...
random_mobility_scale = ...
generation_interval = 5
smoothing_window = 7
```

This is required.

### Required Phase 2 notebook steps

#### A. Load / prepare observed R
- compute `R_obs` from THL daily cases
- smooth with 7-day moving average

#### B. Run mobility-driven scenario
- use the selected baseline `infectious_rate`
- use mobility-driven multipliers

#### C. Compute simulated R
- compute `R_agent`
- smooth with 7-day moving average

#### D. Plot `R_obs` vs `R_agent`
Create a comparison plot with:
- smoothed `R_obs`
- smoothed `R_agent`
- horizontal line at `R = 1`

This plot is required.

#### E. Manual sensitivity grid
Run a small manual grid such as:

```python
work_mobility_scale_grid = [0.5, 1.0, 1.5]
random_mobility_scale_grid = [0.5, 1.0, 1.5]
```

You do not need full Cartesian explosion if too slow.
A modest set of combinations is enough.

For each tested combination:
- compute / plot / summarize fit quality qualitatively

#### F. Summary table
Create a compact summary table with at least:
- infectious_rate
- work_mobility_scale
- random_mobility_scale
- whether `R_agent` drops below 1
- whether timing of the drop roughly matches `R_obs`

Qualitative labels are acceptable.

#### G. Short interpretation cell
At the end of Phase 2, print a short note:
- which combination gave the best directional agreement with `R_obs`
- whether remaining mismatch seems due to baseline transmission, mobility scaling, or still-incomplete intervention wiring

No optimizer yet.

---

## Required helper functions for R diagnostics

Reuse or refine existing helpers:

```python
compute_r_proxy_from_incidence(timeseries, generation_interval=5, new_name=None) -> TimeSeries
smooth_timeseries_moving_average(timeseries, window=7, new_name=None) -> TimeSeries
```

Use the same method for:
- `R_obs`
- `R_agent`

Do not compare differently computed R curves.

---

## Required notebook controls

This is an explicit requirement.

At the top of the calibration section, the notebook must expose and print:

```python
initial_infected = ...
simulated_population = ...
```

These must not remain hidden inside lower-level defaults.

---

## Validation requirements

Implement clear validation for:

- invalid `initial_infected`
- invalid `simulated_population`
- invalid `infectious_rate`
- missing observed daily cases
- missing mobility data
- invalid mobility scale parameters
- failure to compute `R_obs` or `R_agent`

Raise explicit `ValueError` or `RuntimeError`.
Do not fail silently.

---

## Success criteria

This task is complete when all of the following are true:

1. Phase 1 baseline R0 calibration can be run manually
2. `infectious_rate` can be scanned explicitly
3. notebook exposes and prints:
   - `initial_infected`
   - `simulated_population`
4. Phase 2 mobility-driven Reff calibration can be run manually
5. notebook compares:
   - `R_obs`
   - `R_agent`
6. notebook produces:
   - a Phase 1 R0 plot/grid summary
   - a Phase 2 `R_obs` vs `R_agent` plot
   - a compact summary table for tested settings

---

## Design rules

Do NOT:

- jump to full case-count fitting
- add many calibration knobs at once
- implement automatic optimization yet
- bury notebook controls in hidden cells
- create a virus library yet

Keep it:
- staged
- manual
- explicit
- interpretable

---

## Final note

This step is only about the first two calibration phases:

1. set the baseline epidemic growth correctly (`R0`)
2. set the intervention response over time correctly (`Reff`)

Only after these are in reasonable shape should deeper fitting or virus-profile packaging be introduced.
