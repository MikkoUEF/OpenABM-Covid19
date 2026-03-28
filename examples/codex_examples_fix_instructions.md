# Codex-ohje VS Code SSH -ympäristöön: examples-hakemiston skriptien korjaus ja testaus

## Tavoite

Käy läpi `OpenABM-Covid19/examples`-hakemiston Python-skriptit ja notebookit, korjaa ne nykyisessä CSC + VS Code Remote SSH -ympäristössä toimiviksi ja testaa ne yksi kerrallaan. Tee vain sellaisia muutoksia, jotka ovat välttämättömiä yhteensopivuuden kannalta. Älä muuta simulaatiologiikkaa, ellei se ole pakollista ajon onnistumiseksi.

## Ympäristö

Projektin juuri:
`/home/ubuntu/OpenABM-Covid19`

Virtuaaliympäristö:
`/home/ubuntu/OpenABM-Covid19/venv`

Ennen testejä varmista, että käytössä on tämä ympäristö:

```bash
cd /home/ubuntu/OpenABM-Covid19
source venv/bin/activate
export PYTHONPATH=$PYTHONPATH:$(pwd)/src
```

## Tärkeät periaatteet

1. Älä koske simulaatioytimen C-koodiin, ellei jokin esimerkki aivan varmasti vaadi sitä.
2. Säilytä alkuperäinen logiikka. Korjaa vain yhteensopivuusongelmat.
3. Muokkaa tiedostoja suoraan examples-kansiossa ja tarvittaessa `examples/plotting.py`:ssä.
4. Tee muutokset yksi tiedosto kerrallaan, mutta pidä kirjaa siitä mitä korjasit.
5. Testaa heti jokaisen muutoksen jälkeen.
6. Jos notebook ei toimi VS Codessa import-polkujen takia, lisää alkuun vain tämä minimikorjaus:

```python
import sys, os
sys.path.append(os.path.abspath("../src"))
```

## Yleiset tunnetut korjaukset

### Pandas
- Vaihda set-indexer listaksi:
  - väärin: `df.loc[:, {"a","b"}]`
  - oikein: `df.loc[:, ["a","b"]]`

- Korvaa poistunut `DataFrame.append(...)`:
  - käytä `pd.concat([...], ignore_index=True)`

### Pandas Styler
- `hide_index()` → `hide(axis="index")`
- `set_precision(n)` → `format(precision=n)`

### Matplotlib
- `tick.label` → `tick.label1`

### Tick/label mismatch histogrammeissa
Jos virhe sanoo että tickien määrä ei vastaa labelien määrää, korjaa `plotting.py`:ssä tick-riviltä yleensä bin-reunat luokkakeskipisteiksi tai poista viimeinen reuna, esimerkiksi:
- `bins` → `bins[:-1]`
- `bin_list` → `bin_list[:-1]`

Älä muuta datan merkitystä, vain visualisoinnin yhteensopivuutta.

### Numpy
- `np.bool` → `bool`

## Testausjärjestys

Käy läpi ainakin nämä:

1. `example_101.ipynb`
2. `example_102.ipynb`
3. `example_extended_output.ipynb`
4. muut `examples`-hakemiston `.py` ja `.ipynb` tiedostot

## Testauskäytäntö

### Python-skriptit
Aja projektin juuresta:

```bash
cd /home/ubuntu/OpenABM-Covid19
source venv/bin/activate
export PYTHONPATH=$PYTHONPATH:$(pwd)/src
python examples/TIEDOSTO.py
```

### Notebookit
- Avaa notebook VS Codessa
- valitse kerneliksi `/home/ubuntu/OpenABM-Covid19/venv/bin/python`
- aja ylhäältä alas
- korjaa vain todellinen virhekohta

## Korjausten kirjaaminen

Pidä jokaisesta tiedostosta lyhyt muistiinpano:
- mikä tiedosto
- mikä virhe
- mikä korjaus tehtiin
- menikö testi läpi

Muistiinpanomuoto voi olla esimerkiksi:

```text
example_101.ipynb
- added sys.path to ../src
- replaced set indexer with list
- test passed in VS Code notebook
```

## Git-käytäntö

Kun yksi tiedosto tai pieni looginen kokonaisuus toimii:

```bash
git add <tiedostot>
git commit -m "Fix compatibility for example_101 notebook"
git push
```

Älä commitoi:
- `venv/`
- build-artifakteja
- generoituja `.so`-tiedostoja
- muita väliaikaistiedostoja

## Jos jokin esimerkki vaatii suuremman muutoksen

Jos näyttää siltä, että esimerkki edellyttää:
- ydinkoodin muutosta
- uuden parametrin lisäämistä
- SWIG/build-prosessin muuttamista

niin älä tee muutosta suoraan, vaan pysähdy ja kirjaa:
- mikä tiedosto
- mikä ominaisuus puuttuu
- miksi sitä ei voi ratkaista pelkällä Python/esimerkkikorjauksella

## Tavoite lopuksi

Lopputuloksena:
- `examples`-hakemiston esimerkit toimivat nykyisessä CSC-ympäristössä
- kaikki korjaukset on tehty minimaalisesti
- OpenABM:n julkaistu ydin säilyy koskemattomana
- muutokset ovat commitoitu GitHub-forkkiin pieninä järkevinä committeina
