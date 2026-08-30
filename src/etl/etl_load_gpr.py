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

def load_gpr_fact():
    print("--- AVVIO ETL FACT_GPR ---")
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(os.path.dirname(script_dir))
    default_gpr_file = os.path.join(
        project_dir, "data", "raw", "gpr", "data_gpr_export_202608.xls"
    )
    gpr_file = os.path.expanduser(os.environ.get('GPR_SOURCE_FILE', default_gpr_file))
    
    if not os.path.exists(gpr_file):
        print(f"[ERRORE] Impossibile trovare il file {gpr_file}.")
        return

    print(f"Trovato file sorgente GPR: {gpr_file}")
    
    try:
        # 2. Lettura del file Excel (utilizzando pandas con il motore xlrd per i file .xls vecchi)
        df = pd.read_excel(gpr_file, engine='xlrd')
            
        print(f"File caricato con successo. Colonne presenti: {df.columns.tolist()}")
        
        # 3. Pulizia dei nomi delle colonne
        df.columns = [str(c).strip().lower() for c in df.columns]
        
        # Individuazione dinamica delle colonne nel file GPR
        date_col = next((c for c in df.columns if 'date' in c or 'month' in c or 'm' in c), df.columns[0])
        
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Recuperiamo la geo_sk per 'GLOBAL'
        cursor.execute("SELECT geo_sk FROM DIM_GEO_ENTITY WHERE eurostat_code = 'GLOBAL';")
        res = cursor.fetchone()
        if not res:
            print("[ERRORE] Entità 'GLOBAL' non trovata in DIM_GEO_ENTITY.")
            return
        global_geo_sk = res[0]
        
        # 4. Preparazione dei dati
        tuples_to_insert = []
        for _, row in df.iterrows():
            raw_date = str(row[date_col]).strip()
            
            try:
                # Gestione della data (es. formato 'YYYY-MM' o timestamp)
                if len(raw_date) >= 7:
                    month_sk = raw_date[:7].replace('/', '-')
                else:
                    continue
                
                # Estrazione sicura delle metriche GPR dal file Excel
                val_gpr = float(row['gpr']) if 'gpr' in df.columns and pd.notna(row['gpr']) else None
                val_gprt = float(row['gprt']) if 'gprt' in df.columns and pd.notna(row['gprt']) else None
                val_gpra = float(row['gpra']) if 'gpra' in df.columns and pd.notna(row['gpra']) else None
                
                if month_sk:
                    tuples_to_insert.append((month_sk, global_geo_sk, val_gpr, val_gprt, val_gpra))
            except Exception:
                continue

        # 5. Inserimento nel database con upsert
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
        print(f"[ERRORE] Durante l'ETL del GPR: {e}")
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()
        print("--- FINE ETL FACT_GPR ---")

if __name__ == "__main__":
    load_gpr_fact()
