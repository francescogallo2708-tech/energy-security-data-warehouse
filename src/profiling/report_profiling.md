# Final profiling and validation report

**Project:** Data Warehouse for the analysis of European energy security and geopolitical risk  
**Reference date:** 5 September 2026  
**Environment:** local PostgreSQL test database after the complete execution of the final ETL workflow.

## 1. Objective and scope

Profiling guided the design of dimensions, fact tables, and ETL rules. Final
validation verifies that source files were transformed at the intended grain,
that natural keys do not produce duplicates, and that every loaded row has valid
dimension references.

The workflow uses raw Eurostat TSV files and a GPR XLS file. Wide files are
converted to long format when required; codes, Eurostat flags, and geographic
mapping are resolved during ETL.

## 2. Sources used

| Domain | File | Format | Frequency | Coverage used |
|---|---|---|---|---|
| Import dependency | `nrg_ind_id_tabular.tsv` | Wide TSV | Annual | 1990–2024 |
| Gas prices | `nrg_pc_202_tabular.tsv`, `nrg_pc_203_tabular.tsv` | Wide TSV | Half-yearly | 2007-S1–2025-S2 |
| Electricity prices | `nrg_pc_204_tabular.tsv`, `nrg_pc_205_tabular.tsv` | Wide TSV | Half-yearly | 2007-S1–2025-S2 |
| Emergency oil stocks | `nrg_stk_oem_tabular.tsv` | Wide TSV | Monthly | 2013-01–2026-06 |
| Geopolitical Risk | `data_gpr_export_202608.xls` | Tabular XLS | Monthly | 1985-01–2026-07 within the loaded scope |

## 3. Final loading results

| Fact table | Logical grain | Loaded rows | Loaded period |
|---|---|---:|---|
| `FACT_GPR` | month, geographic entity | 499 | 1985-01–2026-07 |
| `FACT_IMPORT_DEPENDENCY` | year, geographic entity, energy product | 17,316 | 1990–2024 |
| `FACT_ENERGY_PRICE` | semester, geographic entity, band, tax level, price unit | 314,671 | 2007-S1–2025-S2 |
| `FACT_OIL_STOCKS` | month, geographic entity, indicator, measurement unit | 15,103 | 2013-01–2026-06 |

Time dimensions are populated for years, semesters, and months. The geographic
dimension contains 46 entities, and the EU bridge table contains 1,191
historical relationships.

## 4. Transformation rules

### Import dependency

The wide file was converted into annual observations. The `DT_YEAR`,
`DIM_GEO_ENTITY`, and `DT_ENERGY_PRODUCT` dimensions are resolved through the
source natural keys. The final load includes 17,316 quantitative observations.

### Energy price

The four price files were converted from wide to long format. The grain includes
currency and energy unit through `DT_PRICE_UNIT`, preventing observations with
different currencies from being combined. Twenty-five consumption bands, three
tax levels, and six unit-currency combinations were loaded.

### Emergency oil stocks

Quantitative observations consistent with the fact table were retained. 13,144
categorical records related to calculation methods were excluded; 15,103 records
were loaded at the intended monthly grain. `eurostat_flag` is retained as a
descriptive attribute. The semantically unusable `compliance_status` column was
removed from the physical model and the ETL.

### Geopolitical Risk

The GPR file contains 1,519 source rows. 1,020 rows without values for `GPR`,
`GPRT`, and `GPRA` were excluded; the final load covers 499 observations of the
global series within the 1985-01–2026-07 scope. National and alternative series
in the file are outside the scope of the first DW version.

## 5. Quality checks

Checks were performed on counts and periods, duplicates on natural keys,
orphaned dimensions, time/geography keys, and ETL idempotence.

| Check | Result |
|---|---:|
| `FACT_GPR` duplicates | 0 |
| `FACT_IMPORT_DEPENDENCY` duplicates | 0 |
| `FACT_ENERGY_PRICE` duplicates | 0 |
| `FACT_OIL_STOCKS` duplicates | 0 |
| `FACT_IMPORT_DEPENDENCY` orphaned dimensions | 0 |
| `FACT_ENERGY_PRICE` orphaned dimensions | 0 |
| `FACT_OIL_STOCKS` orphaned dimensions | 0 |

The checks confirm that fact tables respect their declared grain and that every
populated foreign key finds its corresponding dimension. Each fact table grain
is also physically enforced through a composite primary key made of its foreign
keys.

## 6. Coverage and limitations

- GPR is limited to the three global measures `GPR`, `GPRT`, and `GPRA`.
- Geographic coverage depends on the shared mapping and on entities published by the sources.
- Prices, percentage rates, GPR indicators, and equivalent days are non-additive: analyses use `AVG`, `MIN`, and `MAX` at the appropriate grain.
- `BR_GEO_EU_MEMBERSHIP` is a bridge table for historical EU membership, not a fact table with measures.
- Staging tables are not present in the final DDL: raw files constitute the source area and ETLs load dimensions and fact tables directly.
- `compliance_status` was removed from the DDL and ETL because it was never populated and had no usable semantics.

## 7. Conclusion

Profiling and final validation confirm consistency among sources, ETL
transformations, the fact constellation schema, and OLAP queries. This document
reports only the final state used for submission.
