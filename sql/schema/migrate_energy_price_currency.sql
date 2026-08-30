-- Rebuild FACT_ENERGY_PRICE to align it with the approved star schema.
-- The table is derived from reproducible raw sources and is reloaded by
-- src/etl/etl_load_energy_prices.py immediately after this migration.

BEGIN;

CREATE TABLE IF NOT EXISTS DT_PRICE_UNIT (
    price_unit_sk SERIAL PRIMARY KEY,
    energy_unit_code VARCHAR(30) NOT NULL,
    currency_code VARCHAR(10) NOT NULL,
    energy_unit_label VARCHAR(100),
    currency_label VARCHAR(100),
    price_basis VARCHAR(100),
    CONSTRAINT uk_price_unit UNIQUE (energy_unit_code, currency_code)
);

DROP TABLE IF EXISTS FACT_ENERGY_PRICE;

CREATE TABLE FACT_ENERGY_PRICE (
    price_fact_id SERIAL PRIMARY KEY,
    semester_sk VARCHAR(10) NOT NULL REFERENCES DT_SEMESTER(semester_sk),
    geo_sk INT NOT NULL REFERENCES DIM_GEO_ENTITY(geo_sk),
    commodity_type VARCHAR(20) NOT NULL,
    consumer_type VARCHAR(20) NOT NULL,
    product_code VARCHAR(50) NOT NULL,
    tax_status VARCHAR(20) NOT NULL,
    price_unit_sk INT NOT NULL REFERENCES DT_PRICE_UNIT(price_unit_sk),
    price_comparability_flag VARCHAR(50),
    eurostat_flag VARCHAR(20),
    price_val NUMERIC(10, 4) NOT NULL,
    CONSTRAINT uk_energy_price UNIQUE (
        semester_sk,
        geo_sk,
        commodity_type,
        consumer_type,
        product_code,
        tax_status,
        price_unit_sk
    )
);

COMMIT;
