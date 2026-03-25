# Codex-resepti: skenaario- ja parametrirajapinnan ensimmäinen toteutus OpenABM:n päälle

Huom: tee tämä työ vasta sen jälkeen, kun `examples/`-korjaukset on commitattu erikseen. Tätä muutosta ei pidä sekoittaa examples-korjauksiin.

## 1. Intro: mitä ollaan tekemässä

Tavoite on rakentaa ensimmäinen Python-rajapinta OpenABM:n päälle ilman ydinkoodin muuttamista.

OpenABM pidetään tässä vaiheessa laskentamoottorina sellaisenaan. Uusi työ tehdään Python-kerrokseen. Tarkoitus ei ole vielä toteuttaa kaikkea valmiiksi, vaan rakentaa ohut mutta siisti perusarkkitehtuuri, jonka päälle voidaan myöhemmin lisätä interventiot, skenaariot, verkkomääritykset, datarajapinnat, visualisointi ja käyttöliittymä.

Ensimmäinen tavoite on saada toimimaan tämä ketju:

1. määritellään parametrilohkoja
2. määritellään skenaario
3. määritellään aikajanan tapahtumia
4. ajetaan simulaatio askel kerrallaan
5. kerätään tulos yhteiseen aikasarjaformaattiin
6. verrataan tätä myöhemmin havaintodataan samalla tasolla

Rajaukset:

- ei muutoksia OpenABM:n ytimeen
- ei vielä oikeaa verkkojen generointia
- ei vielä GUI:ta
- ei vielä kalibrointia
- ei vielä hiipuvan immuniteetin ydintoteutusta

Periaate:

- `Scenario` on deklaratiivinen resepti
- `Runner` suorittaa reseptin
- `TimeSeries` on yhteinen tuloskieli simulaatiolle ja datalle

## 2. Hakemistorakenteen luonti

Luo projektin juureen uusi hakemisto:

```text
extensions/
```

Sen alle tämä rakenne:

```text
extensions/
  scenario_api/
    __init__.py
    blocks.py
    networks.py
    events.py
    scenarios.py
    resolver.py
    runner.py
    results.py
    data.py
  notebooks/
    scenario_api_smoke_test.ipynb
```

Tarkoitus tiedostoittain:

- `blocks.py`: parametrilohkot
- `networks.py`: verkkomääritysten kuvaus, ei vielä varsinaista generointia
- `events.py`: aikajanan tapahtumat
- `scenarios.py`: skenaarioluokka ja siihen liittyvät operaatiot
- `resolver.py`: skenaarion ratkaisu ajokelpoiseen muotoon
- `runner.py`: simulaation askelittainen suoritus ja eventtien soveltaminen
- `results.py`: tulosoliot ja aikasarjaformaatti
- `data.py`: havaintodatan abstraktio ja muunnos aikasarjaformaattiin
- `__init__.py`: vie ulos tärkeimmät luokat ja funktiot

## 3. Oliot

Toteuta nämä mieluiten `@dataclass`-rakenteina.

### `ParameterBlock`

Kentät:
- `name: str`
- `params: dict[str, object]`
- `metadata: dict[str, object] = {}`

Pelkkä dataolio. Ei saa tietää mitään OpenABM-instanssista.

### `NetworkSpec`

Kentät:
- `name: str`
- `kind: str`
- `config: dict[str, object]`
- `metadata: dict[str, object] = {}`

Kuvaa mitä verkkoa käytetään, ei vielä generoi sitä.

### `TimelineEvent`

Kentät:
- `time: int`
- `action: str`
- `target: str`
- `value: object`
- `event_type: str = "soft"`
- `metadata: dict[str, object] = {}`

Tuki vähintään:
- `set`
- `scale`

Rakenna valmius myös `hard`-eventeille, vaikka niiden täyttä logiikkaa ei vielä tehdä.

### `Scenario`

Kentät:
- `name: str`
- `base_params: dict[str, object]`
- `blocks: list[ParameterBlock]`
- `network_specs: list[NetworkSpec]`
- `events: list[TimelineEvent]`
- `parent: str | None = None`
- `metadata: dict[str, object] = {}`

Deklaratiivinen resepti, ei simulaatio.

### `ResolvedScenario`

Kentät:
- `name: str`
- `resolved_params: dict[str, object]`
- `network_specs: list[NetworkSpec]`
- `events_by_time: dict[int, list[TimelineEvent]]`
- `metadata: dict[str, object] = {}`

Ajokelpoinen versio skenaariosta.

### `TimeSeries`

Kentät:
- `name: str`
- `times: list[int]`
- `values: list[float]`
- `variable: str`
- `source_type: str`
- `source_name: str`
- `metadata: dict[str, object] = {}`

Yksi muuttuja per aikasarja riittää tässä vaiheessa.

### `SimulationResult`

Kentät:
- `scenario_name: str`
- `raw_outputs: dict[str, list[float]]`
- `metadata: dict[str, object] = {}`

Simulaation tulosolio.

### `ObservedDataset`

Kentät:
- `name: str`
- `data: dict[str, list[float] | list[int]]`
- `metadata: dict[str, object] = {}`

Havaintodatan kuvaus.

## 4. Funktiorajapinta

### `blocks.py`

```python
create_block(name, params, metadata=None) -> ParameterBlock
merge_blocks(blocks) -> dict
```

Toiminta:
- `create_block`: validointi, luo `ParameterBlock`
- `merge_blocks`: yhdistää lohkot, myöhempi lohko yliajaa aiemman

### `networks.py`

```python
create_network_spec(name, kind, config, metadata=None) -> NetworkSpec
```

Toiminta:
- luo verkkomäärityksen
- tarkistaa että `config` on dict

### `events.py`

```python
create_event(time, action, target, value, event_type="soft", metadata=None) -> TimelineEvent
group_events_by_time(events) -> dict[int, list[TimelineEvent]]
```

Toiminta:
- `create_event`: validointi
- `group_events_by_time`: ryhmittely ajan mukaan

### `scenarios.py`

```python
create_scenario(name, base_params, blocks=None, network_specs=None, events=None, parent=None, metadata=None) -> Scenario
add_block(scenario, block) -> Scenario
add_event(scenario, event) -> Scenario
add_network_spec(scenario, network_spec) -> Scenario
```

### `resolver.py`

```python
resolve_scenario(scenario) -> ResolvedScenario
```

Toiminta:
- kopioi `base_params`
- yhdistää lohkot
- ryhmittelee eventit ajan mukaan
- palauttaa `ResolvedScenario`

Tässä vaiheessa ei tarvitse toteuttaa monimutkaista periytymistä.

### `runner.py`

```python
apply_event_to_params(current_params, event) -> dict
run_scenario(resolved_scenario, steps, model_factory=None, result_extractor=None) -> SimulationResult
```

`apply_event_to_params`:
- tukee vähintään `set` ja `scale`
- `scale` nostaa virheen, jos target puuttuu

`run_scenario`:
1. alustaa `current_params`
2. rakentaa mallin joko `model_factory`-funktion kautta tai käyttää dummy-ajotapaa
3. ajaa loopissa `t = 0 ... steps-1`
4. soveltaa eventit oikealla hetkellä
5. suorittaa yhden askeleen
6. kerää tulokset
7. palauttaa `SimulationResult`

Tärkeä vaatimus:
- notebookin pitää toimia myös ilman oikeaa OpenABM-ajuria

### `results.py`

```python
result_to_timeseries(result, variable) -> TimeSeries
align_timeseries(series_list) -> list[TimeSeries]
```

Ensimmäisessä versiossa `align_timeseries` voi palauttaa listan sellaisenaan.

### `data.py`

```python
load_observed_dataset(name, data, metadata=None) -> ObservedDataset
dataset_to_timeseries(dataset, variable, time_key="time") -> TimeSeries
```

Tässä vaiheessa ei tarvitse toteuttaa tiedostonlukua.

### `__init__.py`

Vie ulos ainakin kaikki ydinkäsitteet ja yllä olevat funktiot.

## 5. Jupyter notebook testiksi

Luo notebook:

```text
extensions/notebooks/scenario_api_smoke_test.ipynb
```

Notebookin sisältö:

### A. Importit
- tuo rajapinnan luokat ja funktiot
- varmista import-polku

### B. Parametrilohkot
Luo ainakin:
- varianttilohko, esim. `relative_transmission = 1.3`, `asymptomatic_fraction = 0.35`
- testauslohko, esim. `testing_rate = 0.2`

### C. Verkkomääritykset
Luo ainakin:
- household
- community

### D. Aikajanan tapahtumat
Luo ainakin:
- askel 10: `set relative_transmission = 0.9`
- askel 20: `scale testing_rate *= 1.5`

### E. Skenaario
Luo yksi `Scenario`, johon liitetään:
- `base_params`
- 2 blokkia
- 2 verkkomääritystä
- 2 eventtiä

Aja `resolve_scenario` ja tulosta tulos.

### F. Dummy-runner
Koska oikea OpenABM-integraatio voi olla kesken, tee notebookiin pieni dummy-malli tai käytä `run_scenario`-funktion sisäistä dummy-polkuja.

Dummy-logiikka saa olla yksinkertainen:
- yksi tila `cases`
- joka stepissä arvo kasvaa parametrin `relative_transmission` mukaan
- `testing_rate` vaikuttaa raportoitujen tapausten arvoon yksinkertaisella tavalla

Tarkoitus ei ole realismi vaan se, että:
- eventit vaihtuvat oikealla hetkellä
- runner toimii
- tulokset saadaan ulos

### G. Tulos aikasarjaksi
- muodosta `SimulationResult` -> `TimeSeries`
- piirrä yksinkertainen kuvaaja

### H. Havaintodata
Luo pieni keinotekoinen havaintodata:
- `time = [0, 1, ..., n]`
- `cases = [...]`

Muodosta `ObservedDataset` ja siitä `TimeSeries`.

### I. Vertailu
Piirrä samaan kuvaan:
- simuloitu aikasarja
- havaittu aikasarja

Tavoite:
- simulaatio ja data voidaan tuoda samalle tasolle
- rajapinnan ydin toimii

## 6. Toteutustyyli

Vaatimukset:
- käytä `dataclass`-rakenteita
- lisää type hintit
- pidä funktiot pieniä
- lisää lyhyet docstringit
- vältä ennenaikaista abstraktiota
- älä tuo mukaan vielä pandas-riippuvuutta, ellei notebook oikeasti sitä tarvitse
- pidä ensimmäinen versio luettavana ja debugattavana

## 7. Mitä ei tehdä tässä commitissa

Älä toteuta vielä:
- oikeaa verkkojen generointia
- hard-eventtien täyttä rebuild-logiikkaa
- laajaa OpenABM-spesifistä adapterikerrosta
- kalibrointia
- GUI:ta
- waning immunity -muutoksia ytimeen
- monimutkaista skenaarioperiytymistä

## 8. Minimikriteeri onnistumiselle

Tämän työn jälkeen pitäisi olla mahdollista:
1. luoda parametrilohkoja
2. luoda skenaario
3. lisätä tapahtumia aikajanalle
4. ratkaista skenaario ajokelpoiseksi muodoksi
5. ajaa se askelittain
6. saada tulos ulos aikasarjana
7. muuntaa myös havaintodata samaan formaattiin
8. piirtää molemmat samaan kuvaan notebookissa

Jos tämä toimii, ensimmäinen rajapinta on valmis jatkokehitystä varten.
