import pandas as pd
import os
import glob
import logging
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
import plotly.express as px
import plotly.graph_objs as go
from pages.statistics import statistics_layout  # Import the statistics page layout
import data_processing  # Import the data processing module

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(message)s')

# -------------------------------
# Data Loading and Preprocessing
# -------------------------------

def load_data(base_folder_path):
    """
    Load and concatenate all CSV files from the date folders,
    but only those related to the Metropolitan area.
    """
    csv_files = glob.glob(os.path.join(base_folder_path, '**', '*metropolitan*.csv'), recursive=True)

    if not csv_files:
        logging.error(f"No CSV files found in the base directory: {base_folder_path}")
        return pd.DataFrame()

    # Use ThreadPoolExecutor to load files concurrently
    def read_file(file):
        try:
            df = pd.read_csv(file)
            logging.info(f"Read {file} successfully.")
            return df
        except Exception as e:
            logging.error(f"Error reading {file}: {e}")
            return None

    with ThreadPoolExecutor() as executor:
        df_list = list(executor.map(read_file, csv_files))

    df_list = [df for df in df_list if df is not None]
    if not df_list:
        logging.error("No data was loaded.")
        return pd.DataFrame()

    return pd.concat(df_list, ignore_index=True)

def clean_data(df):
    """
    Clean and preprocess the DataFrame.
    """
    df.columns = df.columns.str.strip()

    # Rename columns if they exist
    df.rename(columns={'Last outcome category': 'Outcome type'}, inplace=True, errors='ignore')

    # Fill missing values
    df['Outcome type'] = df.get('Outcome type', 'Unknown').fillna('Unknown')
    df['Crime type'] = df.get('Crime type', 'Unknown').fillna('Unknown')

    # Drop rows with missing Latitude and Longitude
    df = df.dropna(subset=['Latitude', 'Longitude'])

    # Convert Latitude and Longitude to numeric
    df['Latitude'] = pd.to_numeric(df['Latitude'], errors='coerce')
    df['Longitude'] = pd.to_numeric(df['Longitude'], errors='coerce')
    df = df.dropna(subset=['Latitude', 'Longitude'])

    # Convert 'Month' to datetime
    df['Month'] = pd.to_datetime(df.get('Month', pd.to_datetime('today')), format='%Y-%m', errors='coerce')

    return df.reset_index(drop=True)

# Cache the loaded data to avoid reloading unnecessarily
@lru_cache(maxsize=1)
def load_cached_data(base_folder_path):
    return load_data(base_folder_path)

# -------------------------------
# Dash Dashboard Setup
# -------------------------------

# Initialize the Dash app with multi-page support
app = dash.Dash(__name__, suppress_callback_exceptions=True)
app.title = 'UK Crime Data Dashboard'

server = app.server  # Expose the server variable for deployments

# Load data
base_folder_path = os.path.join(os.path.dirname(__file__), 'data')  # Updated to use the data directory
crime_data_raw = load_cached_data(base_folder_path)
crime_data = clean_data(crime_data_raw)

# Print columns for debugging
logging.info(f"Columns in crime_data: {crime_data.columns.tolist()}")

# -------------------------------
# Layout and Navigation
# -------------------------------

# Define the navigation bar
navbar = html.Div(
    [
        dcc.Link('Dashboard', href='/', className='nav-link'),
        dcc.Link('View Models', href='/statistics', className='nav-link'),
    ],
    className='navbar'
)

# Define the app layout with page content
app.layout = html.Div([  # Define the app layout
    dcc.Location(id='url', refresh=False),
    navbar,
    html.Div(id='page-content')
])

# -------------------------------
# Page: Dashboard
# -------------------------------

def dashboard_layout():
    # Check if data is available
    if crime_data.empty:
        return html.Div(
            "No data available.",
            style={
                'color': '#e0e0e0',
                'backgroundColor': '#121212',
                'height': '100vh',
                'display': 'flex',
                'justifyContent': 'center',
                'alignItems': 'center',
                'font-size': '24px'
            }
        )
    else:
        # Prepare dropdown options
        outcome_options = [{'label': i, 'value': i} for i in sorted(crime_data['Outcome type'].dropna().unique())]
        crime_type_options = [{'label': i, 'value': i} for i in sorted(crime_data['Crime type'].dropna().unique()) if pd.notnull(i)]

        return html.Div(
            style={'backgroundColor': '#121212', 'font-family': 'Segoe UI, Tahoma, Geneva, Verdana, sans-serif'},
            children=[
                html.Div(
                    className='header',
                    children=[
                        html.H1('UK Crime Data Interactive Dashboard'),
                        html.P('''This dashboard presents street-level crime data from Metropolitan areas from 2021 - July 2024
                                The data includes various crimes reported, their locations, and the outcomes.
                                Use the filters below to explore the data. The visualizations show trends,
                                outcomes, and crime type statistics over time. Note the map only displays 10000 incidents''')
                    ]
                ),

                # Filters
                html.Div([
                    html.Div([
                        html.Label('Select Outcome Type:', style={'font-weight': 'bold', 'color': '#e0e0e0'}),
                        dcc.Dropdown(
                            id='outcome-type-dropdown',
                            options=outcome_options,
                            value=[option['value'] for option in outcome_options],  # Select all by default
                            multi=True,
                            placeholder='Select Outcome Type(s)',
                            className='dropdown'
                        ),
                        html.Button('Select All', id='select-all-outcome', n_clicks=0, className='select-all-btn'),
                        html.Button('Deselect All', id='deselect-all-outcome', n_clicks=0, className='deselect-all-btn'),
                    ], className='dropdown-container'),

                    html.Div([
                        html.Label('Select Crime Type:', style={'font-weight': 'bold', 'color': '#e0e0e0'}),
                        dcc.Dropdown(
                            id='crime-type-dropdown',
                            options=crime_type_options,
                            value=[option['value'] for option in crime_type_options],  # Select all by default
                            multi=True,
                            placeholder='Select Crime Type(s)',
                            className='dropdown'
                        ),
                        html.Button('Select All', id='select-all-crime', n_clicks=0, className='select-all-btn'),
                        html.Button('Deselect All', id='deselect-all-crime', n_clicks=0, className='deselect-all-btn'),
                    ], className='dropdown-container'),
                ], className='filters'),

                # Loading Indicators
                dcc.Loading(
                    id="loading-graphs",
                    type="circle",
                    children=[
                        # Map
                        html.Div(
                            dcc.Graph(
                                id='crime-scatter-map',
                                config={'displayModeBar': False, 'scrollZoom': True},  # Enabled scrollZoom here
                                style={'height': '600px'}
                            ),
                            className='graph-container'
                        ),

                        # Heatmap
                        html.Div(
                            dcc.Graph(
                                id='crime-heatmap',
                                config={'displayModeBar': False},
                                style={'height': '600px'}
                            ),
                            className='graph-container'
                        ),

                        # Time Series Plot
                        html.Div([
                            html.H2('Crime Trends Over Time'),
                            dcc.Graph(id='time-series-plot')
                        ], className='graph-container'),

                        # Bar Chart of Crime Outcomes
                        html.Div([
                            html.H2('Crime Outcomes Statistics'),
                            dcc.Graph(id='outcome-bar-chart')
                        ], className='graph-container'),

                        # Crime Type Bar Chart
                        html.Div([
                            html.H2('Most Common Crime Types'),
                            dcc.Graph(id='crime-type-bar-chart')
                        ], className='graph-container'),

                        # Yearly Comparison of Crime Types
                        html.Div([
                            html.H2('Crime Type Trends Over the Years'),
                            dcc.Graph(id='yearly-comparison-chart')
                        ], className='graph-container'),
                    ]
                ),

                # Summary Statistics Section
                html.Div(
                    className='summary',
                    children=[
                        html.H2('Summary Statistics'),
                        html.Ul([
                            html.Li(f"Total number of crimes: {len(crime_data)}"),
                            html.Li(f"Most common crime type: {data_processing.get_crime_type_counts(crime_data).iloc[0]['Crime Type']}" if 'Crime type' in crime_data.columns else "Most common crime type: N/A"),
                            html.Li(f"Most common outcome type: {data_processing.get_outcome_counts(crime_data).iloc[0]['Outcome Type']}" if 'Outcome type' in crime_data.columns else "Most common outcome type: N/A"),
                            html.Li(
                                f"Data covers from {crime_data['Month'].min().strftime('%B %Y')} to {crime_data['Month'].max().strftime('%B %Y')}"
                                if 'Month' in crime_data.columns else "Data covers an unknown time period."
                            ),
                        ])
                    ]
                ),
            ]
        )

# -------------------------------
# Update Page Content
# -------------------------------

@app.callback(
    Output('page-content', 'children'),
    [Input('url', 'pathname')]
)
def display_page(pathname):
    if pathname == '/statistics':
        return statistics_layout(crime_data)  # Pass crime_data to statistics_layout
    else:
        return dashboard_layout()

# -------------------------------
# Select/Deselect All Callbacks
# -------------------------------

@app.callback(
    [
        Output('outcome-type-dropdown', 'value'),
    ],
    [
        Input('select-all-outcome', 'n_clicks'),
        Input('deselect-all-outcome', 'n_clicks'),
    ],
    [State('outcome-type-dropdown', 'options')]
)
def select_deselect_outcome(select_all_clicks, deselect_all_clicks, options):
    ctx = dash.callback_context
    if not ctx.triggered:
        return [dash.no_update]
    else:
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]
        if button_id == 'select-all-outcome':
            return [[option['value'] for option in options]]
        elif button_id == 'deselect-all-outcome':
            return [[]]
    return [dash.no_update]

@app.callback(
    [
        Output('crime-type-dropdown', 'value'),
    ],
    [
        Input('select-all-crime', 'n_clicks'),
        Input('deselect-all-crime', 'n_clicks'),
    ],
    [State('crime-type-dropdown', 'options')]
)
def select_deselect_crime(select_all_clicks, deselect_all_clicks, options):
    ctx = dash.callback_context
    if not ctx.triggered:
        return [dash.no_update]
    else:
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]
        if button_id == 'select-all-crime':
            return [[option['value'] for option in options]]
        elif button_id == 'deselect-all-crime':
            return [[]]
    return [dash.no_update]

# -------------------------------
# Callback Functions
# -------------------------------

# Add a cap for maximum points to load
MAX_POINTS = 10000

def generate_map(filtered_data, map_view):
    """
    Generate the scatter mapbox figure.
    """
    if map_view:
        center = map_view.get('mapbox.center', {'lat': filtered_data['Latitude'].mean(), 'lon': filtered_data['Longitude'].mean()})
        zoom = map_view.get('mapbox.zoom', 6)
    else:
        center = {'lat': filtered_data['Latitude'].mean(), 'lon': filtered_data['Longitude'].mean()}
        zoom = 6

    map_fig = px.scatter_mapbox(
        filtered_data,
        lat='Latitude',
        lon='Longitude',
        hover_name='Location',
        hover_data=['Outcome type', 'Crime type'],
        color='Crime type',
        zoom=zoom,
        height=600,
        mapbox_style='open-street-map',
        center=center
    )
    return map_fig.update_layout(
        paper_bgcolor='#121212',
        plot_bgcolor='#121212',
        font_color='#e0e0e0',
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        uirevision='constant',  # Prevent map from refreshing unnecessarily
        dragmode='pan'           # Allow panning
    )

def generate_heatmap(filtered_data):
    """
    Generate a heatmap figure based on crime density.
    """
    if filtered_data.empty:
        logging.warning("Filtered data is empty, cannot generate heatmap.")
        return go.Figure()

    heatmap_fig = go.Figure(
        go.Densitymapbox(
            lat=filtered_data['Latitude'],
            lon=filtered_data['Longitude'],
            z=filtered_data['Crime type'].apply(lambda x: 1),  # Each crime has equal weight
            radius=10,
            colorscale='Viridis',
            showscale=True
        )
    )
    heatmap_fig.update_layout(
        mapbox_style="open-street-map",
        mapbox_center_lat=filtered_data['Latitude'].mean(),
        mapbox_center_lon=filtered_data['Longitude'].mean(),
        mapbox_zoom=10,
        paper_bgcolor='#121212',
        plot_bgcolor='#121212',
        font_color='#e0e0e0',
        margin={"r": 0, "t": 0, "l": 0, "b": 0}
    )
    return heatmap_fig

def generate_time_series(filtered_data):
    if 'Month' not in filtered_data.columns:
        logging.warning("'Month' column not found for time series plot.")
        return {}
    if filtered_data.empty:
        logging.warning("Filtered data is empty, cannot generate time series.")
        return go.Figure()
    time_series_filtered = data_processing.get_time_series_data(filtered_data)
    return px.line(
        time_series_filtered,
        x='Month',
        y='Count',
        title='Crime Incidents Over Time',
        labels={'Count': 'Number of Crimes', 'Month': 'Month'},
        template='plotly_dark'
    ).update_layout(
        paper_bgcolor='#121212',
        plot_bgcolor='#121212',
        font_color='#e0e0e0'
    )

def generate_outcome_bar_chart(filtered_data):
    if 'Outcome type' not in filtered_data.columns:
        logging.warning("'Outcome type' column not found for outcome bar chart.")
        return {}
    if filtered_data.empty:
        logging.warning("Filtered data is empty, cannot generate outcome bar chart.")
        return go.Figure()
    outcome_counts_filtered = data_processing.get_outcome_counts(filtered_data)
    return px.bar(
        outcome_counts_filtered,
        x='Outcome Type',
        y='Count',
        title='Crimes per Outcome Type',
        labels={'Count': 'Number of Crimes', 'Outcome Type': 'Outcome Type'},
        template='plotly_dark'
    ).update_layout(xaxis_tickangle=-45)

def generate_crime_type_bar_chart(filtered_data):
    if 'Crime type' not in filtered_data.columns:
        logging.warning("'Crime type' column not found for crime type bar chart.")
        return {}
    if filtered_data.empty:
        logging.warning("Filtered data is empty, cannot generate crime type bar chart.")
        return go.Figure()
    crime_type_counts_filtered = data_processing.get_crime_type_counts(filtered_data)
    return px.bar(
        crime_type_counts_filtered,
        x='Crime Type',
        y='Count',
        title='Most Common Crime Types',
        labels={'Count': 'Number of Crimes', 'Crime Type': 'Crime Type'},
        template='plotly_dark'
    ).update_layout(xaxis_tickangle=-45)

def generate_yearly_comparison_chart(filtered_data):
    if 'Month' not in filtered_data.columns or 'Crime type' not in filtered_data.columns:
        logging.warning("'Month' or 'Crime type' column not found for yearly comparison chart.")
        return {}
    if filtered_data.empty:
        logging.warning("Filtered data is empty, cannot generate yearly comparison chart.")
        return go.Figure()
    yearly_comparison_data = data_processing.get_yearly_comparison(filtered_data)
    return px.bar(
        yearly_comparison_data,
        x='Year',
        y='Count',
        color='Crime type',
        barmode='group',
        title='Yearly Comparison of Crime Types',
        labels={'Count': 'Number of Crimes', 'Year': 'Year'},
        template='plotly_dark'
    )

@app.callback(
    [
        Output('crime-scatter-map', 'figure'),
        Output('crime-heatmap', 'figure'),
        Output('time-series-plot', 'figure'),
        Output('outcome-bar-chart', 'figure'),
        Output('crime-type-bar-chart', 'figure'),
        Output('yearly-comparison-chart', 'figure')
    ],
    [
        Input('outcome-type-dropdown', 'value'),
        Input('crime-type-dropdown', 'value')
    ],
    [
        State('crime-scatter-map', 'relayoutData')
    ]
)
def update_dashboard(selected_outcomes, selected_crimes, relayout_data):
    # Filter data based on selected outcomes and crimes
    filtered_data = crime_data[
        (crime_data['Outcome type'].isin(selected_outcomes)) &
        (crime_data['Crime type'].isin(selected_crimes))
    ]

    logging.info(f"Filtered data contains {len(filtered_data)} records.")

    # Cap the number of points loaded for the map
    if len(filtered_data) > MAX_POINTS:
        map_data = filtered_data.sample(MAX_POINTS)
    else:
        map_data = filtered_data

    # Extract map view
    map_view = {}
    if relayout_data:
        if 'mapbox.center' in relayout_data:
            map_view['mapbox.center'] = relayout_data['mapbox.center']
        if 'mapbox.zoom' in relayout_data:
            map_view['mapbox.zoom'] = relayout_data['mapbox.zoom']

    return (
        generate_map(map_data, map_view),
        generate_heatmap(filtered_data),
        generate_time_series(filtered_data),
        generate_outcome_bar_chart(filtered_data),
        generate_crime_type_bar_chart(filtered_data),
        generate_yearly_comparison_chart(filtered_data)
    )

# -------------------------------
# Run the App
# -------------------------------

if __name__ == '__main__':
    app.run_server(debug=True)