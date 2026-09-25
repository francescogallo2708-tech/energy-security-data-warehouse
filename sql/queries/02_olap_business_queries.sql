-- ==============================================================================
-- BUSINESS OLAP QUERIES - ENERGY SECURITY & GPR DATA WAREHOUSE
-- ==============================================================================

-- 1. DRILL-ACROSS AND CORRELATION BETWEEN GLOBAL GPR AND ELECTRICITY PRICES
-- For each country, calculates the Pearson coefficient between average annual
-- global GPR and the average annual non-household electricity price (IC band,
-- EUR/kWh, excluding VAT). The two series are aggregated separately before the
-- join to respect their monthly and half-yearly granularities. Only countries
-- with at least 18 comparable years are included.
WITH gpr_by_year AS (
    SELECT
        m.year_val AS year,
        AVG(gpr.gpr_val) AS average_annual_gpr
    FROM fact_gpr gpr
    JOIN dt_month m ON m.month_sk = gpr.month_sk
    JOIN dim_geo_entity geo ON geo.geo_sk = gpr.geo_sk
    WHERE geo.eurostat_code = 'GLOBAL'
    GROUP BY m.year_val
),
price_by_country_year AS (
    SELECT
        s.year_val AS year,
        g.country_name AS country,
        AVG(p.price_val) AS average_annual_price
    FROM fact_energy_price p
    JOIN dt_semester s ON s.semester_sk = p.semester_sk
    JOIN dim_geo_entity g ON g.geo_sk = p.geo_sk
    JOIN dt_consumption_band cb ON cb.consumption_band_sk = p.consumption_band_sk
    JOIN dt_tax_level tl ON tl.tax_level_sk = p.tax_level_sk
    JOIN dt_price_unit pu ON pu.price_unit_sk = p.price_unit_sk
    WHERE cb.commodity_type = 'ELECTRICITY'
      AND cb.consumer_type = 'NON_HOUSEHOLD'
      AND cb.band_code = 'MWH500-1999'
      AND tl.tax_code = 'X_VAT'
      AND pu.currency_code = 'EUR'
      AND pu.energy_unit_code = 'KWH'
      AND g.entity_type = 'Country'
    GROUP BY s.year_val, g.country_name
),
paired_series AS (
    SELECT
        p.year,
        p.country,
        g.average_annual_gpr,
        p.average_annual_price
    FROM price_by_country_year p
    JOIN gpr_by_year g ON g.year = p.year
)
SELECT
    country,
    COUNT(*) AS comparable_years,
    MIN(year) AS first_year,
    MAX(year) AS last_year,
    ROUND(CORR(
        average_annual_gpr::DOUBLE PRECISION,
        average_annual_price::DOUBLE PRECISION
    )::NUMERIC, 3) AS pearson_correlation_gpr_price
FROM paired_series
GROUP BY country
HAVING COUNT(*) >= 18
ORDER BY pearson_correlation_gpr_price DESC NULLS LAST, country;


-- 2. WINDOW ANALYSIS ON EMERGENCY OIL STOCKS
-- Calculates equivalent stock days through a three-month moving average,
-- retaining monthly detail and without mixing different indicators or units.
-- This is not a drill-down or roll-up operation.
SELECT
    m.month_sk AS month,
    g.country_name AS country,
    ind.indicator_label AS indicator,
    s.indicator_value AS equivalent_days,
    ROUND(AVG(s.indicator_value) OVER (
        PARTITION BY s.geo_sk, s.indicator_sk
        ORDER BY m.month_sk
        ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
    ), 2) AS three_month_moving_average_days
FROM fact_oil_stocks s
JOIN dt_month m ON s.month_sk = m.month_sk
JOIN dim_geo_entity g ON s.geo_sk = g.geo_sk
JOIN dt_stock_indicator ind ON s.indicator_sk = ind.indicator_sk
JOIN dt_measure_unit u ON s.measure_unit_sk = u.measure_unit_sk
WHERE g.eurostat_code IN ('IT', 'DE', 'FR', 'ES')
  AND ind.indicator_code = 'STK_EUE_DIR'
  AND u.unit_code = 'NR'
ORDER BY g.country_name, m.month_sk DESC;


-- 3. DRILL-ACROSS AND SLICE & DICE: ENERGY IMPORT DEPENDENCY AND GAS PRICES
-- Compares annual import-dependency rates with gas prices in Eurostat D2
-- (household) and I3 (non-household) bands, in EUR/kWh and with X_VAT. The two
-- fact tables are aggregated separately before the join.
WITH dependency_by_year AS (
    SELECT
        y.year_value AS year,
        g.geo_sk,
        g.country_name AS country,
        AVG(dep.dep_rate_val) AS import_dependency_rate_pct
    FROM fact_import_dependency dep
    JOIN dt_year y ON y.year_sk = dep.year_sk
    JOIN dim_geo_entity g ON g.geo_sk = dep.geo_sk
    JOIN dt_energy_product prod ON prod.product_sk = dep.product_sk
    WHERE g.entity_type = 'Country'
      AND prod.siec_code = 'TOTAL'
    GROUP BY y.year_value, g.geo_sk, g.country_name
),
gas_price_by_year AS (
    SELECT
        s.year_val AS year,
        ep.geo_sk,
        AVG(CASE WHEN cb.consumer_type = 'HOUSEHOLD' THEN ep.price_val END)
            AS household_gas_price,
        AVG(CASE WHEN cb.consumer_type = 'NON_HOUSEHOLD' THEN ep.price_val END)
            AS non_household_gas_price
    FROM fact_energy_price ep
    JOIN dt_semester s ON s.semester_sk = ep.semester_sk
    JOIN dt_consumption_band cb
      ON cb.consumption_band_sk = ep.consumption_band_sk
    JOIN dt_tax_level tl ON tl.tax_level_sk = ep.tax_level_sk
    JOIN dt_price_unit pu ON pu.price_unit_sk = ep.price_unit_sk
    WHERE cb.commodity_type = 'GAS'
      AND (
            (cb.consumer_type = 'HOUSEHOLD' AND cb.band_code = 'GJ20-199')
         OR (cb.consumer_type = 'NON_HOUSEHOLD' AND cb.band_code = 'GJ10000-99999')
      )
      AND tl.tax_code = 'X_VAT'
      AND pu.currency_code = 'EUR'
      AND pu.energy_unit_code = 'KWH'
    GROUP BY s.year_val, ep.geo_sk
)
SELECT
    d.year,
    d.country,
    ROUND(d.import_dependency_rate_pct, 2) AS import_dependency_rate_pct,
    ROUND(p.household_gas_price, 4) AS household_gas_price,
    ROUND(p.non_household_gas_price, 4) AS non_household_gas_price
FROM dependency_by_year d
LEFT JOIN gas_price_by_year p
  ON p.year = d.year
 AND p.geo_sk = d.geo_sk
WHERE p.geo_sk IS NOT NULL
ORDER BY d.year DESC, import_dependency_rate_pct DESC, d.country;


-- 4. DYNAMIC EU-MEMBERSHIP ANALYSIS THROUGH BR_GEO_EU_MEMBERSHIP
-- Facts are first aggregated at country-year level to avoid duplication across
-- semesters. Only years with both metrics available are retained. The result
-- separately reports theoretical EU members and actual contributors to each
-- average, which may differ.
WITH eu_members AS (
    SELECT br.year_sk, COUNT(DISTINCT br.geo_sk) AS eu_member_count
    FROM br_geo_eu_membership br
    GROUP BY br.year_sk
),
dependency_country_year AS (
    SELECT d.year_sk, d.geo_sk, AVG(d.dep_rate_val) AS country_dependency_pct
    FROM fact_import_dependency d
    JOIN dt_energy_product prod ON d.product_sk = prod.product_sk
    JOIN br_geo_eu_membership br ON br.year_sk = d.year_sk AND br.geo_sk = d.geo_sk
    WHERE prod.siec_code = 'TOTAL'
    GROUP BY d.year_sk, d.geo_sk
),
dependency_eu_year AS (
    SELECT year_sk,
           COUNT(*) AS dependency_contributor_count,
           AVG(country_dependency_pct) AS average_eu_import_dependency_pct
    FROM dependency_country_year
    GROUP BY year_sk
),
price_country_year AS (
    SELECT s.year_val AS year_sk, ep.geo_sk,
           AVG(ep.price_val) AS country_electricity_price
    FROM fact_energy_price ep
    JOIN dt_semester s ON ep.semester_sk = s.semester_sk
    JOIN br_geo_eu_membership br ON br.year_sk = s.year_val AND br.geo_sk = ep.geo_sk
    JOIN dt_consumption_band cb ON ep.consumption_band_sk = cb.consumption_band_sk
    JOIN dt_tax_level tl ON ep.tax_level_sk = tl.tax_level_sk
    JOIN dt_price_unit pu ON ep.price_unit_sk = pu.price_unit_sk
    WHERE cb.commodity_type = 'ELECTRICITY'
      AND cb.consumer_type = 'NON_HOUSEHOLD'
      AND cb.band_code = 'MWH500-1999'
      AND tl.tax_code = 'X_VAT'
      AND pu.currency_code = 'EUR'
      AND pu.energy_unit_code = 'KWH'
    GROUP BY s.year_val, ep.geo_sk
),
price_eu_year AS (
    SELECT year_sk,
           COUNT(*) AS electricity_price_contributor_count,
           AVG(country_electricity_price) AS average_eu_electricity_price
    FROM price_country_year
    GROUP BY year_sk
)
SELECT y.year_value AS year,
       m.eu_member_count,
       d.dependency_contributor_count,
       p.electricity_price_contributor_count,
       ROUND(d.average_eu_import_dependency_pct, 2) AS average_eu_import_dependency_pct,
       ROUND(p.average_eu_electricity_price, 4) AS average_eu_electricity_price
FROM eu_members m
JOIN dt_year y ON m.year_sk = y.year_sk
LEFT JOIN dependency_eu_year d ON d.year_sk = m.year_sk
LEFT JOIN price_eu_year p ON p.year_sk = m.year_sk
WHERE d.year_sk IS NOT NULL
  AND p.year_sk IS NOT NULL
ORDER BY y.year_value DESC;
