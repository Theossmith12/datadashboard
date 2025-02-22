import psycopg2
import logging
import sys

def main():
    # Database connection parameters
    dbname = "crime_data"
    user = "crime_user"
    password = "password"
    host = "localhost"
    port = "5432"

    # Path to your CSV file
    csv_file_path = r"C:\Users\theos\OneDrive\Ambiente de Trabalho\Lower_Layer_Super_Output_Area_(2021)_to_LAD_(April_2023)_Lookup_in_England_and_Wales.csv"

    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)]
    )

    # 1) Connect to PostgreSQL
    try:
        conn = psycopg2.connect(
            dbname=dbname,
            user=user,
            password=password,
            host=host,
            port=port
        )
        logging.info("Successfully connected to the database '%s'.", dbname)
    except Exception as e:
        logging.error("Failed to connect to the database: %s", e)
        sys.exit(1)

    # 2) Create a new table (drop if exists, then create)
    create_table_sql = """
        DROP TABLE IF EXISTS LSOA_to_LD_lookup;
        CREATE TABLE LSOA_to_LD_lookup (
            LSOA21CD   TEXT,
            LSOA21NM   TEXT,
            LSOA21NMW  TEXT,
            LAD23CD    TEXT,
            LAD23NM    TEXT,
            LAD23NMW   TEXT,
            ObjectId   INTEGER
        );
    """

    try:
        with conn.cursor() as cur:
            cur.execute(create_table_sql)
            conn.commit()
            logging.info("Table 'LSOA_to_LD_lookup' created (or replaced) successfully.")
    except Exception as e:
        logging.error("Failed to create the table: %s", e)
        conn.rollback()
        conn.close()
        sys.exit(1)

    # 3) Load data from CSV into the table
    # Using COPY with HEADER to handle the first row as column names
    copy_sql = """
        COPY LSOA_to_LD_lookup
        FROM STDIN
        WITH (
            FORMAT CSV,
            HEADER TRUE,
            DELIMITER ',',
            NULL ''
        )
    """

    try:
        with conn.cursor() as cur:
            with open(csv_file_path, 'r', encoding='utf-8') as f:
                cur.copy_expert(copy_sql, f)
            conn.commit()
            logging.info("Data loaded into 'LSOA_to_LD_lookup' successfully.")
    except Exception as e:
        logging.error("Failed to load data from CSV: %s", e)
        conn.rollback()
    finally:
        conn.close()
        logging.info("Connection closed.")

if __name__ == "__main__":
    main()
