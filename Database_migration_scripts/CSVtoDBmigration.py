import os
import re
import psycopg2
import pandas as pd
import logging
import tempfile

# -----------------------------------
# Configuration and PostgreSQL Setup
# -----------------------------------

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# PostgreSQL connection setup (update with your actual credentials)
try:
    conn = psycopg2.connect(
        dbname="crime_data",         # Your database name
        user="crime_user",           # Your PostgreSQL user
        password="password",         # Your PostgreSQL password
        host="localhost",
        port="5432"
    )
    logging.info("Successfully connected to the database 'crime_data'.")
except Exception as e:
    logging.error("Failed to connect to the database: %s", e)
    exit(1)

cur = conn.cursor()

# Folder containing CSV files
csv_folder = r"C:\Users\theos\OneDrive\Ambiente de Trabalho\All data"

# -----------------------------------
# Function: Clear the Table
# -----------------------------------

def clear_table():
    """
    Clears all data from the crime_records table.
    """
    try:
        with conn.cursor() as cur_local:
            cur_local.execute("TRUNCATE TABLE crime_records RESTART IDENTITY;")
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
    # Standardize column names: strip whitespace, convert to lowercase, and replace spaces with underscores.
    df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')
    
    # Optionally, rename columns to match the PostgreSQL schema exactly.
    # For example, rename 'last_outcome_category' to 'outcome_type'
    df.rename(columns={'last_outcome_category': 'outcome_type'}, inplace=True)
    
    # Fill missing outcome_type and crime_type with 'Unknown'
    df['outcome_type'] = df.get('outcome_type', pd.Series('Unknown')).fillna('Unknown')
    df['crime_type'] = df.get('crime_type', pd.Series('Unknown')).fillna('Unknown')
    
    # Drop rows with missing latitude or longitude and coerce them to numeric
    df = df.dropna(subset=['latitude', 'longitude'])
    df['latitude'] = pd.to_numeric(df['latitude'], errors='coerce')
    df['longitude'] = pd.to_numeric(df['longitude'], errors='coerce')
    df = df.dropna(subset=['latitude', 'longitude'])
    
    # Do not drop rows with null 'crime_id'; we allow them since our table uses an auto-increment key.
    # Convert the 'month' column to a proper datetime.
    # If the month column is in "YYYY-MM" format, append "-01" and convert.
    def convert_month(val):
        if pd.isnull(val):
            return pd.NaT
        val_str = str(val).strip()
        if len(val_str) == 7:  # Expected format "YYYY-MM"
            val_str += "-01"
        try:
            return pd.to_datetime(val_str, format="%Y-%m-%d", errors='raise')
        except Exception as e:
            logging.error(f"Error converting month value '{val}': {e}")
            return pd.NaT

    df['month'] = df['month'].apply(convert_month)
    df = df.dropna(subset=['month'])
    
    # Drop duplicate rows if any
    df.drop_duplicates(inplace=True)
    
    return df

# -----------------------------------
# Main Data Loading Function
# -----------------------------------

def load_and_insert_data():
    """
    Load, clean, and insert CSV data into PostgreSQL.
    """
    # Clear the table before inserting new data
    clear_table()
    
    # Regular expression to match folder names in the format YYYY-MM
    folder_pattern = re.compile(r'^\d{4}-\d{2}$')
    # Define the expected file name suffixes.
    target_suffixes = ["city-of-london-street.csv", "metropolitan-street.csv"]
    
    # Loop over each folder in the base directory that matches the YYYY-MM pattern
    for folder in os.listdir(csv_folder):
        if folder_pattern.match(folder):
            folder_path = os.path.join(csv_folder, folder)
            if os.path.isdir(folder_path):
                logging.info("Processing folder: %s", folder)
                # For each target file: construct the filename as "foldername-target_suffix"
                for suffix in target_suffixes:
                    file_name = f"{folder}-{suffix}"
                    file_path = os.path.join(folder_path, file_name)
                    if os.path.exists(file_path):
                        logging.info("Found file: %s", file_path)
                        try:
                            # Load CSV file into a DataFrame
                            df = pd.read_csv(file_path)
                            logging.info("Loaded file %s with shape %s", file_path, df.shape)
                        except Exception as e:
                            logging.error("Error reading CSV file %s: %s", file_path, e)
                            continue
                        
                        try:
                            # Clean the data
                            cleaned_df = clean_data(df)
                            logging.info("After cleaning, %s has shape %s", file_path, cleaned_df.shape)
                        except Exception as e:
                            logging.error("Error cleaning data in %s: %s", file_path, e)
                            continue
                        
                        if not cleaned_df.empty:
                            # Write the cleaned DataFrame to a temporary CSV file
                            try:
                                with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.csv', newline='', encoding='utf-8') as tmp:
                                    temp_file_path = tmp.name
                                    cleaned_df.to_csv(temp_file_path, index=False)
                                logging.info("Written transformed data to temporary file: %s", temp_file_path)
                            except Exception as e:
                                logging.error("Error writing temporary CSV file for %s: %s", file_path, e)
                                continue
                            
                            # Import the temporary CSV file using PostgreSQL's COPY command
                            try:
                                with open(temp_file_path, 'r', encoding='utf-8') as f:
                                    copy_sql = """
                                        COPY public.crime_records(
                                            crime_id,
                                            month,
                                            reported_by,
                                            falls_within,
                                            longitude,
                                            latitude,
                                            location,
                                            lsoa_code,
                                            lsoa_name,
                                            crime_type,
                                            outcome_type,
                                            context
                                        )
                                        FROM STDIN WITH CSV HEADER DELIMITER as ','
                                    """
                                    cur.copy_expert(sql=copy_sql, file=f)
                                conn.commit()
                                logging.info("Successfully imported file: %s", file_path)
                            except Exception as e:
                                logging.error("Error importing file %s: %s", file_path, e)
                                conn.rollback()
                            finally:
                                # Remove the temporary file
                                try:
                                    os.remove(temp_file_path)
                                except Exception as e:
                                    logging.warning("Could not remove temporary file %s: %s", temp_file_path, e)
                        else:
                            logging.warning("No valid data in %s, skipping upload.", file_path)
                    else:
                        logging.warning("File not found: %s", file_path)
        else:
            logging.info("Skipping folder '%s' (does not match YYYY-MM pattern)", folder)
    
    logging.info("All files have been processed and loaded into the database.")

# -----------------------------------
# Main Execution
# -----------------------------------

if __name__ == "__main__":
    load_and_insert_data()
    cur.close()
    conn.close()
    logging.info("Data import complete and database connection closed.")
