# Report di Profiling Preliminare dei Dataset
**Progetto:** Data Warehouse per l'analisi della sicurezza energetica europea e del rischio geopolitico  
**Data:** 30 agosto 2026
**Stato:** Completata la validazione strutturale e la riconciliazione delle fact table caricate; corretta la grana unità-valuta dei prezzi, resta da completare il mapping geografico.

---

## 1. Introduzione e Obiettivi
Questo documento raccoglie le evidenze emerse durante la fase di data profiling dei dataset grezzi acquisiti (`data/raw/`). L'obiettivo è validare la struttura formale, identificare le criticità di formattazione (es. separatori complessi, formati wide/long) e definire le regole di trasformazione necessarie per la successiva fase di ETL (Extract, Transform, Load) verso le tabelle di staging e le dimensioni del Data Warehouse.

---

## 2. Sintesi dei Dataset Analizzati

| Fonte / Dominio | Nome File | Formato | Dimensioni Rilevate | Copertura Temporale | Note Strutturali / Criticità |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Import Dependency** | `nrg_ind_id_tabular.tsv` | TSV (Eurostat) | 533 righe, 36 colonne | 1990 - 2024 | Formato *wide*: prima colonna mista (`freq,siec,unit,geo`), anni disposti sulle colonne successive con separatore a tabulazione (`\t`). |
| **Gas Prices (Household)** | `nrg_pc_202_tabular.tsv` | TSV (Eurostat) | 2.268 righe, 39 colonne | 2007-S1 - 2025-S2 | Formato *wide* semestrale. Prima colonna mista (`freq,siec,nrg_cons,unit,tax,currency,geo`). |
| **Gas Prices (Non-House.)** | `nrg_pc_203_tabular.tsv` | TSV (Eurostat) | 4.104 righe, 39 colonne | 2007-S1 - 2025-S2 | Formato *wide* semestrale con medesima struttura della famiglia prezzi. |
| **Electricity Prices (House.)**| `nrg_pc_204_tabular.tsv` | TSV (Eurostat) | 2.196 righe, 39 colonne | 2007-S1 - 2025-S2 | Formato *wide* semestrale. |
| **Electricity Prices (Non-House.)**| `nrg_pc_205_tabular.tsv` | TSV (Eurostat) | 2.895 righe, 39 colonne | 2007-S1 - 2025-S2 | Formato *wide* semestrale. |
| **Emergency Oil Stocks** | `nrg_stk_oem_tabular.tsv` | TSV (Eurostat) | 223 righe, 163 colonne | 2013-01 - 2026-06 | Formato *wide* mensile. Prima colonna: `freq,stk_flow,unit,geo`. |
| **Geopolitical Risk (GPR)** | `data_gpr_export_202608.xls` | Excel (Tabulare) | 1.519 righe, 115 colonne | 1900-01 - 2026-07 | Formato tabulare classico. Colonne ben distinte (es. `month`, `GPR`, `GPRT`, ecc.). Presenza di valori nulli storici nativi. |

---

## 3. Risultanze Principali e Specificità Tecniche

### A. Famiglia Dataset Eurostat (`.tsv`)
* **Struttura delle Chiavi Naturali:** Le dimensioni non si trovano su colonne separate, bensì concatenate in un'unica stringa iniziale divisa da virgole (es. `A,G3000,PC_IMP,IT`). L'ETL richiederà una fase di string splitting mirata (`.str.split(',')`).
* **Orientamento Temporale (*Wide to Long*):** I periodi temporali (anni, semestri o mesi) costituiscono le intestazioni delle colonne a destra della prima. È obbligatorio applicare un'operazione di `melt` (pivot inverso) per convertire la struttura da orizzontale a verticale, rendendola compatibile con le Fact Table del Data Warehouse.
* **Valori Mancanti e Flag:** I valori nulli o non disponibili non sono lasciati a celle vuote standard, ma codificati tramite stringhe testuali (es. `": "`) o accompagnati da flag statistici ufficiali Eurostat che andranno intercettati e salvati negli attributi descrittivi dedicati.

### B. Dataset Geopolitical Risk (`.xls`)
* **Pulizia e Normalizzazione:** Il file Excel è strutturato correttamente in formato tabulare. La coordinata temporale principale è rappresentata dalla colonna `month`.
* **Nulli Storici:** Il profiling ha rilevato oltre 55.000 celle a valore nullo complessivo, concentratie principalmente nelle serie storiche più remote (inizi del '900) o in indicatori specifici/nazionali non calcolati per tutti i periodi. Tale comportamento è del tutto fisiologico e gestibile a livello di caricamento.

---

## 4. Indicazioni per le Fasi Successive (ETL e Staging)
1. **Creazione Staging Area:** Implementare tabelle di staging intermedie che rispecchino fedelmente i file raw grezzi, evitando blocchi in fase di lettura.
2. **Normalizzazione Geografica:** Prima di popolare le Fact Table, sarà indispensabile completare la tabella di mapping comune per risolvere disallineamenti di codifica (es. codici a 2 caratteri Eurostat vs codici ISO o GPR).
3. **Popolamento Dimensioni:** Procedere rigorosamente al caricamento preventivo delle dimensioni temporali (`DT_MONTH`, `DT_SEMESTER`, `DT_YEAR`), geografiche (`DT_GEO_ENTITY`) e di dominio (`DT_PRICE_UNIT`, `DT_RISK_SERIES`) prima di alimentare le tabelle dei fatti.

---

## 5. Riconciliazione delle fact table del 30 agosto 2026

La riconciliazione è stata eseguita confrontando a livello di chiave e valore le sorgenti trasformate con le righe presenti in PostgreSQL (`energy_gpr_dw`, istanza locale di lavoro sulla porta 5433). Sono stati inoltre controllati duplicati, null, copertura temporale, integrità referenziale, geografie escluse e flag Eurostat.

### 5.1 Sintesi del confronto database-ETL

| Fact table | Righe attese dalla logica ETL | Righe DB | Chiavi mancanti | Chiavi extra | Valori differenti | Orfani dimensionali |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| `FACT_GPR` | 1.519 | 1.519 | 0 | 0 | 0 | 0 |
| `FACT_IMPORT_DEPENDENCY` | 16.016 | 16.016 | 0 | 0 | 0 | 0 |
| `FACT_ENERGY_PRICE` | 290.620 | 290.620 | 0 | 0 | 0 | 0 |

Le tre tabelle corrispondono esattamente alla logica implementata negli ETL. Questa corrispondenza tecnica, tuttavia, non implica una copertura completa delle sorgenti: i controlli successivi evidenziano scarti geografici e dimensionali.

### 5.2 Geopolitical Risk

* Grana verificata: una riga per `month_sk` e riga geografica `GLOBAL`.
* Copertura continua: `1900-01`--`2026-07`.
* Duplicati sulla chiave: 0.
* Le misure `gpr_val`, `gprt_val` e `gpra_val` coincidono con la fonte dopo l'arrotondamento previsto dal tipo `NUMERIC(10,4)`.
* I null coincidono con la fonte: 1.020 per ciascuna delle tre misure, relativi alla parte storica in cui gli indici recenti non sono disponibili.

**Limite di copertura:** il file contiene 115 colonne, ma l'implementazione corrente carica soltanto `month`, `GPR`, `GPRT` e `GPRA`. Le serie storiche alternative e nazionali (`GPRH`, `GPRC_*`, `GPRHC_*`, ecc.) non sono ancora rappresentate nella fact table. Occorre decidere esplicitamente se la prima versione del DW resta limitata ai tre indici globali oppure se implementare `DT_RISK_SERIES` e il caricamento *wide-to-long* delle altre serie.

### 5.3 Import Dependency

* Osservazioni numeriche nella fonte: 17.316.
* Osservazioni caricate e perfettamente riconciliate: 16.016.
* Copertura caricata: 1990--2024, 37 entità geografiche.
* Duplicati sulla chiave naturale: 0.
* Valori differenti tra sorgente trasformata e database: 0.
* Osservazioni caricate accompagnate da flag Eurostat: 0.

Sono escluse 1.300 osservazioni numeriche perché i relativi codici non sono ancora presenti in `DIM_GEO_ENTITY`:

| Codice | Righe escluse |
| :--- | ---: |
| `BA` | 143 |
| `IS` | 455 |
| `UA` | 403 |
| `XK` | 299 |

Queste righe non devono essere considerate errori di parsing: richiedono l'estensione e la validazione del mapping geografico comune.

### 5.4 Energy Prices

| Dataset | Valori numerici | Esclusi per geografia | Chiavi naturali complete mappate | Righe caricate | Righe mappate con flag |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| Gas Household (`nrg_pc_202`) | 60.526 | 4.740 | 55.786 | 55.786 | 936 |
| Gas Non-Household (`nrg_pc_203`) | 109.038 | 7.578 | 101.460 | 101.460 | 1.854 |
| Electricity Household (`nrg_pc_204`) | 65.466 | 6.105 | 59.361 | 59.361 | 1.380 |
| Electricity Non-Household (`nrg_pc_205`) | 79.641 | 5.628 | 74.013 | 74.013 | 1.278 |
| **Totale** | **314.671** | **24.051** | **290.620** | **290.620** | **5.448** |

Le 290.620 osservazioni mappate sono univoche usando la chiave naturale completa della fonte, che comprende `currency`. L'anomalia iniziale è stata corretta introducendo `DT_PRICE_UNIT`, con chiave univoca sulla coppia `energy_unit_code`/`currency_code`, e usando `price_unit_sk` nella grana della fact table.

La nuova fact contiene 99.601 righe `EUR`, 95.949 `NAC` e 95.070 `PPS`. Sono presenti sei combinazioni unità-valuta: `GJ_GCV` e `KWH`, ciascuna associata a `EUR`, `NAC` e `PPS`. Tutti i 5.448 flag Eurostat della parte mappata sono stati conservati senza differenze rispetto alla fonte.

Sono inoltre escluse 24.051 osservazioni associate ai codici geografici `BA`, `EA`, `IS`, `LI`, `UA` e `XK`. `EA` è un aggregato temporale generico e non deve essere automaticamente assimilato a `EA20` senza una regola esplicita.

**Esito:** `FACT_ENERGY_PRICE` è ora completamente riconciliata per tutte le geografie già mappate: 0 chiavi mancanti, 0 chiavi extra, 0 differenze di valore, 0 differenze nei flag e 0 orfani dimensionali. Restano da estendere il mapping per i paesi mancanti e da definire esplicitamente il trattamento dell'aggregato `EA`. `price_comparability_flag` resta `NULL` finché non sarà definita una regola derivata verificabile.

### 5.5 Valutazione conclusiva

* `FACT_GPR`: riconciliata per le tre misure globali implementate; resta aperta la decisione sulle serie nazionali e storiche.
* `FACT_IMPORT_DEPENDENCY`: valori caricati riconciliati; caricamento ancora incompleto per quattro codici geografici.
* `FACT_ENERGY_PRICE`: grana unità-valuta corretta e 290.620 righe riconciliate; restano soltanto gli scarti geografici da risolvere.
* `FACT_OIL_STOCKS`: già riconciliata separatamente con 28.247 righe, nessun duplicato e nessun orfano dimensionale.
