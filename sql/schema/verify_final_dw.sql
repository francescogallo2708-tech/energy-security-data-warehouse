-- Verifiche finali dopo il caricamento completo su database vuoto.
-- Ogni query deve restituire conteggi coerenti e nessun orfano/duplicato.

SELECT 'FACT_GPR' AS fact_table, COUNT(*) AS row_count,
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
FROM FACT_OIL_STOCKS;

SELECT 'GPR duplicate natural keys' AS check_name, COUNT(*) AS issue_count
FROM (
    SELECT month_sk, geo_sk
    FROM FACT_GPR GROUP BY month_sk, geo_sk HAVING COUNT(*) > 1
) duplicates
UNION ALL
SELECT 'Import dependency duplicate natural keys', COUNT(*)
FROM (
    SELECT year_sk, geo_sk, product_sk
    FROM FACT_IMPORT_DEPENDENCY
    GROUP BY year_sk, geo_sk, product_sk HAVING COUNT(*) > 1
) duplicates
UNION ALL
SELECT 'Energy price duplicate natural keys', COUNT(*)
FROM (
    SELECT semester_sk, geo_sk, consumption_band_sk, tax_level_sk, price_unit_sk
    FROM FACT_ENERGY_PRICE
    GROUP BY semester_sk, geo_sk, consumption_band_sk, tax_level_sk, price_unit_sk
    HAVING COUNT(*) > 1
) duplicates
UNION ALL
SELECT 'Oil stocks duplicate natural keys', COUNT(*)
FROM (
    SELECT month_sk, geo_sk, indicator_sk, measure_unit_sk
    FROM FACT_OIL_STOCKS
    GROUP BY month_sk, geo_sk, indicator_sk, measure_unit_sk HAVING COUNT(*) > 1
) duplicates;

SELECT 'Import dependency orphan dimensions' AS check_name, COUNT(*) AS issue_count
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
   OR u.measure_unit_sk IS NULL;
