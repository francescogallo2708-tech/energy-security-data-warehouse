import os
import getpass
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

def load_import_dependency_fact():
    print("--- AVVIO ETL FACT_IMPORT_DEPENDENCY ---")
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(script_dir)
    tsv_file = os.path.join(project_dir, "Dataset", "raw", "eurostat", "nrg_ind_id_tabular.tsv")
    
    if not os.path.exists(tsv_file):
        print(f"[ERRORE] File {tsv_file} non trovato nella cartella corrente.")
        return

    print(f"Trovato file sorgente: {tsv_file}")
    
    try:
        # 1. Lettura del file TSV (Eurostat usa la tabulazione come separatore)
        df_raw = pd.read_csv(tsv_file, sep='\t', low_memory=False)
        print(f"File caricato. Righe grezze: {len(df_raw)}")
        
        # 2. Scomposizione della colonna mista 'freq,siec,unit,geo\\time'
        first_col = df_raw.columns[0]
        meta_cols = [c.strip() for c in first_col.split(',')]
        
        # Separiamo la prima colonna mista in 4 colonne distinte
        df_split = df_raw[first_col].str.split(',', expand=True)
        df_split.columns = ['freq', 'siec', 'unit', 'geo']
        
        # Uniamo le colonne metadati con il resto delle colonne temporali (gli anni)
        df_data = pd.concat([df_split, df_raw.drop(columns=[first_col])], axis=1)
        
        # Puliamo i nomi delle colonne temporali (rimuoviamo spazi vuoti)
        df_data.columns = [str(c).strip() for c in df_data.columns]
        
        # Identifichiamo le colonne degli anni (es. '2023', '2022', ecc.)
        year_cols = [c for c in df_data.columns if c.isdigit()]
        
        # 3. Reshape da Wide a Long (Unpivot / Melt)
        df_long = pd.melt(
            df_data,
            id_vars=['freq', 'siec', 'unit', 'geo'],
            value_vars=year_cols,
            var_name='year',
            value_name='raw_val'
        )
        
        # 4. Pulizia dei dati
        # Convertiamo l'anno in intero
        df_long['year'] = df_long['year'].astype(int)
        
        # Pulizia del valore numerico Eurostat (rimozione flag alfabetici come 'p', 'e', 'b', ecc.)
        df_long['clean_val'] = df_long['raw_val'].astype(str).str.replace(r'[^\d.-]', '', regex=True)
        df_long['dep_rate_val'] = pd.to_numeric(df_long['clean_val'], errors='coerce')
        
        # Scartiamo i record dove il valore è nullo o mancante
        df_valid = df_long.dropna(subset=['dep_rate_val']).copy()
        
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Mappatura dei codici paese Eurostat con i corrispondenti geo_sk nel database
        cursor.execute("SELECT eurostat_code, geo_sk FROM DIM_GEO_ENTITY;")
        geo_map = dict(cursor.fetchall())
        
        tuples_to_insert = []
        for _, row in df_valid.iterrows():
            geo_code = row['geo']
            
            # Verifichiamo se il codice paese esiste nella nostra dimensione geografica
            if geo_code in geo_map:
                geo_sk = geo_map[geo_code]
                year_sk = int(row['year'])
                siec_code = str(row['siec'])
                unit_code = str(row['unit'])
                val = float(row['dep_rate_val'])
                
                tuples_to_insert.append((year_sk, geo_sk, siec_code, unit_code, val))

        print(f"Record pronti per l'inserimento: {len(tuples_to_insert)}")

        # 5. Caricamento in batch nel database PostgreSQL
        insert_query = """
            INSERT INTO FACT_IMPORT_DEPENDENCY (year_sk, geo_sk, siec_code, unit_code, dep_rate_val)
            VALUES %s
            ON CONFLICT (year_sk, geo_sk, siec_code, unit_code) DO UPDATE SET
                dep_rate_val = EXCLUDED.dep_rate_val;
        """
        
        execute_values(cursor, insert_query, tuples_to_insert)
        conn.commit()
        
        print(f"[SUCCESSO] Inseriti/Aggiornati {len(tuples_to_insert)} record nella tabella FACT_IMPORT_DEPENDENCY.")

    except Exception as e:
        print(f"[ERRORE] Durante l'ETL Import Dependency: {e}")
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()
        print("--- FINE ETL FACT_IMPORT_DEPENDENCY ---")

if __name__ == "__main__":
    load_import_dependency_fact()
