# Codex Recipe: Single-SHP Execution Mode Before Full National Run

## Goal

Implement a **small intermediate execution mode** before the full end-to-end Finland run.

The purpose is to support:

- one hospital district (SHP) at a time
- independent runs with no coupling between districts
- comparison of simulated cases against THL cases for that one SHP

This is **not** yet a full regional Finland model.
It is only a practical intermediate step that lets us test:

- the timeline -> intervention pipeline
- the OpenABM run
- the comparison against observed data
- region-specific scaling logic

without yet introducing multi-region coupling or postcode-level population structure.

---

## Scope

Implement:

- a simple SHP execution mode
- region-specific observed-data loading for one SHP
- region-specific scaling settings
- notebook test for one SHP run

Do NOT implement:

- multi-region coupled model
- SHP-to-SHP mobility
- postcode-to-SHP aggregation
- full population model
- calibration
- GUI

Keep this step small and explicit.

---

## Design principle

Treat each SHP as an **independent simulation world** for now.

Conceptually:

choose SHP
-> load THL observed cases for that SHP
-> load national Finland timeline events
-> map timeline to interventions
-> run one simulation
-> scale simulated output to SHP population
-> compare simulated vs observed cases

This is a bridge step.
Do not overgeneralize it.

---

## Files

Add if needed:

- `extensions/scenario_api/region_config.py`

Update if needed:

- `data.py`
- `runner.py`
- `openabm_adapter.py`
- `__init__.py`

Notebook:

- `extensions/notebooks/single_shp_run_test.ipynb`

If a better existing notebook already exists and is still readable, you may extend it instead.
But prefer a focused notebook.

---

## 1. Region config object

Create a simple config object for single-SHP runs.

Suggested dataclass:

```python
@dataclass
class RegionConfig:
    name: str
    region_level: str
    real_population: int
    simulated_population: int
    metadata: dict[str, object] = field(default_factory=dict)
```

### Required meaning

- `name`
  - e.g. `"Helsinki and Uusimaa"`

- `region_level`
  - use `"hospital_district"`

- `real_population`
  - actual real-world population used for scaling

- `simulated_population`
  - simulation population size for this run

### Required helper

```python
population_scale_factor(region_config) -> float
```

Behavior:
- returns `real_population / simulated_population`

Use explicit float math.

---

## 2. Region lookup / defaults

Implement a simple built-in region population lookup for a small first set of SHPs.

At minimum include:
- Helsinki and Uusimaa
- Pirkanmaa
- Northern Ostrobothnia or another clear third example if convenient

It is acceptable to start with just one SHP if you want to keep the first version minimal.
But structure the code so more can be added easily.

Suggested function:

```python
get_default_shp_region_config(name, simulated_population) -> RegionConfig
```

Behavior:
- returns a `RegionConfig`
- raises a clear error for unknown SHP name

Do not fetch population from the web here.
Hardcode a small first dictionary with comments if needed.

---

## 3. Observed data loading for one SHP

Reuse the THL processed data pipeline.

Implement or refine a helper like:

```python
load_observed_cases_timeseries_for_region(
    processed_path,
    region,
    region_level="hospital_district",
) -> TimeSeries
```

Behavior:
- loads the processed THL dataset
- filters to the requested SHP
- returns one cases time series

Raise clear errors if region not found.

---

## 4. Timeline handling

For this step, use the existing **Finland national timeline** as-is.

Do not attempt SHP-specific policy timelines.

Required helper if useful:

```python
load_finland_timeline_interventions(...)
```

Meaning:
- load normalized Finland timeline events
- map them to interventions using the existing default mapping profiles

Keep this logic explicit.
Do not hide too much behind one giant function if it becomes hard to debug.

---

## 5. Simulation execution helper

Implement a thin helper that runs one SHP configuration.

Suggested function:

```python
run_single_shp_cases_scenario(
    region_config,
    timeline_events,
    mapping_profiles,
    simulation_steps,
    ...
) -> tuple[SimulationResult, TimeSeries]
```

Behavior:
- receives one SHP config
- uses national timeline events
- maps them to interventions
- runs the simulation using `simulated_population`
- extracts simulated cases
- scales simulated cases to real population using the scale factor
- returns:
  - raw `SimulationResult`
  - scaled simulated `TimeSeries`

Important:
- keep scaling explicit
- do not hide it deep inside unrelated code
- label scaled outputs clearly in metadata

---

## 6. Scaling rule

Use a simple first scaling rule:

scaled_cases = simulated_cases * (real_population / simulated_population)

This is intentionally simple.

Do not try to correct for:
- age structure
- region contact structure
- testing bias
- healthcare differences

Those come later.

The purpose here is only to get a first region-level comparison.

---

## 7. Notebook

Create:

- `extensions/notebooks/single_shp_run_test.ipynb`

### Required notebook flow

#### A. Imports
Import:
- region config helpers
- THL observed data loader
- timeline loader / mapper
- simulation runner
- plotting helpers if available

#### B. Choose one SHP
Use a clearly named example, preferably:
- `"Helsinki and Uusimaa"`

Also define:
- `simulated_population`, for example `200000`

#### C. Build `RegionConfig`
Print:
- real population
- simulated population
- scale factor

#### D. Load observed THL cases
Load the SHP cases series from the processed THL data.

Print:
- date range
- first values
- region metadata

#### E. Load timeline + map to interventions
Use the Finland OxCGRT timeline and the existing default mapping profiles.

Print:
- number of timeline events used
- number of interventions created
- a few example interventions

#### F. Run the simulation
Run one SHP scenario for the matching time span.

Use the selected simulated population size.

#### G. Scale simulated cases
Convert simulated output to a scaled cases time series using the region config.

Print:
- raw and scaled example values
- scale factor used

#### H. Plot comparison
Plot:
- observed THL cases for the SHP
- scaled simulated cases for the same SHP

This is the main notebook output.

#### I. Short interpretation cell
At the end of the notebook, print a short summary:
- whether the timing looks roughly plausible
- whether the magnitude is wildly off
- whether the pipeline worked end-to-end

No calibration yet.
No optimization yet.

---

## 8. Validation requirements

Implement clear errors for:

- unknown SHP name
- missing observed cases for the requested SHP
- zero or invalid simulated population
- zero or invalid real population

Raise `ValueError` with explicit messages.

---

## 9. Success criteria

This task is complete when all of the following are true:

1. one SHP can be configured independently
2. one SHP's THL observed cases can be loaded
3. the national timeline can be mapped to interventions
4. one simulation can be run for that SHP
5. the simulated cases can be scaled to the SHP population
6. the notebook demonstrates:
   - SHP config
   - observed data load
   - timeline-to-intervention mapping
   - simulation run
   - scaled comparison plot

---

## 10. Design rules

Do NOT:

- pretend this is already a real regional transmission model
- add inter-SHP coupling
- add postcode aggregation here
- hide scaling assumptions
- overgeneralize to full Finland multi-region architecture yet

Keep it honest:
- one SHP
- one independent world
- one comparison

---

## Final note

This is a practical checkpoint step.

It should answer one concrete question:

**Can the current timeline -> intervention -> simulation -> observed-data pipeline produce a sensible first region-level comparison for one SHP?**

That is the only purpose of this step.
