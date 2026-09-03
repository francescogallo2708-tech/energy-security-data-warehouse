-- Migrazione del modello petrolifero verso soli indicatori quantitativi.
-- Eseguire questo file una sola volta sui database gia popolati, prima di
-- rilanciare src/etl/etl_load_oil_stocks.py.

BEGIN;

DO $$
DECLARE
    has_stock_value BOOLEAN;
    has_indicator_value BOOLEAN;
BEGIN
    SELECT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = current_schema()
          AND table_name = 'fact_oil_stocks'
          AND column_name = 'stock_value'
    ) INTO has_stock_value;

    SELECT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = current_schema()
          AND table_name = 'fact_oil_stocks'
          AND column_name = 'indicator_value'
    ) INTO has_indicator_value;

    IF has_stock_value AND NOT has_indicator_value THEN
        ALTER TABLE FACT_OIL_STOCKS
            RENAME COLUMN stock_value TO indicator_value;
    ELSIF has_stock_value AND has_indicator_value THEN
        RAISE EXCEPTION
            'FACT_OIL_STOCKS contiene sia stock_value sia indicator_value: migrazione interrotta';
    ELSIF NOT has_indicator_value THEN
        RAISE EXCEPTION
            'Nessuna misura trovata in FACT_OIL_STOCKS: attesa stock_value oppure indicator_value';
    END IF;
END $$;

COMMENT ON COLUMN FACT_OIL_STOCKS.indicator_value IS
    'Misura quantitativa non additiva; aggregare solo entro lo stesso indicatore e la stessa unita';

INSERT INTO DT_STOCK_INDICATOR
    (indicator_code, indicator_label, indicator_class, obligation_basis)
VALUES
    ('IC_DC',
     'Daily inland consumption for compliance',
     'Compliance consumption',
     'Compliance'),
    ('IMP_DNC',
     'Daily net imports for compliance',
     'Compliance import flow',
     'Compliance'),
    ('STK_EUE_DIR',
     'Emergency stocks held under EU Directive (days equivalent)',
     'Emergency stock',
     'EU Directive'),
    ('STK_MIN_CAL',
     'Minimum stock level for compliance - calculated',
     'Minimum stock requirement',
     'Compliance')
ON CONFLICT (indicator_code) DO UPDATE SET
    indicator_label = EXCLUDED.indicator_label,
    indicator_class = EXCLUDED.indicator_class,
    obligation_basis = EXCLUDED.obligation_basis;

-- Questi tre flussi contengono codici di metodo (1/2/3), non misure.
DELETE FROM FACT_OIL_STOCKS f
USING DT_STOCK_INDICATOR i
WHERE f.indicator_sk = i.indicator_sk
  AND i.indicator_code IN (
      'STK_EUE_DNY_MTH',
      'STK_EUE_MIN_MTH',
      'STK_EUE_MTH'
  );

DELETE FROM DT_STOCK_INDICATOR
WHERE indicator_code IN (
    'STK_EUE_DNY_MTH',
    'STK_EUE_MIN_MTH',
    'STK_EUE_MTH'
);

COMMIT;

-- Controlli informativi: dopo il successivo ETL sono attese 15.103 righe
-- con il file sorgente attualmente incluso nel progetto.
SELECT COUNT(*) AS oil_fact_rows
FROM FACT_OIL_STOCKS;

SELECT
    i.indicator_code,
    u.unit_code,
    COUNT(*) AS row_count
FROM FACT_OIL_STOCKS f
JOIN DT_STOCK_INDICATOR i ON i.indicator_sk = f.indicator_sk
JOIN DT_MEASURE_UNIT u ON u.measure_unit_sk = f.measure_unit_sk
GROUP BY i.indicator_code, u.unit_code
ORDER BY i.indicator_code, u.unit_code;
