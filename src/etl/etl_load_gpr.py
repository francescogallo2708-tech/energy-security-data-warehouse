import os
import getpass
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values


DB_CONFIG = {
    'dbname': os.environ.get('PGDATABASE', 'energy_gpr_dw'),
    'user': os.environ.get('PGUSER', 'postgres'),
    'host': os.environ.get('PGHOST', 'localhost'),
    'port': os.environ.get('PGPORT', '5433')
}
if os.environ.get('PGPASSWORD'):
    DB_CONFIG['password'] = os.environ['PGPASSWORD']
elif not os.environ.get('PGPASSFILE'):
    DB_CONFIG['password'] = getpass.getpass('Password PostgreSQL: ')


GPR_METRICS = ('gpr', 'gprt', 'gpra')
GPR_START_MONTH = '1985-01'


def prepare_gpr_data(df):
    df = df.copy()
    df.columns = [str(column).strip().lower() for column in df.columns]

    missing_metrics = [column for column in GPR_METRICS if column not in df.columns]
    if missing_metrics:
        raise ValueError(
            'Colonne GPR obbligatorie mancanti: ' + ', '.join(missing_metrics)
        )

    date_col = next(
        (column for column in ('month', 'date') if column in df.columns),
        df.columns[0]
    )

    df['month_sk'] = pd.to_datetime(df[date_col], errors='coerce').dt.strftime('%Y-%m')
    for metric in GPR_METRICS:
        df[metric] = pd.to_numeric(df[metric], errors='coerce')

    all_metrics_null = df[list(GPR_METRICS)].isna().all(axis=1)
    excluded_empty_rows = int(all_metrics_null.sum())
    df_scope = df.loc[~all_metrics_null].copy()

    if df_scope['month_sk'].isna().any():
        invalid_dates = int(df_scope['month_sk'].isna().sum())
        raise ValueError(
            f'Trovate {invalid_dates} date non valide in righe con misure GPR valorizzate.'
        )

    partial_rows = df_scope[list(GPR_METRICS)].isna().any(axis=1)
    if partial_rows.any():
        raise ValueError(
            f'Trovate {int(partial_rows.sum())} righe con misure GPR parziali.'
        )

    outside_scope = df_scope['month_sk'] < GPR_START_MONTH
    excluded_outside_scope = int(outside_scope.sum())
    df_scope = df_scope.loc[~outside_scope].copy()

    if df_scope.empty:
        raise ValueError('Nessun record GPR disponibile nello scope selezionato.')

    duplicated_months = df_scope['month_sk'].duplicated(keep=False)
    if duplicated_months.any():
        duplicate_values = sorted(df_scope.loc[duplicated_months, 'month_sk'].unique())
        raise ValueError(
            'Mesi GPR duplicati nel file sorgente: ' + ', '.join(duplicate_values)
        )

    df_scope = df_scope.sort_values('month_sk')
    print(f'Righe senza GPR/GPRT/GPRA escluse: {excluded_empty_rows}')
    print(f'Righe valorizzate anteriori a {GPR_START_MONTH} escluse: {excluded_outside_scope}')
    print(
        'Intervallo GPR selezionato: '
        f"{df_scope['month_sk'].min()} - {df_scope['month_sk'].max()}"
    )

    return df_scope


def load_gpr_fact():
    print("--- AVVIO ETL FACT_GPR ---")

    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(os.path.dirname(script_dir))
    default_gpr_file = os.path.join(
        project_dir, "data", "raw", "gpr", "data_gpr_export_202608.xls"
    )
    gpr_file = os.path.expanduser(os.environ.get('GPR_SOURCE_FILE', default_gpr_file))

    if not os.path.exists(gpr_file):
        raise FileNotFoundError(f"Impossibile trovare il file {gpr_file}.")

    print(f"Trovato file sorgente GPR: {gpr_file}")

    conn = None
    cursor = None

    try:
        # Lettura del file Excel storico .xls.
        df = pd.read_excel(gpr_file, engine='xlrd')
        print(f"File caricato con successo. Righe grezze: {len(df)}")
        df_scope = prepare_gpr_data(df)

        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # La serie GPR selezionata e una serie globale.
        cursor.execute("SELECT geo_sk FROM DIM_GEO_ENTITY WHERE eurostat_code = 'GLOBAL';")
        res = cursor.fetchone()
        if not res:
            raise RuntimeError("Entita 'GLOBAL' non trovata in DIM_GEO_ENTITY.")
        global_geo_sk = res[0]

        month_keys = df_scope['month_sk'].tolist()
        cursor.execute(
            "SELECT month_sk FROM DT_MONTH WHERE month_sk = ANY(%s);",
            (month_keys,)
        )
        available_months = {row[0] for row in cursor.fetchall()}
        missing_months = sorted(set(month_keys) - available_months)
        if missing_months:
            raise RuntimeError(
                'Mesi mancanti in DT_MONTH: ' + ', '.join(missing_months[:12])
            )

        tuples_to_insert = [
            (
                row.month_sk,
                global_geo_sk,
                float(row.gpr),
                float(row.gprt),
                float(row.gpra)
            )
            for row in df_scope.itertuples(index=False)
        ]

        # Refresh completo e transazionale della sola serie globale.
        cursor.execute("DELETE FROM FACT_GPR WHERE geo_sk = %s;", (global_geo_sk,))

        insert_query = """
            INSERT INTO FACT_GPR (month_sk, geo_sk, gpr_val, gprt_val, gpra_val)
            VALUES %s
            ON CONFLICT (month_sk, geo_sk) DO UPDATE SET
                gpr_val = EXCLUDED.gpr_val,
                gprt_val = EXCLUDED.gprt_val,
                gpra_val = EXCLUDED.gpra_val;
        """

        execute_values(cursor, insert_query, tuples_to_insert)
        conn.commit()

        print(f"[SUCCESSO] Inseriti/Aggiornati {len(tuples_to_insert)} record nella tabella FACT_GPR.")

    except Exception as e:
        if conn is not None:
            conn.rollback()
        print(f"[ERRORE] Durante l'ETL del GPR: {e}")
        raise
    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()
        print("--- FINE ETL FACT_GPR ---")


if __name__ == "__main__":
    load_gpr_fact()
