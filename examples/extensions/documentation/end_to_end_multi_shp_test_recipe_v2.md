# Codex Recipe: End-to-End Execution Pipeline with Multi-SHP Notebook Test

## Goal

Implement the **first end-to-end execution pipeline** that connects:

- processed Finland timeline events
- timeline-to-intervention mapping
- OpenABM execution
- SHP-specific observed THL cases
- region-specific scaling
- comparison plots

This is **not** yet calibration and **not** yet the GUI.
This step creates the **actual execution layer** that the future GUI will call.

At the same time, create a notebook that clearly tests the pipeline for **multiple SHPs**.

---

## Important time-window constraint for this step

For this notebook and this execution test, use the explicit historical window:

- **start date: 2020-03-01**
- **end date: 2020-06-30**

Reason:
- this is a short, interpretable first-wave window
- later Omicron peaks do not flatten the plots
- the user knows this period well and wants this interval first

This date window must be explicit near the top of the notebook and used consistently for:
- timeline filtering
- observed-data filtering
- simulation step count
- plot x-axis range

Do **not** default to 2020-2022 in this notebook.

---

## Main architectural rule

This is **not just a notebook experiment**.

The notebook must call reusable Python modules.
The actual pipeline logic must live in the package code, not inside notebook cells.

Use this structure:

timeline -> interventions -> simulation -> scaling -> comparison

The notebook is only the test harness for this execution layer.

---

## Scope

Implement:

- reusable execution helper(s) for end-to-end runs
- SHP-specific observed-data loading
- SHP-specific scaling
- comparison output as `TimeSeries`
- notebook test for multiple SHPs

Do NOT implement:

- automated calibration
- optimization
- GUI
- inter-SHP coupling
- postcode-level aggregation
- multi-region coupled simulation
- fancy dashboarding

Keep it explicit and testable.

---

## Files

Add or update as needed under:

extensions/scenario_api/

Possible files:
- `execution_pipeline.py`
- `region_config.py`
- `data.py`
- `timeline_mapper.py`
- `openabm_adapter.py`
- `runner.py`
- `__init__.py`

Create notebook:

- `extensions/notebooks/end_to_end_multi_shp_test.ipynb`

If there is already a suitable helper file, adapt instead of duplicating.
But keep the final structure clear.

---

## 1. Execution pipeline module

Create a dedicated module, preferably:

- `extensions/scenario_api/execution_pipeline.py`

This module should contain the reusable glue logic.

### Required public function

Implement something close to:

```python
run_region_scenario_against_observed(
    region_config,
    observed_cases_path,
    timeline_processed_path,
    reference_start_date,
    simulation_steps,
    mask_mapping_profile,
    contact_mapping_profile,
    testing_tracing_mapping_profile=None,
    mask_profiles=None,
    model_factory=None,
    result_variable="cases",
) -> dict
```

### Required behavior

This function should:

1. load the observed THL cases for the selected SHP
2. load processed Finland timeline events
3. assign relative day indices from the given reference start date
4. map timeline events to interventions
5. run the OpenABM scenario for the requested number of steps
6. extract simulated cases
7. scale simulated cases to the SHP real population
8. return a dictionary containing at least:
   - `region_config`
   - `observed_timeseries`
   - `simulated_raw_timeseries`
   - `simulated_scaled_timeseries`
   - `timeline_events`
   - `interventions`
   - optional metadata

Keep all steps explicit and easy to inspect.

---

## 2. Required helper functions

Implement or refine small helpers as needed.

### A. Observed data loader

Use or refine something like:

```python
load_observed_cases_timeseries_for_region(
    processed_path,
    region,
    region_level="hospital_district",
    start_date=None,
    end_date=None,
) -> TimeSeries
```

This should return one clean cases series for the requested SHP, filtered to the notebook date window.

---

### B. Relative day alignment

Use or refine a helper like:

```python
assign_relative_day_indices(events, reference_start_date) -> list
```

This must be used consistently so that:
- day 0 in the simulation
- day 0 in the observed series
- day 0 in the mapped interventions

all match the same reference start date.

Be explicit about the date convention.

---

### C. Region scaling

Use or refine:

```python
population_scale_factor(region_config) -> float
```

and a helper like:

```python
scale_timeseries_values(timeseries, factor, new_name=None, metadata=None) -> TimeSeries
```

Behavior:
- multiply values by factor
- preserve times
- update metadata clearly
- label the result as scaled

Do not bury the scaling inside plotting code.

---

### D. Comparison packaging

Optionally implement:

```python
build_region_comparison_bundle(...) -> dict
```

if that helps readability.
Do not overengineer it.

---

## 3. Region config requirements

Use the existing or newly created `RegionConfig`.

Required fields:
- `name`
- `region_level`
- `real_population`
- `simulated_population`

At minimum include defaults for these SHPs:

1. `Helsinki and Uusimaa`
2. `Pirkanmaa`
3. `Northern Ostrobothnia`

If the THL processed file uses slightly different English names, match those exactly.
Do not silently guess region names.

---

## 4. Simulation assumptions for this step

For this step, treat each SHP as an independent world.

Use:
- Finland national OxCGRT timeline
- one SHP observed cases series
- one SHP region scale factor

Do NOT implement:
- region-specific timelines
- region-specific transmission between districts
- postcode populations
- hospital comparison here

Keep this checkpoint intentionally simple.

---

## 5. Required output objects

For each region run, produce at least:

### A. Observed time series
- SHP cases from THL

### B. Simulated raw time series
- direct model output for the simulated population

### C. Simulated scaled time series
- scaled to the real SHP population

### D. Optional metadata
Include at least:
- SHP name
- real population
- simulated population
- scale factor
- reference start date
- end date
- number of timeline events used
- number of interventions created

This metadata should be printable in the notebook.

---

## 6. Notebook requirements

Create:

- `extensions/notebooks/end_to_end_multi_shp_test.ipynb`

This notebook must be **clear and structured**.
Do not hide important choices in random cells.

### Required notebook sections

### Section A. Imports

Import:
- region config helpers
- observed data loaders
- timeline loaders
- mapping profile constructors
- execution pipeline runner
- plotting libraries

If any import fails, the notebook should fail clearly.

### Section B. Configure paths and dates

Define explicit paths for:
- processed THL cases file
- processed Finland timeline file

Also define explicitly near the top:

```python
reference_start_date = "2020-03-01"
end_date = "2020-06-30"
```

Compute simulation steps from this window and print the result.

This date window must be used consistently everywhere in the notebook.

### Section C. Build mapping profiles

Instantiate:
- default mask mapping profile
- default contact mapping profile
- testing/tracing profile if available
- mask profile(s)

Print a short summary of the created profiles.

### Section D. Choose SHPs

Define an explicit list of SHPs to test:

```python
regions_to_test = [
    ("Helsinki and Uusimaa", 200000),
    ("Pirkanmaa", 120000),
    ("Northern Ostrobothnia", 120000),
]
```

These numbers are examples.
Adjust if needed, but keep them explicit.

For each tuple:
- first value = exact SHP name used in THL data
- second value = simulated population size for that run

### Section E. Build region configs

Create a `RegionConfig` for each SHP.
Print for each:
- SHP name
- real population
- simulated population
- scale factor

This printout is required.

### Section F. Run the end-to-end pipeline for each SHP

Loop over the chosen SHPs and call the reusable execution function.

For each SHP, print:
- date window used
- number of timeline events used
- number of interventions created
- length of observed series
- length of simulated raw series
- length of simulated scaled series

Collect the outputs into a list or dictionary.

### Section G. Plot comparison for each SHP

Create one plot per SHP.
Do NOT combine everything into one unreadable plot.

Each plot must show:
- observed THL cases
- scaled simulated cases

Use the same x-axis convention for both.

Recommended:
- one plot per SHP in separate notebook cells
- or one loop that prints the region name and then draws one figure

Keep it readable.

### Section H. Compact summary table

At the end, build a small summary table showing for each SHP:

- SHP name
- real population
- simulated population
- scale factor
- observed peak
- simulated scaled peak

This can be a pandas DataFrame if convenient.

This summary is required.

### Section I. Short interpretation text cell

Add one final notebook cell that prints a short human-readable summary:
- whether the timing looks roughly plausible
- whether peaks were too high / too low
- whether the end-to-end pipeline worked cleanly
- whether the same timeline clearly behaves differently by SHP only through scaling

No automatic calibration.
No optimization yet.

---

## 7. Validation requirements

Implement clear errors for:

- missing observed THL region
- invalid region config
- zero or negative simulated population
- zero or negative real population
- missing processed timeline file
- no timeline events after filtering / alignment
- no interventions created when they should be present

Raise explicit `ValueError` or `RuntimeError`.
Do not fail silently.

---

## 8. Success criteria

This task is complete when all of the following are true:

1. there is a reusable execution pipeline module
2. one SHP can be run end-to-end for 2020-03-01 to 2020-06-30
3. multiple SHPs can be run one by one using the same code path
4. observed THL cases are loaded correctly for the same date window
5. timeline events are mapped to interventions for the same date window
6. OpenABM runs through the pipeline
7. simulated cases are scaled to SHP population
8. the notebook demonstrates:
   - clear path configuration
   - explicit date window
   - mapping profile creation
   - multi-SHP execution
   - one comparison plot per SHP
   - a compact summary table

---

## 9. Design rules

Do NOT:

- hide the pipeline in the notebook only
- mix GUI code into this step
- introduce inter-SHP coupling
- pretend scaling makes this a true regional model
- bury assumptions inside plotting helpers

Keep it honest:
- same national timeline
- separate independent SHP runs
- explicit scaling
- explicit comparison

---

## 10. Interpretation of bad first fit

If the first HUS/Helsinki-and-Uusimaa run looks very poor, do **not** treat that alone as a reason to redesign the architecture.

For this step, the primary question is:
- does the pipeline run correctly end-to-end?

A poor first fit is expected because:
- default mapping profiles are still hand-crafted assumptions
- no calibration has been performed
- population structure is still simplified
- regional runs are still independent and scaled, not true coupled regional models

So:
- **pipeline correctness matters more than fit quality in this step**
- the notebook should still print a short note when the fit is poor, but should not treat it as a failure of the software architecture

---

## Final note

This step is the first real **execution-layer checkpoint**.

Its purpose is to answer:

**Can the current architecture run the full pipeline from timeline to interventions to simulation to observed-data comparison for several SHPs using one reusable execution path, over the explicit first-wave period 2020-03-01 to 2020-06-30?**

That is the exact goal of this step.
