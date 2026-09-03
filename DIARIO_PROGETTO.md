# Diario di progetto — Energy Security Data Warehouse

**Ultimo aggiornamento:** 3 settembre 2026  
**Stato:** workflow SQL/Python e query OLAP validati su database PostgreSQL di test; documentazione e risultati in fase di consolidamento.

Questo diario è il runbook interno per ricreare localmente il progetto. Le sorgenti sotto `data/raw/` devono essere procurate separatamente e non devono essere modificate.

## 1. Struttura finale e decisioni di modello

Il progetto usa una costellazione di quattro fatti alla granularità nativa:

- `FACT_GPR`: GPR mensile, con le serie globali implementate;
- `FACT_IMPORT_DEPENDENCY`: dipendenza energetica annuale;
- `FACT_ENERGY_PRICE`: prezzi semestrali di gas ed elettricità;
- `FACT_OIL_STOCKS`: scorte mensili in giorni equivalenti.

Le dimensioni temporali sono separate (`DT_MONTH`, `DT_SEMESTER`, `DT_YEAR`). `DIM_GEO_ENTITY` contiene Paesi, aggregati Eurostat e `GLOBAL`; la tabella ponte `BR_GEO_EU_MEMBERSHIP` conserva l'appartenenza UE anno per anno.

Decisioni importanti:

- i fatti mantengono la frequenza della fonte, senza forzare una dimensione temporale unica;
- rischio, dipendenza e prezzi sono unit measure: niente `SUM`, ma `AVG`, `MIN` o `MAX` in contesti omogenei;
- gli stock sono level measure e non sono additivi nel tempo;
- valuta e unità energetica restano attributi distinti di `DT_PRICE_UNIT`;
- i flag Eurostat sono attributi descrittivi nullable nelle fact interessate;
- i codici metodo delle scorte (`STK_EUE_DNY_MTH`, `STK_EUE_MIN_MTH`, `STK_EUE_MTH`) sono esclusi perché categorici e non misure quantitative;
- le sorgenti GPR e Eurostat sono trasformate da wide a long e deduplicate alla grana naturale prima del caricamento;
- tutti gli ETL sono idempotenti tramite upsert e possono essere rieseguiti.

## 2. Esecuzione locale da database vuoto

### 2.1 Preparazione PowerShell

Dalla radice del repository impostare i parametri della propria installazione:

```powershell
Set-Location "C:\percorso\energy-security-data-warehouse-main"
$env:PGHOST = "localhost"
$env:PGPORT = "5432"
$env:PGDATABASE = "energy_gpr_dw"
$env:PGUSER = "postgres"
# Impostare PGPassword oppure usare PGPassFile, se richiesto dall'installazione.
```

Le sorgenti richieste sono:

```text
data/raw/gpr/data_gpr_export_202608.xls
data/raw/eurostat/nrg_ind_id_tabular.tsv
data/raw/eurostat/nrg_pc_202_tabular.tsv
data/raw/eurostat/nrg_pc_203_tabular.tsv
data/raw/eurostat/nrg_pc_204_tabular.tsv
data/raw/eurostat/nrg_pc_205_tabular.tsv
data/raw/eurostat/nrg_stk_oem_tabular.tsv
```

Se i file si trovano altrove, usare le variabili opzionali supportate dagli ETL: `GPR_SOURCE_FILE`, `IMPORT_DEPENDENCY_TSV`, `ENERGY_PRICES_DIR` e `OIL_STOCKS_TSV`.

### 2.2 DDL

Su un database vuoto eseguire una sola volta `sql/schema/create_dw_schema.sql` in pgAdmin (oppure con `psql -v ON_ERROR_STOP=1`). Non eseguire vecchie migrazioni: non fanno parte del workflow finale.

### 2.3 Caricamento ETL

Il comando unico esegue gli script nel seguente ordine:

```text
1. etl_load_time.py
2. etl_load_geo.py
3. etl_load_bridge_eu.py
4. etl_load_gpr.py
5. etl_load_import_dep.py
6. etl_load_energy_prices.py
7. etl_load_oil_stocks.py
```

Da PowerShell:

```powershell
.\scripts\run_etl.ps1 -Database $env:PGDATABASE -Port $env:PGPORT
```

Lo script interrompe il processo al primo errore. Non eseguire manualmente script di correzione dopo il caricamento: il DDL e gli ETL sono già la versione definitiva.

### 2.4 Verifica

In pgAdmin eseguire `sql/schema/verify_final_dw.sql`. La versione validata ha prodotto:

| Tabella | Righe | Copertura |
|-|-:|-|
| `FACT_GPR` | 499 | 1985-01–2026-07 |
| `FACT_IMPORT_DEPENDENCY` | 17.316 | 1990–2024 |
| `FACT_ENERGY_PRICE` | 314.671 | 2007-S1–2025-S2 |
| `FACT_OIL_STOCKS` | 15.103 | 2013-01–2026-06 |

I controlli validati hanno restituito zero duplicati sulle chiavi naturali e zero chiavi dimensionali orfane. Una seconda esecuzione non deve aumentare i conteggi.

## 3. Query OLAP definitive e ordine di esecuzione

Eseguire le query dopo il caricamento e la verifica del database.

### `sql/queries/01_olap_business_queries.sql`

1. Correlazione Pearson tra GPR globale annuale e prezzo elettrico annuale;
2. media mobile a tre mesi delle scorte per Italia, Germania, Francia e Spagna;
3. dipendenza dalle importazioni e prezzi gas household/non-household;
4. confronto annuale di dipendenza e prezzo elettrico per i membri UE effettivi (solo 2007–2024, anni con entrambe le metriche).

### `sql/queries/02_advanced_olap_queries.sql`

5. shock geopolitico 2022: GPR globale e variazione annua del prezzo gas;
6. ranking `DENSE_RANK` e percentile della dipendenza nel 2024;
7. media, minimo e massimo annuale dei giorni equivalenti delle scorte nel periodo completo 2020–2025 (il 2026 parziale è escluso).

## 4. Risultati CSV

I risultati esportati delle sette query sono conservati in `docs/results/` con questi nomi:

```text
results_prima_query.csv
results_seconda_query.csv
results_terza_query.csv
results_quarta_query.csv
results_quinta_query.csv
results_sesta_query.csv
results_settima_query.csv
```

I CSV sono output analitici, non input per gli ETL. Se una fonte viene aggiornata, rigenerare i risultati dopo il caricamento e registrare la nuova copertura nel diario.

## 5. Grafici e selezione per la presentazione

È stato creato `src/visualization/create_presentation_charts.py`, che legge i
sette CSV finali e genera sei figure PNG in `docs/results/figures/`:

```powershell
python src/visualization/create_presentation_charts.py
```

Le dipendenze Python sono indicate in `requirements.txt` (`pandas` e
`matplotlib`). La selezione consigliata dei grafici e delle righe da riportare
nelle slide è in `docs/results/presentation_selection.md`.

La selezione principale comprende andamento UE 2007–2024, shock del gas nel
2022, ranking della dipendenza 2024, autonomia delle scorte 2025 e una tabella
di dettaglio sull'Italia. Le figure sono derivate dai risultati SQL e non
introducono valori aggiuntivi.

## 6. Esiti e note sulle query

- Query 1: le serie mensile GPR e semestrale dei prezzi vengono aggregate separatamente prima del join; la correlazione non dimostra causalità.
- Query 2: la media mobile usa le ultime tre osservazioni mensili per Paese e indicatore.
- Query 3: le fact vengono aggregate separatamente per evitare il prodotto tra anni e semestri; le fasce gas D2 e I3 sono contesti distinti.
- Query 4: la tabella ponte applica l'appartenenza UE storica; il passaggio da 28 a 27 Paesi nel 2020 è coerente con la Brexit.
- Query 5: il 2021 ha variazione `NULL` perché manca l'anno precedente nella finestra; prezzi precedenti pari a zero producono correttamente `NULL`.
- Query 6: l'indicatore Eurostat può assumere valori negativi, quindi non va interpretato come percentuale necessariamente compresa tra 0 e 100.
- Query 7: zeri e differenze nel numero di Paesi riflettono i valori e la copertura pubblicati dalla fonte; non vengono sostituiti automaticamente.

## 7. Cronologia sintetica

- **25–27 agosto 2026:** validazione della proposta, profiling delle fonti, revisione DFM e Star Schema, separazione delle granularità temporali, dimensione geografica conforme e ponte UE.
- **29–30 agosto 2026:** sviluppo e correzione degli ETL, completamento della grana dei prezzi con valuta/unità, gestione dei flag, mapping geografico, caricamento dei quattro fatti e verifica di idempotenza.
- **3 settembre 2026:** eliminazione delle migrazioni dal workflow, creazione dello script ETL unico, aggiornamento del DDL e dei controlli, revisione delle sette query OLAP e validazione dei rispettivi CSV.

## 8. Prossimi passi

1. Integrare nelle slide le figure e le righe selezionate, indicando sempre periodo, unità e filtri.
2. Eseguire un ultimo controllo dei file da consegnare e del workflow già validato.
3. Non inserire nelle slide tutte le righe dei CSV: usare i risultati completi come allegato riproducibile.
