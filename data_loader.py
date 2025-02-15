import os
import logging
import pandas as pd
from functools import lru_cache
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# Configuration Flags
CLOUD_DEPLOY = False
SAMPLE_DATA = True
CHUNK_SIZE = 10000

@lru_cache(maxsize=1)
def load_data():
    """
    Load crime data from the PostgreSQL database using chunking and optional sampling.
    Only necessary columns are selected and the data is sorted chronologically by month.
    """
    try:
        DB_USER = os.getenv('DB_USER')
        DB_PASS = os.getenv('DB_PASSWORD')
        DB_NAME = os.getenv('DB_NAME')
        DB_CONN_NAME = os.getenv('INSTANCE_CONNECTION_NAME')

        if CLOUD_DEPLOY:
            DATABASE_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@/{DB_NAME}?host=/cloudsql/{DB_CONN_NAME}"
        else:
            DATABASE_URL = "postgresql+psycopg2://postgres:Fluminense99@localhost:5432/crime_data"

        engine = create_engine(DATABASE_URL)
        query = """
            SELECT month, longitude, latitude, crime_type, outcome_type, lsoa_id 
            FROM crime_records_enriched;
        """

        if SAMPLE_DATA:
            logging.info("Loading data in chunks with sampling...")
            chunks = pd.read_sql(query, engine, parse_dates=['month'], chunksize=CHUNK_SIZE)
            data_list = []
            for i, chunk in enumerate(chunks, start=1):
                logging.info(f"Processing chunk {i}...")
                sampled_chunk = chunk.sample(frac=1.0)
                data_list.append(sampled_chunk)
            data = pd.concat(data_list, ignore_index=True)
        else:
            logging.info("Loading full dataset without sampling...")
            data = pd.read_sql(query, engine, parse_dates=['month'])

        data = data.sort_values("month")
        data['longitude'] = pd.to_numeric(data['longitude'], downcast='float')
        data['latitude'] = pd.to_numeric(data['latitude'], downcast='float')
        data['crime_type'] = data['crime_type'].astype('category')
        data['outcome_type'] = data['outcome_type'].astype('category')

        logging.info("Data loaded successfully.")
        logging.info(f"Data types:\n{data.dtypes}")
        logging.info(f"First few rows:\n{data.head()}")
        return data

    except Exception as e:
        logging.error(f"Failed to load data: {e}")
        return pd.DataFrame()

@lru_cache(maxsize=1)
def load_lsoa_lookup():
    """
    Load the LSOA lookup table that maps lsoa_id to lsoa_code and lsoa_name.
    """
    try:
        DB_USER = os.getenv('DB_USER')
        DB_PASS = os.getenv('DB_PASSWORD')
        DB_NAME = os.getenv('DB_NAME')
        DB_CONN_NAME = os.getenv('INSTANCE_CONNECTION_NAME')

        if CLOUD_DEPLOY:
            DATABASE_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@/{DB_NAME}?host=/cloudsql/{DB_CONN_NAME}"
        else:
            DATABASE_URL = "postgresql+psycopg2://postgres:Fluminense99@localhost:5432/crime_data"

        engine = create_engine(DATABASE_URL)
        query = "SELECT lsoa_id, lsoa_code, lsoa_name FROM lsoa_lookup"
        df = pd.read_sql(query, engine)
        logging.info("LSOA lookup loaded successfully.")
        return df

    except Exception as e:
        logging.error(f"Failed to load lsoa_lookup: {e}")
        return pd.DataFrame()

# Expose the cached data for use in other modules
crime_data = load_data()
lsoa_lookup = load_lsoa_lookup()
