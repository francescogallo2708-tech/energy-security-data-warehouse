-- ==============================================================================
-- Didactic OLAP queries: basic operations on the multidimensional model
-- Energy Security Data Warehouse
-- Francesco Gallo, Daniele Zito
--
-- Steps:
-- 1. Base query (semester level)
-- 2. Roll-up (going up from semester to year)
-- 3. Drill-down (adding consumer type: household vs non-household)
-- 4. Slice (filtering on Italy)
-- 5. Dice (filtering Italy & Germany, 2021-2023, households)
-- 6. Drill-across (joining prices and import dependency at country-year level)
-- ==============================================================================


-- ------------------------------------------------------------------------------
-- 1. Base query
-- Electricity price by country and semester.
-- Using AVG because price is non-additive (cannot be summed).
-- Fixed filters for homogeneous data: EUR, kWh, excluding VAT, standard household band.
-- ------------------------------------------------------------------------------
SELECT 
    g.country_name AS country,
    s.semester_sk AS semester,
    ROUND(AVG(p.price_val), 4) AS avg_price_eur_kwh
FROM fact_energy_price p
JOIN dim_geo_entity g ON p.geo_sk = g.geo_sk
JOIN dt_semester s ON p.semester_sk = s.semester_sk
JOIN dt_consumption_band cb ON p.consumption_band_sk = cb.consumption_band_sk
JOIN dt_tax_level tl ON p.tax_level_sk = tl.tax_level_sk
JOIN dt_price_unit pu ON p.price_unit_sk = pu.price_unit_sk
WHERE cb.commodity_type = 'ELECTRICITY'
  AND cb.band_code = 'KWH2500-4999'
  AND tl.tax_code = 'X_VAT'
  AND pu.currency_code = 'EUR'
  AND pu.energy_unit_code = 'KWH'
  AND g.entity_type = 'Country'
GROUP BY g.country_name, s.semester_sk
ORDER BY g.country_name, s.semester_sk;


-- ------------------------------------------------------------------------------
-- 2. Roll-up
-- Moving up the time hierarchy: from semester to year.
-- Replaced semester_sk with year_val in SELECT and GROUP BY.
-- Number of rows is halved because S1 and S2 are merged into the yearly average.
-- ------------------------------------------------------------------------------
SELECT 
    g.country_name AS country,
    s.year_val AS year,
    ROUND(AVG(p.price_val), 4) AS avg_price_eur_kwh
FROM fact_energy_price p
JOIN dim_geo_entity g ON p.geo_sk = g.geo_sk
JOIN dt_semester s ON p.semester_sk = s.semester_sk
JOIN dt_consumption_band cb ON p.consumption_band_sk = cb.consumption_band_sk
JOIN dt_tax_level tl ON p.tax_level_sk = tl.tax_level_sk
JOIN dt_price_unit pu ON p.price_unit_sk = pu.price_unit_sk
WHERE cb.commodity_type = 'ELECTRICITY'
  AND cb.band_code = 'KWH2500-4999'
  AND tl.tax_code = 'X_VAT'
  AND pu.currency_code = 'EUR'
  AND pu.energy_unit_code = 'KWH'
  AND g.entity_type = 'Country'
GROUP BY g.country_name, s.year_val
ORDER BY g.country_name, s.year_val;


-- ------------------------------------------------------------------------------
-- 3. Drill-down
-- Increasing detail: comparing households and businesses.
-- Added consumer_type to GROUP BY and removed the single band filter.
-- ------------------------------------------------------------------------------
SELECT 
    g.country_name AS country,
    s.year_val AS year,
    cb.consumer_type,
    ROUND(AVG(p.price_val), 4) AS avg_price_eur_kwh
FROM fact_energy_price p
JOIN dim_geo_entity g ON p.geo_sk = g.geo_sk
JOIN dt_semester s ON p.semester_sk = s.semester_sk
JOIN dt_consumption_band cb ON p.consumption_band_sk = cb.consumption_band_sk
JOIN dt_tax_level tl ON p.tax_level_sk = tl.tax_level_sk
JOIN dt_price_unit pu ON p.price_unit_sk = pu.price_unit_sk
WHERE cb.commodity_type = 'ELECTRICITY'
  AND tl.tax_code = 'X_VAT'
  AND pu.currency_code = 'EUR'
  AND pu.energy_unit_code = 'KWH'
  AND g.entity_type = 'Country'
GROUP BY g.country_name, s.year_val, cb.consumer_type
ORDER BY g.country_name, s.year_val, cb.consumer_type;


-- ------------------------------------------------------------------------------
-- 4. Slice
-- Slicing the cube on one dimension: looking only at Italy.
-- Just added WHERE country_name = 'Italy'.
-- ------------------------------------------------------------------------------
SELECT 
    g.country_name AS country,
    s.year_val AS year,
    cb.consumer_type,
    ROUND(AVG(p.price_val), 4) AS avg_price_eur_kwh
FROM fact_energy_price p
JOIN dim_geo_entity g ON p.geo_sk = g.geo_sk
JOIN dt_semester s ON p.semester_sk = s.semester_sk
JOIN dt_consumption_band cb ON p.consumption_band_sk = cb.consumption_band_sk
JOIN dt_tax_level tl ON p.tax_level_sk = tl.tax_level_sk
JOIN dt_price_unit pu ON p.price_unit_sk = pu.price_unit_sk
WHERE cb.commodity_type = 'ELECTRICITY'
  AND tl.tax_code = 'X_VAT'
  AND pu.currency_code = 'EUR'
  AND pu.energy_unit_code = 'KWH'
  AND g.country_name = 'Italy'
GROUP BY g.country_name, s.year_val, cb.consumer_type
ORDER BY s.year_val, cb.consumer_type;


-- ------------------------------------------------------------------------------
-- 5. Dice
-- Sub-cube: filtering on multiple dimensions together.
-- Countries: Italy and Germany.
-- Time: crisis years 2021 to 2023.
-- Consumers: households only.
-- ------------------------------------------------------------------------------
SELECT 
    g.country_name AS country,
    s.year_val AS year,
    ROUND(AVG(p.price_val), 4) AS avg_price_eur_kwh
FROM fact_energy_price p
JOIN dim_geo_entity g ON p.geo_sk = g.geo_sk
JOIN dt_semester s ON p.semester_sk = s.semester_sk
JOIN dt_consumption_band cb ON p.consumption_band_sk = cb.consumption_band_sk
JOIN dt_tax_level tl ON p.tax_level_sk = tl.tax_level_sk
JOIN dt_price_unit pu ON p.price_unit_sk = pu.price_unit_sk
WHERE cb.commodity_type = 'ELECTRICITY'
  AND cb.consumer_type = 'HOUSEHOLD'
  AND tl.tax_code = 'X_VAT'
  AND pu.currency_code = 'EUR'
  AND pu.energy_unit_code = 'KWH'
  AND g.country_name IN ('Italy', 'Germany')
  AND s.year_val BETWEEN 2021 AND 2023
GROUP BY g.country_name, s.year_val
ORDER BY g.country_name, s.year_val;


-- ------------------------------------------------------------------------------
-- 6. Drill-across
-- Joining two different fact tables: prices (half-yearly) and dependency (yearly).
-- Do NOT join the facts directly (different grains would cause a cartesian product).
-- Instead, aggregate both in CTEs to (country, year) first, then join.
-- ------------------------------------------------------------------------------
WITH yearly_prices AS (
    SELECT 
        g.country_name AS country,
        s.year_val AS year,
        ROUND(AVG(p.price_val), 4) AS avg_price_eur_kwh
    FROM fact_energy_price p
    JOIN dim_geo_entity g ON p.geo_sk = g.geo_sk
    JOIN dt_semester s ON p.semester_sk = s.semester_sk
    JOIN dt_consumption_band cb ON p.consumption_band_sk = cb.consumption_band_sk
    JOIN dt_tax_level tl ON p.tax_level_sk = tl.tax_level_sk
    JOIN dt_price_unit pu ON p.price_unit_sk = pu.price_unit_sk
    WHERE cb.commodity_type = 'ELECTRICITY'
      AND cb.consumer_type = 'HOUSEHOLD'
      AND tl.tax_code = 'X_VAT'
      AND pu.currency_code = 'EUR'
      AND pu.energy_unit_code = 'KWH'
    GROUP BY g.country_name, s.year_val
),
yearly_dependency AS (
    SELECT 
        g.country_name AS country,
        dep.year_sk AS year,
        ROUND(AVG(dep.dep_rate_val), 2) AS import_dependency_pct
    FROM fact_import_dependency dep
    JOIN dim_geo_entity g ON dep.geo_sk = g.geo_sk
    JOIN dt_energy_product prod ON dep.product_sk = prod.product_sk
    WHERE prod.siec_code = 'TOTAL'
    GROUP BY g.country_name, dep.year_sk
)
SELECT 
    pr.country,
    pr.year,
    pr.avg_price_eur_kwh,
    dep.import_dependency_pct
FROM yearly_prices pr
JOIN yearly_dependency dep 
  ON pr.country = dep.country 
 AND pr.year = dep.year
WHERE pr.country IN ('Italy', 'Germany', 'France')
  AND pr.year BETWEEN 2019 AND 2024
ORDER BY pr.country, pr.year;
