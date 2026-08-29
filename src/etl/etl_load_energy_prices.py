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

PRICE_FILES = [
    {'file': 'nrg_pc_202_tabular.tsv', 'commodity': 'GAS', 'consumer': 'HOUSEHOLD'},
    {'file': 'nrg_pc_203_tabular.tsv', 'commodity': 'GAS', 'consumer': 'NON_HOUSEHOLD'},
    {'file': 'nrg_pc_204_tabular.tsv', 'commodity': 'ELECTRICITY', 'consumer': 'HOUSEHOLD'},
    {'file': 'nrg_pc_205_tabular.tsv', 'commodity': 'ELECTRICITY', 'consumer': 'NON_HOUSEHOLD'}
]

def load_energy_prices():
    print("--- AVVIO ETL FACT_ENERGY_PRICE ---")
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(script_dir)
    eurostat_dir = os.path.join(project_dir, "Dataset", "raw", "eurostat")
    
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    cursor.execute("SELECT eurostat_code, geo_sk FROM DIM_GEO_ENTITY;")
    geo_map = dict(cursor.fetchall())
    
    cursor.execute("SELECT semester_sk FROM DT_SEMESTER;")
    valid_semesters = set(r[0] for r in cursor.fetchall())
    
    total_inserted = 0

    for cfg in PRICE_FILES:
        filepath = os.path.join(eurostat_dir, cfg['file'])
        if not os.path.exists(filepath):
            print(f"[AVVISO] File {filepath} non trovato. Salto...")
            continue
            
        print(f"Elaborazione file: {filepath} ({cfg['commodity']} - {cfg['consumer']})...")
        
        df_raw = pd.read_csv(filepath, sep='\t', low_memory=False)
        first_col = df_raw.columns[0]
        meta_cols = [c.strip() for c in first_col.split('\\')[0].split(',')]
        
        df_split = df_raw[first_col].str.split(',', expand=True)
        df_split.columns = meta_cols[:df_split.shape[1]]
        
        df_data = pd.concat([df_split, df_raw.drop(columns=[first_col])], axis=1)
        df_data.columns = [str(c).strip() for c in df_data.columns]
        
        semester_cols = [c for c in df_data.columns if '-S' in c or ('S' in c and any(char.isdigit() for char in c))]
        
        df_long = pd.melt(
            df_data,
            id_vars=[c for c in df_split.columns],
            value_vars=semester_cols,
            var_name='semester_sk',
            value_name='raw_val'
        )
        
        df_long['clean_val'] = df_long['raw_val'].astype(str).str.replace(r'[^\d.-]', '', regex=True)
        df_long['price_val'] = pd.to_numeric(df_long['clean_val'], errors='coerce')
        df_valid = df_long.dropna(subset=['price_val']).copy()
        
        geo_col = next((c for c in df_valid.columns if 'geo' in c.lower()), 'geo')
        product_col = next((c for c in df_valid.columns if 'cons' in c.lower() or 'product' in c.lower() or 'nrg' in c.lower()), df_split.columns[1])
        tax_col = next((c for c in df_valid.columns if 'tax' in c.lower()), df_split.columns[2])
        unit_col = next((c for c in df_valid.columns if 'unit' in c.lower()), df_split.columns[0])
        
        # Mappatura e pulizia dei valori
        df_valid['geo_code'] = df_valid[geo_col].astype(str).str.strip()
        df_valid['sem_sk'] = df_valid['semester_sk'].astype(str).str.strip()
        df_valid['product_code'] = df_valid[product_col].astype(str).str.strip()
        df_valid['tax_status'] = df_valid[tax_col].astype(str).str.strip()
        df_valid['unit_code'] = df_valid[unit_col].astype(str).str.strip()
        
        # Filtraggio per codici geografici e semestri validi
        df_filtered = df_valid[
            df_valid['geo_code'].isin(geo_map) & 
            df_valid['sem_sk'].isin(valid_semesters)
        ].copy()
        
        df_filtered['geo_sk'] = df_filtered['geo_code'].map(geo_map)
        df_filtered['commodity_type'] = cfg['commodity']
        df_filtered['consumer_type'] = cfg['consumer']
        
        # Deduplicazione sulle chiavi univoche mantenendo l'ultimo valore letto
        key_cols = ['sem_sk', 'geo_sk', 'commodity_type', 'consumer_type', 'product_code', 'tax_status', 'unit_code']
        df_dedup = df_filtered.drop_duplicates(subset=key_cols, keep='last')
        
        tuples_to_insert = [
            (
                row['sem_sk'],
                row['geo_sk'],
                row['commodity_type'],
                row['consumer_type'],
                row['product_code'],
                row['tax_status'],
                row['unit_code'],
                float(row['price_val'])
            )
            for _, row in df_dedup.iterrows()
        ]
        
        insert_query = """
            INSERT INTO FACT_ENERGY_PRICE 
            (semester_sk, geo_sk, commodity_type, consumer_type, product_code, tax_status, unit_code, price_val)
            VALUES %s
            ON CONFLICT (semester_sk, geo_sk, commodity_type, consumer_type, product_code, tax_status, unit_code) 
            DO UPDATE SET price_val = EXCLUDED.price_val;
        """
        
        execute_values(cursor, insert_query, tuples_to_insert)
        conn.commit()
        print(f" -> Inseriti/Aggiornati {len(tuples_to_insert)} record da {filepath}")
        total_inserted += len(tuples_to_insert)

    cursor.close()
    conn.close()
    print(f"[SUCCESSO] Inseriti {total_inserted} record complessivi in FACT_ENERGY_PRICE.")
    print("--- FINE ETL FACT_ENERGY_PRICE ---")

if __name__ == "__main__":
    load_energy_prices()
