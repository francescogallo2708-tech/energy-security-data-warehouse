import pandas as pd
import getpass
import os
import psycopg2
from psycopg2.extras import execute_values

# Configurazione della connessione al database PostgreSQL
DB_CONFIG = {
    'dbname': os.environ.get('PGDATABASE', 'energy_gpr_dw'),
    'user': os.environ.get('PGUSER', 'postgres'),
    'password': os.environ.get('PGPASSWORD') or getpass.getpass('Password PostgreSQL: '),
    'host': os.environ.get('PGHOST', 'localhost'),
    'port': os.environ.get('PGPORT', '5433')
}

def load_geography_dimension():
    print("--- AVVIO POPOLAMENTO DIM_GEO_ENTITY ---")
    
    # Dati geografici unificati
    geo_data = [
        {"eurostat": "IT", "iso2": "IT", "iso3": "ITA", "name": "Italy", "type": "Country", "eu": True},
        {"eurostat": "DE", "iso2": "DE", "iso3": "DEU", "name": "Germany", "type": "Country", "eu": True},
        {"eurostat": "FR", "iso2": "FR", "iso3": "FRA", "name": "France", "type": "Country", "eu": True},
        {"eurostat": "ES", "iso2": "ES", "iso3": "ESP", "name": "Spain", "type": "Country", "eu": True},
        {"eurostat": "EL", "iso2": "GR", "iso3": "GRC", "name": "Greece", "type": "Country", "eu": True},
        {"eurostat": "UK", "iso2": "GB", "iso3": "GBR", "name": "United Kingdom", "type": "Country", "eu": False},
        {"eurostat": "EU27_2020", "iso2": None, "iso3": None, "name": "European Union - 27 countries (from 2020)", "type": "Aggregate", "eu": True},
        {"eurostat": "EA20", "iso2": None, "iso3": None, "name": "Euro area - 20 countries (from 2023)", "type": "Aggregate", "eu": True},
        {"eurostat": "GLOBAL", "iso2": "WO", "iso3": "WLD", "name": "Global / World", "type": "Global", "eu": False}
    ]
    
    df = pd.DataFrame(geo_data)
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        insert_query = """
            INSERT INTO DIM_GEO_ENTITY (eurostat_code, iso_alpha2, iso_alpha3, country_name, entity_type, is_eu)
            VALUES %s
            ON CONFLICT (eurostat_code) DO UPDATE SET
                country_name = EXCLUDED.country_name,
                iso_alpha2 = EXCLUDED.iso_alpha2,
                iso_alpha3 = EXCLUDED.iso_alpha3,
                entity_type = EXCLUDED.entity_type,
                is_eu = EXCLUDED.is_eu;
        """
        
        # Mappatura esatta delle tuple (gestendo i valori None per convertirli in NULL di SQL)
        tuples = [
            (
                row['eurostat'], 
                row['iso2'] if pd.notna(row['iso2']) else None, 
                row['iso3'] if pd.notna(row['iso3']) else None, 
                row['name'], 
                row['type'], 
                row['eu']
            ) 
            for index, row in df.iterrows()
        ]
        
        execute_values(cursor, insert_query, tuples)
        conn.commit()
        
        print(f"[SUCCESSO] Inseriti/Aggiornati {len(tuples)} record nella tabella DIM_GEO_ENTITY.")
        
    except Exception as e:
        print(f"[ERRORE] Connessione o inserimento fallito: {e}")
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()
        print("--- FINE POPOLAMENTO GEOGRAFIA ---")

if __name__ == "__main__":
    load_geography_dimension()
