import os
import getpass
import psycopg2
from psycopg2.extras import execute_values

# Configurazione connessione PostgreSQL
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

# Mappatura storica ingresso (ed eventuale uscita) paesi UE: (eurostat_code, entry_year, exit_year)
# NOTA: exit_year è None se il paese è tuttora membro dell'Unione Europea.
EU_MEMBERSHIP_HISTORY = [
    # Paesi fondatori (1957/1958)
    ("BE", 1957, None), ("DE", 1957, None), ("FR", 1957, None),
    ("IT", 1957, None), ("LU", 1957, None), ("NL", 1957, None),
    # Allargamento 1973
    ("DK", 1973, None), ("IE", 1973, None), ("UK", 1973, 2020), # Brexit nel 2020
    # Allargamento 1981
    ("EL", 1981, None),
    # Allargamento 1986
    ("ES", 1986, None), ("PT", 1986, None),
    # Allargamento 1995
    ("AT", 1995, None), ("FI", 1995, None), ("SE", 1995, None),
    # Allargamento 2004 (10 nuovi paesi)
    ("CY", 2004, None), ("CZ", 2004, None), ("EE", 2004, None),
    ("HU", 2004, None), ("LT", 2004, None), ("LV", 2004, None),
    ("MT", 2004, None), ("PL", 2004, None), ("SI", 2004, None), ("SK", 2004, None),
    # Allargamento 2007
    ("BG", 2007, None), ("RO", 2007, None),
    # Allargamento 2013
    ("HR", 2013, None)
]

def load_bridge_eu_membership():
    print("--- AVVIO POPOLAMENTO TABELLA PONTE BR_GEO_EU_MEMBERSHIP ---")
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # 1. Recupera il mapping (eurostat_code -> geo_sk)
        cursor.execute("SELECT eurostat_code, geo_sk FROM DIM_GEO_ENTITY;")
        geo_map = dict(cursor.fetchall())
        
        # 2. Recupera tutti gli anni disponibili in DT_YEAR
        cursor.execute("SELECT year_sk, year_value FROM DT_YEAR;")
        years = cursor.fetchall()
        
        tuples_to_insert = []
        
        for code, entry_year, exit_year in EU_MEMBERSHIP_HISTORY:
            if code in geo_map:
                geo_sk = geo_map[code]
                for year_sk, year_val in years:
                    # Il paese fa parte dell'UE nell'anno se: year >= entry_year AND (exit_year IS NULL OR year < exit_year)
                    if year_val >= entry_year and (exit_year is None or year_val < exit_year):
                        tuples_to_insert.append((geo_sk, year_sk))
        
        insert_query = """
            INSERT INTO BR_GEO_EU_MEMBERSHIP (geo_sk, year_sk)
            VALUES %s
            ON CONFLICT (geo_sk, year_sk) DO NOTHING;
        """
        
        execute_values(cursor, insert_query, tuples_to_insert)
        conn.commit()
        
        print(f"[SUCCESSO] Inserite {len(tuples_to_insert)} relazioni di appartenenza UE nella tabella ponte.")
        
    except Exception as e:
        print(f"[ERRORE] Durante il popolamento della tabella ponte UE: {e}")
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()
        print("--- FINE POPOLAMENTO TABELLA PONTE UE ---")

if __name__ == "__main__":
    load_bridge_eu_membership()
