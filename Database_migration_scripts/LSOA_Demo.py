import os
import re
import psycopg2
import pandas as pd

def detect_header_line(file_path, header_keyword="LAD 2021 Code"):
    """
    Reads the first few lines of the file and returns the index of the line
    that contains the header_keyword.
    """
    with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
        for i in range(10):  # check the first 10 lines
            line = f.readline()
            if header_keyword in line:
                return i
    # If not found, assume header is at line 0
    return 0

# Database connection parameters
conn = psycopg2.connect(
    dbname="crime_data",         # Your database name
    user="crime_user",           # Your PostgreSQL user
    password="password",         # Your PostgreSQL password
    host="localhost",
    port="5432"
)
cur = conn.cursor()

# Create the new table if it doesn't already exist.
# The table includes: year, lad_code, lad_name, lsoa_code, lsoa_name, total,
# plus f0 to f90 and m0 to m90 as integer columns.
create_table_sql = """
CREATE TABLE IF NOT EXISTS census_demographics (
    year INTEGER,
    lad_code TEXT,
    lad_name TEXT,
    lsoa_code TEXT,
    lsoa_name TEXT,
    total INTEGER,
"""

# Build the f0–f90 and m0–m90 column definitions
f_columns = [f'    f{i} INTEGER' for i in range(91)]
m_columns = [f'    m{i} INTEGER' for i in range(91)]

# Complete the CREATE TABLE statement
create_table_sql += ",\n".join(f_columns + m_columns)
create_table_sql += "\n);"

cur.execute(create_table_sql)
conn.commit()
print("Table 'census_demographics' created or already exists.")

base_dir = r"C:\Users\theos\OneDrive\Ambiente de Trabalho\Census_data"

# Define expected column names in the final table (order matters)
expected_cols = ['year', 'lad_code', 'lad_name', 'lsoa_code', 'lsoa_name', 'total'] + \
                [f'f{i}' for i in range(91)] + [f'm{i}' for i in range(91)]

# Process each file in the directory
for file in os.listdir(base_dir):
    # Match files that end with "LSOADemoData.csv" (case-insensitive)
    if re.search(r'\d{4}LSOADemoData\.csv$', file, re.IGNORECASE):
        file_path = os.path.join(base_dir, file)
        try:
            # Extract the year from the first 4 characters of the filename
            year = int(file[:4])
        except ValueError:
            print(f"Cannot extract year from filename {file}. Skipping.")
            continue
        print(f"\nProcessing file for year {year}: {file_path}")
        
        # Detect the header line (if extra junk rows exist, this will catch it)
        header_line = detect_header_line(file_path, header_keyword="LAD 2021 Code")
        print(f"Detected header on line {header_line} for file {file}")
        
        # Read the CSV with the correct skiprows setting
        df = pd.read_csv(file_path, skiprows=header_line, header=0, 
                         low_memory=False, thousands=",")
        
        # Add a new column for the census year
        df['year'] = year
        
        # Rename columns to a standard schema.
        # In these CSVs, all files use "LAD 2021 Code", etc., regardless of the file year.
        rename_mapping = {
            "LAD 2021 Code": "lad_code",
            "LAD 2021 Name": "lad_name",
            "LSOA 2021 Code": "lsoa_code",
            "LSOA 2021 Name": "lsoa_name",
            "Total": "total"
        }
        df = df.rename(columns=rename_mapping)
        
        # Standardize all column names: trim, lower-case, and replace spaces with underscores.
        df.columns = [col.strip().lower().replace(" ", "_") for col in df.columns]
        
        # Convert the 'total' column to an integer (cleaning commas if necessary)
        if 'total' in df.columns:
            df['total'] = pd.to_numeric(df['total'].astype(str).str.replace(",", ""), errors='coerce')
            df['total'] = df['total'].fillna(0).astype(int)
        
        # Ensure that every expected column exists. If missing, add it with a default value of 0.
        for col in expected_cols:
            if col not in df.columns:
                df[col] = 0
        
        # Reorder the DataFrame's columns to match the expected schema.
        df = df[expected_cols]
        
        # Write the modified DataFrame to a temporary CSV file
        temp_csv = os.path.join(base_dir, "temp.csv")
        df.to_csv(temp_csv, index=False, header=True)
        
        # Use PostgreSQL's COPY command to import the data into the table.
        copy_sql = f"""
            COPY census_demographics FROM '{temp_csv}' CSV HEADER;
        """
        try:
            cur.execute(copy_sql)
            conn.commit()
            print(f"Successfully imported data for year {year}.")
        except Exception as e:
            print(f"Error importing data for year {year}: {e}")
            conn.rollback()
        
        # Remove the temporary CSV file
        os.remove(temp_csv)

cur.close()
conn.close()
