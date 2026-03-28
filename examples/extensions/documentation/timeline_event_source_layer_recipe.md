# Codex Recipe: Timeline Event Source Layer (Separate from Interventions)

## Goal

Implement a **separate timeline event source layer**.

This layer must be distinct from:

- the intervention layer
- the scenario layer
- the THL epidemiological data layer

The purpose of this step is to create a clean pipeline for **policy / timeline events** such as:

- school restrictions
- gathering restrictions
- stay-at-home restrictions
- travel restrictions
- mask guidance / mandates
- testing / tracing policy changes
- vaccination policy milestones

These are **historical or externally defined policy events**, not yet model interventions.

The key architectural rule is:

```text
timeline source data -> normalized TimelineEvent objects -> later mapping to Interventions
```

Do **not** implement the mapping to interventions yet in this task.

---

## Why this layer exists

This layer must stay separate because these are three different things:

1. **event source**
   - where the historical event came from
   - e.g. OxCGRT, STM, THL, manually curated Finland timeline

2. **policy event representation**
   - normalized event object
   - still historical / descriptive

3. **model intervention**
   - how the event affects OpenABM parameters

This task is only about (1) and (2), not yet (3).

---

## Scope

Implement:

- timeline event data model
- timeline source fetch/load/save layer
- raw snapshot saving
- processed normalized event saving
- conversion into normalized `TimelineEvent` objects
- notebook test for loading and inspecting timeline events

Do NOT implement:

- mapping TimelineEvent -> Intervention
- calibration
- scenario comparison
- GUI
- automatic policy-to-parameter interpretation
- broad multi-country support

Keep this first version focused and explicit.

---

## Files

Add these modules under:

```text
extensions/scenario_api/
```

Create:

```text
extensions/scenario_api/timeline.py
extensions/scenario_api/timeline_sources.py
```

Update if needed:

```text
extensions/scenario_api/__init__.py
```

Notebook:

```text
extensions/notebooks/timeline_event_ingestion_test.ipynb
```

---

## Data source scope for first version

Support **one usable source first**.

Preferred first source:

- **OxCGRT Finland 2020-2022**

If OxCGRT is awkward in practice, it is acceptable to support:
- a manually downloaded local CSV snapshot
- or a manually curated normalized CSV

But the code should still preserve the architecture:
- raw source snapshot
- processed normalized event file
- normalized event objects

Do not try to support several sources at once in the first version.

---

## Time scope

Use:

- Finland
- 2020-01-01 to 2022-12-31

If the source naturally includes a wider date range, filter down to this window in the processed normalized file.

---

## Geographic scope

For the first version, it is acceptable to use:

- `country` level only
- region = `"Finland"`

Do not attempt regional timeline events yet unless the source already provides them cleanly and you can support them with very little extra complexity.

This first version is only meant to establish the timeline architecture.

---

## 1. Timeline event model

In `timeline.py`, implement a normalized event object.

Use `@dataclass`.

Required fields:

```python
date: str
source: str
region_level: str
region: str
event_type: str
value: object
notes: str = ""
metadata: dict[str, object] = field(default_factory=dict)
```

Suggested class name:

```python
TimelineEvent
```

### Required meaning of fields

- `date`
  - ISO date string like `2020-03-16`

- `source`
  - e.g. `"OxCGRT"`

- `region_level`
  - e.g. `"country"`

- `region`
  - e.g. `"Finland"`

- `event_type`
  - normalized event class, for example:
    - `"school_closing"`
    - `"workplace_closing"`
    - `"public_events"`
    - `"gathering_restrictions"`
    - `"public_transport"`
    - `"stay_at_home"`
    - `"internal_movement"`
    - `"international_travel"`
    - `"public_information"`
    - `"testing_policy"`
    - `"contact_tracing"`
    - `"facial_coverings"`
    - `"vaccination_policy"`
    - `"elderly_protection"`

- `value`
  - source-specific severity / level / state
  - keep it explicit
  - can be int or string in the first version

- `notes`
  - optional human-readable note

- `metadata`
  - optional extra source-specific information

---

## 2. Normalized processed file format

The processed local file should be simple and explicit.

Recommended columns:

- `date`
- `source`
- `region_level`
- `region`
- `event_type`
- `value`
- `notes`

Optional:
- source-specific original code column in metadata or extra column
- e.g. `source_code`

Use a normalized long format.
One row = one event type value at one date.

Example:

```text
2020-03-16,OxCGRT,country,Finland,school_closing,3,
2020-03-16,OxCGRT,country,Finland,workplace_closing,2,
2020-08-13,OxCGRT,country,Finland,facial_coverings,2,
```

Do not overengineer the schema.

---

## 3. timeline.py functions

Implement at least:

```python
load_timeline_events_from_processed(path) -> list[TimelineEvent]
timeline_events_to_table(events) -> object
filter_timeline_events(events, start_date=None, end_date=None, event_type=None) -> list[TimelineEvent]
```

If you use pandas, `timeline_events_to_table` can return a DataFrame.
That is acceptable here.

Behavior:
- loading should read the processed local file
- filtering should be explicit and simple
- do not add hidden magic

---

## 4. timeline_sources.py functions

Implement the source-specific ingestion logic here.

Required public functions:

```python
fetch_oxcgrt_finland_raw(...) -> object
save_timeline_raw_snapshot(data, path) -> str
load_timeline_raw_snapshot(path) -> object
process_oxcgrt_finland_raw_to_events(raw_data, start_date=None, end_date=None) -> object
save_processed_timeline_events(table, path) -> str
load_processed_timeline_events_table(path) -> object
```

Recommended convenience function:

```python
download_and_save_oxcgrt_finland_timeline(
    raw_output_path,
    processed_output_path,
    start_date="2020-01-01",
    end_date="2022-12-31",
) -> tuple[str, str]
```

Behavior:
- fetch raw source
- save raw snapshot
- normalize and filter
- save processed file
- return paths

---

## 5. Explicit source mapping for first version

If using OxCGRT, map the source columns explicitly into the normalized `event_type` values.

For example:

- `C1M` or equivalent -> `school_closing`
- `C2M` -> `workplace_closing`
- `C3M` -> `public_events`
- `C4M` -> `gathering_restrictions`
- `C5M` -> `public_transport`
- `C6M` -> `stay_at_home`
- `C7M` -> `internal_movement`
- `C8EV` or equivalent travel control column -> `international_travel`
- `H1` -> `public_information`
- `H2` -> `testing_policy`
- `H3` -> `contact_tracing`
- `H6M` -> `facial_coverings`
- `H7` -> `vaccination_policy`
- `H8M` -> `elderly_protection`

Important:
- inspect the actual OxCGRT column names in the current downloadable file
- do not assume blindly if the dataset schema has changed
- implement the mapping explicitly in code comments

If the schema differs, adapt to the actual current file.

---

## 6. Validation requirements

Implement clear errors for:

- missing expected source columns
- empty Finland subset
- empty processed output after filtering
- invalid processed file missing required normalized columns

Use direct `ValueError` / `RuntimeError`.
Do not fail silently.

---

## 7. Snapshot philosophy

This must follow the same philosophy as the THL data layer:

- fetch remotely only when ingesting / refreshing
- save raw snapshot locally
- save processed normalized file locally
- normal project use should read local processed files

This should be explicit in notebook comments and function docstrings.

---

## 8. Notebook

Create:

```text
extensions/notebooks/timeline_event_ingestion_test.ipynb
```

### Required notebook steps

#### A. Imports
- import timeline source functions
- import `TimelineEvent` loading / filtering helpers

#### B. Configure paths
Use clear paths such as:

```text
data/raw/oxcgrt_finland_2020_2022_raw.*
data/processed/oxcgrt_finland_2020_2022_timeline.csv
```

#### C. Fetch source
At the top of the notebook:
- download OxCGRT Finland timeline data
- save raw snapshot
- process and save normalized local event file

Print the saved paths.

This step should be easy to comment out later once the snapshot exists.

#### D. Reload processed local file
Load the processed local file again from disk, not from the remote source.

#### E. Create `TimelineEvent` objects
Load normalized processed rows into `TimelineEvent` objects.

Print:
- number of events
- min/max date
- distinct event types

#### F. Inspect events
Print a few example rows / objects, for example:
- first 10 events
- all facial covering events
- all testing policy events

#### G. Simple plot or summary
At the end, add a simple visualization or summary table, for example:
- count of events by type
- timeline plot of one event type’s values over time
- step plot for `school_closing` or `facial_coverings`

Do not connect this to interventions yet.

---

## 9. Success criteria

This task is complete when all of the following are true:

1. there is a separate timeline event source layer
2. raw source data can be fetched and saved locally
3. processed normalized event files can be saved locally
4. processed local files can be reloaded without remote access
5. normalized `TimelineEvent` objects can be created
6. the notebook demonstrates:
   - remote fetch
   - raw snapshot save
   - processed normalized save
   - reload from local processed file
   - event inspection
   - simple summary / plot

---

## 10. Design rules

Do NOT:

- map events to model interventions yet
- mix this with `interventions.py`
- put source-specific fetch logic into the notebook only
- hardcode future scenario semantics here
- overgeneralize to many sources

Keep it:
- source-aware
- normalized
- local-snapshot based
- separate from intervention semantics

---

## Final note

This layer is the **historical policy event data layer**.

It exists so that later you can build:

```text
TimelineEvent -> Intervention mapper
```

without mixing:
- data ingestion
- policy semantics
- model semantics

That separation is the whole point of this step.
