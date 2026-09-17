# Energy Security Data Warehouse

An analytical data warehouse for the joint study of European energy security
and geopolitical risk. The project integrates the Geopolitical Risk Index (GPR)
with Eurostat datasets on import dependency, energy prices, and emergency oil
stocks.

## Repository contents

```text
docs/
├── proposal/                    approved proposal
├── data-sources/                sources, metadata, and transformation criteria
├── modeling/                    Fact Constellation, DFM and Star Schema diagrams
│   ├── dfm/                     four final DFM diagrams in PNG format
│   └── star-schema/             four final Star Schema diagrams in PNG format
└── results/                     CSV files and presentation figures

data/raw/                        versioned source snapshots used by the ETL
data/processed/                  reserved area for possible persistent transformed outputs
src/profiling/                   exploratory source-data analysis
src/etl/                         Python loading scripts
sql/schema/                      final DDL and validation checks
sql/queries/                     business, advanced, and didactic OLAP queries
scripts/run_etl.sh               ordered ETL execution for macOS / Linux
scripts/run_etl.ps1              ordered ETL execution for Windows PowerShell
requirements.txt                 Python dependencies for ETL, profiling, and charts
```

## Architecture

The model is a constellation of four fact tables, each preserved at the native
granularity of its source:

- `FACT_GPR`: monthly GPR indicators;
- `FACT_IMPORT_DEPENDENCY`: annual energy import dependency;
- `FACT_ENERGY_PRICE`: half-yearly energy prices;
- `FACT_OIL_STOCKS`: monthly oil stocks expressed in days of equivalent consumption.

For each fact table, the grain is enforced through a composite primary key made
of the foreign keys to the relevant dimensions, following the DFM-to-Star
Schema translation adopted in the course.

The time dimensions are separated into `DT_MONTH`, `DT_SEMESTER`, and `DT_YEAR`.
`DIM_GEO_ENTITY` is shared across processes, while
`BR_GEO_EU_MEMBERSHIP` represents historical European Union membership. The DFM
and Star Schema diagrams are available in `docs/modeling/`.

Risk, dependency, and price measures are non-additive: they are aggregated only
within homogeneous contexts using `AVG`, `MIN`, or `MAX`. Stock measures are
level measures and are not summed over time. Eurostat flags are retained as
nullable descriptive attributes.

The DDL does not create separate staging tables: files under `data/raw/` are the
source area of the process, and the ETL scripts apply transformations directly
to dimensions and fact tables. The semantically unusable `compliance_status`
column was excluded from `FACT_OIL_STOCKS`; the relevant Eurostat observation
status is represented by `eurostat_flag`.

## Running the data warehouse

The final loading workflow is idempotent and requires no intermediate
migrations. On an empty PostgreSQL database:

1. run `sql/schema/create_dw_schema.sql`;
2. verify that the source snapshots are available in the `data/raw/` structure
   described in `docs/data-sources/README.md`;
3. run `scripts/run_etl.sh` (macOS/Linux) or `scripts/run_etl.ps1` (Windows),
   which automatically loads dimensions and facts in the correct order;
4. run `sql/schema/verify_final_dw.sql` to perform quality checks;
5. run the queries in `sql/queries/`.

PostgreSQL connections use the standard environment variables (`PGHOST`,
`PGPORT`, `PGDATABASE`, `PGUSER`, `PGPASSWORD`, or `PGPASSFILE`). Passwords and
local databases are not part of the repository.

## Analytical queries

`01_olap_business_queries.sql` contains:

1. Pearson correlation between global GPR and electricity prices;
2. three-month moving average of oil stocks;
3. import dependency and gas prices;
4. annual comparison of metrics for actual EU members.

`02_advanced_olap_queries.sql` contains:

5. 2022 temporal comparison and gas-price variation;
6. 2024 energy-dependency ranking and percentile;
7. annual oil-stock autonomy from 2020 to 2025.

`03_olap_didactic_session.sql` contains a guided sequence illustrating core multidimensional OLAP operations:

8. **Base**: half-yearly EU gas prices across consumption bands;
9. **Roll-up**: aggregation from bands to total commodity level;
10. **Drill-down**: breakdown from EU aggregate to individual member states;
11. **Slice**: restriction to a single country (Italy);
12. **Dice**: multi-dimensional subcube (Italy & Germany, 2022–2023, medium consumption band);
13. **Drill-across**: cross-fact correlation combining emergency oil stocks and geopolitical risk.

Exported results are available in `docs/results/`. Correlations and temporal
variations describe observed associations and do not demonstrate causality.

## Charts

The figures used in the presentation are generated from the CSV files with:

```bash
python3 src/visualization/create_presentation_charts.py
```

The script saves six PNG files in `docs/results/figures/`. The selection of
charts and key rows is described in `docs/results/presentation_selection.md`.
Required dependencies are listed in `requirements.txt`.

## Validated loading results

The validated version produces 499 GPR rows, 17,316 import-dependency rows,
314,671 energy-price rows, and 15,103 oil-stock rows. The checks defined in
`verify_final_dw.sql` validate counts, natural-key uniqueness, and the absence
of orphaned dimension references.

## Sources

Official sources, the snapshots used, Eurostat dataset links, SDMX metadata,
frequencies, and applied transformations are documented in
`docs/data-sources/README.md`.
