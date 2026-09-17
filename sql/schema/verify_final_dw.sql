-- ==============================================================================
-- Final verification script: integrity and quality checks
-- Energy Security Data Warehouse
--
-- Run this script in pgAdmin or psql after ETL loading.
-- Check 1: Row counts and temporal coverage per fact table and bridge
-- Check 2: Natural key uniqueness (must all return 0)
-- Check 3: Orphan foreign keys (must all return 0)
-- Check 4: Domain validity and sanity checks (must all return 0)
-- ==============================================================================

-- ------------------------------------------------------------------------------
-- 1. Table row counts and coverage
-- ------------------------------------------------------------------------------
SELECT 'FACT_GPR' AS table_name, COUNT(*) AS row_count,
       MIN(month_sk) AS first_period, MAX(month_sk) AS last_period
FROM FACT_GPR
UNION ALL
SELECT 'FACT_IMPORT_DEPENDENCY', COUNT(*),
       MIN(year_sk)::TEXT, MAX(year_sk)::TEXT
FROM FACT_IMPORT_DEPENDENCY
UNION ALL
SELECT 'FACT_ENERGY_PRICE', COUNT(*),
       MIN(semester_sk), MAX(semester_sk)
FROM FACT_ENERGY_PRICE
UNION ALL
SELECT 'FACT_OIL_STOCKS', COUNT(*),
       MIN(month_sk), MAX(month_sk)
FROM FACT_OIL_STOCKS
UNION ALL
SELECT 'BR_GEO_EU_MEMBERSHIP', COUNT(*),
       MIN(year_sk)::TEXT, MAX(year_sk)::TEXT
FROM BR_GEO_EU_MEMBERSHIP;


-- ------------------------------------------------------------------------------
-- 2. Duplicate natural key checks (must all return 0)
-- ------------------------------------------------------------------------------
SELECT 'GPR duplicates' AS check_name, COUNT(*) AS issue_count
FROM (
    SELECT month_sk, geo_sk
    FROM FACT_GPR GROUP BY month_sk, geo_sk HAVING COUNT(*) > 1
) dup
UNION ALL
SELECT 'Import dependency duplicates', COUNT(*)
FROM (
    SELECT year_sk, geo_sk, product_sk
    FROM FACT_IMPORT_DEPENDENCY
    GROUP BY year_sk, geo_sk, product_sk HAVING COUNT(*) > 1
) dup
UNION ALL
SELECT 'Energy price duplicates', COUNT(*)
FROM (
    SELECT semester_sk, geo_sk, consumption_band_sk, tax_level_sk, price_unit_sk
    FROM FACT_ENERGY_PRICE
    GROUP BY semester_sk, geo_sk, consumption_band_sk, tax_level_sk, price_unit_sk
    HAVING COUNT(*) > 1
) dup
UNION ALL
SELECT 'Oil stocks duplicates', COUNT(*)
FROM (
    SELECT month_sk, geo_sk, indicator_sk, measure_unit_sk
    FROM FACT_OIL_STOCKS
    GROUP BY month_sk, geo_sk, indicator_sk, measure_unit_sk HAVING COUNT(*) > 1
) dup
UNION ALL
SELECT 'EU membership bridge duplicates', COUNT(*)
FROM (
    SELECT geo_sk, year_sk
    FROM BR_GEO_EU_MEMBERSHIP
    GROUP BY geo_sk, year_sk HAVING COUNT(*) > 1
) dup;


-- ------------------------------------------------------------------------------
-- 3. Orphan foreign key checks (must all return 0)
-- ------------------------------------------------------------------------------
SELECT 'GPR orphan dimensions' AS check_name, COUNT(*) AS issue_count
FROM FACT_GPR f
LEFT JOIN DT_MONTH m ON m.month_sk = f.month_sk
LEFT JOIN DIM_GEO_ENTITY g ON g.geo_sk = f.geo_sk
WHERE m.month_sk IS NULL OR g.geo_sk IS NULL
UNION ALL
SELECT 'Import dependency orphan dimensions', COUNT(*)
FROM FACT_IMPORT_DEPENDENCY f
LEFT JOIN DT_YEAR y ON y.year_sk = f.year_sk
LEFT JOIN DIM_GEO_ENTITY g ON g.geo_sk = f.geo_sk
LEFT JOIN DT_ENERGY_PRODUCT p ON p.product_sk = f.product_sk
WHERE y.year_sk IS NULL OR g.geo_sk IS NULL OR p.product_sk IS NULL
UNION ALL
SELECT 'Energy price orphan dimensions', COUNT(*)
FROM FACT_ENERGY_PRICE f
LEFT JOIN DT_SEMESTER s ON s.semester_sk = f.semester_sk
LEFT JOIN DIM_GEO_ENTITY g ON g.geo_sk = f.geo_sk
LEFT JOIN DT_CONSUMPTION_BAND b ON b.consumption_band_sk = f.consumption_band_sk
LEFT JOIN DT_TAX_LEVEL t ON t.tax_level_sk = f.tax_level_sk
LEFT JOIN DT_PRICE_UNIT u ON u.price_unit_sk = f.price_unit_sk
WHERE s.semester_sk IS NULL OR g.geo_sk IS NULL OR b.consumption_band_sk IS NULL
   OR t.tax_level_sk IS NULL OR u.price_unit_sk IS NULL
UNION ALL
SELECT 'Oil stocks orphan dimensions', COUNT(*)
FROM FACT_OIL_STOCKS f
LEFT JOIN DT_MONTH m ON m.month_sk = f.month_sk
LEFT JOIN DIM_GEO_ENTITY g ON g.geo_sk = f.geo_sk
LEFT JOIN DT_STOCK_INDICATOR i ON i.indicator_sk = f.indicator_sk
LEFT JOIN DT_MEASURE_UNIT u ON u.measure_unit_sk = f.measure_unit_sk
WHERE m.month_sk IS NULL OR g.geo_sk IS NULL OR i.indicator_sk IS NULL
   OR u.measure_unit_sk IS NULL
UNION ALL
SELECT 'EU membership bridge orphan dimensions', COUNT(*)
FROM BR_GEO_EU_MEMBERSHIP b
LEFT JOIN DIM_GEO_ENTITY g ON g.geo_sk = b.geo_sk
LEFT JOIN DT_YEAR y ON y.year_sk = b.year_sk
WHERE g.geo_sk IS NULL OR y.year_sk IS NULL;


-- ------------------------------------------------------------------------------
-- 4. Domain and value sanity checks (must all return 0)
-- ------------------------------------------------------------------------------
-- Note: Eurostat legitimately records negative prices only in micro-consumption bands
-- (KWH_LT1000, KWH1000-2499) where fixed tax credits exceed raw commodity costs (NL, CZ).
-- Any negative price outside these specific bands would be an anomaly.
SELECT 'Unexpected negative energy prices' AS check_name, COUNT(*) AS issue_count
FROM FACT_ENERGY_PRICE p
JOIN DT_CONSUMPTION_BAND cb ON p.consumption_band_sk = cb.consumption_band_sk
WHERE p.price_val < 0 AND cb.band_code NOT IN ('KWH_LT1000', 'KWH1000-2499')
UNION ALL
SELECT 'Negative gas prices', COUNT(*)
FROM FACT_ENERGY_PRICE p
JOIN DT_CONSUMPTION_BAND cb ON p.consumption_band_sk = cb.consumption_band_sk
WHERE p.price_val < 0 AND cb.commodity_type = 'GAS'
UNION ALL
SELECT 'Negative oil stock values', COUNT(*)
FROM FACT_OIL_STOCKS
WHERE indicator_value < 0
UNION ALL
SELECT 'Negative GPR values', COUNT(*)
FROM FACT_GPR
WHERE gpr_val < 0 OR gprt_val < 0 OR gpra_val < 0;
