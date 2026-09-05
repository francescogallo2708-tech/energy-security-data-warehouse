# Data sources

This directory documents the official sources and the SDMX metadata used by
the Energy Security Data Warehouse. The source data snapshots used by the final
ETL are versioned under `data/raw/` so that the project can be reproduced
directly from the repository. The XML files stored here are versioned metadata
artifacts documenting the same source releases.

## Eurostat datasets

| Dataset | Official Eurostat link | Role | Frequency / coverage | Local file |
|---|---|---|---|---|
| `nrg_ind_id` | [Data Browser](https://ec.europa.eu/eurostat/databrowser/view/nrg_ind_id/default/table?lang=en) | Import dependency | Annual, 1990–2024 | `data/raw/eurostat/nrg_ind_id_tabular.tsv` |
| `nrg_pc_202` | [Data Browser](https://ec.europa.eu/eurostat/databrowser/view/nrg_pc_202/default/table?lang=en) | Gas prices, household | Half-yearly, 2007-S1–2025-S2 | `data/raw/eurostat/nrg_pc_202_tabular.tsv` |
| `nrg_pc_203` | [Data Browser](https://ec.europa.eu/eurostat/databrowser/view/nrg_pc_203/default/table?lang=en) | Gas prices, non-household | Half-yearly, 2007-S1–2025-S2 | `data/raw/eurostat/nrg_pc_203_tabular.tsv` |
| `nrg_pc_204` | [Data Browser](https://ec.europa.eu/eurostat/databrowser/view/nrg_pc_204/default/table?lang=en) | Electricity prices, household | Half-yearly, 2007-S1–2025-S2 | `data/raw/eurostat/nrg_pc_204_tabular.tsv` |
| `nrg_pc_205` | [Data Browser](https://ec.europa.eu/eurostat/databrowser/view/nrg_pc_205/default/table?lang=en) | Electricity prices, non-household | Half-yearly, 2007-S1–2025-S2 | `data/raw/eurostat/nrg_pc_205_tabular.tsv` |
| `nrg_stk_oem` | [Data Browser](https://ec.europa.eu/eurostat/databrowser/view/nrg_stk_oem/default/table?lang=en) | Emergency oil-security indicators | Monthly, 2013-01–2026-06 | `data/raw/eurostat/nrg_stk_oem_tabular.tsv` |

The corresponding metadata files are `ESTAT_NRG_*.xml`. They document the
dimensions and codelists (`GEO`, `SIEC`, `NRG_CONS`, `TAX`, `UNIT`, `CURRENCY`,
`STK_FLOW`, `OBS_FLAG` and `CONF_STATUS`). At runtime, the import-dependency
and energy-price ETLs read their XML files to validate the source structure and
codes. The Oil Stocks XML is retained as versioned source documentation; its
ETL uses the explicit quantitative scope defined in the Python mappings because
the final fact excludes the categorical method indicators.

### Eurostat transformations

The tabular downloads are wide: the first column contains comma-separated
dimension codes and the remaining columns contain periods. The ETL performs a
wide-to-long transformation, parses numeric values and observation flags, maps
codes to warehouse dimensions and rejects invalid or incomplete keys.

- Import dependency is fixed to annual frequency and unit `PC` (percentage).
- Energy prices retain consumer type, commodity, consumption band, tax level,
  energy unit and currency in the fact grain; prices are not additive.
- Oil Stocks retains the four quantitative indicators and excludes the three
  categorical method codes.

## Geopolitical Risk

The project uses the monthly Geopolitical Risk Index dataset published by
Matteo Iacoviello. The reproducible snapshot is `data_gpr_export_202608.xls`
under `data/raw/gpr/` and is included in the repository so that the ETL can be
executed without a separate download step. The ETL selects the global `GPR`, `GPRT` and `GPRA` series,
requires all three measures to be present and uses the complete comparable
scope 1985-01–2026-07. The global series are linked to the `GLOBAL` row of
`DIM_GEO_ENTITY`.

Reference: [Geopolitical Risk Index](https://www.matteoiacoviello.com/gpr.htm).

## Reproducibility and provenance

The final profiling report is available in `src/profiling/report_profiling.md`.
The profiling scripts are optional inspection tools; the reproducible loading
workflow starts with the definitive DDL and then executes the ETL scripts in
the documented order. Raw files remain immutable; all cleaning, filtering and
mapping rules are implemented in the ETL scripts rather than by editing source
files.
