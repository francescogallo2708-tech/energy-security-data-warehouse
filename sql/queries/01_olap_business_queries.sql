-- ==============================================================================
-- QUERY OLAP & ANALISI ANALITICA - DATA WAREHOUSE ENERGY SECURITY & GPR
-- ==============================================================================

-- 1. ANALISI CORRELAZIONE RISCHIO GEOPOLITICO GLOBALE E PREZZI ENERGIA NEI PAESI (CROSS-PROCESSO)
-- Calcola la media annuale dell'indice Geopolitical Risk (GPR) rispetto ai prezzi medi
-- dell'Elettricità nei paesi europei per consumatori Non-Household nella fascia Eurostat IC,
-- espressi in EUR/kWh ed esclusi IVA e tributi recuperabili.
SELECT 
    y.year_value AS anno,
    g.country_name AS paese,
    ROUND(AVG(gpr.gpr_val), 2) AS gpr_medio_annuale,
    ROUND(AVG(p.price_val), 4) AS prezzo_medio_elettricita_non_household
FROM fact_energy_price p
JOIN dt_semester s ON p.semester_sk = s.semester_sk
JOIN dt_year y ON s.year_val = y.year_sk
JOIN dim_geo_entity g ON p.geo_sk = g.geo_sk
JOIN dt_consumption_band cb ON p.consumption_band_sk = cb.consumption_band_sk
JOIN dt_tax_level tl ON p.tax_level_sk = tl.tax_level_sk
JOIN dt_price_unit pu ON p.price_unit_sk = pu.price_unit_sk
JOIN dt_month m ON m.year_val = y.year_sk
JOIN dim_geo_entity g_global ON g_global.eurostat_code = 'GLOBAL'
JOIN fact_gpr gpr ON gpr.month_sk = m.month_sk AND gpr.geo_sk = g_global.geo_sk
WHERE cb.commodity_type = 'ELECTRICITY'
  AND cb.consumer_type = 'NON_HOUSEHOLD'
  AND cb.band_code = 'MWH500-1999'
  AND tl.tax_code = 'X_VAT'
  AND pu.currency_code = 'EUR'
  AND pu.energy_unit_code = 'KWH'
  AND g.entity_type = 'Country'
GROUP BY y.year_value, g.country_name
ORDER BY y.year_value DESC, gpr_medio_annuale DESC;


-- 2. DRILL-DOWN / ROLL-UP SULLE SCORTE PETROLIFERE D'EMERGENZA
-- Calcola i giorni equivalenti di scorte di emergenza con la media mobile
-- (Window Function) a 3 mesi, senza mescolare indicatori o unita differenti.
SELECT 
    m.month_sk AS mese,
    g.country_name AS paese,
    ind.indicator_label AS indicatore,
    s.indicator_value AS giorni_equivalenti,
    ROUND(AVG(s.indicator_value) OVER (
        PARTITION BY s.geo_sk, s.indicator_sk 
        ORDER BY m.month_sk 
        ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
    ), 2) AS media_mobile_3_mesi_giorni
FROM fact_oil_stocks s
JOIN dt_month m ON s.month_sk = m.month_sk
JOIN dim_geo_entity g ON s.geo_sk = g.geo_sk
JOIN dt_stock_indicator ind ON s.indicator_sk = ind.indicator_sk
JOIN dt_measure_unit u ON s.measure_unit_sk = u.measure_unit_sk
WHERE g.eurostat_code IN ('IT', 'DE', 'FR', 'ES')
  AND ind.indicator_code = 'STK_EUE_DIR'
  AND u.unit_code = 'NR'
ORDER BY g.country_name, m.month_sk DESC;


-- 3. SLICE & DICE: VALUTAZIONE DIPENDENZA ENERGETICA E PREZZI GAS HOUSEHOLD vs NON-HOUSEHOLD
-- Confronta il tasso di dipendenza dalle importazioni energetiche con i prezzi del Gas
-- nelle fasce Eurostat di riferimento D2 (Household) e I3 (Non-Household), entrambi
-- espressi in EUR/kWh ed esclusi IVA e tributi recuperabili.
SELECT 
    y.year_value AS anno,
    g.country_name AS paese,
    ROUND(AVG(dep.dep_rate_val), 2) AS tasso_dipendenza_import_pct,
    ROUND(AVG(CASE WHEN p.consumer_type = 'HOUSEHOLD' THEN p.price_val END), 4) AS prezzo_gas_household,
    ROUND(AVG(CASE WHEN p.consumer_type = 'NON_HOUSEHOLD' THEN p.price_val END), 4) AS prezzo_gas_non_household
FROM fact_import_dependency dep
JOIN dt_year y ON dep.year_sk = y.year_sk
JOIN dim_geo_entity g ON dep.geo_sk = g.geo_sk
JOIN dt_energy_product prod ON dep.product_sk = prod.product_sk
LEFT JOIN dt_semester s ON s.year_val = y.year_sk
LEFT JOIN (
    SELECT
        ep.semester_sk,
        ep.geo_sk,
        cb.consumer_type,
        ep.price_val
    FROM fact_energy_price ep
    JOIN dt_consumption_band cb
      ON ep.consumption_band_sk = cb.consumption_band_sk
    JOIN dt_tax_level tl ON ep.tax_level_sk = tl.tax_level_sk
    JOIN dt_price_unit pu ON ep.price_unit_sk = pu.price_unit_sk
    WHERE cb.commodity_type = 'GAS'
      AND (
            (cb.consumer_type = 'HOUSEHOLD' AND cb.band_code = 'GJ20-199')
         OR (cb.consumer_type = 'NON_HOUSEHOLD' AND cb.band_code = 'GJ10000-99999')
      )
      AND tl.tax_code = 'X_VAT'
      AND pu.currency_code = 'EUR'
      AND pu.energy_unit_code = 'KWH'
) p ON p.semester_sk = s.semester_sk
   AND p.geo_sk = g.geo_sk
WHERE g.entity_type = 'Country'
  AND prod.siec_code = 'TOTAL'
GROUP BY y.year_value, g.country_name
HAVING AVG(dep.dep_rate_val) IS NOT NULL
ORDER BY y.year_value DESC, tasso_dipendenza_import_pct DESC;


-- 4. ANALISI DINAMICA APPARTENENZA UE (TRAMITE TABELLA PONTE BR_GEO_EU_MEMBERSHIP)
-- Calcola la dipendenza energetica media ed i prezzi dell'energia per i soli paesi
-- che erano EFFETTIVAMENTE membri dell'Unione Europea in ciascun specifico anno storico.
-- Il prezzo usa l'Elettricità Non-Household, fascia Eurostat IC, EUR/kWh e X_VAT.
SELECT 
    y.year_value AS anno,
    COUNT(DISTINCT g.geo_sk) AS numero_paesi_membri_ue,
    ROUND(AVG(dep.dep_rate_val), 2) AS dipendenza_media_membri_ue_pct,
    ROUND(AVG(p.price_val), 4) AS prezzo_medio_elettricita_ue
FROM br_geo_eu_membership br
JOIN dt_year y ON br.year_sk = y.year_sk
JOIN dim_geo_entity g ON br.geo_sk = g.geo_sk
LEFT JOIN (
    SELECT
        d.year_sk,
        d.geo_sk,
        d.dep_rate_val
    FROM fact_import_dependency d
    JOIN dt_energy_product prod ON d.product_sk = prod.product_sk
    WHERE prod.siec_code = 'TOTAL'
) dep ON dep.year_sk = y.year_sk
     AND dep.geo_sk = g.geo_sk
LEFT JOIN dt_semester s ON s.year_val = y.year_sk
LEFT JOIN (
    SELECT
        ep.semester_sk,
        ep.geo_sk,
        ep.price_val
    FROM fact_energy_price ep
    JOIN dt_consumption_band cb
      ON ep.consumption_band_sk = cb.consumption_band_sk
    JOIN dt_tax_level tl ON ep.tax_level_sk = tl.tax_level_sk
    JOIN dt_price_unit pu ON ep.price_unit_sk = pu.price_unit_sk
    WHERE cb.commodity_type = 'ELECTRICITY'
      AND cb.consumer_type = 'NON_HOUSEHOLD'
      AND cb.band_code = 'MWH500-1999'
      AND tl.tax_code = 'X_VAT'
      AND pu.currency_code = 'EUR'
      AND pu.energy_unit_code = 'KWH'
) p ON p.semester_sk = s.semester_sk
   AND p.geo_sk = g.geo_sk
GROUP BY y.year_value
ORDER BY y.year_value DESC;
