import logging
import pandas as pd
from cache_config import cache
from data_service import CrimeDataService

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Initialize data service
data_service = CrimeDataService()

@cache.memoize(timeout=0)
def load_data():
    """
    Load crime data from the database using the data service.
    Returns a DataFrame with all necessary columns for the dashboard.
    """
    logger.info("Loading complete crime data through data service...")
    # Don't specify columns to get all columns (original behavior)
    return data_service.get_filtered_crime_data(filters={'census_year': 2015})

@cache.memoize(timeout=0)
def load_filtered_data(filters=None, columns=None):
    """
    Load only the necessary columns and filtered rows.
    
    Parameters:
    -----------
    filters : dict
        Filters to apply
    columns : list
        Only load these specific columns
    """
    logger.info(f"Loading filtered data with columns={columns} and filters={filters}")
    return data_service.get_filtered_crime_data(filters, columns)

@cache.memoize(timeout=0)
def load_lsoa_lookup():
    """
    Load the LSOA lookup table using the data service.
    """
    logger.info("Loading LSOA lookup through data service...")
    return data_service.get_lsoa_lookup()

@cache.memoize(timeout=0)
def load_demographic_data(lsoa_codes=None):
    """
    Load demographic data for specified LSOAs.
    """
    logger.info(f"Loading demographic data for {len(lsoa_codes) if lsoa_codes else 'all'} LSOAs...")
    return data_service.get_demographic_data(lsoa_codes)

@cache.memoize(timeout=0)
def load_aggregated_data(group_by_columns, metric_columns=None, filters=None):
    """
    Load pre-aggregated data from the database.
    
    Parameters:
    -----------
    group_by_columns : list
        Columns to group by (e.g., ['lsoa_code', 'crime_type'])
    metric_columns : dict
        Dict mapping column names to aggregation functions
    filters : dict
        Filters to apply before aggregation
    """
    logger.info(f"Loading aggregated data, grouping by {group_by_columns}")
    return data_service.get_aggregated_data(group_by_columns, metric_columns, filters)

@cache.memoize(timeout=0)
def load_unique_values(column_name):
    """
    Get unique values for a column directly from the database.
    Useful for populating dropdown options without loading all data.
    """
    logger.info(f"Loading unique values for {column_name}")
    return data_service.get_unique_values(column_name)

def reset_cache():
    """
    Manually reset the cached data. This clears the cached results for all data functions,
    ensuring that subsequent calls fetch fresh data from the database.
    """
    cache.delete_memoized(load_data)
    cache.delete_memoized(load_filtered_data)
    cache.delete_memoized(load_lsoa_lookup)
    cache.delete_memoized(load_demographic_data)
    cache.delete_memoized(load_aggregated_data)
    cache.delete_memoized(load_unique_values)
    logger.info("Cache has been manually reset for all data functions.")

def run_custom_query(query, params=None):
    """
    Run a custom SQL query through the data service.
    This function is not cached - use with caution.
    """
    logger.warning("Running custom query (uncached) - use with caution")
    return data_service.run_custom_query(query, params)