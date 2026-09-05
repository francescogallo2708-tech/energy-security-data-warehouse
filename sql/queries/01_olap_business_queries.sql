-- ==============================================================================
-- QUERY OLAP & ANALISI ANALITICA - DATA WAREHOUSE ENERGY SECURITY & GPR
-- ==============================================================================

-- 1. DRILL-ACROSS E CORRELAZIONE TRA GPR GLOBALE E PREZZI ELETTRICI
-- Per ogni paese calcola il coefficiente di Pearson tra il GPR globale medio
-- annuale e il prezzo medio annuo dell'elettricità non-household (fascia IC,
-- EUR/kWh, IVA esclusa). Le due serie vengono aggregate separatamente prima
-- del join per rispettare le rispettive granularità mensile e semestrale. Sono
-- inclusi solo i paesi con almeno 18 anni confrontabili.
WITH gpr_by_year AS (
    SELECT
        m.year_val AS anno,
        AVG(gpr.gpr_val) AS gpr_medio_annuale
    FROM fact_gpr gpr
    JOIN dt_month m ON m.month_sk = gpr.month_sk
    JOIN dim_geo_entity geo ON geo.geo_sk = gpr.geo_sk
    WHERE geo.eurostat_code = 'GLOBAL'
    GROUP BY m.year_val
),
price_by_country_year AS (
    SELECT
        s.year_val AS anno,
        g.country_name AS paese,
        AVG(p.price_val) AS prezzo_medio_annuale
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
        p.anno,
        p.paese,
        g.gpr_medio_annuale,
        p.prezzo_medio_annuale
    FROM price_by_country_year p
    JOIN gpr_by_year g ON g.anno = p.anno
)
SELECT
    paese,
    COUNT(*) AS anni_confrontabili,
    MIN(anno) AS primo_anno,
    MAX(anno) AS ultimo_anno,
    ROUND(CORR(
        gpr_medio_annuale::DOUBLE PRECISION,
        prezzo_medio_annuale::DOUBLE PRECISION
    )::NUMERIC, 3)
        AS correlazione_pearson_gpr_prezzo
FROM paired_series
GROUP BY paese
HAVING COUNT(*) >= 18
ORDER BY correlazione_pearson_gpr_prezzo DESC NULLS LAST, paese;


-- 2. WINDOW ANALYSIS SULLE SCORTE PETROLIFERE D'EMERGENZA
-- Calcola i giorni equivalenti di scorte con una media mobile a 3 mesi
-- (Window Function), mantenendo il dettaglio mensile e senza mescolare
-- indicatori o unità differenti. Non è un drill-down/roll-up.
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


-- 3. DRILL-ACROSS E SLICE & DICE: DIPENDENZA ENERGETICA E PREZZI DEL GAS
-- Confronta annualmente il tasso di dipendenza dalle importazioni con i prezzi
-- del gas nelle fasce Eurostat D2 (household) e I3 (non-household), in EUR/kWh
-- con X_VAT. Le due fact vengono aggregate separatamente prima del join.
WITH dependency_by_year AS (
    SELECT
        y.year_value AS anno,
        g.geo_sk,
        g.country_name AS paese,
        AVG(dep.dep_rate_val) AS tasso_dipendenza_import_pct
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
        s.year_val AS anno,
        ep.geo_sk,
        AVG(CASE WHEN cb.consumer_type = 'HOUSEHOLD' THEN ep.price_val END)
            AS prezzo_gas_household,
        AVG(CASE WHEN cb.consumer_type = 'NON_HOUSEHOLD' THEN ep.price_val END)
            AS prezzo_gas_non_household
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
    d.anno,
    d.paese,
    ROUND(d.tasso_dipendenza_import_pct, 2) AS tasso_dipendenza_import_pct,
    ROUND(p.prezzo_gas_household, 4) AS prezzo_gas_household,
    ROUND(p.prezzo_gas_non_household, 4) AS prezzo_gas_non_household
FROM dependency_by_year d
LEFT JOIN gas_price_by_year p
  ON p.anno = d.anno
 AND p.geo_sk = d.geo_sk
WHERE p.geo_sk IS NOT NULL
ORDER BY d.anno DESC, tasso_dipendenza_import_pct DESC, d.paese;


-- 4. ANALISI DINAMICA APPARTENENZA UE (TRAMITE TABELLA PONTE BR_GEO_EU_MEMBERSHIP)
-- Aggrega prima le fact a livello paese-anno per evitare duplicazioni tra semestri.
-- Vengono mantenuti solo gli anni in cui entrambe le metriche sono disponibili.
-- Il risultato mostra separatamente i membri UE teorici e i contributori
-- effettivi alle medie, che possono non coincidere.
WITH eu_members AS (
    SELECT br.year_sk, COUNT(DISTINCT br.geo_sk) AS numero_paesi_membri_ue
    FROM br_geo_eu_membership br
    GROUP BY br.year_sk
),
dependency_country_year AS (
    SELECT d.year_sk, d.geo_sk, AVG(d.dep_rate_val) AS dipendenza_paese_pct
    FROM fact_import_dependency d
    JOIN dt_energy_product prod ON d.product_sk = prod.product_sk
    JOIN br_geo_eu_membership br ON br.year_sk = d.year_sk AND br.geo_sk = d.geo_sk
    WHERE prod.siec_code = 'TOTAL'
    GROUP BY d.year_sk, d.geo_sk
),
dependency_eu_year AS (
    SELECT year_sk,
           COUNT(*) AS numero_paesi_contributori_dipendenza,
           AVG(dipendenza_paese_pct) AS dipendenza_media_membri_ue_pct
    FROM dependency_country_year
    GROUP BY year_sk
),
price_country_year AS (
    SELECT s.year_val AS year_sk, ep.geo_sk, AVG(ep.price_val) AS prezzo_paese_elettricita
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
           COUNT(*) AS numero_paesi_contributori_prezzo,
           AVG(prezzo_paese_elettricita) AS prezzo_medio_elettricita_ue
    FROM price_country_year
    GROUP BY year_sk
)
SELECT y.year_value AS anno,
       m.numero_paesi_membri_ue,
       d.numero_paesi_contributori_dipendenza,
       p.numero_paesi_contributori_prezzo,
       ROUND(d.dipendenza_media_membri_ue_pct, 2) AS dipendenza_media_membri_ue_pct,
       ROUND(p.prezzo_medio_elettricita_ue, 4) AS prezzo_medio_elettricita_ue
FROM eu_members m
JOIN dt_year y ON m.year_sk = y.year_sk
LEFT JOIN dependency_eu_year d ON d.year_sk = m.year_sk
LEFT JOIN price_eu_year p ON p.year_sk = m.year_sk
WHERE d.year_sk IS NOT NULL
  AND p.year_sk IS NOT NULL
ORDER BY y.year_value DESC;
