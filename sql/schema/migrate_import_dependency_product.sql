-- Migrazione di FACT_IMPORT_DEPENDENCY verso la dimensione DT_ENERGY_PRODUCT.
-- La fact e la dimensione prodotto sono interamente ricostruibili dal TSV
-- Eurostat nrg_ind_id; eseguire src/etl/etl_load_import_dep.py subito dopo.

BEGIN;

DROP TABLE IF EXISTS FACT_IMPORT_DEPENDENCY;
DROP TABLE IF EXISTS DT_ENERGY_PRODUCT;

CREATE TABLE DT_ENERGY_PRODUCT (
    product_sk SERIAL PRIMARY KEY,
    siec_code VARCHAR(30) UNIQUE NOT NULL,
    siec_label VARCHAR(200) NOT NULL,
    product_order SMALLINT NOT NULL,
    is_total BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE FACT_IMPORT_DEPENDENCY (
    dep_fact_id SERIAL PRIMARY KEY,
    year_sk INT NOT NULL REFERENCES DT_YEAR(year_sk),
    geo_sk INT NOT NULL REFERENCES DIM_GEO_ENTITY(geo_sk),
    product_sk INT NOT NULL REFERENCES DT_ENERGY_PRODUCT(product_sk),
    eurostat_flag VARCHAR(20),
    dep_rate_val NUMERIC(12, 4) NOT NULL,
    CONSTRAINT uk_dep_year_geo_product UNIQUE (year_sk, geo_sk, product_sk)
);

COMMENT ON TABLE DT_ENERGY_PRODUCT IS
    'Energy products in Eurostat SIEC classification used by nrg_ind_id';

COMMENT ON TABLE FACT_IMPORT_DEPENDENCY IS
    'Annual energy import-dependency percentage by geography and SIEC product';

COMMENT ON COLUMN FACT_IMPORT_DEPENDENCY.dep_rate_val IS
    'Percentage (Eurostat unit PC); non-additive measure';

COMMIT;

-- Subito dopo la migrazione la fact deve essere vuota; verra ricaricata dall'ETL.
SELECT COUNT(*) AS import_dependency_rows_before_reload
FROM FACT_IMPORT_DEPENDENCY;
