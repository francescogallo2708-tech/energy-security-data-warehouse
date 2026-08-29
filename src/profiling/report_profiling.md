# Report di Profiling Preliminare dei Dataset
**Progetto:** Data Warehouse per l'analisi della sicurezza energetica europea e del rischio geopolitico  
**Data:** 29 agosto 2026  
**Stato:** Completata la validazione strutturale e il tracciamento dei formati sorgente.

---

## 1. Introduzione e Obiettivi
Questo documento raccoglie le evidenze emerse durante la fase di data profiling dei dataset grezzi acquisiti (`Dataset/raw/`). L'obiettivo è validare la struttura formale, identificare le criticità di formattazione (es. separatori complessi, formati wide/long) e definire le regole di trasformazione necessarie per la successiva fase di ETL (Extract, Transform, Load) verso le tabelle di staging e le dimensioni del Data Warehouse.

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