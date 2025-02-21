import psycopg2

# Database connection parameters
conn = psycopg2.connect(
    dbname="crime_data",         # Your database name
    user="crime_user",           # Your PostgreSQL user
    password="password",         # Your PostgreSQL password
    host="localhost",
    port="5432"
)
cur = conn.cursor()

# Drop the enriched table if it exists and create a new one.
# The new table will drop crime_id and context from crime_records,
# and will join in the demographic data from census_demographics
# based on lsoa_code and the year (extracted from the month column).
create_enriched_sql = """
DROP TABLE IF EXISTS crime_records_enriched;

CREATE TABLE crime_records_enriched AS
SELECT 
    -- From crime_records (dropping crime_id and context)
    c.month,
    c.reported_by,
    c.falls_within,
    c.longitude,
    c.latitude,
    c.location,
    c.lsoa_code,
    c.lsoa_name,
    c.crime_type,
    c.outcome_type,
    -- Insert demographic data from census_demographics:
    d.year AS census_year,
    d.lad_code,
    d.lad_name,
    d.total,
    d.f0, d.f1, d.f2, d.f3, d.f4, d.f5, d.f6, d.f7, d.f8, d.f9,
    d.f10, d.f11, d.f12, d.f13, d.f14, d.f15, d.f16, d.f17, d.f18, d.f19,
    d.f20, d.f21, d.f22, d.f23, d.f24, d.f25, d.f26, d.f27, d.f28, d.f29,
    d.f30, d.f31, d.f32, d.f33, d.f34, d.f35, d.f36, d.f37, d.f38, d.f39,
    d.f40, d.f41, d.f42, d.f43, d.f44, d.f45, d.f46, d.f47, d.f48, d.f49,
    d.f50, d.f51, d.f52, d.f53, d.f54, d.f55, d.f56, d.f57, d.f58, d.f59,
    d.f60, d.f61, d.f62, d.f63, d.f64, d.f65, d.f66, d.f67, d.f68, d.f69,
    d.f70, d.f71, d.f72, d.f73, d.f74, d.f75, d.f76, d.f77, d.f78, d.f79,
    d.f80, d.f81, d.f82, d.f83, d.f84, d.f85, d.f86, d.f87, d.f88, d.f89,
    d.f90,
    d.m0, d.m1, d.m2, d.m3, d.m4, d.m5, d.m6, d.m7, d.m8, d.m9,
    d.m10, d.m11, d.m12, d.m13, d.m14, d.m15, d.m16, d.m17, d.m18, d.m19,
    d.m20, d.m21, d.m22, d.m23, d.m24, d.m25, d.m26, d.m27, d.m28, d.m29,
    d.m30, d.m31, d.m32, d.m33, d.m34, d.m35, d.m36, d.m37, d.m38, d.m39,
    d.m40, d.m41, d.m42, d.m43, d.m44, d.m45, d.m46, d.m47, d.m48, d.m49,
    d.m50, d.m51, d.m52, d.m53, d.m54, d.m55, d.m56, d.m57, d.m58, d.m59,
    d.m60, d.m61, d.m62, d.m63, d.m64, d.m65, d.m66, d.m67, d.m68, d.m69,
    d.m70, d.m71, d.m72, d.m73, d.m74, d.m75, d.m76, d.m77, d.m78, d.m79,
    d.m80, d.m81, d.m82, d.m83, d.m84, d.m85, d.m86, d.m87, d.m88, d.m89,
    d.m90
FROM crime_records c
JOIN census_demographics d
  ON c.lsoa_code = d.lsoa_code
  AND EXTRACT(YEAR FROM c.month) = d.year;
"""

try:
    cur.execute(create_enriched_sql)
    conn.commit()
    print("Table 'crime_records_enriched' created successfully.")
except Exception as e:
    conn.rollback()
    print("Error creating 'crime_records_enriched':", e)

cur.close()
conn.close()
