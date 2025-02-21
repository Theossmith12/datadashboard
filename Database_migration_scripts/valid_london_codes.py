import psycopg2
import csv

# Database connection parameters
conn = psycopg2.connect(
    dbname="crime_data",         # Your database name
    user="crime_user",           # Your PostgreSQL user
    password="password",         # Your PostgreSQL password
    host="localhost",
    port="5432"
)
cur = conn.cursor()

# Step 1: Drop the valid_london_codes table if it exists, and create it
print("Creating table 'valid_london_codes'...")
cur.execute("DROP TABLE IF EXISTS valid_london_codes;")
create_table_sql = """
CREATE TABLE valid_london_codes (
    lsoa_code TEXT PRIMARY KEY
);
"""
cur.execute(create_table_sql)
conn.commit()

# Step 2: Read valid_codes.csv and insert rows into valid_london_codes
csv_path = r"C:\Users\theos\OneDrive\Ambiente de Trabalho\valid_codes.csv"

with open(csv_path, "r", encoding="utf-8") as f:
    # Skip the first two lines (junk/blank)
    next(f)
    next(f)
    
    # Read the third line as the header
    header_line = next(f).strip()
    # Remove any surrounding quotes and split by comma
    header = [col.strip().replace('"', '').lower() for col in header_line.split(',')]
    print("Detected header:", header)
    
    # Create a DictReader using the cleaned header
    reader = csv.DictReader(f, fieldnames=header)
    
    # Since the header should contain "codes", ensure it does
    if "codes" not in header:
        raise ValueError("CSV header does not contain 'Codes' (after lowercasing it should be 'codes')")
    
    count = 0
    for row in reader:
        # row should now have key "codes"
        code = row["codes"].strip()
        if code:  # Only insert non-empty codes
            cur.execute(
                "INSERT INTO valid_london_codes (lsoa_code) VALUES (%s) ON CONFLICT DO NOTHING;",
                (code,)
            )
            count += 1
    print(f"Inserted {count} valid codes into 'valid_london_codes'.")

conn.commit()
cur.close()
conn.close()
