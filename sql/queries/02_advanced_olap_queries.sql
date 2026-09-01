-- ==============================================================================
-- QUERY OLAP AVANZATE - DATA WAREHOUSE ENERGY SECURITY & GPR (FASE 2)
-- ==============================================================================

-- 5. ANALISI DELLO SHOCK GEOPOLITICO 2022 (GUERRA IN UCRAINA)
-- Confronta i valori del GPR prima (2021), durante (2022) e dopo lo shock (2023) 
-- con la variazione percentuale dei prezzi del Gas Household nei paesi europei.
WITH price_by_year AS (
    SELECT 
        y.year_value AS anno,
        g.country_name AS paese,
        AVG(p.price_val) AS prezzo_gas_household
    FROM fact_energy_price p
    JOIN dt_semester s ON p.semester_sk = s.semester_sk
    JOIN dt_year y ON s.year_val = y.year_sk
    JOIN dim_geo_entity g ON p.geo_sk = g.geo_sk
    WHERE UPPER(p.commodity_type) = 'GAS'
      AND UPPER(p.consumer_type) = 'HOUSEHOLD'
      AND y.year_value BETWEEN 2021 AND 2023
    GROUP BY y.year_value, g.country_name
),
gpr_by_year AS (
    SELECT 
        m.year_val AS anno,
        AVG(gpr.gpr_val) AS gpr_medio
    FROM fact_gpr gpr
    JOIN dt_month m ON gpr.month_sk = m.month_sk
    JOIN dim_geo_entity g ON gpr.geo_sk = g.geo_sk
    WHERE g.eurostat_code = 'GLOBAL'
      AND m.year_val BETWEEN 2021 AND 2023
    GROUP BY m.year_val
)
SELECT 
    p.anno,
    p.paese,
    ROUND(g.gpr_medio, 2) AS gpr_medio_globale,
    ROUND(p.prezzo_gas_household, 4) AS prezzo_gas,
    ROUND(
        CASE 
            WHEN LAG(p.prezzo_gas_household) OVER (PARTITION BY p.paese ORDER BY p.anno) IS NULL 
              OR LAG(p.prezzo_gas_household) OVER (PARTITION BY p.paese ORDER BY p.anno) = 0 THEN NULL
            ELSE ((p.prezzo_gas_household - LAG(p.prezzo_gas_household) OVER (PARTITION BY p.paese ORDER BY p.anno)) 
                 / LAG(p.prezzo_gas_household) OVER (PARTITION BY p.paese ORDER BY p.anno)) * 100
        END, 2
    ) AS variazione_prezzo_pct
FROM price_by_year p
JOIN gpr_by_year g ON p.anno = g.anno
ORDER BY p.paese, p.anno;


-- 6. RANKING PAESI PER DIPENDENZA ENERGETICA E COPERTURA PREZZI (PERCENT_RANK & DENSE_RANK)
-- Classifica i paesi europei in base alla dipendenza dalle importazioni nel 2024 e calcola il loro rango.
SELECT 
    g.country_name AS paese,
    ROUND(dep.dep_rate_val, 2) AS tasso_dipendenza_2024_pct,
    DENSE_RANK() OVER (ORDER BY dep.dep_rate_val DESC) AS ranking_dipendenza,
    ROUND(PERCENT_RANK() OVER (ORDER BY dep.dep_rate_val ASC)::numeric * 100, 2) AS percentile_dipendenza
FROM fact_import_dependency dep
JOIN dt_year y ON dep.year_sk = y.year_sk
JOIN dim_geo_entity g ON dep.geo_sk = g.geo_sk
WHERE y.year_value = 2024
  AND dep.siec_code = 'TOTAL'
  AND g.entity_type = 'Country'
ORDER BY ranking_dipendenza;


-- 7. AUTONOMIA SCORTE PETROLIFERE D'EMERGENZA PER PAESE (LEVEL MEASURE vs SOGLIE DI SICUREZZA)
-- Analisi delle scorte petrolifere per verificare l'andamento delle riserve strategiche
-- rispetto ai requisiti minimi di sicurezza energetica europea.
SELECT 
    y.year_value AS anno,
    g.country_name AS paese,
    ROUND(AVG(s.stock_value), 2) AS scorta_media_mensile,
    ROUND(MIN(s.stock_value), 2) AS scorta_minima_registrata,
    ROUND(MAX(s.stock_value), 2) AS scorta_massima_registrata
FROM fact_oil_stocks s
JOIN dt_month m ON s.month_sk = m.month_sk
JOIN dt_year y ON m.year_val = y.year_sk
JOIN dim_geo_entity g ON s.geo_sk = g.geo_sk
WHERE g.entity_type = 'Country'
  AND y.year_value >= 2020
GROUP BY y.year_value, g.country_name
ORDER BY y.year_value DESC, scorta_media_mensile DESC;
