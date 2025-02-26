import os
import logging
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

class CrimeDataService:
    """
    Service class for accessing crime data from the database.
    Separates SQL queries from data processing logic.
    """
    
    def __init__(self):
        """Initialize the data service with database connection parameters."""
        load_dotenv()
        self.cloud_deploy = os.getenv('CLOUD_DEPLOY', 'False').lower() == 'true'
        self.sample_data = os.getenv('SAMPLE_DATA', 'True').lower() == 'true'
        self.chunk_size = int(os.getenv('CHUNK_SIZE', '10000'))
        
        # Database connection parameters
        self.db_user = os.getenv('DB_USER')
        self.db_pass = os.getenv('DB_PASSWORD')
        self.db_name = os.getenv('DB_NAME')
        self.db_conn_name = os.getenv('INSTANCE_CONNECTION_NAME')
        
        # Create database URL
        if self.cloud_deploy:
            self.database_url = f"postgresql+psycopg2://{self.db_user}:{self.db_pass}@/{self.db_name}?host=/cloudsql/{self.db_conn_name}"
        else:
            self.database_url = os.getenv('DATABASE_URL', "postgresql+psycopg2://postgres:Fluminense99@localhost:5432/crime_data")
        
        # Initialize engine
        try:
            self.engine = create_engine(self.database_url)
            logger.info(f"Database engine initialized for {'cloud' if self.cloud_deploy else 'local'} deployment")
        except Exception as e:
            logger.error(f"Failed to initialize database engine: {e}")
            self.engine = None
    
    def get_connection(self):
        """Get a connection from the engine."""
        if self.engine:
            return self.engine.connect()
        else:
            logger.error("Cannot get connection: Database engine not initialized")
            return None
    
    def get_crime_data(self, census_year=2015, filters=None):
        """
        Get crime data from the database.
        
        Parameters:
        -----------
        census_year : int
            The census year to filter by
        filters : dict
            Additional filters to apply to the query
            
        Returns:
        --------
        pandas.DataFrame
            The crime data
        """
        # For backward compatibility, just call get_filtered_crime_data
        return self.get_filtered_crime_data(filters={'census_year': census_year})
    
    def get_filtered_crime_data(self, filters=None, columns=None):
        """
        Get filtered crime data with only selected columns.
        
        Parameters:
        -----------
        filters : dict
            Filters to apply (e.g., {'crime_type': ['Robbery'], 'outcome_type': ['Investigation complete']})
        columns : list
            Specific columns to retrieve (reduces memory usage)
        """
        try:
            # Start with base select statement - if no columns specified, select all
            column_str = "*"
            if columns:
                # Validate columns exist - if not, select all
                try:
                    # Get a list of actual columns in the table
                    col_query = "SELECT column_name FROM information_schema.columns WHERE table_name = 'crime_records_enriched'"
                    actual_columns = pd.read_sql(col_query, self.engine)['column_name'].tolist()
                    
                    # Filter to only valid columns
                    valid_columns = [col for col in columns if col in actual_columns]
                    if valid_columns:
                        column_str = ", ".join(valid_columns)
                        logger.info(f"Using columns: {valid_columns}")
                    else:
                        logger.warning(f"No valid columns in {columns}, using all columns")
                except Exception as e:
                    logger.error(f"Error validating columns: {e}, using all columns")
            
            base_query = f"SELECT {column_str} FROM crime_records_enriched WHERE 1=1"
            
            # Apply filters
            if filters:
                for column, value in filters.items():
                    if isinstance(value, list):
                        placeholders = ', '.join(f"'{v}'" for v in value)
                        base_query += f" AND {column} IN ({placeholders})"
                    elif isinstance(value, (int, float)):
                        base_query += f" AND {column} = {value}"
                    else:
                        base_query += f" AND {column} = '{value}'"
            
            logger.info(f"Executing query: {base_query}")
            
            if self.sample_data:
                logger.info("Loading data in chunks with sampling...")
                chunks = pd.read_sql(base_query, self.engine, chunksize=self.chunk_size)
                data_list = []
                for i, chunk in enumerate(chunks, start=1):
                    logger.info(f"Processing chunk {i} with {len(chunk)} rows...")
                    sampled_chunk = chunk.sample(frac=1.0)
                    data_list.append(sampled_chunk)
                data = pd.concat(data_list, ignore_index=True)
            else:
                logger.info("Loading full dataset without sampling...")
                data = pd.read_sql(base_query, self.engine)
            
            # Process data types
            self._process_data_types(data)
            
            logger.info(f"Data loaded successfully: {len(data)} rows with columns {data.columns.tolist()}")
            return data
            
        except Exception as e:
            logger.error(f"Failed to load filtered crime data: {e}")
            return pd.DataFrame()
    
    def get_lsoa_lookup(self):
        """
        Get the LSOA lookup table from the database.
        
        Returns:
        --------
        pandas.DataFrame
            The LSOA lookup table
        """
        try:
            query = "SELECT lsoa_id, lsoa_code, lsoa_name FROM lsoa_lookup"
            df = pd.read_sql(query, self.engine)
            logger.info(f"LSOA lookup loaded successfully with {len(df)} rows.")
            return df
        except Exception as e:
            logger.error(f"Failed to load lsoa_lookup: {e}")
            return pd.DataFrame()
        
    
    
    def get_aggregated_data(self, group_by_columns, metric_columns=None, filters=None):
        """
        Get pre-aggregated data directly from the database.
        """
        try:
            # Construct metrics part of query
            metrics = []
            if metric_columns:
                for col, agg_func in metric_columns.items():
                    metrics.append(f"{agg_func}({col}) as {col}")
            
            # Always include count with consistent capitalization - use 'Count' 
            metrics.append("COUNT(*) as Count")  # Use uppercase 'Count'
            
            # Build query
            group_by_str = ", ".join(group_by_columns)
            metrics_str = ", ".join(metrics)
            
            query = f"""
            SELECT {group_by_str}, {metrics_str}
            FROM crime_records_enriched
            WHERE 1=1
            """
            
            # Always include census_year filter
            query += " AND census_year = 2015"
            
            # Apply other filters
            if filters:
                for column, value in filters.items():
                    if column == 'census_year':
                        continue  # Already handled
                    elif column == 'start_date':
                        query += f" AND month >= '{value}'"
                    elif column == 'end_date':
                        query += f" AND month <= '{value}'"
                    elif isinstance(value, list):
                        placeholders = ', '.join(f"'{v}'" for v in value)
                        query += f" AND {column} IN ({placeholders})"
                    elif isinstance(value, (int, float)):
                        query += f" AND {column} = {value}"
                    else:
                        query += f" AND {column} = '{value}'"
            
            # Finalize query
            query += f" GROUP BY {group_by_str}"
            
            # Execute query
            logger.info(f"Executing aggregation query: {query}")
            df = pd.read_sql(query, self.engine)
            logger.info(f"Aggregation returned {len(df)} rows with columns {df.columns.tolist()}")
            return df
            
        except Exception as e:
            logger.error(f"Failed to execute aggregation: {e}")
            return pd.DataFrame()
    
    def get_unique_values(self, column_name):
        """
        Get unique values for a specific column, filtered to 2015 data.
        
        Parameters:
        -----------
        column_name : str
            The column to get unique values for
            
        Returns:
        --------
        list
            List of unique values
        """
        try:
            # Filter to only 2015 data
            query = f"""
            SELECT DISTINCT {column_name}
            FROM crime_records_enriched 
            WHERE census_year = 2015 
            AND {column_name} IS NOT NULL
            """
            result = pd.read_sql(query, self.engine)
            return result[column_name].tolist()
        except Exception as e:
            logger.error(f"Failed to get unique values for {column_name}: {e}")
            return []
    
    def get_demographic_data(self, lsoa_codes=None):
        """
        Get demographic data for specified LSOA codes.
        
        Parameters:
        -----------
        lsoa_codes : list
            List of LSOA codes to get demographic data for
            
        Returns:
        --------
        pandas.DataFrame
            The demographic data
        """
        try:
            if lsoa_codes:
                placeholders = ', '.join(f"'{code}'" for code in lsoa_codes)
                query = f"""
                SELECT lsoa_code, 
                       youth_male_percent, youth_female_percent,
                       young_adult_male_percent, young_adult_female_percent,
                       adult_male_percent, adult_female_percent,
                       senior_male_percent, senior_female_percent,
                       income
                FROM crime_records_enriched
                WHERE lsoa_code IN ({placeholders})
                GROUP BY lsoa_code, youth_male_percent, youth_female_percent,
                         young_adult_male_percent, young_adult_female_percent,
                         adult_male_percent, adult_female_percent,
                         senior_male_percent, senior_female_percent,
                         income
                """
            else:
                query = """
                SELECT lsoa_code, 
                       AVG(youth_male_percent) as youth_male_percent,
                       AVG(youth_female_percent) as youth_female_percent,
                       AVG(young_adult_male_percent) as young_adult_male_percent,
                       AVG(young_adult_female_percent) as young_adult_female_percent,
                       AVG(adult_male_percent) as adult_male_percent,
                       AVG(adult_female_percent) as adult_female_percent,
                       AVG(senior_male_percent) as senior_male_percent,
                       AVG(senior_female_percent) as senior_female_percent,
                       AVG(income) as income
                FROM crime_records_enriched
                GROUP BY lsoa_code
                """
            
            df = pd.read_sql(query, self.engine)
            logger.info(f"Demographic data loaded successfully with {len(df)} rows.")
            return df
        except Exception as e:
            logger.error(f"Failed to load demographic data: {e}")
            return pd.DataFrame()
    
    def run_custom_query(self, query, params=None):
        """
        Run a custom SQL query.
        
        Parameters:
        -----------
        query : str
            The SQL query to run
        params : dict
            Parameters to use in the query
            
        Returns:
        --------
        pandas.DataFrame
            The query results
        """
        try:
            if params:
                df = pd.read_sql(query, self.engine, params=params)
            else:
                df = pd.read_sql(query, self.engine)
            logger.info(f"Custom query executed successfully, returned {len(df)} rows")
            return df
        except Exception as e:
            logger.error(f"Failed to execute custom query: {e}")
            return pd.DataFrame()
    
    def _process_data_types(self, data):
        """
        Process and optimize data types in the DataFrame.
        
        Parameters:
        -----------
        data : pandas.DataFrame
            The DataFrame to process
        """
        if 'month' in data.columns:
            data['month'] = pd.to_datetime(data['month'], errors='coerce')
            if 'year' not in data.columns:
                data['year'] = data['month'].dt.year

        if 'longitude' in data.columns:
            data['longitude'] = pd.to_numeric(data['longitude'], downcast='float', errors='coerce')
        if 'latitude' in data.columns:
            data['latitude'] = pd.to_numeric(data['latitude'], downcast='float', errors='coerce')
        if 'crime_type' in data.columns:
            data['crime_type'] = data['crime_type'].astype('category')
        if 'outcome_type' in data.columns:
            data['outcome_type'] = data['outcome_type'].astype('category')