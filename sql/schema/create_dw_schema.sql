-- =========================================================================
-- SCRIPT DDL DEFINITIVO: struttura del Data Warehouse (energy_gpr_dw)
-- Da eseguire su database vuoto prima degli ETL. Questo file definisce gia il
-- modello finale: le migrazioni storiche nella stessa cartella non sono parte
-- del flusso ordinario di consegna.
-- =========================================================================

-- Tabella Dimensione Geografica Comune
CREATE TABLE IF NOT EXISTS DIM_GEO_ENTITY (
    geo_sk SERIAL PRIMARY KEY,
    eurostat_code VARCHAR(30) UNIQUE NOT NULL,
    iso_alpha2 VARCHAR(5),
    iso_alpha3 VARCHAR(5),
    country_name VARCHAR(100) NOT NULL,
    entity_type VARCHAR(30) NOT NULL, -- 'Country', 'Aggregate', 'Global'
    is_eu BOOLEAN DEFAULT FALSE
);

-- Dimensione Temporale Annuale
CREATE TABLE IF NOT EXISTS DT_YEAR (
    year_sk INT PRIMARY KEY,
    year_value INT UNIQUE NOT NULL
);

-- Dimensione Temporale Semestrale
CREATE TABLE IF NOT EXISTS DT_SEMESTER (
    semester_sk VARCHAR(10) PRIMARY KEY, -- es. '2007-S1'
    year_val INT NOT NULL,
    semester_num INT NOT NULL
);

-- Dimensione Temporale Mensile
CREATE TABLE IF NOT EXISTS DT_MONTH (
    month_sk VARCHAR(10) PRIMARY KEY, -- es. '2013-01'
    year_val INT NOT NULL,
    month_num INT NOT NULL
);

-- Tabella Ponte per la storicizzazione dell'appartenenza UE
CREATE TABLE IF NOT EXISTS BR_GEO_EU_MEMBERSHIP (
    geo_sk INT REFERENCES DIM_GEO_ENTITY(geo_sk),
    year_sk INT REFERENCES DT_YEAR(year_sk),
    PRIMARY KEY (geo_sk, year_sk)
);

-- =========================================================================
-- TABELLE DEI FATTI (FACT TABLES)
-- =========================================================================

-- 1. Tabella dei Fatti: Rischio Geopolitico Mensile
CREATE TABLE IF NOT EXISTS FACT_GPR (
    month_sk VARCHAR(10) NOT NULL REFERENCES DT_MONTH(month_sk),
    geo_sk INT NOT NULL REFERENCES DIM_GEO_ENTITY(geo_sk),
    gpr_val NUMERIC(10, 4) NOT NULL,   -- geopolitical risk index
    gprt_val NUMERIC(10, 4) NOT NULL,  -- GPR Threat index
    gpra_val NUMERIC(10, 4) NOT NULL,  -- GPR Act index
    CONSTRAINT pk_fact_gpr PRIMARY KEY (month_sk, geo_sk),
    CONSTRAINT ck_gpr_scope_start CHECK (month_sk >= '1985-01')
);

COMMENT ON TABLE FACT_GPR IS
    'Monthly global GPR, GPRT and GPRA series; analytical scope starts at 1985-01';
COMMENT ON COLUMN FACT_GPR.gpr_val IS 'Geopolitical Risk index';
COMMENT ON COLUMN FACT_GPR.gprt_val IS 'Geopolitical Risk Threats index';
COMMENT ON COLUMN FACT_GPR.gpra_val IS 'Geopolitical Risk Acts index';

-- Dimensione Prodotto Energetico per la dipendenza dalle importazioni
CREATE TABLE IF NOT EXISTS DT_ENERGY_PRODUCT (
    product_sk SERIAL PRIMARY KEY,
    siec_code VARCHAR(30) UNIQUE NOT NULL,
    siec_label VARCHAR(200) NOT NULL,
    product_order SMALLINT NOT NULL,
    is_total BOOLEAN NOT NULL DEFAULT FALSE
);

-- 2. Tabella dei Fatti: Dipendenza dall'Importazione Energetica (Annuale)
-- La sorgente nrg_ind_id usa esclusivamente l'unita PC (percentuale),
-- validata dall'ETL e quindi implicita nella misura dep_rate_val.
CREATE TABLE IF NOT EXISTS FACT_IMPORT_DEPENDENCY (
    year_sk INT NOT NULL REFERENCES DT_YEAR(year_sk),
    geo_sk INT NOT NULL REFERENCES DIM_GEO_ENTITY(geo_sk),
    product_sk INT NOT NULL REFERENCES DT_ENERGY_PRODUCT(product_sk),
    eurostat_flag VARCHAR(20),
    dep_rate_val NUMERIC(12, 4) NOT NULL,
    CONSTRAINT pk_fact_import_dependency PRIMARY KEY (year_sk, geo_sk, product_sk)
);

COMMENT ON TABLE DT_ENERGY_PRODUCT IS
    'Energy products in Eurostat SIEC classification used by nrg_ind_id';
COMMENT ON TABLE FACT_IMPORT_DEPENDENCY IS
    'Annual energy import-dependency percentage by geography and SIEC product';
COMMENT ON COLUMN FACT_IMPORT_DEPENDENCY.dep_rate_val IS
    'Percentage (Eurostat unit PC); non-additive measure';

-- Dimensione Unita di Prezzo (unita energetica + valuta)
CREATE TABLE IF NOT EXISTS DT_PRICE_UNIT (
    price_unit_sk SERIAL PRIMARY KEY,
    energy_unit_code VARCHAR(30) NOT NULL,
    currency_code VARCHAR(10) NOT NULL,
    energy_unit_label VARCHAR(100),
    currency_label VARCHAR(100),
    price_basis VARCHAR(100),
    CONSTRAINT uk_price_unit UNIQUE (energy_unit_code, currency_code)
);

-- Dimensione Fascia di Consumo (classificata per consumatore e commodity)
CREATE TABLE IF NOT EXISTS DT_CONSUMPTION_BAND (
    consumption_band_sk SERIAL PRIMARY KEY,
    commodity_type VARCHAR(20) NOT NULL,  -- 'GAS' o 'ELECTRICITY'
    siec_code VARCHAR(20) NOT NULL,        -- G3000 o E7000
    siec_label VARCHAR(100) NOT NULL,
    consumer_type VARCHAR(20) NOT NULL,   -- 'HOUSEHOLD' o 'NON_HOUSEHOLD'
    band_code VARCHAR(50) NOT NULL,       -- Codice NRG_CONS Eurostat
    band_label VARCHAR(250) NOT NULL,
    band_order SMALLINT NOT NULL,
    is_total_band BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT uk_consumption_band UNIQUE (commodity_type, consumer_type, band_code)
);

-- Dimensione Livello di Tassazione
CREATE TABLE IF NOT EXISTS DT_TAX_LEVEL (
    tax_level_sk SERIAL PRIMARY KEY,
    tax_code VARCHAR(20) UNIQUE NOT NULL,
    tax_label VARCHAR(250) NOT NULL,
    tax_inclusion_order SMALLINT NOT NULL
);

-- 3. Tabella dei Fatti: Prezzi dell'Energia (Semestrale)
CREATE TABLE IF NOT EXISTS FACT_ENERGY_PRICE (
    semester_sk VARCHAR(10) NOT NULL REFERENCES DT_SEMESTER(semester_sk),
    geo_sk INT NOT NULL REFERENCES DIM_GEO_ENTITY(geo_sk),
    consumption_band_sk INT NOT NULL REFERENCES DT_CONSUMPTION_BAND(consumption_band_sk),
    tax_level_sk INT NOT NULL REFERENCES DT_TAX_LEVEL(tax_level_sk),
    price_unit_sk INT NOT NULL REFERENCES DT_PRICE_UNIT(price_unit_sk),
    eurostat_flag VARCHAR(20),
    price_val NUMERIC(10, 4) NOT NULL,   -- Prezzo finale
    CONSTRAINT pk_fact_energy_price PRIMARY KEY (
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

-- Dimensione degli indicatori quantitativi di sicurezza petrolifera
CREATE TABLE IF NOT EXISTS DT_STOCK_INDICATOR (
    indicator_sk SERIAL PRIMARY KEY,
    indicator_code VARCHAR(50) UNIQUE NOT NULL,
    indicator_label VARCHAR(200),
    indicator_class VARCHAR(100),
    obligation_basis VARCHAR(100)
);

-- Dimensione Unita di Misura
CREATE TABLE IF NOT EXISTS DT_MEASURE_UNIT (
    measure_unit_sk SERIAL PRIMARY KEY,
    unit_code VARCHAR(30) UNIQUE NOT NULL,
    unit_label VARCHAR(100)
);

-- 4. Tabella dei Fatti: Indicatori quantitativi di sicurezza petrolifera (Mensile)
CREATE TABLE IF NOT EXISTS FACT_OIL_STOCKS (
    month_sk VARCHAR(10) NOT NULL REFERENCES DT_MONTH(month_sk),
    geo_sk INT NOT NULL REFERENCES DIM_GEO_ENTITY(geo_sk),
    indicator_sk INT NOT NULL REFERENCES DT_STOCK_INDICATOR(indicator_sk),
    measure_unit_sk INT NOT NULL REFERENCES DT_MEASURE_UNIT(measure_unit_sk),
    eurostat_flag VARCHAR(20),
    indicator_value NUMERIC(14, 4) NOT NULL,
    CONSTRAINT pk_fact_oil_stocks PRIMARY KEY (month_sk, geo_sk, indicator_sk, measure_unit_sk)
);

COMMENT ON TABLE FACT_OIL_STOCKS IS
    'Monthly quantitative oil-security indicators; non-additive measure';
COMMENT ON COLUMN FACT_OIL_STOCKS.indicator_value IS
    'Non-additive measure; aggregate only within the same indicator and unit';
