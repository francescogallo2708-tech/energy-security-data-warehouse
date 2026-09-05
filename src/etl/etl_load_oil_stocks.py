import getpass
import os
import re

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values


DB_CONFIG = {
    'dbname': os.environ.get('PGDATABASE', 'energy_gpr_dw'),
    'user': os.environ.get('PGUSER', 'postgres'),
    'host': os.environ.get('PGHOST', 'localhost'),
    'port': os.environ.get('PGPORT', '5432')
}
if os.environ.get('PGPASSWORD'):
    DB_CONFIG['password'] = os.environ['PGPASSWORD']
elif not os.environ.get('PGPASSFILE'):
    DB_CONFIG['password'] = getpass.getpass('Password PostgreSQL: ')

STOCK_INDICATORS = {
    'IC_DC': ('Daily inland consumption for compliance', 'Compliance consumption', 'Compliance'),
    'IMP_DNC': ('Daily net imports for compliance', 'Compliance import flow', 'Compliance'),
    'STK_EUE_DIR': (
        'Emergency stocks held under EU Directive (days equivalent)',
        'Emergency stock',
        'EU Directive'
    ),
    'STK_MIN_CAL': (
        'Minimum stock level for compliance - calculated',
        'Minimum stock requirement',
        'Compliance'
    ),
}

EXPECTED_UNITS = {
    'IC_DC': 'THS_T',
    'IMP_DNC': 'THS_T',
    'STK_EUE_DIR': 'NR',
    'STK_MIN_CAL': 'THS_T',
}

EXCLUDED_METHOD_INDICATORS = {
    'STK_EUE_DNY_MTH',
    'STK_EUE_MIN_MTH',
    'STK_EUE_MTH',
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
    print("--- STARTING FACT_OIL_STOCKS ETL ---")

    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(os.path.dirname(script_dir))
    tsv_file = os.environ.get(
        'OIL_STOCKS_TSV',
        os.path.join(project_dir, "data", "raw", "eurostat", "nrg_stk_oem_tabular.tsv")
    )

    if not os.path.exists(tsv_file):
        raise FileNotFoundError(f"File not found: {tsv_file}.")

    print(f"Found source file: {tsv_file}")

    try:
        df_raw = pd.read_csv(tsv_file, sep='\t', low_memory=False)
        print(f"File loaded. Raw rows: {len(df_raw)}")

        first_col = df_raw.columns[0]
        df_split = df_raw[first_col].str.split(',', expand=True)
        df_split.columns = ['freq', 'stk_flow', 'unit', 'geo']

        df_data = pd.concat([df_split, df_raw.drop(columns=[first_col])], axis=1)
        df_data.columns = [str(c).strip() for c in df_data.columns]

        month_cols = [c for c in df_data.columns if re.match(r'^\d{4}-\d{2}$', c)]
        if not month_cols:
            raise ValueError('No YYYY-MM monthly column found in the Oil Stocks file.')

        df_long = pd.melt(
            df_data,
            id_vars=['freq', 'stk_flow', 'unit', 'geo'],
            value_vars=month_cols,
            var_name='month_sk',
            value_name='raw_val'
        )

        df_long['clean_val'] = df_long['raw_val'].astype(str).str.replace(r'[^\d.-]', '', regex=True)
        df_long['indicator_value'] = pd.to_numeric(df_long['clean_val'], errors='coerce')
        df_long['eurostat_flag'] = df_long['raw_val'].apply(extract_flag)
        df_valid = df_long.dropna(subset=['indicator_value']).copy()

        excluded_method_rows = int(
            df_valid['stk_flow'].isin(EXCLUDED_METHOD_INDICATORS).sum()
        )
        print(
            'Categorical records related to methods excluded from the fact table: '
            f'{excluded_method_rows}'
        )

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

        quantitative_rows = df_valid[
            ~df_valid['stk_flow'].isin(EXCLUDED_METHOD_INDICATORS)
        ].copy()
        supported_rows = (
            quantitative_rows['geo'].isin(geo_map)
            & quantitative_rows['stk_flow'].isin(STOCK_INDICATORS)
            & quantitative_rows['unit'].isin(unit_map)
            & quantitative_rows['unit'].eq(quantitative_rows['stk_flow'].map(EXPECTED_UNITS))
            & quantitative_rows['month_sk'].isin(valid_months)
        )
        unexpected_rows = quantitative_rows.loc[~supported_rows]
        print(f'Unexpected quantitative records: {len(unexpected_rows)}')
        if not unexpected_rows.empty:
            sample = (
                unexpected_rows[['stk_flow', 'unit', 'geo', 'month_sk']]
                .drop_duplicates()
                .head(10)
                .to_dict('records')
            )
            raise ValueError(
                'The Oil Stocks file contains unrecognized quantitative records. '
                f'Sample: {sample}'
            )

        df_filtered = quantitative_rows.loc[supported_rows].copy()

        df_filtered['geo_sk'] = df_filtered['geo'].map(geo_map)
        df_filtered['indicator_sk'] = df_filtered['stk_flow'].map(indicator_map)
        df_filtered['measure_unit_sk'] = df_filtered['unit'].map(unit_map)

        key_cols = ['month_sk', 'geo_sk', 'indicator_sk', 'measure_unit_sk']
        duplicate_rows = df_filtered[df_filtered.duplicated(subset=key_cols, keep=False)]
        if not duplicate_rows.empty:
            duplicate_sample = (
                duplicate_rows[key_cols]
                .drop_duplicates()
                .head(10)
                .to_dict('records')
            )
            raise ValueError(
                'The Oil Stocks file contains duplicates at the fact-table grain. '
                f'Sample: {duplicate_sample}'
            )

        tuples_to_insert = [
            (
                row['month_sk'],
                int(row['geo_sk']),
                int(row['indicator_sk']),
                int(row['measure_unit_sk']),
                row['eurostat_flag'],
                float(row['indicator_value'])
            )
            for _, row in df_filtered.iterrows()
        ]

        print(f"Records ready for insertion: {len(tuples_to_insert)}")
        if not tuples_to_insert:
            raise ValueError('No valid quantitative record is available for loading into FACT_OIL_STOCKS.')

        # Full refresh: avoids retaining obsolete rows when the source is
        # updated. DELETE and INSERT belong to the same transaction and are
        # rolled back together if an error occurs.
        cursor.execute("DELETE FROM FACT_OIL_STOCKS;")

        execute_values(
            cursor,
            """
            INSERT INTO FACT_OIL_STOCKS
            (month_sk, geo_sk, indicator_sk, measure_unit_sk, eurostat_flag, indicator_value)
            VALUES %s
            ;
            """,
            tuples_to_insert
        )

        conn.commit()
        print(f"[SUCCESS] Inserted/updated {len(tuples_to_insert)} records in FACT_OIL_STOCKS.")

    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
        print(f"[ERROR] FACT_OIL_STOCKS ETL failed: {e}")
        raise
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()
        print("--- FACT_OIL_STOCKS ETL COMPLETED ---")


if __name__ == "__main__":
    load_oil_stocks_fact()
