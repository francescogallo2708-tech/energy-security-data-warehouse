-- ==============================================================================
-- QUERY OLAP AVANZATE - DATA WAREHOUSE ENERGY SECURITY & GPR (FASE 2)
-- ==============================================================================

-- 5. ANALISI DELLO SHOCK GEOPOLITICO 2022 (GUERRA IN UCRAINA)
-- Confronta i valori del GPR prima (2021), durante (2022) e dopo lo shock (2023) 
-- con la variazione percentuale dei prezzi del Gas Household nella fascia Eurostat D2,
-- espressi in EUR/kWh con tasse e tributi inclusi.
WITH price_by_year AS (
    SELECT 
        y.year_value AS anno,
        g.country_name AS paese,
        AVG(p.price_val) AS prezzo_gas_household
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
    SELECT anno, paese, prezzo_gas_household,
           LAG(prezzo_gas_household) OVER (
               PARTITION BY paese ORDER BY anno
           ) AS prezzo_gas_anno_precedente
    FROM price_by_year
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
SELECT p.anno, p.paese,
       ROUND(g.gpr_medio, 2) AS gpr_medio_globale,
       ROUND(p.prezzo_gas_household, 4) AS prezzo_gas,
       ROUND(CASE
           WHEN p.prezzo_gas_anno_precedente IS NULL
             OR p.prezzo_gas_anno_precedente = 0 THEN NULL
           ELSE ((p.prezzo_gas_household - p.prezzo_gas_anno_precedente)
                / p.prezzo_gas_anno_precedente) * 100
       END, 2) AS variazione_prezzo_pct
FROM price_with_lag p
JOIN gpr_by_year g ON p.anno = g.anno
ORDER BY p.paese, p.anno;


-- 6. RANKING PAESI PER DIPENDENZA ENERGETICA E PERCENTILE (PERCENT_RANK & DENSE_RANK)
-- Classifica i paesi europei in base alla dipendenza dalle importazioni nel 2024.
-- Il percentile crescente assegna il valore più alto ai paesi più dipendenti.
SELECT 
    g.country_name AS paese,
    ROUND(dep.dep_rate_val, 2) AS tasso_dipendenza_2024_pct,
    DENSE_RANK() OVER (ORDER BY dep.dep_rate_val DESC) AS ranking_dipendenza,
    ROUND(PERCENT_RANK() OVER (ORDER BY dep.dep_rate_val ASC)::numeric * 100, 2) AS percentile_dipendenza
FROM fact_import_dependency dep
JOIN dt_year y ON dep.year_sk = y.year_sk
JOIN dim_geo_entity g ON dep.geo_sk = g.geo_sk
JOIN dt_energy_product prod ON dep.product_sk = prod.product_sk
WHERE y.year_value = 2024
  AND prod.siec_code = 'TOTAL'
  AND g.entity_type = 'Country'
  AND dep.dep_rate_val IS NOT NULL
ORDER BY ranking_dipendenza;


-- 7. AUTONOMIA DELLE SCORTE PETROLIFERE D'EMERGENZA PER PAESE
-- Analizza esclusivamente le scorte espresse in giorni equivalenti, senza
-- aggregarle con consumi, importazioni, livelli minimi o codici di metodo.
-- Sono considerati gli anni completi 2020-2025; il 2026 è escluso perché parziale.
SELECT 
    y.year_value AS anno,
    g.country_name AS paese,
    ROUND(AVG(s.indicator_value), 2) AS giorni_equivalenti_medi,
    ROUND(MIN(s.indicator_value), 2) AS giorni_equivalenti_minimi,
    ROUND(MAX(s.indicator_value), 2) AS giorni_equivalenti_massimi
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
ORDER BY y.year_value DESC, giorni_equivalenti_medi DESC;
