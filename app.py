import pandas as pd
import os
import numpy as np
import folium
from folium.plugins import HeatMap
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.express as px
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(message)s')

# -------------------------------
# Data Loading and Preprocessing
# -------------------------------

def load_data(base_folder_path):
    """
    Load and concatenate all CSV files from the date folders of 2023,
    but only those related to the City of London.
    """
    files_to_load = []

    # List all subdirectories in base_folder_path
    for subfolder in os.listdir(base_folder_path):
        folder_path = os.path.join(base_folder_path, subfolder)

        # Only process folders that correspond to 2023
        if os.path.isdir(folder_path) and ('2023' in subfolder):
            # List all CSV files in the subfolder
            for file in os.listdir(folder_path):
                if file.endswith('.csv'):
                    # Check if the file relates to City of London
                    if 'city-of-london'  in file.lower():
                        files_to_load.append(os.path.join(folder_path, file))

    if len(files_to_load) == 0:
        logging.error(f"No CSV files related to the City of London for 2023 found in the base directory: {base_folder_path}")
        return pd.DataFrame()
    else:
        logging.info(f"Total files selected: {len(files_to_load)} related to City of London from 2023")

    df_list = []
    for file in files_to_load:
        try:
            df = pd.read_csv(file)
            logging.info(f"Read {file} successfully.")
            df_list.append(df)
        except Exception as e:
            logging.error(f"Error reading {file}: {e}")

    if len(df_list) == 0:
        logging.error("No data was loaded into the DataFrame list.")
        return pd.DataFrame()
    else:
        crime_data = pd.concat(df_list, ignore_index=True)
        logging.info("Data successfully loaded.")
        return crime_data

def clean_data(df):
    """
    Clean and preprocess the DataFrame.
    """
    # Clean column names
    df.columns = df.columns.str.strip()

    # Print the columns to verify
    print("Columns in DataFrame:", df.columns.tolist())

    # Rename 'Last outcome category' to 'Outcome type'
    if 'Last outcome category' in df.columns:
        df.rename(columns={'Last outcome category': 'Outcome type'}, inplace=True)
    else:
        print("'Last outcome category' column not found in DataFrame.")
        df['Outcome type'] = 'Unknown'

    # Ensure 'Outcome type' column exists
    if 'Outcome type' in df.columns:
        df['Outcome type'] = df['Outcome type'].fillna('Unknown')
    else:
        print("'Outcome type' column not found in DataFrame.")
        df['Outcome type'] = 'Unknown'

    # Ensure 'Crime type' column exists
    if 'Crime type' in df.columns:
        df['Crime type'] = df['Crime type'].fillna('Unknown')
    else:
        print("'Crime type' column not found in DataFrame.")
        df['Crime type'] = 'Unknown'

    # Drop rows with missing Latitude or Longitude
    df = df.dropna(subset=['Latitude', 'Longitude'])

    # Convert Latitude and Longitude to numeric
    df = df.copy()
    df['Latitude'] = pd.to_numeric(df['Latitude'], errors='coerce')
    df['Longitude'] = pd.to_numeric(df['Longitude'], errors='coerce')

    # Drop rows where conversion to numeric failed
    df = df.dropna(subset=['Latitude', 'Longitude'])

    # Convert 'Month' to datetime if it exists
    if 'Month' in df.columns:
        df['Month'] = pd.to_datetime(df['Month'], format='%Y-%m', errors='coerce')
    else:
        print("'Month' column not found in DataFrame.")
        df['Month'] = pd.to_datetime('today')

    # Reset index after cleaning
    df.reset_index(drop=True, inplace=True)

    return df

def generate_heatmap(df):
    """
    Generate a heatmap HTML file using folium.
    """
    map_center = [df['Latitude'].mean(), df['Longitude'].mean()]
    crime_map = folium.Map(location=map_center, zoom_start=10)  # Adjusted zoom level for London
    heat_data = df[['Latitude', 'Longitude']].values.tolist()
    HeatMap(heat_data).add_to(crime_map)
    crime_map.save('crime_heatmap.html')
    logging.info("Heatmap generated and saved as 'crime_heatmap.html'.")

# -------------------------------
# Statistical Analysis Functions
# -------------------------------

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

# -------------------------------
# Main Script
# -------------------------------

# Define the path to your extracted CSV files
base_folder_path = r'C:\Users\theos\Downloads\922ca9480458c7842af50d981868fc9fce65aa62'

# Load and clean data from all date folders related to the City of London
crime_data_raw = load_data(base_folder_path)
if crime_data_raw.empty:
    raise Exception("No data available to process.")

crime_data = clean_data(crime_data_raw)

# Generate heatmap
generate_heatmap(crime_data)

# Prepare data for visualizations
outcome_counts = get_outcome_counts(crime_data)
time_series_data = get_time_series_data(crime_data)
crime_type_counts = get_crime_type_counts(crime_data)

# -------------------------------
# Dashboard Setup
# -------------------------------

# Initialize the Dash app
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
app.title = 'UK Crime Data Dashboard'

# Dark theme styling
dark_theme = {
    'background': '#1e1e1e',
    'text': '#ffffff',
    'primary': '#007aff',
    'secondary': '#8e8e93',
    'font-family': 'Helvetica Neue, Helvetica, Arial, sans-serif'
}

# Available options for filters
outcome_options = [{'label': i, 'value': i} for i in crime_data['Outcome type'].dropna().unique()]
crime_type_options = [{'label': i, 'value': i} for i in crime_data['Crime type'].dropna().unique() if pd.notnull(i)]

# Layout of the dashboard
app.layout = html.Div(style={'backgroundColor': dark_theme['background'], 'font-family': dark_theme['font-family']},
                      children=[
    html.H1(children='UK Crime Data Interactive Dashboard',
            style={'textAlign': 'center', 'color': dark_theme['primary'], 'padding': '20px 0'}),
    html.P(children='''This dashboard presents crime data from the City of London for 2023. 
        The data includes various crimes reported, their locations, and the outcomes. Use the filters below to explore the data.''',
           style={'textAlign': 'center', 'color': dark_theme['text'], 'padding': '0 20px'}),
    html.Br(),

    # Filters
    html.Div([
        html.Div([
            html.Label('Select Outcome Type:', style={'font-weight': 'bold', 'color': dark_theme['text']}),
            dcc.Dropdown(
                id='outcome-type-dropdown',
                options=outcome_options,
                value=[option['value'] for option in outcome_options],
                multi=True,
                placeholder='Select Outcome Type(s)',
                style={'backgroundColor': 'white', 'color': 'black', 'border-radius': '5px'}
            ),
        ], style={'width': '45%', 'display': 'inline-block', 'verticalAlign': 'top', 'padding': '0 20px'}),
        html.Div([
            html.Label('Select Crime Type:', style={'font-weight': 'bold', 'color': dark_theme['text']}),
            dcc.Dropdown(
                id='crime-type-dropdown',
                options=crime_type_options,
                value=[option['value'] for option in crime_type_options],
                multi=True,
                placeholder='Select Crime Type(s)',
                style={'backgroundColor': 'white', 'color': 'black', 'border-radius': '5px'}
            ),
        ], style={'width': '45%', 'display': 'inline-block', 'verticalAlign': 'top', 'padding': '0 20px'}),
    ], style={'width': '90%', 'margin': 'auto'}),
    html.Br(),

    # Map
    dcc.Graph(id='crime-scatter-map',
              style={'backgroundColor': dark_theme['background'], 'color': dark_theme['text']}),
    html.Br(),

    # Time Series Plot
    html.H2('Crime Trends Over Time',
            style={'textAlign': 'center', 'color': dark_theme['primary'],
                   'font-family': dark_theme['font-family']}),
    dcc.Graph(id='time-series-plot',
              style={'backgroundColor': dark_theme['background'], 'color': dark_theme['text']}),

    # Bar Chart of Crime Outcomes
    html.H2('Crime Outcomes Statistics',
            style={'textAlign': 'center', 'color': dark_theme['primary'],
                   'font-family': dark_theme['font-family']}),
    dcc.Graph(id='outcome-bar-chart',
              style={'backgroundColor': dark_theme['background'], 'color': dark_theme['text']}),

    # New Bar Chart of Crime Types
    html.H2('Most Common Crime Types in 2023',
            style={'textAlign': 'center', 'color': dark_theme['primary'],
                   'font-family': dark_theme['font-family']}),
    dcc.Graph(id='crime-type-bar-chart',
              style={'backgroundColor': dark_theme['background'], 'color': dark_theme['text']}),

    # Statistical Observations
    html.Div(children=[
        html.H3('Statistical Observations',
                style={'color': dark_theme['text'], 'font-family': dark_theme['font-family']}),
        html.Ul([
            html.Li(f"Total number of crimes: {len(crime_data)}",
                    style={'color': dark_theme['text']}),
            html.Li(
                f"Most common outcome: {outcome_counts.iloc[0]['Outcome Type']} ({outcome_counts.iloc[0]['Count']} occurrences)",
                style={'color': dark_theme['text']}),
            html.Li(
                f"Most frequent crime type: {crime_type_counts.iloc[0]['Crime Type']} ({crime_type_counts.iloc[0]['Count']} occurrences)",
                style={'color': dark_theme['text']}),
            html.Li(
                f"Data covers from {crime_data['Month'].min().strftime('%B %Y')} to {crime_data['Month'].max().strftime('%B %Y')}",
                style={'color': dark_theme['text']}),
        ])
    ], style={'width': '80%', 'margin': 'auto'}),
    html.Br(),
    html.Footer('© 2024 Crime Data Dashboard',
                style={'textAlign': 'center', 'color': dark_theme['secondary'],
                       'padding': '10px'})
])

# -------------------------------
# Callback Functions
# -------------------------------

@app.callback(
    [Output('crime-scatter-map', 'figure'),
     Output('time-series-plot', 'figure'),
     Output('outcome-bar-chart', 'figure'),
     Output('crime-type-bar-chart', 'figure')],  # Add the new output here
    [Input('outcome-type-dropdown', 'value'),
     Input('crime-type-dropdown', 'value')]
)
def update_dashboard(selected_outcomes, selected_crimes):
    # Filter data based on selections
    filtered_data = crime_data[
        (crime_data['Outcome type'].isin(selected_outcomes)) &
        (crime_data['Crime type'].isin(selected_crimes))
    ]

    # Update Map
    map_fig = px.scatter_mapbox(
        filtered_data,
        lat='Latitude',
        lon='Longitude',
        hover_name='Location',
        hover_data=['Outcome type', 'Crime type'],
        color='Crime type',
        zoom=6,
        height=600,
        mapbox_style='open-street-map'
    )
    map_fig.update_layout(
        paper_bgcolor=dark_theme['background'],
        plot_bgcolor=dark_theme['background'],
        font_color=dark_theme['text'],
        margin={"r": 0, "t": 0, "l": 0, "b": 0}
    )

    # Update Time Series Plot
    time_series_filtered = filtered_data.groupby(filtered_data['Month'].dt.to_period('M')).size().reset_index(
        name='Count')
    time_series_filtered['Month'] = time_series_filtered['Month'].dt.to_timestamp()
    time_series_fig = px.line(
        time_series_filtered,
        x='Month',
        y='Count',
        title='Number of Crimes Over Time',
        labels={'Count': 'Number of Crimes', 'Month': 'Month'},
        template='plotly_dark'
    )
    time_series_fig.update_layout(
        paper_bgcolor=dark_theme['background'],
        plot_bgcolor=dark_theme['background'],
        font_color=dark_theme['text']
    )

    # Update Outcome Bar Chart
    outcome_counts_filtered = filtered_data['Outcome type'].value_counts().reset_index()
    outcome_counts_filtered.columns = ['Outcome Type', 'Count']
    outcome_bar_fig = px.bar(
        outcome_counts_filtered,
        x='Outcome Type',
        y='Count',
        title='Number of Crimes per Outcome Type',
        labels={'Count': 'Number of Crimes', 'Outcome Type': 'Outcome Type'},
        template='plotly_dark'
    ).update_layout(xaxis_tickangle=-45)
    outcome_bar_fig.update_layout(
        paper_bgcolor=dark_theme['background'],
        plot_bgcolor=dark_theme['background'],
        font_color=dark_theme['text']
    )

    # Update Crime Type Bar Chart
    crime_type_counts_filtered = filtered_data['Crime type'].value_counts().reset_index()
    crime_type_counts_filtered.columns = ['Crime Type', 'Count']
    crime_type_bar_fig = px.bar(
        crime_type_counts_filtered,
        x='Crime Type',
        y='Count',
        title='Most Common Crime Types in 2023 for City of London',
        labels={'Count': 'Number of Crimes', 'Crime Type': 'Crime Type'},
        template='plotly_dark'
    ).update_layout(xaxis_tickangle=-45)
    crime_type_bar_fig.update_layout(
        paper_bgcolor=dark_theme['background'],
        plot_bgcolor=dark_theme['background'],
        font_color=dark_theme['text']
    )

    return map_fig, time_series_fig, outcome_bar_fig, crime_type_bar_fig  # Return the new bar chart

# -------------------------------
# Run the App
# -------------------------------

if __name__ == '__main__':
    app.run_server(debug=True)
