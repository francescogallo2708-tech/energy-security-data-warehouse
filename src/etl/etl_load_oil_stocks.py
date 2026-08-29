import getpass
import os
import re

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values


DB_CONFIG = {
    'dbname': os.environ.get('PGDATABASE', 'energy_gpr_dw'),
    'user': os.environ.get('PGUSER', 'postgres'),
    'password': os.environ.get('PGPASSWORD') or getpass.getpass('Password PostgreSQL: '),
    'host': os.environ.get('PGHOST', 'localhost'),
    'port': os.environ.get('PGPORT', '5433')
}

STOCK_INDICATORS = {
    'IC_DC': ('Closing stock level', 'Stock level', None),
    'IMP_DNC': ('Net imports', 'Import flow', None),
    'STK_EUE_DIR': ('Emergency stocks under EU directive', 'Emergency stock', 'EU directive'),
    'STK_EUE_DNY_MTH': ('Days of net imports covered by emergency stocks', 'Emergency stock coverage', 'Days/months'),
    'STK_EUE_MIN_MTH': ('Minimum emergency stock obligation in months', 'Emergency stock obligation', 'Minimum months'),
    'STK_EUE_MTH': ('Emergency stocks in months of consumption', 'Emergency stock coverage', 'Months'),
    'STK_MIN_CAL': ('Minimum stock obligation calendar days', 'Emergency stock obligation', 'Calendar days'),
}

MEASURE_UNITS = {
    'THS_T': 'Thousand tonnes',
    'NR': 'Number',
}


def extract_flag(raw_value):
    text = str(raw_value).strip()
    flags = ''.join(re.findall(r'[A-Za-z]+', text))
    return flags or None


def load_oil_stocks_fact():
    print("--- AVVIO ETL FACT_OIL_STOCKS ---")

    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(script_dir)
    tsv_file = os.path.join(project_dir, "Dataset", "raw", "eurostat", "nrg_stk_oem_tabular.tsv")

    if not os.path.exists(tsv_file):
        print(f"[ERRORE] File {tsv_file} non trovato.")
        return

    print(f"Trovato file sorgente: {tsv_file}")

    try:
        df_raw = pd.read_csv(tsv_file, sep='\t', low_memory=False)
        print(f"File caricato. Righe grezze: {len(df_raw)}")

        first_col = df_raw.columns[0]
        df_split = df_raw[first_col].str.split(',', expand=True)
        df_split.columns = ['freq', 'stk_flow', 'unit', 'geo']

        df_data = pd.concat([df_split, df_raw.drop(columns=[first_col])], axis=1)
        df_data.columns = [str(c).strip() for c in df_data.columns]

        month_cols = [c for c in df_data.columns if re.match(r'^\d{4}-\d{2}$', c)]

        df_long = pd.melt(
            df_data,
            id_vars=['freq', 'stk_flow', 'unit', 'geo'],
            value_vars=month_cols,
            var_name='month_sk',
            value_name='raw_val'
        )

        df_long['clean_val'] = df_long['raw_val'].astype(str).str.replace(r'[^\d.-]', '', regex=True)
        df_long['stock_value'] = pd.to_numeric(df_long['clean_val'], errors='coerce')
        df_long['eurostat_flag'] = df_long['raw_val'].apply(extract_flag)
        df_valid = df_long.dropna(subset=['stock_value']).copy()

        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        indicator_rows = [
            (code, label, indicator_class, obligation_basis)
            for code, (label, indicator_class, obligation_basis) in STOCK_INDICATORS.items()
        ]
        execute_values(
            cursor,
            """
            INSERT INTO DT_STOCK_INDICATOR
            (indicator_code, indicator_label, indicator_class, obligation_basis)
            VALUES %s
            ON CONFLICT (indicator_code) DO UPDATE SET
                indicator_label = EXCLUDED.indicator_label,
                indicator_class = EXCLUDED.indicator_class,
                obligation_basis = EXCLUDED.obligation_basis;
            """,
            indicator_rows
        )

        unit_rows = [(code, label) for code, label in MEASURE_UNITS.items()]
        execute_values(
            cursor,
            """
            INSERT INTO DT_MEASURE_UNIT (unit_code, unit_label)
            VALUES %s
            ON CONFLICT (unit_code) DO UPDATE SET
                unit_label = EXCLUDED.unit_label;
            """,
            unit_rows
        )

        cursor.execute("SELECT eurostat_code, geo_sk FROM DIM_GEO_ENTITY;")
        geo_map = dict(cursor.fetchall())

        cursor.execute("SELECT indicator_code, indicator_sk FROM DT_STOCK_INDICATOR;")
        indicator_map = dict(cursor.fetchall())

        cursor.execute("SELECT unit_code, measure_unit_sk FROM DT_MEASURE_UNIT;")
        unit_map = dict(cursor.fetchall())

        cursor.execute("SELECT month_sk FROM DT_MONTH;")
        valid_months = set(r[0] for r in cursor.fetchall())

        df_filtered = df_valid[
            df_valid['geo'].isin(geo_map)
            & df_valid['stk_flow'].isin(indicator_map)
            & df_valid['unit'].isin(unit_map)
            & df_valid['month_sk'].isin(valid_months)
        ].copy()

        df_filtered['geo_sk'] = df_filtered['geo'].map(geo_map)
        df_filtered['indicator_sk'] = df_filtered['stk_flow'].map(indicator_map)
        df_filtered['measure_unit_sk'] = df_filtered['unit'].map(unit_map)
        df_filtered['compliance_status'] = None

        key_cols = ['month_sk', 'geo_sk', 'indicator_sk', 'measure_unit_sk']
        df_dedup = df_filtered.drop_duplicates(subset=key_cols, keep='last')

        tuples_to_insert = [
            (
                row['month_sk'],
                int(row['geo_sk']),
                int(row['indicator_sk']),
                int(row['measure_unit_sk']),
                row['compliance_status'],
                row['eurostat_flag'],
                float(row['stock_value'])
            )
            for _, row in df_dedup.iterrows()
        ]

        print(f"Record pronti per l'inserimento: {len(tuples_to_insert)}")

        execute_values(
            cursor,
            """
            INSERT INTO FACT_OIL_STOCKS
            (month_sk, geo_sk, indicator_sk, measure_unit_sk, compliance_status, eurostat_flag, stock_value)
            VALUES %s
            ON CONFLICT (month_sk, geo_sk, indicator_sk, measure_unit_sk) DO UPDATE SET
                compliance_status = EXCLUDED.compliance_status,
                eurostat_flag = EXCLUDED.eurostat_flag,
                stock_value = EXCLUDED.stock_value;
            """,
            tuples_to_insert
        )

        conn.commit()
        print(f"[SUCCESSO] Inseriti/Aggiornati {len(tuples_to_insert)} record nella tabella FACT_OIL_STOCKS.")

    except Exception as e:
        print(f"[ERRORE] Durante l'ETL Oil Stocks: {e}")
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()
        print("--- FINE ETL FACT_OIL_STOCKS ---")


if __name__ == "__main__":
    load_oil_stocks_fact()
