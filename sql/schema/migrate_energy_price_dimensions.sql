-- Migrazione di FACT_ENERGY_PRICE verso le dimensioni Consumption Band e Tax Level.
-- La fact e interamente derivata dai quattro TSV Eurostat e viene ricreata vuota;
-- eseguire src/etl/etl_load_energy_prices.py subito dopo questa migrazione.

BEGIN;

-- L'area prezzi e interamente ricostruibile dai quattro TSV Eurostat.
-- La ricreazione rende la migrazione deterministica anche partendo dal vecchio schema.
DROP TABLE IF EXISTS FACT_ENERGY_PRICE;
DROP TABLE IF EXISTS DT_CONSUMPTION_BAND;
DROP TABLE IF EXISTS DT_TAX_LEVEL;
DROP TABLE IF EXISTS DT_PRICE_UNIT;

CREATE TABLE DT_CONSUMPTION_BAND (
    consumption_band_sk SERIAL PRIMARY KEY,
    commodity_type VARCHAR(20) NOT NULL,
    siec_code VARCHAR(20) NOT NULL,
    siec_label VARCHAR(100) NOT NULL,
    consumer_type VARCHAR(20) NOT NULL,
    band_code VARCHAR(50) NOT NULL,
    band_label VARCHAR(250) NOT NULL,
    band_order SMALLINT NOT NULL,
    is_total_band BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT uk_consumption_band UNIQUE (commodity_type, consumer_type, band_code)
);

CREATE TABLE DT_TAX_LEVEL (
    tax_level_sk SERIAL PRIMARY KEY,
    tax_code VARCHAR(20) UNIQUE NOT NULL,
    tax_label VARCHAR(250) NOT NULL,
    tax_inclusion_order SMALLINT NOT NULL
);

CREATE TABLE DT_PRICE_UNIT (
    price_unit_sk SERIAL PRIMARY KEY,
    energy_unit_code VARCHAR(30) NOT NULL,
    currency_code VARCHAR(10) NOT NULL,
    energy_unit_label VARCHAR(100),
    currency_label VARCHAR(100),
    price_basis VARCHAR(100),
    CONSTRAINT uk_price_unit UNIQUE (energy_unit_code, currency_code)
);

CREATE TABLE FACT_ENERGY_PRICE (
    price_fact_id SERIAL PRIMARY KEY,
    semester_sk VARCHAR(10) NOT NULL REFERENCES DT_SEMESTER(semester_sk),
    geo_sk INT NOT NULL REFERENCES DIM_GEO_ENTITY(geo_sk),
    consumption_band_sk INT NOT NULL REFERENCES DT_CONSUMPTION_BAND(consumption_band_sk),
    tax_level_sk INT NOT NULL REFERENCES DT_TAX_LEVEL(tax_level_sk),
    price_unit_sk INT NOT NULL REFERENCES DT_PRICE_UNIT(price_unit_sk),
    eurostat_flag VARCHAR(20),
    price_val NUMERIC(10, 4) NOT NULL,
    CONSTRAINT uk_energy_price UNIQUE (
        semester_sk,
        geo_sk,
        consumption_band_sk,
        tax_level_sk,
        price_unit_sk
    )
);

COMMENT ON TABLE DT_CONSUMPTION_BAND IS
    'Eurostat consumption bands with consumer and energy commodity hierarchy';

COMMENT ON TABLE DT_TAX_LEVEL IS
    'Eurostat tax inclusion levels for energy prices';

COMMENT ON TABLE FACT_ENERGY_PRICE IS
    'Half-yearly energy prices by geography, consumption band, tax level and price unit';

COMMIT;

-- Subito dopo la migrazione la fact deve essere vuota; verra ricaricata dall'ETL.
SELECT COUNT(*) AS energy_price_rows_before_reload
FROM FACT_ENERGY_PRICE;
