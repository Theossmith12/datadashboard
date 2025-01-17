import os
import pandas as pd
from sqlalchemy import create_engine
import logging

# -----------------------------------
# Configuration and PostgreSQL Setup
# -----------------------------------

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(message)s')

# PostgreSQL connection setup
engine = create_engine('postgresql://crime_user:password@localhost:5432/crime_data')

# Folder containing CSV files
csv_folder = r'C:\Users\theos\OneDrive\Ambiente de Trabalho\livedashboard\data'

# -----------------------------------
# Function: Clear the Table
# -----------------------------------

def clear_table():
    """
    Clears all data from the crime_records table.
    """
    try:
        with engine.connect() as conn:
            conn.execute("TRUNCATE TABLE crime_records RESTART IDENTITY;")
            conn.commit()
        logging.info("crime_records table has been cleared.")
    except Exception as e:
        logging.error(f"Error clearing table: {e}")

# -----------------------------------
# Function: Clean the Data
# -----------------------------------


def clean_data(df):
    """
    Clean and preprocess the DataFrame before loading into the database.
    """
    # Standardize column names to lowercase and replace spaces with underscores
    df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')

    # Rename columns to match the PostgreSQL schema exactly
    df.rename(columns={
        'last_outcome_category': 'outcome_type',
        'crime_type': 'crime_type',
        'month': 'month',
        'latitude': 'latitude',
        'longitude': 'longitude',
        'crime_id': 'crime_id'
    }, inplace=True)

    # Fill missing 'outcome_type' and 'crime_type' with 'Unknown'
    df['outcome_type'] = df.get('outcome_type', pd.Series('Unknown')).fillna('Unknown')
    df['crime_type'] = df.get('crime_type', pd.Series('Unknown')).fillna('Unknown')

    # Drop rows with missing Latitude or Longitude
    df = df.dropna(subset=['latitude', 'longitude'])

    # Convert Latitude and Longitude to numeric
    df.loc[:, 'latitude'] = pd.to_numeric(df['latitude'], errors='coerce')
    df.loc[:, 'longitude'] = pd.to_numeric(df['longitude'], errors='coerce')
    df = df.dropna(subset=['latitude', 'longitude'])

    # Convert 'month' to proper datetime format
    df['month'] = pd.to_datetime(df['month'], format='%Y-%m', errors='coerce')

    # Drop duplicates if any
    df.drop_duplicates(inplace=True)

    return df



def load_and_insert_data():
    """
    Load, clean, and insert CSV data into PostgreSQL.
    """
    # Clear the table before inserting new data
    clear_table()

    # Loop through all CSV files in the folder
    for file in os.listdir(csv_folder):
        if file.endswith('.csv'):
            file_path = os.path.join(csv_folder, file)
            logging.info(f"Processing {file}...")

            try:
                # Load CSV
                df = pd.read_csv(file_path)

                # Clean the data before uploading
                cleaned_df = clean_data(df)

                if not cleaned_df.empty:
                    # Upload cleaned data to PostgreSQL
                    cleaned_df.to_sql('crime_records', engine, if_exists='append', index=False)
                    logging.info(f"Loaded {file} into the database.")
                else:
                    logging.warning(f"No valid data in {file}, skipping upload.")

            except Exception as e:
                logging.error(f"Error processing {file}: {e}")

    logging.info("All files have been processed and loaded into the database.")

# -----------------------------------
# Main Execution
# -----------------------------------

if __name__ == "__main__":
    load_and_insert_data()
