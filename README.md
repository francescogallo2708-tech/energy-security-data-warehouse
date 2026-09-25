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
├── results/                     CSV files and presentation figures
├── report/                      formal academic report (PDF)
└── presentation/                slides for project discussion (PDF/PPTX)

data/raw/                        versioned source snapshots used by the ETL
data/processed/                  reserved area for possible persistent transformed outputs
src/profiling/                   exploratory source-data analysis
src/etl/                         Python loading scripts
sql/schema/                      final DDL and validation checks
sql/queries/                     didactic, business, and advanced OLAP queries
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

## Complete local execution guide

This is the only execution guide for the project. The workflow creates a local
PostgreSQL database, loads the versioned source snapshots, validates the result,
and then runs the OLAP queries.

### Prerequisites

- PostgreSQL, including the `psql`, `createdb`, and `pg_isready` command-line
  tools;
- Python 3.10 or later;
- the repository cloned with the `data/raw/` directory intact.

Create an isolated Python environment and install the dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Choose the PostgreSQL connection parameters for the local installation. The
macOS/Linux runner defaults to `localhost:5433`, database `energy_gpr_dw`, and
user `postgres`; set the variables explicitly to avoid ambiguity:

```bash
export PGHOST=localhost
export PGPORT=5433
export PGDATABASE=energy_gpr_dw
export PGUSER=postgres
```

Use `PGPASSFILE` (recommended) or `PGPASSWORD` only in the local shell; neither
password nor password file belongs in the repository. A `.pgpass` entry has the
format `host:port:database:user:password` and must be readable only by its
owner (`chmod 600 ~/.pgpass` on macOS/Linux).

Check that PostgreSQL is reachable, then create the database if it does not
already exist:

```bash
pg_isready -h "$PGHOST" -p "$PGPORT" -U "$PGUSER"
createdb -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" "$PGDATABASE"
```

If the database already exists, skip `createdb`. For a clean rebuild, first
drop **only this project database** with `dropdb` and recreate it; this removes
all tables and data in that database.

### Load and validate

From the repository root, create the schema and run the ordered ETL pipeline:

```bash
psql -v ON_ERROR_STOP=1 -f sql/schema/create_dw_schema.sql
./scripts/run_etl.sh
psql -v ON_ERROR_STOP=1 -f sql/schema/verify_final_dw.sql
```

The runner loads time and geography dimensions, the historical EU-membership
bridge, and then the GPR, import-dependency, energy-price, and oil-stock facts.
It is safe to re-run on the same schema because the loading workflow is
idempotent. The validation script checks row counts, duplicate natural keys,
and orphaned dimension references.

On Windows PowerShell, use the equivalent command below after installing the
same Python dependencies. Its default port is `5432`, so pass `-Port 5433` when
using the configuration above:

```powershell
.\scripts\run_etl.ps1 -Database energy_gpr_dw -HostName localhost -Port 5433 -User postgres
```

### Run the OLAP queries

Run the files in the following order; each can be executed independently after
a successful load:

```bash
psql -v ON_ERROR_STOP=1 -f sql/queries/01_olap_didactic_session.sql
psql -v ON_ERROR_STOP=1 -f sql/queries/02_olap_business_queries.sql
psql -v ON_ERROR_STOP=1 -f sql/queries/03_advanced_olap_queries.sql
```

The exported result CSV files and the figures used in the slides are in
`docs/results/`. To regenerate the six presentation figures from those CSV
files, run:

```bash
python3 src/visualization/create_presentation_charts.py
```

## Query scripts

`01_olap_didactic_session.sql` contains a guided sequence illustrating core multidimensional OLAP operations:

1. **Base**: half-yearly electricity prices by country;
2. **Roll-up**: aggregation from semester to year;
3. **Drill-down**: breakdown by consumer type;
4. **Slice**: restriction to Italy;
5. **Dice**: subcube for Italy and Germany during 2021--2023;
6. **Drill-across**: comparison of electricity prices and import dependency at country-year grain.

`02_olap_business_queries.sql` contains:

1. Pearson correlation between global GPR and electricity prices;
2. three-month moving average of oil stocks;
3. import dependency and gas prices;
4. annual comparison of metrics for actual EU members.

`03_advanced_olap_queries.sql` contains:

5. 2022 temporal comparison and gas-price variation;
6. 2024 energy-dependency ranking and percentile;
7. annual oil-stock autonomy from 2020 to 2025.

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
