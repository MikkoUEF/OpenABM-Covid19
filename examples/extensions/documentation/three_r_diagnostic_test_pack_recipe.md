# Codex Recipe: Three-R Diagnostic Test Pack (R0 / R_obs / R_agent) with 7-Day Smoothed Notebook Plot

## Goal

Implement a **small diagnostic test pack** that computes and compares three different R-type quantities:

1. **R0**
   - the baseline reproduction target / baseline reproduction level used for the no-intervention model setup

2. **R_obs**
   - estimated from observed THL daily cases

3. **R_agent**
   - estimated from simulated daily incidence produced by the OpenABM run

The purpose is to make these three concepts explicit and visible in the same workflow.

This is a **diagnostic comparison tool**, not a final calibration system.

---

## Main requirement

At the end of the latest execution notebook, add a section that computes:

- `R_obs`
- `R_agent`

and also clearly reports the current baseline `R0` assumption / target.

Then visualize the smoothed curves together in one clear comparison plot.

Important:
- `R0` is not a full time series in the same sense as the other two
- so it can be shown as a constant reference line or printed explicitly alongside the plot

---

## Scope

Implement:

- a helper to compute `R_obs` from observed daily cases
- a helper to compute `R_agent` from simulated daily incidence
- a 7-day smoothing helper
- notebook comparison section at the end of the latest notebook
- clear naming and interpretation

Do NOT implement:

- full Rt estimation packages
- Bayesian estimation
- delay correction
- testing-adjusted observation model
- calibration automation
- GUI

Keep this small, explicit, and diagnostic.

---

## Files

Update as needed:

- `extensions/scenario_api/data.py`
- `extensions/scenario_api/execution_pipeline.py`
- `extensions/scenario_api/__init__.py`

If you already have an R-proxy helper somewhere, reuse and refine it rather than duplicating.

Update notebook:

- `extensions/notebooks/end_to_end_multi_shp_test.ipynb`

Do **not** create a separate notebook for this.
Add the diagnostic section to the end of the latest notebook.

---

## Definitions to use

### 1. `R0`

For this test pack, `R0` means:

- the baseline reproduction assumption / target for the no-intervention setup
- not an observed or dynamically estimated time series

For the notebook, define explicitly near the top or in the diagnostics section:

```python
R0_target = 2.3
```

If the current baseline parameterization implies a different internal value, print both if available:
- `R0_target`
- optional `R0_model_assumption`

But at minimum, `R0_target = 2.3` must be shown explicitly.

---

### 2. `R_obs`

Compute from observed THL **daily cases**.

Use a simple lag-ratio proxy:

```text
R_obs[t] = observed_daily_cases[t] / observed_daily_cases[t - generation_interval]
```

where:

- `generation_interval = 5`

This is acceptable for this diagnostic step.

---

### 3. `R_agent`

Compute from simulated **daily incidence** using the exact same method:

```text
R_agent[t] = simulated_daily_cases[t] / simulated_daily_cases[t - generation_interval]
```

Use the same generation interval.

Do not compute `R_agent` from cumulative values.

---

## Required helper functions

Implement or refine these helpers in reusable code.

### A. Smoothing helper

```python
smooth_timeseries_moving_average(timeseries, window=7, new_name=None) -> TimeSeries
```

Behavior:
- compute a centered or trailing 7-day moving average
- preserve time axis
- label metadata clearly
- default window = 7

Use the same smoothing method for both:
- `R_obs`
- `R_agent`

Be explicit in metadata and notebook text.

---

### B. R-proxy helper

```python
compute_r_proxy_from_incidence(timeseries, generation_interval=5, new_name=None) -> TimeSeries
```

Behavior:
- ratio over lagged incidence
- handle zero / near-zero denominator safely
- produce NaN or skip invalid early points
- store metadata:
  - method = `"ratio_over_lagged_incidence"`
  - generation_interval

Use this same helper for both observed and simulated series.

---

### C. Convenience wrapper (optional but recommended)

```python
compute_smoothed_r_proxy(timeseries, generation_interval=5, smoothing_window=7, new_name=None) -> TimeSeries
```

Behavior:
- compute raw R proxy
- then smooth it
- return smoothed `TimeSeries`

If this helper improves clarity, use it.

---

## Important metric requirement

Before computing any R-type proxy, make sure the notebook is using:

- `observed_daily_cases`
- `simulated_daily_cases`

Do **not** accidentally use:
- cumulative observed values
- cumulative simulated values

This must be explicit in variable names and notebook printouts.

---

## Notebook requirements

Update the **end of**:

- `extensions/notebooks/end_to_end_multi_shp_test.ipynb`

Add a final section titled something like:

```text
R diagnostics: R0 vs R_obs vs R_agent
```

### Required notebook behavior

Use the same main date window already in use:

- `2020-03-01`
- `2020-06-30`

For the first version, focus on:

- `Helsinki and Uusimaa`

If the notebook already loops over multiple SHPs, it is acceptable to compute these diagnostics only for HUS in the final section.

---

## Required notebook steps

### A. Explicit parameter printout

Print clearly:

- SHP name
- date window
- `R0_target`
- generation interval
- smoothing window

This is required.

---

### B. Build `R_obs`

From the observed THL daily cases already loaded in the notebook:

1. compute raw `R_obs`
2. compute 7-day smoothed `R_obs`

Print:
- first valid values
- metadata summary

---

### C. Build `R_agent`

From the simulated daily incidence already produced in the notebook:

1. compute raw `R_agent`
2. compute 7-day smoothed `R_agent`

Print:
- first valid values
- metadata summary

---

### D. Combined plot

Create one final plot showing:

- smoothed `R_obs`
- smoothed `R_agent`
- horizontal constant line for `R0_target = 2.3`
- horizontal reference line at `R = 1`

This plot is required.

### Plot readability requirement

- keep the plot readable
- add legend
- add title including SHP and date window
- use one figure only for this combined diagnostic plot
- do not overplot raw noisy series on top unless clearly labeled

The main plot should use the **7-day smoothed curves**.

---

### E. Optional raw-series debug plot

Optional:
- show a second figure with raw `R_obs` and raw `R_agent`

Only do this if it helps.
The required output is still the smoothed comparison plot.

---

### F. Short interpretation cell

Add one final notebook cell that prints a short human-readable interpretation, for example:

- whether `R_agent` starts near the intended baseline relative to `R0_target`
- whether `R_agent` drops when restrictions begin
- whether `R_agent` tracks `R_obs` at least directionally
- whether the main mismatch is in baseline, timing, or intervention magnitude

No automatic optimization.
Just a structured diagnostic summary.

---

## Validation requirements

Implement clear checks for:

- missing observed daily cases
- missing simulated daily incidence
- invalid smoothing window
- invalid generation interval
- all-zero denominator segments causing unusable ratios

Raise clear `ValueError` where appropriate.
Do not fail silently.

---

## Success criteria

This task is complete when all of the following are true:

1. there is reusable code to compute an R proxy from daily incidence
2. there is reusable code to smooth a time series with a 7-day moving average
3. the notebook computes:
   - `R_obs`
   - `R_agent`
   - shows `R0_target`
4. the notebook ends with one combined comparison plot
5. the plot includes:
   - smoothed `R_obs`
   - smoothed `R_agent`
   - `R0_target` reference line
   - `R = 1` reference line

---

## Design rules

Do NOT:

- call the proxy a formal Rt estimator
- mix cumulative and daily values
- hide the calculation in notebook-only code
- create a second disconnected notebook
- make this step more complex than needed

Keep it:
- explicit
- reusable
- diagnostic
- tied to the latest notebook

---

## Final note

This test pack is meant to answer one practical question:

**Is the model getting the epidemic growth dynamics roughly right, when comparing baseline expectation (`R0_target`), observed growth (`R_obs`), and simulated growth (`R_agent`) over the same first-wave period?**

That is the exact purpose of this step.
