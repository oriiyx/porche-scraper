# Porsche Inter Auto scraper

Dockeriziran indeks trenutno razpoložljivih vozil s PostgreSQL bazo in read-only FastAPI API-jem. Scraper najprej prebere vseh 48 (oziroma trenutno število) strani listinga, nato podrobnosti novih vozil obdeluje vzporedno. Obstoječi URL-ji se privzeto ne odpirajo ponovno; samo označijo se kot še vedno razpoložljivi.

## Zagon na macOS

Potrebujete samo Docker Desktop.

```bash
cp .env.example .env
docker compose up -d db api
docker compose --profile tools run --rm scraper
```

API in interaktivna dokumentacija sta nato na:

- `http://localhost:8000/` — spletni pregled in filtriranje vozil
- `http://localhost:8000/docs`
- `http://localhost:8000/vehicles`
- `http://localhost:8000/facets`

Ponoven navaden zagon ignorira že shranjena vozila:

```bash
docker compose --profile tools run --rm scraper
```

Popolna osvežitev vseh obstoječih zapisov:

```bash
docker compose --profile tools run --rm scraper --overwrite
```

Hiter test s prvimi petimi vozili:

```bash
docker compose --profile tools run --rm scraper --limit 5
```

## Slike

Privzeto se v tabelo `vehicle_images` shranijo vsi HD URL-ji slik. To je za frontend najhitrejše in ne porabi več deset GB diska. Če želite tudi lokalne kopije v trajnem Docker volume-u:

```bash
docker compose --profile tools run --rm scraper --overwrite --download-images
```

Lokalna pot se shrani v `local_path`, API pa volume objavi pod `/media/`. URL sestavite kot `http://localhost:8000/media/{local_path}`.

## Primer filtra

Vlečna kljuka, manj kot 100.000 km, dizel, ročni menjalnik in natanko 110 kW:

```text
GET http://localhost:8000/vehicles?has_tow_hitch=true&max_mileage_km=100000&fuel=dizel&transmission_type=manual&power_kw=110
```

Poljubno opremo lahko zahtevate z enim ali več parametri, na primer:

```text
/vehicles?equipment=ogrevani%20sedeži&equipment=parkirni%20senzor
```

Uporabni filtri: `brand`, `model`, `body_type`, `fuel`, `transmission_type`, razpon kilometrine, moči in redne cene, `min_boot_liters`, `min_rear_space_rating`, `has_tow_hitch`, `warranty_available`, poljubna `equipment`, razvrščanje in paginacija. Za več znamk ponovite parameter, na primer `?brand=Audi&brand=Volkswagen`. API privzeto vrne samo trenutno razpoložljiva vozila.

## Podatkovni model

- `vehicles`: indeksirana polja za filtre, URL oglasa kot unikatni ključ, redna/finančna cena, jamstvo, lokacija, VIN in status razpoložljivosti.
- `vehicle_images`: HD URL, vrstni red in neobvezna lokalna kopija.
- `vehicle_equipment`: ena vrstica na kos opreme, kategorija ter normalizirano ime brez šumnikov za iskanje.
- `vehicle_spec_profiles`: ročno preverjeni seed profili po modelu, generaciji, karoseriji in letniku; vsebujejo prostornino in mere prtljažnika, zadnji prostor, ISOFIX ter Euro NCAP.
- `vehicle_consumption_profiles`: ločeni profili porabe po modelu, letniku, gorivu, moči in po potrebi menjalniku. API izbere najbolj specifičen profil in vrne tudi merilni standard ter URL vira. Obstoječa vozila se z obema profiloma povežejo dinamično in se ne spreminjajo.

Po uspešnem celotnem zajemu se prej shranjena vozila, ki jih ni več na listingu `status:1`, označijo z `is_available=false`; ne izbrišejo se. Če zajem podrobnosti odpove ali uporabite `--limit`, scraper zaradi varnosti ne deaktivira drugih zapisov.

## Nastavitve obremenitve

V `.env` sta privzeto `SCRAPER_CONCURRENCY=8` za vozila in `SCRAPER_PAGE_CONCURRENCY=4` za strani listinga. Vsaka zahteva ima naključen 150–450 ms zamik, omejitev sočasnosti in tri poskuse z eksponentnim čakanjem. Vrednosti lahko znižate, če strežnik začne vračati HTTP 429.
