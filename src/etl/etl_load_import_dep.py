import getpass
import os
import re
import xml.etree.ElementTree as ET

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


REQUIRED_META_COLUMNS = {'freq', 'siec', 'unit', 'geo'}
REQUIRED_CODELISTS = {'SIEC', 'UNIT'}
XML_LANG = '{http://www.w3.org/XML/1998/namespace}lang'


def extract_flag(raw_value):
    flags = ''.join(re.findall(r'[A-Za-z]+', str(raw_value).strip()))
    return flags or None


def local_name(tag):
    return tag.rsplit('}', 1)[-1]


def english_label(element):
    fallback = None
    for child in element:
        if local_name(child.tag) != 'Name':
            continue
        label = (child.text or '').strip()
        if fallback is None:
            fallback = label
        if child.attrib.get(XML_LANG) == 'en':
            return label
    return fallback


def read_codelists(metadata_file):
    root = ET.parse(metadata_file).getroot()
    codelists = {}

    for element in root.iter():
        if local_name(element.tag) != 'Codelist':
            continue

        codes = {}
        for child in element:
            if local_name(child.tag) != 'Code':
                continue
            code = child.attrib.get('id')
            label = english_label(child)
            if code and label:
                codes[code] = label

        if codes:
            codelists[element.attrib.get('id')] = codes

    missing = REQUIRED_CODELISTS - set(codelists)
    if missing:
        raise ValueError(
            f'Codelist mancanti in {metadata_file}: {", ".join(sorted(missing))}'
        )

    return codelists


def map_required_labels(series, labels, dimension_name, source_name):
    source_codes = set(series.dropna().astype(str))
    missing_codes = sorted(source_codes - set(labels))
    if missing_codes:
        raise ValueError(
            f'Codici {dimension_name} senza etichetta in {source_name}: '
            + ', '.join(missing_codes)
        )
    return series.map(labels)


def prepare_import_dependency(tsv_file, metadata_file):
    source_name = os.path.basename(tsv_file)
    codelists = read_codelists(metadata_file)
    df_raw = pd.read_csv(tsv_file, sep='\t', low_memory=False)

    first_col = df_raw.columns[0]
    meta_cols = [column.strip() for column in first_col.split('\\')[0].split(',')]
    missing_meta = REQUIRED_META_COLUMNS - set(meta_cols)
    if missing_meta:
        raise ValueError(
            f'Colonne metadata mancanti in {source_name}: '
            + ', '.join(sorted(missing_meta))
        )

    df_split = df_raw[first_col].str.split(',', expand=True)
    if df_split.shape[1] != len(meta_cols):
        raise ValueError(f'Struttura metadata inattesa in {source_name}.')
    df_split.columns = meta_cols

    df_data = pd.concat([df_split, df_raw.drop(columns=[first_col])], axis=1)
    df_data.columns = [str(column).strip() for column in df_data.columns]
    for column in meta_cols:
        df_data[column] = df_data[column].astype(str).str.strip()

    year_cols = [
        column for column in df_data.columns
        if re.fullmatch(r'\d{4}', column)
    ]
    if not year_cols:
        raise ValueError(f'Nessun anno riconosciuto in {source_name}.')

    df_long = pd.melt(
        df_data,
        id_vars=meta_cols,
        value_vars=year_cols,
        var_name='year_sk',
        value_name='raw_val'
    )
    df_long['year_sk'] = df_long['year_sk'].astype(int)
    df_long['clean_val'] = (
        df_long['raw_val'].astype(str).str.replace(r'[^\d.-]', '', regex=True)
    )
    df_long['dep_rate_val'] = pd.to_numeric(
        df_long['clean_val'], errors='coerce'
    )
    df_long['eurostat_flag'] = df_long['raw_val'].apply(extract_flag)
    dependency = df_long.dropna(subset=['dep_rate_val']).copy()

    if dependency.empty:
        raise ValueError(f'Nessun valore numerico trovato in {source_name}.')

    unexpected_frequency = sorted(set(dependency['freq']) - {'A'})
    if unexpected_frequency:
        raise ValueError(
            f'Frequenze inattese in {source_name}: '
            + ', '.join(unexpected_frequency)
        )

    unexpected_units = sorted(set(dependency['unit']) - {'PC'})
    if unexpected_units:
        raise ValueError(
            f'Unita inattese in {source_name}: ' + ', '.join(unexpected_units)
        )

    dependency['geo_code'] = dependency['geo']
    dependency['siec_code'] = dependency['siec']
    dependency['siec_label'] = map_required_labels(
        dependency['siec_code'], codelists['SIEC'], 'SIEC', source_name
    )

    product_order = {
        code: position
        for position, code in enumerate(codelists['SIEC'], start=1)
    }
    dependency['product_order'] = dependency['siec_code'].map(product_order)
    dependency['is_total'] = dependency['siec_code'].eq('TOTAL')

    natural_key = ['year_sk', 'geo_code', 'siec_code']
    duplicate_rows = dependency.duplicated(natural_key, keep=False)
    if duplicate_rows.any():
        raise ValueError(
            f'Trovate {int(duplicate_rows.sum())} osservazioni duplicate '
            'alla granularita della fact.'
        )

    print(f'Righe sorgente: {len(df_raw)} serie')
    print(f'Osservazioni quantitative: {len(dependency)}')
    print(
        f"Copertura temporale: {dependency['year_sk'].min()}-"
        f"{dependency['year_sk'].max()}"
    )
    return dependency


def load_import_dependency_fact():
    print('--- AVVIO ETL FACT_IMPORT_DEPENDENCY ---')

    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(os.path.dirname(script_dir))
    default_tsv_file = os.path.join(
        project_dir, 'data', 'raw', 'eurostat', 'nrg_ind_id_tabular.tsv'
    )
    default_metadata_file = os.path.join(
        project_dir, 'docs', 'data-sources', 'ESTAT_NRG_IND_ID_1.0.xml'
    )
    tsv_file = os.path.abspath(os.path.expanduser(
        os.environ.get('IMPORT_DEPENDENCY_TSV', default_tsv_file)
    ))
    metadata_file = os.path.abspath(os.path.expanduser(
        os.environ.get('IMPORT_DEPENDENCY_METADATA_FILE', default_metadata_file)
    ))

    conn = None
    cursor = None

    try:
        if not os.path.exists(tsv_file):
            raise FileNotFoundError(f'File TSV non trovato: {tsv_file}')
        if not os.path.exists(metadata_file):
            raise FileNotFoundError(f'File metadata XML non trovato: {metadata_file}')

        print(f'Trovato file sorgente: {tsv_file}')
        dependency = prepare_import_dependency(tsv_file, metadata_file)

        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        cursor.execute('SELECT eurostat_code, geo_sk FROM DIM_GEO_ENTITY;')
        geo_map = dict(cursor.fetchall())
        cursor.execute('SELECT year_sk FROM DT_YEAR;')
        valid_years = {row[0] for row in cursor.fetchall()}

        missing_geos = sorted(set(dependency['geo_code']) - set(geo_map))
        if missing_geos:
            raise RuntimeError(
                'Codici geografici mancanti in DIM_GEO_ENTITY: '
                + ', '.join(missing_geos)
            )

        missing_years = sorted(set(dependency['year_sk']) - valid_years)
        if missing_years:
            raise RuntimeError(
                'Anni mancanti in DT_YEAR: '
                + ', '.join(str(year) for year in missing_years)
            )

        product_columns = [
            'siec_code', 'siec_label', 'product_order', 'is_total'
        ]
        product_data = dependency[product_columns].drop_duplicates().sort_values(
            'product_order'
        )
        product_rows = [
            (
                row.siec_code,
                row.siec_label,
                int(row.product_order),
                bool(row.is_total)
            )
            for row in product_data.itertuples(index=False)
        ]
        execute_values(
            cursor,
            """
            INSERT INTO DT_ENERGY_PRODUCT
                (siec_code, siec_label, product_order, is_total)
            VALUES %s
            ON CONFLICT (siec_code) DO UPDATE SET
                siec_label = EXCLUDED.siec_label,
                product_order = EXCLUDED.product_order,
                is_total = EXCLUDED.is_total;
            """,
            product_rows
        )

        cursor.execute('SELECT siec_code, product_sk FROM DT_ENERGY_PRODUCT;')
        product_map = dict(cursor.fetchall())

        dependency['geo_sk'] = dependency['geo_code'].map(geo_map)
        dependency['product_sk'] = dependency['siec_code'].map(product_map)

        fact_rows = [
            (
                int(row.year_sk),
                int(row.geo_sk),
                int(row.product_sk),
                row.eurostat_flag,
                float(row.dep_rate_val)
            )
            for row in dependency.itertuples(index=False)
        ]

        # Refresh completo: la fact deriva interamente dal TSV Eurostat.
        cursor.execute('DELETE FROM FACT_IMPORT_DEPENDENCY;')
        execute_values(
            cursor,
            """
            INSERT INTO FACT_IMPORT_DEPENDENCY
                (year_sk, geo_sk, product_sk, eurostat_flag, dep_rate_val)
            VALUES %s;
            """,
            fact_rows,
            page_size=10000
        )
        conn.commit()

        print(f'Dimensione prodotti energetici: {len(product_rows)} record')
        print(
            f'[SUCCESSO] Inseriti {len(fact_rows)} record complessivi '
            'in FACT_IMPORT_DEPENDENCY.'
        )

    except Exception as exc:
        if conn is not None:
            conn.rollback()
        print(f'[ERRORE] Durante ETL Import Dependency: {exc}')
        raise
    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()
        print('--- FINE ETL FACT_IMPORT_DEPENDENCY ---')


if __name__ == '__main__':
    load_import_dependency_fact()
