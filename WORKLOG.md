# WORKLOG

Kevyt operatiivinen tilannekortti jatkamiseen katkoksien yli.

## Paivityssaanto
- Paivita aina ennen VS Coden sulkemista tai kun vaihe vaihtuu.
- Paivita myos heti commitin/pushin jalkeen.
- Tyovirta: `git status --short` + `git log --oneline -n 3` -> paivita tahan 5-10 rivia -> tarvittaessa checkpoint-commit.

## Vakiorakenne
- Paivamaara ja aika (UTC)
- Viimeisin valmis commit
- Typuun nykytila (muokatut/uudet tiedostot)
- Mita tehtiin viimeksi
- Seuraava konkreettinen askel
- Mahdolliset riskit / huomiot

---

## Entry 2026-03-26 18:16:28 UTC
- Paivamaara ja aika (UTC): 2026-03-26 18:16:28 UTC
- Viimeisin valmis commit: `a025152 Add THL daily ingestion with district-level series and plots`
- Typuun nykytila (muokatut/uudet tiedostot):
  - Muokatut: `extensions/scenario_api/__init__.py`, `extensions/scenario_api/interventions.py`
  - Uudet (relevantit): `extensions/notebooks/intervention_layer_test.ipynb`, `tests/extensions/test_intervention_layer_api.py`
  - Uudet (paljon muitakin untracked-tiedostoja repussa; ei koskettu nyt)
- Mita tehtiin viimeksi: interventiokerroksen reseptin toteutus + notebookin import/plot-yhteensopivuuskorjaukset + kernel-jumien katkaisu.
- Seuraava konkreettinen askel: aja notebook puhtaalta kernelilta (`Run All`) ja tee sitten kohdennettu commit vain interventiokerroksen tiedostoista.
- Mahdolliset riskit / huomiot: ympaiston `matplotlib==3.2.2` voi aiheuttaa yhteensopivuusreunatapauksia; notebookissa kaytetaan turvallista `to_numpy()`-plottausta.

## Entry 2026-03-26 18:22:58 UTC
- Paivamaara ja aika (UTC): 2026-03-26 18:22:58 UTC
- Viimeisin valmis commit: `8f42e16 Add intervention layer notebook checkpoint and worklog`
- Typuun nykytila (muokatut/uudet tiedostot): intervention layer -muutokset commitissa, ei uusia muutoksia naihin tiedostoihin.
- Mita tehtiin viimeksi: `extensions/notebooks/intervention_layer_test.ipynb` ajettiin onnistuneesti loppuun.
- Seuraava konkreettinen askel: tee pieni worklog-commit ja push.
- Mahdolliset riskit / huomiot: notebook-jumit voivat palata, mutta kernelin tappo toimii palautuskeinona.

## Entry 2026-03-26 18:22:58 UTC
- Paivamaara ja aika (UTC): 2026-03-26 18:22:58 UTC
- Viimeisin valmis commit: `8f42e16 Add intervention layer notebook checkpoint and worklog`
- Typuun nykytila (muokatut/uudet tiedostot): intervention layer -muutokset commitissa, ei uusia muutoksia naihin tiedostoihin.
- Mita tehtiin viimeksi: `extensions/notebooks/intervention_layer_test.ipynb` ajettiin onnistuneesti loppuun.
- Seuraava konkreettinen askel: tee pieni worklog-commit ja push.
- Mahdolliset riskit / huomiot: notebook-jumit voivat palata, mutta kernelin tappo toimii palautuskeinona.

## Entry 2026-03-28 00:00:00 UTC
- Paivamaara ja aika (UTC): 2026-03-28 00:00:00 UTC
- Viimeisin valmis commit: `5c5f413 Add single-SHP execution bridge mode with notebook`
- Typuun nykytila (muokatut/uudet tiedostot):
  - Muokatut (relevantit): `extensions/scenario_api/interventions.py`, `extensions/scenario_api/openabm_adapter.py`, `extensions/scenario_api/runner.py`, `extensions/scenario_api/execution_pipeline.py`, `extensions/scenario_api/__init__.py`
  - Notebook paivitetty: `extensions/notebooks/end_to_end_multi_shp_test.ipynb`
  - Repussa on paljon aiempia untracked/muokattuja tiedostoja, joita ei siivottu tassa vaiheessa.
- Mita tehtiin viimeksi: runtime-interventioiden OpenABM-sovelluspolku korjattu, seed-ohjaus lisatty (`initial_infected`), paivakohtainen `cases` varmistettu, R-proxy helper lisatty, notebookin diagnostiikat (linear+log, runtime-summary, seed-sensitiivisyys, sanity-check) paivitetty.
- Seuraava konkreettinen askel: aja `extensions/notebooks/end_to_end_multi_shp_test.ipynb` loppuun ja tarkista HUS-rivien runtime-diagnostiikka + kuvaajat.
- Mahdolliset riskit / huomiot: testing/tracing-efektit raportoidaan viela placeholderina `unsupported_effects`; ne eivat viela vaikuta OpenABM-ajoon.
