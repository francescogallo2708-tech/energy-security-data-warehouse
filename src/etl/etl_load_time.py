import getpass
import os
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

def load_time_dimensions():
    print("--- AVVIO POPOLAMENTO DIMENSIONI TEMPORALI ---")
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # 1. Popolamento DT_YEAR (es. dal 1990 al 2030)
        years_tuples = [(y, y) for y in range(1900, 2031)]
        cursor.executemany(
            "INSERT INTO DT_YEAR (year_sk, year_value) VALUES (%s, %s) ON CONFLICT (year_sk) DO NOTHING;",
            years_tuples
        )
        print(f"  - Inseriti anni dal 1900 al 2030.")

        # 2. Popolamento DT_SEMESTER (es. dal 2007 al 2026)
        semesters_tuples = []
        for year in range(2007, 2027):
            for sem in [1, 2]:
                sem_sk = f"{year}-S{sem}"
                semesters_tuples.append((sem_sk, year, sem))
        
        cursor.executemany(
            "INSERT INTO DT_SEMESTER (semester_sk, year_val, semester_num) VALUES (%s, %s, %s) ON CONFLICT (semester_sk) DO NOTHING;",
            semesters_tuples
        )
        print(f"  - Inseriti semestri dal 2007 al 2026.")

        # 3. Popolamento DT_MONTH (es. dal 1900 al 2026)
        months_tuples = []
        for year in range(1900, 2027):
            for month in range(1, 13):
                month_sk = f"{year}-{month:02d}" # es. '2026-08'
                months_tuples.append((month_sk, year, month))
        
        execute_values(
            cursor,
            "INSERT INTO DT_MONTH (month_sk, year_val, month_num) VALUES %s ON CONFLICT (month_sk) DO NOTHING;",
            months_tuples
        )
        print(f"  - Inseriti mesi dal 1900 al 2026.")

        conn.commit()
        print("[SUCCESSO] Tutte le dimensioni temporali sono state popolate correttamente.")

    except Exception as e:
        print(f"[ERRORE] Popolamento temporale fallito: {e}")
        raise
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()
        print("--- FINE POPOLAMENTO TEMPORALE ---")

if __name__ == "__main__":
    load_time_dimensions()
