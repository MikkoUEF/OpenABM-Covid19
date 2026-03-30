# Postcode-Based Synthetic Population Model (Phase 1)

## Goal

Construct a synthetic population for Finland at the **postcode level** using:

- Finnish census data (age distribution per postcode)
- OpenABM UK household sample (reference households)

The result must:
- Match **age distribution per postcode**
- Preserve **realistic household structure**
- Be generated entirely in Python (outside OpenABM core)

---

## Key Idea

We do **not** generate households from scratch.

Instead:
- Use the **UK household sample as a template library**
- Sample households until postcode-level age targets are matched

This reproduces the MATLAB prototype logic in a clean Python module.

---

## Scope of This Phase

This phase includes only:

- postcode-level population synthesis
- household sampling
- age-bin harmonisation
- validation of fit

This phase explicitly excludes:

- mobility modelling
- workplace/school/shop assignment
- OpenABM network construction
- intervention logic

These will be handled later in separate phases.

---

## Inputs

### 1. Finnish Census Data

For each postcode area, provide:

- postcode identifier
- total population
- age distribution

Preferred input:
- 1-year age counts, or
- 5-year age bins

Example schema:

```text
postcode, age_0_6, age_7_12, age_13_17, age_18_24, ...
00100, ...
```

---

### 2. UK Household Sample

Extract or reconstruct a reusable household sample from OpenABM reference data.

Each household should be represented as a list of individual ages.

Example:

```python
[34, 36, 8, 5]
[72]
[41, 39, 14]
```

Store as:

```python
List[List[int]]
```

This UK sample is used only as a household-structure template library.

---

## Age Harmonisation

### OpenABM Target Age Bins

OpenABM uses decade bins:

- 0-9
- 10-19
- 20-29
- 30-39
- 40-49
- 50-59
- 60-69
- 70-79
- 80+

The Finnish postcode census data must be mapped into these bins before sampling.

### Special Handling: 7-12 Age Group

If the Finnish source contains a combined 7-12 age group, it must be split between:

- 0-9
- 10-19

This split should be done explicitly and deterministically, using one of the following:

1. proportional split assuming uniform ages within 7-12
2. proportional split using external Finnish age statistics if available

The split method must be documented and reproducible.

---

## Target Representation

For each postcode, convert the target to:

```python
target_counts[postcode][age_bin] = integer_count
```

Example:

```python
target_counts["00100"] = {
    "0_9": 124,
    "10_19": 138,
    "20_29": 201,
    ...
}
```

---

## Output Representation

The module must produce:

### 1. Household-Level Output

```python
{
    "postcode": "00100",
    "households": [
        [34, 36, 8, 5],
        [72],
        [41, 39, 14]
    ]
}
```

### 2. Individual-Level Output

A flat table or dataframe with at least:

- person_id
- household_id
- postcode
- age
- age_bin

Example:

```text
person_id, household_id, postcode, age, age_bin
1, H000001, 00100, 34, 30_39
2, H000001, 00100, 36, 30_39
3, H000001, 00100, 8, 0_9
...
```

---

## Core Sampling Algorithm

For each postcode:

### Step 1: Initialise

Create:

- current age counts = zero vector
- selected households = empty list
- running population size = 0

Example:

```python
current_counts = zeros(age_bins)
selected_households = []
```

---

### Step 2: Candidate Household Sampling

Repeatedly sample one candidate household from the UK reference pool:

```python
h = random.choice(uk_households)
```

Convert the sampled household into its age-bin histogram.

Example:

```python
hist_h = household_age_histogram(h)
```

---

### Step 3: Evaluate Fit

Let:

```python
new_counts = current_counts + hist_h
```

Compute fit against postcode target.

Recommended error metric:

```python
SSE = sum((new_counts - target_counts)**2)
```

At minimum compute:

- error_before
- error_after

Base acceptance rule:

- accept if error_after < error_before

---

### Step 4: Prevent Stalling

A purely greedy algorithm will often stall near the target.

Therefore implement one of the following:

#### Option A: Soft Acceptance

Allow occasional non-improving moves with low probability.

#### Option B: Overshoot Tolerance

Permit bounded temporary overshoot in some bins early in the process.

#### Option C: Two-Phase Strategy

- phase 1: broad matching with relaxed acceptance
- phase 2: refinement with stricter acceptance

The implementation may choose any of these, but it must remain interpretable and reproducible.

---

### Step 5: Termination

Stop sampling for a postcode when both are satisfied:

1. total population is within tolerance of target
2. age-bin mismatch is below threshold

Suggested tolerances:

- total population exact, or within a very small household-size-dependent tolerance
- age-bin SSE below postcode-specific threshold

If exact fitting is not achievable, return:

- best solution found
- diagnostics showing remaining mismatch

Do not silently fail.

---

## Postcode-Level Validation

For every postcode, calculate and store:

- target population
- realised population
- target age-bin counts
- realised age-bin counts
- absolute error by age bin
- SSE
- household count
- household size distribution

Generate validation outputs:

### Required

- summary table across all postcodes
- postcode-level fit table

### Recommended

- bar plot: target vs realised age distribution for sampled postcodes
- histogram: household sizes
- scatter plot: target population vs realised population

---

## Global Validation

Across the full national synthetic population, also check:

- total population
- national age distribution
- overall household size distribution
- stability under repeated runs with same seed

---

## Reproducibility

The whole pipeline must be reproducible.

Requirements:

- explicit random seed support
- deterministic preprocessing
- versioned inputs
- logging of configuration parameters

Example API:

```python
build_population(
    census_data,
    uk_households,
    random_seed=1234,
    config=...
)
```

---

## Module Structure

Create a new Python module outside OpenABM core.

Suggested structure:

```text
population_model/
    __init__.py
    census_loader.py
    uk_households_loader.py
    age_mapping.py
    sampler.py
    validation.py
    models.py
    config.py
```

### Suggested Responsibilities

- `census_loader.py`
  - load Finnish postcode census data

- `uk_households_loader.py`
  - load UK household template sample

- `age_mapping.py`
  - harmonise source age bins to OpenABM bins

- `sampler.py`
  - postcode-level household sampling algorithm

- `validation.py`
  - fit diagnostics and plots

- `models.py`
  - population and household data structures

- `config.py`
  - thresholds, tolerances, random seed handling

---

## API Requirement

Implement a top-level function:

```python
def build_population(census_data, uk_households, random_seed=1234, config=None):
    ...
```

It must return a structured population object containing:

- households by postcode
- individual-level table
- validation diagnostics

---

## Design Constraints

- Do not modify OpenABM core
- Do not implement mobility in this phase
- Do not implement networks in this phase
- Keep the code simple, explicit, and testable
- Prefer readable heuristics over opaque optimisation unless clearly justified

---

## Testing Requirements

At minimum add tests for:

1. age-bin mapping correctness
2. 7-12 split logic
3. postcode sampling on a tiny synthetic example
4. reproducibility with fixed seed
5. validation metrics correctness

---

## Deliverable

The deliverable for this phase is a standalone Python population synthesis module that:

- reproduces the household-sampling idea from the MATLAB prototype
- matches postcode-level Finnish age distributions as closely as possible
- outputs a synthetic household population ready for later mobility assignment

---

## Important Note for Later Phases

This phase defines only the **population base layer**.

Later phases will add:

- mobility assignment
- mapping mobility to contact structures
- conversion into OpenABM-compatible user-defined networks
