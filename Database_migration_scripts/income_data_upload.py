import psycopg2
import pandas as pd
import os

# Connection parameters
conn = psycopg2.connect(
    dbname="crime_data",         # Your database name
    user="crime_user",           # Your PostgreSQL user
    password="password",         # Your PostgreSQL password
    host="localhost",
    port="5432"
)
cur = conn.cursor()

# Create the new table if it doesn't already exist.
create_table_query = """
CREATE TABLE IF NOT EXISTS income_borough_level (
    income_2011 NUMERIC,
    income_2012 NUMERIC,
    income_2013 NUMERIC,
    income_2014 NUMERIC,
    income_2015 NUMERIC,
    income_2016 NUMERIC,
    income_2017 NUMERIC,
    income_2018 NUMERIC,
    income_2019 NUMERIC,
    income_2020 NUMERIC,
    income_2021 NUMERIC,
    income_2022 NUMERIC,
    income_2023 NUMERIC,
    income_2024 NUMERIC,
    lad_code TEXT,
    lad_name TEXT
);
"""
cur.execute(create_table_query)
conn.commit()

# Define the path to your original CSV file
original_file_path = r"C:\Users\theos\OneDrive\Ambiente de Trabalho\Income_data at borough_level.csv"

# Read the CSV file with pandas, converting thousand separators
# Assuming the year columns are named "2011", "2012", ..., "2024", and the last two columns are "Code" and "Area"
df = pd.read_csv(original_file_path, thousands=",")

# Optionally, rename the columns to match the table column names
year_cols = [str(year) for year in range(2011, 2025)]
rename_dict = {year: f"income_{year}" for year in year_cols}
rename_dict["Code"] = "lad_code"
rename_dict["Area"] = "lad_name"
df.rename(columns=rename_dict, inplace=True)

# Write the cleaned data to a temporary CSV file (without index)
temp_file_path = "temp_income_data.csv"
df.to_csv(temp_file_path, index=False)

# Use the PostgreSQL COPY command to load the cleaned CSV into the table.
copy_sql = """
COPY income_borough_level (
    income_2011, income_2012, income_2013, income_2014, income_2015, income_2016,
    income_2017, income_2018, income_2019, income_2020, income_2021, income_2022,
    income_2023, income_2024, lad_code, lad_name
)
FROM STDIN WITH CSV HEADER DELIMITER ',';
"""

with open(temp_file_path, 'r', encoding='utf-8') as f:
    cur.copy_expert(sql=copy_sql, file=f)

conn.commit()
cur.close()
conn.close()

# Optionally, remove the temporary file after loading
os.remove(temp_file_path)

print("Table income_borough_level created and data loaded successfully.")
