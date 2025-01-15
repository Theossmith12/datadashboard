# data_processing.py

import pandas as pd
import logging

def get_outcome_counts(df):
    """
    Get counts of crimes per outcome type.
    """
    outcome_counts = df['outcome_type'].value_counts().reset_index()
    outcome_counts.columns = ['outcome_type', 'Count']
    logging.info(f"Outcome Counts:\n{outcome_counts.head()}")
    return outcome_counts

def get_crime_type_counts(df):
    """
    Get counts of crimes per crime type.
    """
    crime_type_counts = df['crime_type'].value_counts().reset_index()
    crime_type_counts.columns = ['crime_type', 'Count']
    logging.info(f"Crime Type Counts:\n{crime_type_counts.head()}")
    return crime_type_counts

def get_time_series_data(df):
    """
    Get time series data of crime counts per month.
    """
    # Ensure the 'month' column is in datetime format
    if not pd.api.types.is_datetime64_any_dtype(df['month']):
        df['month'] = pd.to_datetime(df['month'], errors='coerce')
    
    # Drop rows with invalid 'month' dates
    initial_count = len(df)
    df = df.dropna(subset=['month'])
    dropped_count = initial_count - len(df)
    if dropped_count > 0:
        logging.warning(f"Dropped {dropped_count} rows due to invalid 'month' values.")
    
    # Group by month and count occurrences
    time_series = df.groupby(df['month'].dt.to_period('M')).size().reset_index(name='Count')
    
    # Convert Period to Timestamp for Plotly
    time_series['month'] = time_series['month'].dt.to_timestamp()
    
    return time_series

def get_yearly_comparison(df):
    """
    Compare how the most popular types of crimes have changed over each year.
    """
    df_copy = df.copy()
    df_copy['Year'] = df_copy['month'].dt.year
    yearly_comparison = df_copy.groupby(['Year', 'crime_type']).size().reset_index(name='Count')
    logging.info(f"Yearly Comparison Data:\n{yearly_comparison.head()}")
    return yearly_comparison
