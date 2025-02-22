import pandas as pd
import psycopg2

# Connection parameters
conn = psycopg2.connect(
    dbname="crime_data",         # Your database name
    user="crime_user",           # Your PostgreSQL user
    password="password",         # Your PostgreSQL password
    host="localhost",
    port="5432"
)
cur = conn.cursor()

# Path to the CSV file (use a raw string to handle backslashes)
csv_file_path = r"C:\Users\theos\OneDrive\Ambiente de Trabalho\LSOA_(2011)_to_LSOA_(2021)_to_Local_Authority_District_(2022)_Best_Fit_Lookup_for_EW_(V2).csv"

# Read the CSV file into a DataFrame
df = pd.read_csv(csv_file_path)

# Create a table to hold the lookup data (if it doesn't exist)
create_table_query = """
CREATE TABLE IF NOT EXISTS lsoa_codes_2011_2022  (
    lsoa11cd TEXT,
    lsoa11nm TEXT,
    lsoa21cd TEXT,
    lsoa21nm TEXT,
    lad22cd TEXT,
    lad22nm TEXT,
    lad22nmw TEXT
);
"""
cur.execute(create_table_query)
conn.commit()

# Insert DataFrame rows into the table
insert_query = """
INSERT INTO lsoa_codes_2011_2022 (lsoa11cd, lsoa11nm, lsoa21cd, lsoa21nm, lad22cd, lad22nm, lad22nmw)
VALUES (%s, %s, %s, %s, %s, %s, %s)
"""
# Loop over the DataFrame and insert each row
for index, row in df.iterrows():
    cur.execute(insert_query, (
        row['LSOA11CD'], row['LSOA11NM'],
        row['LSOA21CD'], row['LSOA21NM'],
        row['LAD22CD'], row['LAD22NM'], row['LAD22NMW']
    ))
conn.commit()

# Clean up by closing the cursor and connection
cur.close()
conn.close()

print("CSV data successfully loaded into the lsoa_lookup table.")
