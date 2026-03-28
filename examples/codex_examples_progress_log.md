# Codex Progress Log (examples)

Päivä: 2026-03-24

## Tehty

- Notebookit korjattu `_fixed`-versioiksi ja ajettu läpi:
  - `economics_visualisation_fixed.ipynb`
  - `example_multiple_working_sectors_fixed.ipynb`
  - `example_recursive_tests_fixed.ipynb`
  - `example_user_defined_networks_fixed.ipynb`
- `networkx` asennettu `venv`-ympäristöön (`3.4.2`), ja `example_user_defined_networks_fixed.ipynb` testattu uudelleen.
- `.py`-korjauksia tehty:
  - `examples/example_multi_strain_vaccinate.py`
  - `examples/geo_plot.py`
  - `examples/multi_region.py`
- `gdp.py` pandas-yhteensopivuuskorjaus tehty:
  - `src/adapter_covid19/gdp.py` (`self.xtilde_iot.index = list(M)`, `clip(lower=1e-6)`).
- Economics-skenaariot generoitu hakemistoon `/home/ubuntu/dumps`:
  - `scenario_no_lockdown.pkl`
  - `scenario_basic.pkl`
  - `scenario_slow_unlock.pkl`
  - `scenario_slow_unlock_constrained.pkl`

## Tekemättä

- Ajaa `economics_visualisation_fixed.ipynb` vielä kerran niin, että se käyttää nyt luotuja `~/dumps/scenario_*.pkl`-tiedostoja (full-data varmistus).
- Tarkistaa halutaanko myös jäljellä olevien raskaiden `.py`-skriptien täysi end-to-end -ajo ilman timeoutia:
  - `examples/example_run_simulation_with_lockdown.py`
  - `examples/multi_run_simulator.py`

## Huomio

- GitHub-pushia ei ole tehty.
