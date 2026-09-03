-- Migrazione della fact GPR allo scope recente GPR/GPRT/GPRA.
-- Lo scope analitico inizia nel 1985-01, primo mese in cui tutte e tre
-- le serie selezionate sono valorizzate nel file sorgente corrente.

BEGIN;

-- Elimina esclusivamente record non utilizzabili nel modello selezionato:
-- chiavi mancanti, mesi anteriori allo scope o tre misure tutte nulle.
DELETE FROM FACT_GPR
WHERE month_sk IS NULL
   OR geo_sk IS NULL
   OR month_sk < '1985-01'
   OR (gpr_val IS NULL AND gprt_val IS NULL AND gpra_val IS NULL);

-- Una riga parzialmente valorizzata renderebbe le tre serie non confrontabili.
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM FACT_GPR
        WHERE gpr_val IS NULL
           OR gprt_val IS NULL
           OR gpra_val IS NULL
    ) THEN
        RAISE EXCEPTION
            'FACT_GPR contiene record parziali: verificare GPR, GPRT e GPRA prima della migrazione';
    END IF;
END $$;

ALTER TABLE FACT_GPR
    ALTER COLUMN month_sk SET NOT NULL,
    ALTER COLUMN geo_sk SET NOT NULL,
    ALTER COLUMN gpr_val SET NOT NULL,
    ALTER COLUMN gprt_val SET NOT NULL,
    ALTER COLUMN gpra_val SET NOT NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'ck_gpr_scope_start'
          AND conrelid = 'fact_gpr'::regclass
    ) THEN
        ALTER TABLE FACT_GPR
            ADD CONSTRAINT ck_gpr_scope_start
            CHECK (month_sk >= '1985-01');
    END IF;
END $$;

COMMENT ON TABLE FACT_GPR IS
    'Monthly global GPR, GPRT and GPRA series; analytical scope starts at 1985-01';

COMMENT ON COLUMN FACT_GPR.gpr_val IS
    'Geopolitical Risk index';

COMMENT ON COLUMN FACT_GPR.gprt_val IS
    'Geopolitical Risk Threats index';

COMMENT ON COLUMN FACT_GPR.gpra_val IS
    'Geopolitical Risk Acts index';

COMMIT;

-- Controlli informativi. Con il file data_gpr_export_202608.xls corrente
-- sono attese 499 righe, da 1985-01 a 2026-07.
SELECT
    COUNT(*) AS gpr_fact_rows,
    MIN(month_sk) AS first_month,
    MAX(month_sk) AS last_month
FROM FACT_GPR;

SELECT COUNT(*) AS invalid_or_incomplete_rows
FROM FACT_GPR
WHERE month_sk < '1985-01'
   OR gpr_val IS NULL
   OR gprt_val IS NULL
   OR gpra_val IS NULL;
