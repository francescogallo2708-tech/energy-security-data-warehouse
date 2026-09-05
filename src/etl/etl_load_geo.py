import pandas as pd
import getpass
import os
import psycopg2
from psycopg2.extras import execute_values

# Configurazione della connessione al database PostgreSQL
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

def load_geography_dimension():
    print("--- AVVIO POPOLAMENTO DIM_GEO_ENTITY ---")
    
    # Dati geografici unificati
    geo_data = [
        {"eurostat": "AL", "iso2": "AL", "iso3": "ALB", "name": "Albania", "type": "Country", "eu": False},
        {"eurostat": "AT", "iso2": "AT", "iso3": "AUT", "name": "Austria", "type": "Country", "eu": True},
        {"eurostat": "BE", "iso2": "BE", "iso3": "BEL", "name": "Belgium", "type": "Country", "eu": True},
        {"eurostat": "BG", "iso2": "BG", "iso3": "BGR", "name": "Bulgaria", "type": "Country", "eu": True},
        {"eurostat": "CY", "iso2": "CY", "iso3": "CYP", "name": "Cyprus", "type": "Country", "eu": True},
        {"eurostat": "CZ", "iso2": "CZ", "iso3": "CZE", "name": "Czechia", "type": "Country", "eu": True},
        {"eurostat": "DE", "iso2": "DE", "iso3": "DEU", "name": "Germany", "type": "Country", "eu": True},
        {"eurostat": "DK", "iso2": "DK", "iso3": "DNK", "name": "Denmark", "type": "Country", "eu": True},
        {"eurostat": "EE", "iso2": "EE", "iso3": "EST", "name": "Estonia", "type": "Country", "eu": True},
        {"eurostat": "EL", "iso2": "GR", "iso3": "GRC", "name": "Greece", "type": "Country", "eu": True},
        {"eurostat": "ES", "iso2": "ES", "iso3": "ESP", "name": "Spain", "type": "Country", "eu": True},
        {"eurostat": "FI", "iso2": "FI", "iso3": "FIN", "name": "Finland", "type": "Country", "eu": True},
        {"eurostat": "FR", "iso2": "FR", "iso3": "FRA", "name": "France", "type": "Country", "eu": True},
        {"eurostat": "GE", "iso2": "GE", "iso3": "GEO", "name": "Georgia", "type": "Country", "eu": False},
        {"eurostat": "HR", "iso2": "HR", "iso3": "HRV", "name": "Croatia", "type": "Country", "eu": True},
        {"eurostat": "HU", "iso2": "HU", "iso3": "HUN", "name": "Hungary", "type": "Country", "eu": True},
        {"eurostat": "IE", "iso2": "IE", "iso3": "IRL", "name": "Ireland", "type": "Country", "eu": True},
        {"eurostat": "IT", "iso2": "IT", "iso3": "ITA", "name": "Italy", "type": "Country", "eu": True},
        {"eurostat": "LT", "iso2": "LT", "iso3": "LTU", "name": "Lithuania", "type": "Country", "eu": True},
        {"eurostat": "LU", "iso2": "LU", "iso3": "LUX", "name": "Luxembourg", "type": "Country", "eu": True},
        {"eurostat": "LV", "iso2": "LV", "iso3": "LVA", "name": "Latvia", "type": "Country", "eu": True},
        {"eurostat": "MD", "iso2": "MD", "iso3": "MDA", "name": "Moldova", "type": "Country", "eu": False},
        {"eurostat": "ME", "iso2": "ME", "iso3": "MNE", "name": "Montenegro", "type": "Country", "eu": False},
        {"eurostat": "MK", "iso2": "MK", "iso3": "MKD", "name": "North Macedonia", "type": "Country", "eu": False},
        {"eurostat": "MT", "iso2": "MT", "iso3": "MLT", "name": "Malta", "type": "Country", "eu": True},
        {"eurostat": "NL", "iso2": "NL", "iso3": "NLD", "name": "Netherlands", "type": "Country", "eu": True},
        {"eurostat": "NO", "iso2": "NO", "iso3": "NOR", "name": "Norway", "type": "Country", "eu": False},
        {"eurostat": "PL", "iso2": "PL", "iso3": "POL", "name": "Poland", "type": "Country", "eu": True},
        {"eurostat": "PT", "iso2": "PT", "iso3": "PRT", "name": "Portugal", "type": "Country", "eu": True},
        {"eurostat": "RO", "iso2": "RO", "iso3": "ROU", "name": "Romania", "type": "Country", "eu": True},
        {"eurostat": "RS", "iso2": "RS", "iso3": "SRB", "name": "Serbia", "type": "Country", "eu": False},
        {"eurostat": "SE", "iso2": "SE", "iso3": "SWE", "name": "Sweden", "type": "Country", "eu": True},
        {"eurostat": "SI", "iso2": "SI", "iso3": "SVN", "name": "Slovenia", "type": "Country", "eu": True},
        {"eurostat": "SK", "iso2": "SK", "iso3": "SVK", "name": "Slovakia", "type": "Country", "eu": True},
        {"eurostat": "TR", "iso2": "TR", "iso3": "TUR", "name": "Türkiye", "type": "Country", "eu": False},
        {"eurostat": "UK", "iso2": "GB", "iso3": "GBR", "name": "United Kingdom", "type": "Country", "eu": False},
        {"eurostat": "BA", "iso2": "BA", "iso3": "BIH", "name": "Bosnia and Herzegovina", "type": "Country", "eu": False},
        {"eurostat": "EA", "iso2": None, "iso3": None, "name": "Euro area (variable composition)", "type": "Aggregate", "eu": True},
        {"eurostat": "EA19", "iso2": None, "iso3": None, "name": "Euro area - 19 countries (2015-2022)", "type": "Aggregate", "eu": True},
        {"eurostat": "EA20", "iso2": None, "iso3": None, "name": "Euro area - 20 countries (from 2023)", "type": "Aggregate", "eu": True},
        {"eurostat": "EU27_2020", "iso2": None, "iso3": None, "name": "European Union - 27 countries (from 2020)", "type": "Aggregate", "eu": True},
        {"eurostat": "GLOBAL", "iso2": "WO", "iso3": "WLD", "name": "Global / World", "type": "Global", "eu": False},
        {"eurostat": "IS", "iso2": "IS", "iso3": "ISL", "name": "Iceland", "type": "Country", "eu": False},
        {"eurostat": "LI", "iso2": "LI", "iso3": "LIE", "name": "Liechtenstein", "type": "Country", "eu": False},
        {"eurostat": "UA", "iso2": "UA", "iso3": "UKR", "name": "Ukraine", "type": "Country", "eu": False},
        {"eurostat": "XK", "iso2": "XK", "iso3": "XKX", "name": "Kosovo", "type": "Country", "eu": False}
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
        raise
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()
        print("--- FINE POPOLAMENTO GEOGRAFIA ---")

if __name__ == "__main__":
    load_geography_dimension()
