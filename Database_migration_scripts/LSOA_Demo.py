import os
import psycopg2
import pandas as pd

# Database connection parameters
conn = psycopg2.connect(
    dbname="crime_data",         # Your database name
    user="crime_user",           # Your PostgreSQL user
    password="password",         # Your PostgreSQL password
    host="localhost",
    port="5432"
)
cur = conn.cursor()

base_dir = r"C:\Users\theos\OneDrive\Ambiente de Trabalho\Census_data"

# Define expected demographic columns for age/sex distribution
f_columns = [f'f{i}' for i in range(91)]
m_columns = [f'm{i}' for i in range(91)]
expected_cols = ['year', 'lad_code', 'lad_name', 'lsoa_code', 'lsoa_name', 'total'] + f_columns + m_columns

for file in os.listdir(base_dir):
    if file.endswith("LSOADemoData.csv"):
        file_path = os.path.join(base_dir, file)
        try:
            year = int(file[:4])
        except ValueError:
            print(f"Cannot extract year from filename {file}. Skipping.")
            continue
        print(f"Processing file for year {year}: {file_path}")
        
        # Read CSV; use low_memory=False and remove thousands separator
        df = pd.read_csv(file_path, low_memory=False, thousands=",")
        
        # Add a new column for the census year
        df['year'] = year
        
        # Build a renaming mapping dynamically based on the file's year.
        # For example, for year 2011, we expect:
        # "LAD 2011 Code" -> "lad_code", "LAD 2011 Name" -> "lad_name",
        # "LSOA 2011 Code" -> "lsoa_code", "LSOA 2011 Name" -> "lsoa_name",
        # "Total" remains "total"
        rename_mapping = {
            f"LAD {year} Code": "lad_code",
            f"LAD {year} Name": "lad_name",
            f"LSOA {year} Code": "lsoa_code",
            f"LSOA {year} Name": "lsoa_name",
            "Total": "total"
        }
        df = df.rename(columns=rename_mapping)
        
        # Standardize all column names: strip spaces, lower-case, replace spaces with underscores.
        df.columns = [col.strip().lower().replace(" ", "_") for col in df.columns]
        
        # Convert the "total" column to integer if it is not already.
        if 'total' in df.columns:
            # Remove any commas and convert to numeric (if not already numeric)
            df['total'] = pd.to_numeric(df['total'].astype(str).str.replace(",", ""), errors='coerce')
            # Fill NaN values (if any) with 0 and convert to integer
            df['total'] = df['total'].fillna(0).astype(int)
        
        # Ensure that the expected columns exist:
        for col in expected_cols:
            if col not in df.columns:
                # If a demographic column is missing, add it with a default value of 0.
                df[col] = 0
        
        # Reorder columns to match the expected schema
        df = df[expected_cols]
        
        # Write the modified DataFrame to a temporary CSV file
        temp_csv = os.path.join(base_dir, "temp.csv")
        df.to_csv(temp_csv, index=False, header=True)
        
        # Execute the COPY command to import the data into PostgreSQL
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
