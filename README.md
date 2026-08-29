# Energy Security Data Warehouse

An analytical data warehouse project focused on energy-security data from
multiple sources.

The repository documents a reproducible workflow covering data profiling,
dimensional modelling, ETL, PostgreSQL and analytical queries.

## Repository structure

```text
docs/
├── proposal/
├── modeling/
│   ├── dfm/
│   └── star-schema/
├── data-sources/
└── presentation/

data/
├── raw/          Local source files; not versioned by default
├── processed/    Generated data; not versioned by default
└── sample/       Small shareable examples, when useful

src/
├── profiling/
└── etl/

sql/
├── schema/
├── staging/
├── warehouse/
└── queries/

scripts/
tests/
```

## Workflow

1. Profile the source datasets.
2. Define the dimensional fact model.
3. Design the star schemas.
4. Transform and integrate the data through ETL.
5. Load the warehouse in PostgreSQL.
6. Run analytical and OLAP queries.

## Project documentation

The approved project proposal is available in `docs/proposal/`. Modelling
artifacts are organised under `docs/modeling/`, while presentation materials
will be added to `docs/presentation/` when they are finalised.

## Data and reproducibility

Source references, metadata and download instructions belong in
`docs/data-sources/`. Large or redistributable-restricted data files should
remain local; small, shareable examples can be placed in `data/sample/`.

Setup and execution instructions will be added as the implementation matures.
