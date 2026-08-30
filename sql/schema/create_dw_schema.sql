-- =========================================================================
-- SCRIPT DDL: Struttura di base del Data Warehouse (Database: energy_gpr_dw)
-- =========================================================================

-- Schema di staging per i dati grezzi
CREATE SCHEMA IF NOT EXISTS staging;

CREATE TABLE IF NOT EXISTS staging.stg_eurostat_raw (
    dataset_name VARCHAR(100),
    metadata_string TEXT,
    raw_data_json TEXT
);

CREATE TABLE IF NOT EXISTS staging.stg_gpr_raw (
    month_date VARCHAR(20),
    gpr_val NUMERIC,
    gprt_val NUMERIC,
    gpra_val NUMERIC,
    raw_row_data TEXT
);

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
    gpr_fact_id SERIAL PRIMARY KEY,
    month_sk VARCHAR(10) REFERENCES DT_MONTH(month_sk),
    geo_sk INT REFERENCES DIM_GEO_ENTITY(geo_sk),
    gpr_val NUMERIC(10, 4),   -- geopolitical risk index
    gprt_val NUMERIC(10, 4),  -- GPR Threat index
    gpra_val NUMERIC(10, 4),  -- GPR Act index
    CONSTRAINT uk_gpr_month_geo UNIQUE (month_sk, geo_sk)
);

-- 2. Tabella dei Fatti: Dipendenza dall'Importazione Energetica (Annuale)
CREATE TABLE IF NOT EXISTS FACT_IMPORT_DEPENDENCY (
    dep_fact_id SERIAL PRIMARY KEY,
    year_sk INT REFERENCES DT_YEAR(year_sk),
    geo_sk INT REFERENCES DIM_GEO_ENTITY(geo_sk),
    siec_code VARCHAR(30) NOT NULL,      -- Prodotto energetico (es. TOTAL, O4000, G3000)
    unit_code VARCHAR(30) NOT NULL,      -- Unità di misura (es. PC - Percentage)
    dep_rate_val NUMERIC(10, 4),         -- Valore della dipendenza dall'importazione
    CONSTRAINT uk_dep_year_geo_siec UNIQUE (year_sk, geo_sk, siec_code, unit_code)
);

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

-- 3. Tabella dei Fatti: Prezzi dell'Energia (Semestrale)
CREATE TABLE IF NOT EXISTS FACT_ENERGY_PRICE (
    price_fact_id SERIAL PRIMARY KEY,
    semester_sk VARCHAR(10) NOT NULL REFERENCES DT_SEMESTER(semester_sk),
    geo_sk INT NOT NULL REFERENCES DIM_GEO_ENTITY(geo_sk),
    commodity_type VARCHAR(20) NOT NULL, -- 'GAS' o 'ELECTRICITY'
    consumer_type VARCHAR(20) NOT NULL,  -- 'HOUSEHOLD' o 'NON_HOUSEHOLD'
    product_code VARCHAR(50) NOT NULL,   -- Codice scaglione consumi Eurostat (es. KWH_GE01, KWH_GJ_GE02)
    tax_status VARCHAR(20) NOT NULL,     -- Regime fiscale (es. X_TAX, X_VAT, ALL_TAX)
    price_unit_sk INT NOT NULL REFERENCES DT_PRICE_UNIT(price_unit_sk),
    price_comparability_flag VARCHAR(50),
    eurostat_flag VARCHAR(20),
    price_val NUMERIC(10, 4) NOT NULL,   -- Prezzo finale
    CONSTRAINT uk_energy_price UNIQUE (semester_sk, geo_sk, commodity_type, consumer_type, product_code, tax_status, price_unit_sk)
);

-- Dimensione Indicatore Scorte Petrolifere
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

-- 4. Tabella dei Fatti: Scorte Petrolifere di Emergenza (Mensile)
CREATE TABLE IF NOT EXISTS FACT_OIL_STOCKS (
    stock_fact_id SERIAL PRIMARY KEY,
    month_sk VARCHAR(10) REFERENCES DT_MONTH(month_sk),
    geo_sk INT REFERENCES DIM_GEO_ENTITY(geo_sk),
    indicator_sk INT REFERENCES DT_STOCK_INDICATOR(indicator_sk),
    measure_unit_sk INT REFERENCES DT_MEASURE_UNIT(measure_unit_sk),
    compliance_status VARCHAR(50),
    eurostat_flag VARCHAR(20),
    stock_value NUMERIC(14, 4),          -- Level measure: non additiva nel tempo
    CONSTRAINT uk_oil_stocks UNIQUE (month_sk, geo_sk, indicator_sk, measure_unit_sk)
);
