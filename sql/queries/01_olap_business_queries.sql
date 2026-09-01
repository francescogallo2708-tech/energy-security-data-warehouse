-- ==============================================================================
-- QUERY OLAP & ANALISI ANALITICA - DATA WAREHOUSE ENERGY SECURITY & GPR
-- ==============================================================================

-- 1. ANALISI CORRELAZIONE RISCHIO GEOPOLITICO GLOBALE E PREZZI ENERGIA NEI PAESI (CROSS-PROCESSO)
-- Calcola la media annuale dell'indice Geopolitical Risk (GPR) rispetto ai prezzi medi
-- dell'Elettricità per consumatori Non-Household nei principali paesi europei.
SELECT 
    y.year_value AS anno,
    g.country_name AS paese,
    ROUND(AVG(gpr.gpr_val), 2) AS gpr_medio_annuale,
    ROUND(AVG(p.price_val), 4) AS prezzo_medio_elettricita_non_household
FROM fact_energy_price p
JOIN dt_semester s ON p.semester_sk = s.semester_sk
JOIN dt_year y ON s.year_val = y.year_sk
JOIN dim_geo_entity g ON p.geo_sk = g.geo_sk
JOIN dt_month m ON m.year_val = y.year_sk
JOIN dim_geo_entity g_global ON g_global.eurostat_code = 'GLOBAL'
JOIN fact_gpr gpr ON gpr.month_sk = m.month_sk AND gpr.geo_sk = g_global.geo_sk
WHERE UPPER(p.commodity_type) = 'ELECTRICITY'
  AND UPPER(p.consumer_type) = 'NON_HOUSEHOLD'
GROUP BY y.year_value, g.country_name
ORDER BY y.year_value DESC, gpr_medio_annuale DESC;


-- 2. DRILL-DOWN / ROLL-UP SULLE SCORTE PETROLIFERE D'EMERGENZA
-- Calcola l'andamento delle scorte petrolifere mensili con la media mobile (Window Function) a 3 mesi
-- per rilevare cali improvvisi delle riserve strategiche durante periodi di crisi.
SELECT 
    m.month_sk AS mese,
    g.country_name AS paese,
    ind.indicator_label AS indicatore,
    s.stock_value AS scorta_mensile,
    ROUND(AVG(s.stock_value) OVER (
        PARTITION BY s.geo_sk, s.indicator_sk 
        ORDER BY m.month_sk 
        ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
    ), 2) AS media_mobile_3_mesi
FROM fact_oil_stocks s
JOIN dt_month m ON s.month_sk = m.month_sk
JOIN dim_geo_entity g ON s.geo_sk = g.geo_sk
JOIN dt_stock_indicator ind ON s.indicator_sk = ind.indicator_sk
WHERE g.eurostat_code IN ('IT', 'DE', 'FR', 'ES')
ORDER BY g.country_name, m.month_sk DESC;


-- 3. SLICE & DICE: VALUTAZIONE DIPENDENZA ENERGETICA E PREZZI GAS HOUSEHOLD vs NON-HOUSEHOLD
-- Confronta il tasso di dipendenza dalle importazioni energetiche con i prezzi del Gas per tipo consumatore.
SELECT 
    y.year_value AS anno,
    g.country_name AS paese,
    ROUND(AVG(dep.dep_rate_val), 2) AS tasso_dipendenza_import_pct,
    ROUND(AVG(CASE WHEN UPPER(p.consumer_type) = 'HOUSEHOLD' THEN p.price_val END), 4) AS prezzo_gas_household,
    ROUND(AVG(CASE WHEN UPPER(p.consumer_type) = 'NON_HOUSEHOLD' THEN p.price_val END), 4) AS prezzo_gas_non_household
FROM fact_import_dependency dep
JOIN dt_year y ON dep.year_sk = y.year_sk
JOIN dim_geo_entity g ON dep.geo_sk = g.geo_sk
LEFT JOIN dt_semester s ON s.year_val = y.year_sk
LEFT JOIN fact_energy_price p ON p.semester_sk = s.semester_sk 
                             AND p.geo_sk = g.geo_sk 
                             AND UPPER(p.commodity_type) = 'GAS'
WHERE g.entity_type = 'Country'
GROUP BY y.year_value, g.country_name
HAVING AVG(dep.dep_rate_val) IS NOT NULL
ORDER BY y.year_value DESC, tasso_dipendenza_import_pct DESC;
