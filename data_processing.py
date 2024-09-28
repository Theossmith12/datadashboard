# data_processing.py

def get_outcome_counts(df):
    """
    Get counts of crimes per outcome type.
    """
    outcome_counts = df['Outcome type'].value_counts().reset_index()
    outcome_counts.columns = ['Outcome Type', 'Count']
    return outcome_counts

def get_time_series_data(df):
    """
    Get time series data of crime counts per month.
    """
    time_series = df.groupby(df['Month'].dt.to_period('M')).size().reset_index(name='Count')
    time_series['Month'] = time_series['Month'].dt.to_timestamp()
    return time_series

def get_crime_type_counts(df):
    """
    Get counts of crimes per crime type.
    """
    crime_type_counts = df['Crime type'].value_counts().reset_index()
    crime_type_counts.columns = ['Crime Type', 'Count']
    return crime_type_counts

def get_yearly_comparison(df):
    """
    Compare how the most popular types of crimes have changed over each year.
    """
    df_copy = df.copy()
    df_copy['Year'] = df_copy['Month'].dt.year
    yearly_comparison = df_copy.groupby(['Year', 'Crime type']).size().reset_index(name='Count')
    return yearly_comparison
