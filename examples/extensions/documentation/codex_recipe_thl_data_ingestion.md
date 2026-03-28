# Codex Recipe: THL Data Ingestion and Local Snapshot Interface

## Goal

Implement the **first data interface layer** for the project, using **THL COVID-19 data for Finland** as the initial source.

At this stage, the purpose is **not** to build full calibration, **not** to build the GUI, and **not** yet to compare scenarios against data in the notebook.

The purpose is to establish a clean and reproducible pipeline:

```text
THL source -> local raw snapshot -> processed local time series -> ObservedDataset / TimeSeries
```

This is important because the project should use **local saved snapshots**, not depend on live remote data during normal execution.

---

## Scope of this task

Implement only the **first THL data ingestion and local snapshot layer**.

This task should include:

- a small ingestion module for THL data
- local raw snapshot saving
- local processed dataset saving
- conversion into the existing `ObservedDataset` / `TimeSeries` abstractions
- a notebook that can fetch the THL data, save it locally, reload it, and print / inspect the resulting time series

This task should **not** include:

- calibration logic
- scenario-vs-data comparison logic
- GUI integration
- automatic scheduled updates
- support for many sources at once
- postcode-level regional mapping
- hospital district vs wellbeing area remapping logic beyond preserving region labels
- full data warehouse design

Keep this first version narrow and reproducible.

---

## Design principle

Use this separation:

```text
remote THL data -> raw snapshot -> processed local file -> API objects
```

Normal project use should rely on **local files**, not live THL calls.

The remote fetch should be used only for:

- initial ingestion
- manual refresh
- reproducible snapshot generation

---

## Recommended directory structure

Create these directories if they do not yet exist:

```text
data/
  raw/
  processed/
extensions/
  scenario_api/
```

The data interface code should live under:

```text
extensions/scenario_api/
```

Add a new module:

```text
extensions/scenario_api/data_sources.py
```

You may also update:

- `data.py`
- `results.py` if needed only minimally
- `__init__.py`

Notebook:
- either extend the existing smoke-test notebook if still manageable
- or preferably create a dedicated notebook:

```text
extensions/notebooks/thl_data_ingestion_test.ipynb
```

Use the cleaner option.

---

## Data scope for the first version

Use **Finland, 2020-2022** as the initial target window.

For the first version, support at least one epidemiological variable cleanly.

### Required first variable
- confirmed cases

### Optional if easy and already available in the chosen THL source
- hospitalizations
- ICU
- deaths
- vaccinations

But do not expand the task too much.
The main target is to get **cases** working first.

---

## Geographic resolution

The interface should support at least these concepts:

- `country`
- `hospital_district`
- `municipality` if available in the chosen THL source and convenient

However, for the first version, it is acceptable to implement and test only:
- `country`
- `hospital_district`

Do not attempt postcode-level data here.

The purpose is to preserve the region information in a clean way so it can later be mapped to model aggregation.

---

## Main architectural requirement

Do **not** hardcode the notebook as the only place where data ingestion logic lives.

Put the real logic into reusable Python modules.
The notebook should only demonstrate and test the pipeline.

---

## Object / interface expectations

Reuse the existing abstractions where possible:

- `ObservedDataset`
- `TimeSeries`

If needed, lightly extend them, but do not redesign the whole API.

The data interface should produce:

1. local saved raw files
2. local saved processed files
3. `ObservedDataset`
4. `TimeSeries`

---

## THL source handling

Use the actual available THL export / API / downloadable data format supported by the current environment and source.

Important:
- inspect the current THL data source format rather than inventing one
- adapt to the real CSV / JSON / API structure
- keep the parsing code explicit and documented

Do not overgeneralize yet.

If the THL source format is awkward, it is acceptable to support one stable download/export path first.

---

## Required files / modules

### 1. `extensions/scenario_api/data_sources.py`

Implement the THL-specific ingestion and file handling here.

### 2. `extensions/scenario_api/data.py`

Update only as needed so that local processed THL data can be turned into `ObservedDataset` and `TimeSeries`.

### 3. `extensions/scenario_api/__init__.py`

Export the new public functions.

---

## Functions to implement

Below are suggested names. If the local codebase strongly prefers slightly different names, adapt carefully, but preserve the architectural roles.

### In `data_sources.py`

Implement at least:

```python
fetch_thl_cases_raw(...) -> object
save_raw_snapshot(data, path) -> str
load_raw_snapshot(path) -> object
process_thl_cases_raw_to_table(raw_data, ...) -> object
save_processed_table(table, path) -> str
load_processed_table(path) -> object
```

The exact return types can be:
- pandas DataFrame, if you choose pandas
- or a simpler structure

Pandas is acceptable here if it clearly simplifies THL table handling.

If you use pandas, keep it localized and simple.

---

### Recommended public functions

Implement a small clean public API such as:

```python
download_and_save_thl_cases_snapshot(
    raw_output_path,
    processed_output_path,
    start_date=None,
    end_date=None,
    region_level="hospital_district",
) -> tuple[str, str]
```

Behavior:
- downloads the THL cases data
- saves raw snapshot
- processes it into a normalized local table
- saves the processed table
- returns paths

And:

```python
load_thl_cases_observed_dataset(processed_path, metadata=None) -> ObservedDataset
```

Behavior:
- loads the processed local file
- creates an `ObservedDataset`

And:

```python
thl_dataset_to_timeseries(
    dataset,
    variable="cases",
    region=None,
    region_level=None,
) -> TimeSeries | list[TimeSeries]
```

Behavior:
- converts the dataset into one or more `TimeSeries`
- if `region` is specified, return the matching region’s series
- if not, either return all matching series or require explicit region choice
- keep behavior explicit and documented

---

## Normalized processed file format

The processed local file should be normalized into a simple tabular structure.

Recommended columns:

- `date`
- `region_level`
- `region`
- `variable`
- `value`
- optional `source`
- optional `notes`

Example rows:

```text
2020-03-01, hospital_district, Helsinki and Uusimaa, cases, 12
2020-03-02, hospital_district, Helsinki and Uusimaa, cases, 18
...
```

This simple long-format structure is strongly preferred because:
- easy to inspect
- easy to convert to `TimeSeries`
- easy to extend later to other variables

Do not overengineer the schema.

---

## Data validation requirements

Implement clear validation for at least:

- missing expected columns after parsing
- empty processed dataset
- invalid region level request
- requested region not found
- invalid date filtering input if applicable

Use direct `ValueError` / `RuntimeError` messages.

Do not fail silently.

---

## Snapshot philosophy

This is important:

- the notebook may fetch THL data remotely
- the code should then save a **raw snapshot**
- and also save a **processed local file**
- later normal use should read the local processed file

This should be explicit in code and notebook comments.

The project should not depend on THL availability at runtime for ordinary use.

---

## Notebook requirements

Create or update a notebook for manual testing.

Preferred path:

```text
extensions/notebooks/thl_data_ingestion_test.ipynb
```

### Required notebook flow

#### A. Imports
- import the new data-source functions
- import `ObservedDataset` / `TimeSeries` conversion helpers

#### B. Configure output paths
Define clear paths such as:

```text
data/raw/thl_cases_2020_2022_raw.*
data/processed/thl_cases_2020_2022_processed.csv
```

Choose the raw extension based on the real downloaded format or saved representation.

#### C. Download THL data
At the top of the notebook, fetch the THL cases data from the real THL source.

Then:
- save the raw snapshot
- process it
- save the processed local file

Print the saved paths.

This step should be easy to comment out later once the snapshot exists.

#### D. Reload from local processed file
Demonstrate that normal use works from the local processed file, not only from the remote fetch.

#### E. Create `ObservedDataset`
Load the processed file into `ObservedDataset`.

Print:
- basic metadata
- available regions
- available variable(s)
- date range

#### F. Convert to time series
Create at least:
- one Finland-wide series if available
- or one hospital-district series
- and at least one additional regional example if the data supports it

Print the resulting `TimeSeries` objects.

#### G. Inspect the time series
At the end of the notebook:
- print head / tail or similar inspection output
- and make one or more simple plots of the resulting time series

The purpose here is only to confirm:
- the ingestion works
- local storage works
- conversion to time series works

### Important notebook constraint

Do **not** add scenario comparison yet in this notebook.
That belongs to a later step.

The notebook should stop at:
- fetch
- save
- load
- inspect
- print / plot time series

---

## Success criteria

This task is complete when all of the following are true:

1. THL cases data can be fetched from the real source
2. a raw snapshot can be saved locally
3. a processed normalized local file can be saved
4. the processed local file can be loaded without remote access
5. an `ObservedDataset` can be created from it
6. one or more `TimeSeries` objects can be produced
7. the notebook demonstrates:
   - remote fetch
   - raw snapshot save
   - processed file save
   - reload from processed local file
   - time-series inspection and printing / plotting

---

## Coding style

Requirements:

- keep the implementation explicit
- use type hints
- add short docstrings
- keep source-specific logic in `data_sources.py`
- avoid broad refactors
- prefer a small honest first version over false generality

---

## What not to do in this task

Do not implement:
- calibration
- scenario-data comparison
- postcode-level mapping
- SHP/HVA remapping abstraction
- automatic data updater
- support for many remote sources
- full ETL framework
- database storage

This is only the first reproducible data ingestion layer.

---

## Final note

The main value of this step is not just “getting data”.
It is establishing a reproducible workflow:

- remote source only for ingestion
- local snapshots for actual work
- normalized processed table
- conversion into the project’s time-series abstractions

That gives a stable base for later calibration and visualization work.
