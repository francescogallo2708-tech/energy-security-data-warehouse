import os
import getpass
import psycopg2
from psycopg2.extras import execute_values

# PostgreSQL connection configuration
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

# Historical EU entry and, where applicable, exit mapping:
# (eurostat_code, entry_year, exit_year). exit_year is None for current members.
EU_MEMBERSHIP_HISTORY = [
    # Founding countries (1957/1958)
    ("BE", 1957, None), ("DE", 1957, None), ("FR", 1957, None),
    ("IT", 1957, None), ("LU", 1957, None), ("NL", 1957, None),
    # 1973 enlargement
    ("DK", 1973, None), ("IE", 1973, None), ("UK", 1973, 2020),  # Brexit in 2020
    # 1981 enlargement
    ("EL", 1981, None),
    # 1986 enlargement
    ("ES", 1986, None), ("PT", 1986, None),
    # 1995 enlargement
    ("AT", 1995, None), ("FI", 1995, None), ("SE", 1995, None),
    # 2004 enlargement (10 new countries)
    ("CY", 2004, None), ("CZ", 2004, None), ("EE", 2004, None),
    ("HU", 2004, None), ("LT", 2004, None), ("LV", 2004, None),
    ("MT", 2004, None), ("PL", 2004, None), ("SI", 2004, None), ("SK", 2004, None),
    # 2007 enlargement
    ("BG", 2007, None), ("RO", 2007, None),
    # 2013 enlargement
    ("HR", 2013, None)
]

def load_bridge_eu_membership():
    print("--- STARTING BR_GEO_EU_MEMBERSHIP BRIDGE LOADING ---")
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # 1. Retrieve the mapping (eurostat_code -> geo_sk).
        cursor.execute("SELECT eurostat_code, geo_sk FROM DIM_GEO_ENTITY;")
        geo_map = dict(cursor.fetchall())
        
        # 2. Retrieve all years available in DT_YEAR.
        cursor.execute("SELECT year_sk, year_value FROM DT_YEAR;")
        years = cursor.fetchall()
        
        tuples_to_insert = []
        
        for code, entry_year, exit_year in EU_MEMBERSHIP_HISTORY:
            if code in geo_map:
                geo_sk = geo_map[code]
                for year_sk, year_val in years:
                    # A country is an EU member if year >= entry_year and
                    # (exit_year is None or year < exit_year).
                    if year_val >= entry_year and (exit_year is None or year_val < exit_year):
                        tuples_to_insert.append((geo_sk, year_sk))
        
        insert_query = """
            INSERT INTO BR_GEO_EU_MEMBERSHIP (geo_sk, year_sk)
            VALUES %s
            ON CONFLICT (geo_sk, year_sk) DO NOTHING;
        """
        
        execute_values(cursor, insert_query, tuples_to_insert)
        conn.commit()
        
        print(f"[SUCCESS] Inserted {len(tuples_to_insert)} EU-membership relationships into the bridge table.")
        
    except Exception as e:
        print(f"[ERROR] EU-membership bridge loading failed: {e}")
        raise
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()
        print("--- BR_GEO_EU_MEMBERSHIP BRIDGE LOADING COMPLETED ---")

if __name__ == "__main__":
    load_bridge_eu_membership()
