-- ==============================================================================
-- ADVANCED OLAP QUERIES - ENERGY SECURITY & GPR DATA WAREHOUSE
-- ==============================================================================

-- 5. DRILL-ACROSS AND TEMPORAL COMPARISON: GLOBAL GPR AND GAS PRICES
-- Compares GPR values from 2021 to 2023 with the percentage variation in
-- household gas prices in Eurostat D2 band, expressed in EUR/kWh with taxes
-- and levies included. The comparison describes a temporal association and
-- does not demonstrate a causal relationship.
WITH price_by_year AS (
    SELECT
        y.year_value AS year,
        g.country_name AS country,
        AVG(p.price_val) AS household_gas_price
    FROM fact_energy_price p
    JOIN dt_semester s ON p.semester_sk = s.semester_sk
    JOIN dt_year y ON s.year_val = y.year_sk
    JOIN dim_geo_entity g ON p.geo_sk = g.geo_sk
    JOIN dt_consumption_band cb ON p.consumption_band_sk = cb.consumption_band_sk
    JOIN dt_tax_level tl ON p.tax_level_sk = tl.tax_level_sk
    JOIN dt_price_unit pu ON p.price_unit_sk = pu.price_unit_sk
    WHERE cb.commodity_type = 'GAS'
      AND cb.consumer_type = 'HOUSEHOLD'
      AND cb.band_code = 'GJ20-199'
      AND tl.tax_code = 'I_TAX'
      AND pu.currency_code = 'EUR'
      AND pu.energy_unit_code = 'KWH'
      AND y.year_value BETWEEN 2021 AND 2023
      AND g.entity_type = 'Country'
    GROUP BY y.year_value, g.country_name
),
price_with_lag AS (
    SELECT year, country, household_gas_price,
           LAG(household_gas_price) OVER (
               PARTITION BY country ORDER BY year
           ) AS previous_year_household_gas_price
    FROM price_by_year
),
gpr_by_year AS (
    SELECT
        m.year_val AS year,
        AVG(gpr.gpr_val) AS average_gpr
    FROM fact_gpr gpr
    JOIN dt_month m ON gpr.month_sk = m.month_sk
    JOIN dim_geo_entity g ON gpr.geo_sk = g.geo_sk
    WHERE g.eurostat_code = 'GLOBAL'
      AND m.year_val BETWEEN 2021 AND 2023
    GROUP BY m.year_val
)
SELECT p.year, p.country,
       ROUND(g.average_gpr, 2) AS average_global_gpr,
       ROUND(p.household_gas_price, 4) AS household_gas_price,
       ROUND(CASE
           WHEN p.previous_year_household_gas_price IS NULL
             OR p.previous_year_household_gas_price = 0 THEN NULL
           ELSE ((p.household_gas_price - p.previous_year_household_gas_price)
                / p.previous_year_household_gas_price) * 100
       END, 2) AS gas_price_variation_pct
FROM price_with_lag p
JOIN gpr_by_year g ON p.year = g.year
ORDER BY p.country, p.year;


-- 6. WINDOW ANALYSIS: 2024 ENERGY-DEPENDENCY RANKING AND PERCENTILE
-- Ranks European countries by import dependency in 2024. The ascending
-- percentile assigns the highest value to the most dependent countries.
SELECT
    g.country_name AS country,
    ROUND(dep.dep_rate_val, 2) AS import_dependency_rate_2024_pct,
    DENSE_RANK() OVER (ORDER BY dep.dep_rate_val DESC) AS dependency_rank,
    ROUND(PERCENT_RANK() OVER (ORDER BY dep.dep_rate_val ASC)::numeric * 100, 2)
        AS dependency_percentile
FROM fact_import_dependency dep
JOIN dt_year y ON dep.year_sk = y.year_sk
JOIN dim_geo_entity g ON dep.geo_sk = g.geo_sk
JOIN dt_energy_product prod ON dep.product_sk = prod.product_sk
WHERE y.year_value = 2024
  AND prod.siec_code = 'TOTAL'
  AND g.entity_type = 'Country'
  AND dep.dep_rate_val IS NOT NULL
ORDER BY dependency_rank;


-- 7. ANNUAL ROLL-UP OF OIL-STOCK AUTONOMY
-- Analyses only stocks expressed in equivalent days, without aggregating them
-- with consumption, imports, minimum levels, or method codes. Complete years
-- from 2020 to 2025 are included; 2026 is excluded because it is partial.
SELECT
    y.year_value AS year,
    g.country_name AS country,
    ROUND(AVG(s.indicator_value), 2) AS average_equivalent_days,
    ROUND(MIN(s.indicator_value), 2) AS minimum_equivalent_days,
    ROUND(MAX(s.indicator_value), 2) AS maximum_equivalent_days
FROM fact_oil_stocks s
JOIN dt_month m ON s.month_sk = m.month_sk
JOIN dt_year y ON m.year_val = y.year_sk
JOIN dim_geo_entity g ON s.geo_sk = g.geo_sk
JOIN dt_stock_indicator ind ON s.indicator_sk = ind.indicator_sk
JOIN dt_measure_unit u ON s.measure_unit_sk = u.measure_unit_sk
WHERE g.entity_type = 'Country'
  AND y.year_value BETWEEN 2020 AND 2025
  AND ind.indicator_code = 'STK_EUE_DIR'
  AND u.unit_code = 'NR'
GROUP BY y.year_value, g.country_name
ORDER BY y.year_value DESC, average_equivalent_days DESC;
