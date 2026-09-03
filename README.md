# Energy Security Data Warehouse

Data warehouse analitico per lo studio congiunto della sicurezza energetica
europea e del rischio geopolitico. Il progetto integra il Geopolitical Risk
Index (GPR) e dataset Eurostat relativi a dipendenza dalle importazioni, prezzi
dell'energia e scorte petrolifere di emergenza.

## Contenuto del repository

```text
docs/
├── proposal/                    proposta approvata
├── data-sources/                fonti, metadati e criteri di trasformazione
├── modeling/dfm/                quattro DFM definitivi in PNG
├── modeling/star-schema/        quattro Star Schema definitivi in PNG
└── results/                     CSV e figure per la presentazione

data/raw/                        sorgenti locali (non versionate)
src/profiling/                   analisi esplorativa delle sorgenti
src/etl/                         script Python di caricamento
sql/schema/                      DDL definitivo e verifiche
sql/queries/                     query OLAP base e avanzate
scripts/run_etl.ps1              esecuzione ordinata degli ETL
requirements.txt                 dipendenze Python per i grafici
```

## Architettura

Il modello è una costellazione di quattro fact table, ciascuna mantenuta alla
granularità nativa della fonte:

- `FACT_GPR`: indicatori GPR mensili;
- `FACT_IMPORT_DEPENDENCY`: dipendenza energetica annuale;
- `FACT_ENERGY_PRICE`: prezzi dell'energia semestrali;
- `FACT_OIL_STOCKS`: scorte petrolifere mensili espresse in giorni equivalenti.

Le dimensioni temporali sono separate in `DT_MONTH`, `DT_SEMESTER` e `DT_YEAR`.
`DIM_GEO_ENTITY` è condivisa dai processi e
`BR_GEO_EU_MEMBERSHIP` rappresenta l'appartenenza storica all'Unione Europea.
I diagrammi DFM e Star Schema sono disponibili in `docs/modeling/`.

Le misure di rischio, dipendenza e prezzo sono non additive: vengono aggregate
solo in contesti omogenei con `AVG`, `MIN` o `MAX`. Le scorte sono level measure
e non vengono sommate nel tempo. I flag Eurostat sono conservati come attributi
descrittivi nullable.

## Esecuzione del data warehouse

Il caricamento definitivo è idempotente e non richiede migrazioni intermedie.
Su un database PostgreSQL vuoto:

1. eseguire `sql/schema/create_dw_schema.sql`;
2. predisporre le sorgenti nella struttura `data/raw/` descritta in
   `docs/data-sources/README.md`;
3. eseguire `scripts/run_etl.ps1`, che carica automaticamente dimensioni e
   fact nell'ordine corretto;
4. eseguire `sql/schema/verify_final_dw.sql` per i controlli di qualità;
5. eseguire le query contenute in `sql/queries/`.

Le connessioni PostgreSQL usano le variabili d'ambiente standard (`PGHOST`,
`PGPORT`, `PGDATABASE`, `PGUSER`, `PGPASSWORD` o `PGPASSFILE`). Le password e i
database locali non fanno parte del repository.

## Query analitiche

`01_olap_business_queries.sql` contiene:

1. correlazione Pearson tra GPR globale e prezzi elettrici;
2. media mobile a tre mesi delle scorte;
3. dipendenza dalle importazioni e prezzi del gas;
4. confronto annuale delle metriche per i membri UE effettivi.

`02_advanced_olap_queries.sql` contiene:

5. shock geopolitico 2022 e variazione dei prezzi del gas;
6. ranking e percentile della dipendenza energetica nel 2024;
7. autonomia annuale delle scorte petrolifere nel periodo 2020–2025.

I risultati esportati sono disponibili in `docs/results/`. Le correlazioni e le
variazioni temporali descrivono associazioni osservate e non costituiscono
dimostrazioni di causalità.

## Grafici

Le figure utilizzate per la presentazione vengono generate dai CSV con:

```powershell
python src/visualization/create_presentation_charts.py
```

Lo script salva sei PNG in `docs/results/figures/`. La selezione dei grafici e
delle righe più significative è descritta in
`docs/results/presentation_selection.md`. Le dipendenze necessarie sono
elencate in `requirements.txt`.

## Risultati del caricamento validato

La versione verificata produce 499 righe GPR, 17.316 righe di dipendenza dalle
importazioni, 314.671 righe di prezzi energetici e 15.103 righe di scorte
petrolifere. I controlli definiti in `verify_final_dw.sql` verificano conteggi,
unicità delle chiavi naturali e assenza di orfani dimensionali.

## Fonti

Le fonti ufficiali, i collegamenti ai dataset Eurostat, i metadati SDMX, le
frequenze e le trasformazioni applicate sono documentati in
`docs/data-sources/README.md`.
