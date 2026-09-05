# Report finale di profiling e validazione

**Progetto:** Data Warehouse per l'analisi della sicurezza energetica europea e del rischio geopolitico  
**Data di riferimento:** 5 settembre 2026  
**Ambiente:** PostgreSQL locale di test, dopo l'esecuzione completa del workflow ETL finale.

## 1. Obiettivo e perimetro

Il profiling ha guidato la progettazione delle dimensioni, delle fact table e delle regole ETL. La validazione finale verifica che i file sorgente siano stati trasformati alla grana prevista, che le chiavi naturali non producano duplicati e che ogni riga caricata abbia riferimenti dimensionali validi.

Il workflow utilizza file raw Eurostat TSV e il file GPR XLS. I file wide vengono convertiti in long quando necessario; codici, flag Eurostat e mapping geografico sono risolti durante l'ETL.

## 2. Sorgenti utilizzate

| Dominio | File | Formato | Frequenza | Copertura utilizzata |
|---|---|---|---|---|
| Import dependency | `nrg_ind_id_tabular.tsv` | TSV wide | annuale | 1990–2024 |
| Gas prices | `nrg_pc_202_tabular.tsv`, `nrg_pc_203_tabular.tsv` | TSV wide | semestrale | 2007-S1–2025-S2 |
| Electricity prices | `nrg_pc_204_tabular.tsv`, `nrg_pc_205_tabular.tsv` | TSV wide | semestrale | 2007-S1–2025-S2 |
| Emergency oil stocks | `nrg_stk_oem_tabular.tsv` | TSV wide | mensile | 2013-01–2026-06 |
| Geopolitical Risk | `data_gpr_export_202608.xls` | XLS tabulare | mensile | 1985-01–2026-07 nello scope caricato |

## 3. Risultati finali del caricamento

| Fact table | Grana logica | Righe caricate | Periodo caricato |
|---|---|---:|---|
| `FACT_GPR` | mese, entità geografica | 499 | 1985-01–2026-07 |
| `FACT_IMPORT_DEPENDENCY` | anno, entità geografica, prodotto energetico | 17.316 | 1990–2024 |
| `FACT_ENERGY_PRICE` | semestre, entità geografica, fascia, livello fiscale, unità-prezzo | 314.671 | 2007-S1–2025-S2 |
| `FACT_OIL_STOCKS` | mese, entità geografica, indicatore, unità di misura | 15.103 | 2013-01–2026-06 |

Le dimensioni temporali sono popolate per anni, semestri e mesi. La dimensione geografica contiene 46 entità e la tabella ponte UE contiene 1.191 relazioni storiche.

## 4. Regole di trasformazione

### Import dependency

Il file wide è stato convertito in osservazioni annuali. Le dimensioni `DT_YEAR`, `DIM_GEO_ENTITY` e `DT_ENERGY_PRODUCT` vengono risolte tramite le chiavi naturali della fonte. Il caricamento finale comprende 17.316 osservazioni quantitative.

### Energy price

I quattro file dei prezzi sono stati convertiti da wide a long. La grana comprende valuta e unità energetica attraverso `DT_PRICE_UNIT`, evitando di accorpare osservazioni con valuta diversa. Sono state popolate 25 fasce di consumo, 3 livelli fiscali e 6 combinazioni unità-valuta.

### Emergency oil stocks

Sono state mantenute le osservazioni quantitative coerenti con la fact table. 13.144 record categoriali relativi ai metodi di calcolo sono stati esclusi; 15.103 record sono stati caricati alla grana mensile prevista. `eurostat_flag` è conservato come attributo descrittivo. La colonna priva di semantica `compliance_status` è stata rimossa dal modello fisico e dall'ETL.

### Geopolitical Risk

Il file GPR contiene 1.519 righe sorgente. Sono state escluse 1.020 righe prive di valori per `GPR`, `GPRT` e `GPRA`; il caricamento finale riguarda 499 osservazioni della serie globale nello scope 1985-01–2026-07. Le serie nazionali e alternative presenti nel file non fanno parte della prima versione del DW.

## 5. Controlli di qualità

Sono stati eseguiti controlli su conteggi e periodi, duplicati sulle chiavi naturali, orfani dimensionali, chiavi temporali/geografiche e idempotenza degli ETL.

| Controllo | Risultato |
|---|---:|
| Duplicati `FACT_GPR` | 0 |
| Duplicati `FACT_IMPORT_DEPENDENCY` | 0 |
| Duplicati `FACT_ENERGY_PRICE` | 0 |
| Duplicati `FACT_OIL_STOCKS` | 0 |
| Orfani `FACT_IMPORT_DEPENDENCY` | 0 |
| Orfani `FACT_ENERGY_PRICE` | 0 |
| Orfani `FACT_OIL_STOCKS` | 0 |

I controlli confermano che le fact table rispettano la grana dichiarata e che ogni chiave esterna valorizzata trova la relativa dimensione. La grana di ogni fact table è inoltre applicata fisicamente mediante una chiave primaria composta dalle rispettive chiavi esterne.

## 6. Copertura e limiti

- Il GPR è limitato alle tre misure globali `GPR`, `GPRT` e `GPRA`.
- La copertura geografica dipende dal mapping comune e dalle entità pubblicate dalle fonti.
- Prezzi, tassi percentuali, indicatori GPR e giorni equivalenti non sono additivi: le analisi usano `AVG`, `MIN` e `MAX` alla grana appropriata.
- `BR_GEO_EU_MEMBERSHIP` è una tabella ponte per la membership UE storica, non una fact table con misure.
- Le tabelle di staging non sono presenti nel DDL finale: i file raw costituiscono l'area sorgente e gli ETL caricano direttamente le dimensioni e le fact table.
- `compliance_status` è stato rimosso dal DDL e dall'ETL perché non era mai valorizzato e non aveva una semantica utilizzabile.

## 7. Conclusione

Il profiling e la validazione finale confermano la coerenza tra sorgenti, trasformazioni ETL, schema a costellazione e query OLAP. Il presente documento riporta esclusivamente lo stato finale utilizzato per la consegna.
