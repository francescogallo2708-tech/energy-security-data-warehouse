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
    'port': os.environ.get('PGPORT', '5432')
}
if os.environ.get('PGPASSWORD'):
    DB_CONFIG['password'] = os.environ['PGPASSWORD']
elif not os.environ.get('PGPASSFILE'):
    DB_CONFIG['password'] = getpass.getpass('Password PostgreSQL: ')


PRICE_FILES = [
    {
        'file': 'nrg_pc_202_tabular.tsv',
        'metadata': 'ESTAT_NRG_PC_202_1.0.xml',
        'commodity': 'GAS',
        'consumer': 'HOUSEHOLD',
        'siec': 'G3000'
    },
    {
        'file': 'nrg_pc_203_tabular.tsv',
        'metadata': 'ESTAT_NRG_PC_203_1.0.xml',
        'commodity': 'GAS',
        'consumer': 'NON_HOUSEHOLD',
        'siec': 'G3000'
    },
    {
        'file': 'nrg_pc_204_tabular.tsv',
        'metadata': 'ESTAT_NRG_PC_204_1.0.xml',
        'commodity': 'ELECTRICITY',
        'consumer': 'HOUSEHOLD',
        'siec': 'E7000'
    },
    {
        'file': 'nrg_pc_205_tabular.tsv',
        'metadata': 'ESTAT_NRG_PC_205_1.0.xml',
        'commodity': 'ELECTRICITY',
        'consumer': 'NON_HOUSEHOLD',
        'siec': 'E7000'
    }
]

REQUIRED_META_COLUMNS = {
    'freq', 'siec', 'nrg_cons', 'unit', 'tax', 'currency', 'geo'
}
REQUIRED_CODELISTS = {'SIEC', 'NRG_CONS', 'UNIT', 'TAX', 'CURRENCY'}
TAX_INCLUSION_ORDER = {'X_TAX': 1, 'X_VAT': 2, 'I_TAX': 3}
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
            f'Missing codelists in {metadata_file}: {", ".join(sorted(missing))}'
        )

    return codelists


def map_required_labels(series, labels, dimension_name, source_name):
    source_codes = set(series.dropna().astype(str))
    missing_codes = sorted(source_codes - set(labels))
    if missing_codes:
        raise ValueError(
            f'{dimension_name} codes without labels in {source_name}: '
            + ', '.join(missing_codes)
        )
    return series.map(labels)


def prepare_price_file(filepath, metadata_file, config):
    source_name = os.path.basename(filepath)
    codelists = read_codelists(metadata_file)
    df_raw = pd.read_csv(filepath, sep='\t', low_memory=False)

    first_col = df_raw.columns[0]
    meta_cols = [column.strip() for column in first_col.split('\\')[0].split(',')]
    missing_meta = REQUIRED_META_COLUMNS - set(meta_cols)
    if missing_meta:
        raise ValueError(
            f'Missing metadata columns in {filepath}: {", ".join(sorted(missing_meta))}'
        )

    df_split = df_raw[first_col].str.split(',', expand=True)
    if df_split.shape[1] != len(meta_cols):
        raise ValueError(f'Unexpected metadata structure in {filepath}.')
    df_split.columns = meta_cols

    df_data = pd.concat([df_split, df_raw.drop(columns=[first_col])], axis=1)
    df_data.columns = [str(column).strip() for column in df_data.columns]
    for column in meta_cols:
        df_data[column] = df_data[column].astype(str).str.strip()

    semester_cols = [
        column for column in df_data.columns
        if re.fullmatch(r'\d{4}-S[12]', column)
    ]
    if not semester_cols:
        raise ValueError(f'No recognized semester found in {filepath}.')

    df_long = pd.melt(
        df_data,
        id_vars=meta_cols,
        value_vars=semester_cols,
        var_name='semester_sk',
        value_name='raw_val'
    )
    df_long['clean_val'] = (
        df_long['raw_val'].astype(str).str.replace(r'[^\d.-]', '', regex=True)
    )
    df_long['price_val'] = pd.to_numeric(df_long['clean_val'], errors='coerce')
    df_long['eurostat_flag'] = df_long['raw_val'].apply(extract_flag)
    df_valid = df_long.dropna(subset=['price_val']).copy()

    if df_valid.empty:
        raise ValueError(f'No numeric price found in {filepath}.')

    unexpected_frequency = sorted(set(df_valid['freq']) - {'S'})
    if unexpected_frequency:
        raise ValueError(
            f'Unexpected frequencies in {filepath}: {", ".join(unexpected_frequency)}'
        )

    source_siec = sorted(df_valid['siec'].unique())
    if source_siec != [config['siec']]:
        raise ValueError(
            f'Unexpected SIEC codes in {filepath}: {", ".join(source_siec)}'
        )

    band_order = {
        code: position
        for position, code in enumerate(codelists['NRG_CONS'])
    }

    df_valid['geo_code'] = df_valid['geo']
    df_valid['commodity_type'] = config['commodity']
    df_valid['consumer_type'] = config['consumer']
    df_valid['siec_code'] = df_valid['siec']
    df_valid['siec_label'] = map_required_labels(
        df_valid['siec_code'], codelists['SIEC'], 'SIEC', source_name
    )
    df_valid['band_code'] = df_valid['nrg_cons']
    df_valid['band_label'] = map_required_labels(
        df_valid['band_code'], codelists['NRG_CONS'], 'NRG_CONS', source_name
    )
    df_valid['band_order'] = df_valid['band_code'].map(band_order)
    df_valid['is_total_band'] = df_valid['band_code'].str.startswith('TOT_')
    df_valid['tax_code'] = df_valid['tax']
    df_valid['tax_label'] = map_required_labels(
        df_valid['tax_code'], codelists['TAX'], 'TAX', source_name
    )
    df_valid['tax_inclusion_order'] = df_valid['tax_code'].map(TAX_INCLUSION_ORDER)
    if df_valid['tax_inclusion_order'].isna().any():
        unknown_taxes = sorted(
            df_valid.loc[df_valid['tax_inclusion_order'].isna(), 'tax_code'].unique()
        )
        raise ValueError(
            f'Undefined tax order in {filepath}: {", ".join(unknown_taxes)}'
        )

    df_valid['energy_unit_code'] = df_valid['unit']
    df_valid['energy_unit_label'] = map_required_labels(
        df_valid['energy_unit_code'], codelists['UNIT'], 'UNIT', source_name
    )
    df_valid['currency_code'] = df_valid['currency']
    df_valid['currency_label'] = map_required_labels(
        df_valid['currency_code'], codelists['CURRENCY'], 'CURRENCY', source_name
    )
    df_valid['price_basis'] = (
        df_valid['currency_code'] + ' per ' + df_valid['energy_unit_code']
    )

    print(
        f"  - {config['commodity']} / {config['consumer']}: "
        f'{len(df_valid)} quantitative observations'
    )
    return df_valid


def load_energy_prices():
    print('--- STARTING FACT_ENERGY_PRICE ETL ---')

    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(os.path.dirname(script_dir))
    default_eurostat_dir = os.path.join(project_dir, 'data', 'raw', 'eurostat')
    default_metadata_dir = os.path.join(project_dir, 'docs', 'data-sources')
    eurostat_dir = os.path.expanduser(
        os.environ.get('ENERGY_PRICES_DIR', default_eurostat_dir)
    )
    metadata_dir = os.path.expanduser(
        os.environ.get('ENERGY_PRICES_METADATA_DIR', default_metadata_dir)
    )

    conn = None
    cursor = None

    try:
        prepared_frames = []
        for config in PRICE_FILES:
            filepath = os.path.join(eurostat_dir, config['file'])
            metadata_file = os.path.join(metadata_dir, config['metadata'])
            if not os.path.exists(filepath):
                raise FileNotFoundError(f'TSV file not found: {filepath}')
            if not os.path.exists(metadata_file):
                raise FileNotFoundError(f'XML metadata file not found: {metadata_file}')

            print(f"Processing: {config['file']}")
            prepared_frames.append(
                prepare_price_file(
                    filepath=os.path.abspath(filepath),
                    metadata_file=os.path.abspath(metadata_file),
                    config=config
                )
            )

        prices = pd.concat(prepared_frames, ignore_index=True)
        natural_key = [
            'semester_sk',
            'geo_code',
            'commodity_type',
            'consumer_type',
            'band_code',
            'tax_code',
            'energy_unit_code',
            'currency_code'
        ]
        duplicate_rows = prices.duplicated(natural_key, keep=False)
        if duplicate_rows.any():
            raise ValueError(
                f'Found {int(duplicate_rows.sum())} duplicate observations '
                'at the fact-table grain.'
            )

        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        cursor.execute('SELECT eurostat_code, geo_sk FROM DIM_GEO_ENTITY;')
        geo_map = dict(cursor.fetchall())
        cursor.execute('SELECT semester_sk FROM DT_SEMESTER;')
        valid_semesters = {row[0] for row in cursor.fetchall()}

        missing_geos = sorted(set(prices['geo_code']) - set(geo_map))
        if missing_geos:
            raise RuntimeError(
                'Missing geographic codes in DIM_GEO_ENTITY: '
                + ', '.join(missing_geos)
            )

        missing_semesters = sorted(set(prices['semester_sk']) - valid_semesters)
        if missing_semesters:
            raise RuntimeError(
                'Missing semesters in DT_SEMESTER: ' + ', '.join(missing_semesters)
            )

        band_columns = [
            'commodity_type',
            'siec_code',
            'siec_label',
            'consumer_type',
            'band_code',
            'band_label',
            'band_order',
            'is_total_band'
        ]
        band_data = prices[band_columns].drop_duplicates().sort_values(
            ['commodity_type', 'consumer_type', 'band_order']
        )
        band_rows = [
            (
                row.commodity_type,
                row.siec_code,
                row.siec_label,
                row.consumer_type,
                row.band_code,
                row.band_label,
                int(row.band_order),
                bool(row.is_total_band)
            )
            for row in band_data.itertuples(index=False)
        ]
        execute_values(
            cursor,
            """
            INSERT INTO DT_CONSUMPTION_BAND
                (commodity_type, siec_code, siec_label, consumer_type,
                 band_code, band_label, band_order, is_total_band)
            VALUES %s
            ON CONFLICT (commodity_type, consumer_type, band_code) DO UPDATE SET
                siec_code = EXCLUDED.siec_code,
                siec_label = EXCLUDED.siec_label,
                band_label = EXCLUDED.band_label,
                band_order = EXCLUDED.band_order,
                is_total_band = EXCLUDED.is_total_band;
            """,
            band_rows
        )

        tax_data = prices[
            ['tax_code', 'tax_label', 'tax_inclusion_order']
        ].drop_duplicates().sort_values('tax_inclusion_order')
        tax_rows = [
            (row.tax_code, row.tax_label, int(row.tax_inclusion_order))
            for row in tax_data.itertuples(index=False)
        ]
        execute_values(
            cursor,
            """
            INSERT INTO DT_TAX_LEVEL
                (tax_code, tax_label, tax_inclusion_order)
            VALUES %s
            ON CONFLICT (tax_code) DO UPDATE SET
                tax_label = EXCLUDED.tax_label,
                tax_inclusion_order = EXCLUDED.tax_inclusion_order;
            """,
            tax_rows
        )

        price_unit_columns = [
            'energy_unit_code',
            'currency_code',
            'energy_unit_label',
            'currency_label',
            'price_basis'
        ]
        price_unit_data = prices[price_unit_columns].drop_duplicates().sort_values(
            ['energy_unit_code', 'currency_code']
        )
        price_unit_rows = list(
            price_unit_data.itertuples(index=False, name=None)
        )
        execute_values(
            cursor,
            """
            INSERT INTO DT_PRICE_UNIT
                (energy_unit_code, currency_code, energy_unit_label,
                 currency_label, price_basis)
            VALUES %s
            ON CONFLICT (energy_unit_code, currency_code) DO UPDATE SET
                energy_unit_label = EXCLUDED.energy_unit_label,
                currency_label = EXCLUDED.currency_label,
                price_basis = EXCLUDED.price_basis;
            """,
            price_unit_rows
        )

        cursor.execute(
            """
            SELECT commodity_type, consumer_type, band_code, consumption_band_sk
            FROM DT_CONSUMPTION_BAND;
            """
        )
        band_map = {
            (commodity, consumer, band): sk
            for commodity, consumer, band, sk in cursor.fetchall()
        }
        cursor.execute('SELECT tax_code, tax_level_sk FROM DT_TAX_LEVEL;')
        tax_map = dict(cursor.fetchall())
        cursor.execute(
            """
            SELECT energy_unit_code, currency_code, price_unit_sk
            FROM DT_PRICE_UNIT;
            """
        )
        price_unit_map = {
            (unit, currency): sk
            for unit, currency, sk in cursor.fetchall()
        }

        prices['geo_sk'] = prices['geo_code'].map(geo_map)
        prices['consumption_band_sk'] = [
            band_map[(commodity, consumer, band)]
            for commodity, consumer, band in zip(
                prices['commodity_type'],
                prices['consumer_type'],
                prices['band_code']
            )
        ]
        prices['tax_level_sk'] = prices['tax_code'].map(tax_map)
        prices['price_unit_sk'] = [
            price_unit_map[(unit, currency)]
            for unit, currency in zip(
                prices['energy_unit_code'], prices['currency_code']
            )
        ]

        fact_rows = [
            (
                row.semester_sk,
                int(row.geo_sk),
                int(row.consumption_band_sk),
                int(row.tax_level_sk),
                int(row.price_unit_sk),
                row.eurostat_flag,
                float(row.price_val)
            )
            for row in prices.itertuples(index=False)
        ]

        # Full refresh: the complete fact table derives from the four source files.
        cursor.execute('DELETE FROM FACT_ENERGY_PRICE;')
        execute_values(
            cursor,
            """
            INSERT INTO FACT_ENERGY_PRICE
                (semester_sk, geo_sk, consumption_band_sk, tax_level_sk,
                 price_unit_sk, eurostat_flag, price_val)
            VALUES %s;
            """,
            fact_rows,
            page_size=10000
        )
        conn.commit()

        print(f'Consumption-band dimension: {len(band_rows)} records')
        print(f'Tax-level dimension: {len(tax_rows)} records')
        print(f'Price-unit dimension: {len(price_unit_rows)} records')
        print(
            f'[SUCCESS] Inserted {len(fact_rows)} total records '
            'in FACT_ENERGY_PRICE.'
        )

    except Exception as exc:
        if conn is not None:
            conn.rollback()
        print(f'[ERROR] FACT_ENERGY_PRICE ETL failed: {exc}')
        raise
    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()
        print('--- FACT_ENERGY_PRICE ETL COMPLETED ---')


if __name__ == '__main__':
    load_energy_prices()
