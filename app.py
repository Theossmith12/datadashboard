# app.py

import pandas as pd
import logging
from functools import lru_cache
import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
import plotly.express as px
import plotly.graph_objs as go
from pages.statistics import statistics_layout  # Import the statistics page layout
import data_processing  # Import the data processing module
from sqlalchemy import create_engine
from dotenv import load_dotenv
import os

load_dotenv()  # <-- This line must be at the top

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(message)s')

# -------------------------------
# Data Loading and Preprocessing
# -------------------------------
def load_data():
    """
    Load all crime data from the PostgreSQL database.
    """
    try:

        DB_USER = os.getenv('DB_USER')
        DB_PASS = os.getenv('DB_PASSWORD')
        DB_NAME = os.getenv('DB_NAME')
        DB_CONN_NAME = os.getenv('INSTANCE_CONNECTION_NAME')

        DATABASE_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@/{DB_NAME}?host=/cloudsql/{DB_CONN_NAME}"

        # PostgreSQL connection setup
        engine = create_engine(DATABASE_URL)
        
        # SQL query to fetch all data
        query = "SELECT * FROM crime_records"
        
        # Load data from PostgreSQL
        data = pd.read_sql(query, engine, parse_dates=['month'])
        
        logging.info("Data loaded successfully from the PostgreSQL database.")
        logging.info(f"Data types after loading:\n{data.dtypes}")
        logging.info(f"First few rows of data:\n{data.head()}")
        return data

    except Exception as e:
        logging.error(f"Failed to load data from the database: {e}")
        return pd.DataFrame()  # Always return a DataFrame

# Cache the loaded data to avoid reloading unnecessarily
@lru_cache(maxsize=1)
def load_cached_data():
    return load_data()

# -------------------------------
# Dash Dashboard Setup
# -------------------------------

# Initialize the Dash app with multi-page support
app = dash.Dash(__name__, suppress_callback_exceptions=True)
app.title = 'UK Crime Data Dashboard'

server = app.server  # Expose the server variable for deployments

# Load data
crime_data = load_cached_data()

# Print columns for debugging
logging.info(f"Columns in crime_data: {crime_data.columns.tolist()}")

# -------------------------------
# Layout and Navigation
# -------------------------------

# Define the navigation bar
navbar = html.Div(
    [
        dcc.Link('Dashboard', href='/', className='nav-link', style={'margin-right': '20px', 'color': '#e0e0e0'}),
        dcc.Link('View Models', href='/statistics', className='nav-link', style={'color': '#e0e0e0'}),
    ],
    className='navbar',
    style={
        'backgroundColor': '#1f1f1f',
        'padding': '10px',
        'font-size': '18px'
    }
)

# Define the app layout with page content
app.layout = html.Div([  # Define the app layout
    dcc.Location(id='url', refresh=False),
    navbar,
    html.Div(id='page-content')
], style={'backgroundColor': '#121212'})

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
        outcome_options = [{'label': i, 'value': i} for i in sorted(crime_data['outcome_type'].dropna().unique())]
        crime_type_options = [{'label': i, 'value': i} for i in sorted(crime_data['crime_type'].dropna().unique()) if pd.notnull(i)]

        return html.Div(
            style={'backgroundColor': '#121212', 'font-family': 'Segoe UI, Tahoma, Geneva, Verdana, sans-serif'},
            children=[
                html.Div(
                    className='header',
                    children=[
                        html.H1('UK Crime Data Interactive Dashboard', style={'color': '#e0e0e0'}),
                        html.P('''This dashboard presents street-level crime data from Metropolitan areas from 2021 - July 2024.
                                The data includes various crimes reported, their locations, and the outcomes.
                                Use the filters below to explore the data. The visualizations show trends,
                                outcomes, and crime type statistics over time. Note the map only displays up to 10,000 incidents.''',
                               style={'color': '#e0e0e0'})
                    ]
                ),

                # Filters
                html.Div([
                    html.Div([
                        html.Label('Select Outcome Type:', style={'font-weight': 'bold', 'color': '#e0e0e0'}),
                        dcc.Dropdown(
                            id='outcome-type-dropdown',
                            options=outcome_options,
                            value=[],  # Select all by default
                            multi=True,
                            placeholder='Select Outcome Type(s)',
                            className='dropdown',
                            style={'color': '#000000'}
                        ),
                        html.Button('Select All', id='select-all-outcome', n_clicks=0, className='select-all-btn', style={'margin-top': '5px'}),
                        html.Button('Deselect All', id='deselect-all-outcome', n_clicks=0, className='deselect-all-btn', style={'margin-top': '5px'}),
                    ], className='dropdown-container', style={'width': '45%', 'display': 'inline-block', 'margin-right': '5%'}),

                    html.Div([
                        html.Label('Select Crime Type:', style={'font-weight': 'bold', 'color': '#e0e0e0'}),
                        dcc.Dropdown(
                            id='crime-type-dropdown',
                            options=crime_type_options,
                            value=[option['value'] for option in crime_type_options],  # Select all by default
                            multi=True,
                            placeholder='Select Crime Type(s)',
                            className='dropdown',
                            style={'color': '#000000'}
                        ),
                        html.Button('Select All', id='select-all-crime', n_clicks=0, className='select-all-btn', style={'margin-top': '5px'}),
                        html.Button('Deselect All', id='deselect-all-crime', n_clicks=0, className='deselect-all-btn', style={'margin-top': '5px'}),
                    ], className='dropdown-container', style={'width': '45%', 'display': 'inline-block'}),
                ], className='filters', style={'padding': '20px'}),

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
                            className='graph-container',
                            style={'width': '100%', 'padding': '10px'}
                        ),

                        # Heatmap with Label
                        html.Div([
                            html.H2('Crime Density Heatmap', style={'color': '#e0e0e0', 'textAlign': 'center'}),
                            dcc.Graph(
                                id='crime-heatmap',
                                config={
                                    'displayModeBar': True,    # show the bar with zoom, fullscreen, etc.
                                    'scrollZoom': True,        # allow trackpad/mousewheel zoom
                                    'doubleClick': 'reset',    # optional: double-click to reset
                                    'showTips': True           # optional: show tips on how to interact
                                },
                                style={'height': '600px'}
                            )
                        ], className='graph-container', style={'width': '100%', 'padding': '10px'}),

                        # Time Series Plot
                        html.Div([
                            html.H2('Crime Trends Over Time', style={'color': '#e0e0e0'}),
                            dcc.Graph(id='time-series-plot')
                        ], className='graph-container', style={'width': '100%', 'padding': '10px'}),

                        # Bar Chart of Crime Outcomes
                        html.Div([
                            html.H2('Crime Outcomes Statistics', style={'color': '#e0e0e0'}),
                            dcc.Graph(id='outcome-bar-chart')
                        ], className='graph-container', style={'width': '48%', 'display': 'inline-block', 'padding': '10px'}),

                        # Crime Type Bar Chart
                        html.Div([
                            html.H2('Most Common Crime Types', style={'color': '#e0e0e0'}),
                            dcc.Graph(id='crime-type-bar-chart')
                        ], className='graph-container', style={'width': '48%', 'display': 'inline-block', 'padding': '10px'}),

                        # Yearly Comparison of Crime Types
                        html.Div([
                            html.H2('Crime Type Trends Over the Years', style={'color': '#e0e0e0'}),
                            dcc.Graph(id='yearly-comparison-chart')
                        ], className='graph-container', style={'width': '100%', 'padding': '10px'}),
                    ]
                ),

                # Summary Statistics Section
                html.Div(
                    id='summary-statistics',  # Assign a unique ID for dynamic updates
                    className='summary',
                    style={'padding': '20px'},
                    children=[
                        html.H2('Summary Statistics', style={'color': '#e0e0e0'}),
                        html.Ul([
                            # Placeholder list items; will be updated via callback
                            html.Li("Total number of crimes: Loading...", style={'color': '#e0e0e0'}),
                            html.Li("Most common crime type: Loading...", style={'color': '#e0e0e0'}),
                            html.Li("Most common outcome type: Loading...", style={'color': '#e0e0e0'}),
                            html.Li("Data covers from Loading... to Loading...", style={'color': '#e0e0e0'}),
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
    Output('outcome-type-dropdown', 'value'),
    [
        Input('select-all-outcome', 'n_clicks'),
        Input('deselect-all-outcome', 'n_clicks'),
    ],
    [State('outcome-type-dropdown', 'options')]
)
def select_deselect_outcome(select_all_clicks, deselect_all_clicks, options):
    ctx = dash.callback_context
    if not ctx.triggered:
        return dash.no_update
    else:
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]
        if button_id == 'select-all-outcome':
            return [option['value'] for option in options]
        elif button_id == 'deselect-all-outcome':
            return []
    return dash.no_update

@app.callback(
    Output('crime-type-dropdown', 'value'),
    [
        Input('select-all-crime', 'n_clicks'),
        Input('deselect-all-crime', 'n_clicks'),
    ],
    [State('crime-type-dropdown', 'options')]
)
def select_deselect_crime(select_all_clicks, deselect_all_clicks, options):
    ctx = dash.callback_context
    if not ctx.triggered:
        return dash.no_update
    else:
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]
        if button_id == 'select-all-crime':
            return [option['value'] for option in options]
        elif button_id == 'deselect-all-crime':
            return []
    return dash.no_update

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
        center = map_view.get('mapbox.center', {'lat': filtered_data['latitude'].mean(), 'lon': filtered_data['longitude'].mean()})
        zoom = map_view.get('mapbox.zoom', 6)
    else:
        center = {'lat': filtered_data['latitude'].mean(), 'lon': filtered_data['longitude'].mean()}
        zoom = 6

    map_fig = px.scatter_mapbox(
        filtered_data,
        lat='latitude',
        lon='longitude',
        hover_data=['outcome_type', 'crime_type'],
        color='crime_type',
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
    Generate a heatmap figure based on crime density with a smooth gradient.
    """
    if filtered_data.empty:
        logging.warning("Filtered data is empty, cannot generate heatmap.")
        return go.Figure()

    # Copy the filtered DataFrame so we don't modify the original
    heatmap_data = filtered_data.copy()
    # Create a dummy column with a constant value of 1
    heatmap_data['density_val'] = 1

    # Now pass 'density_val' for z
    heatmap_fig = px.density_mapbox(
        heatmap_data,
        lat='latitude',
        lon='longitude',
        z='density_val',  # <--- reference the dummy column here
        radius=20,
        center=dict(
            lat=heatmap_data['latitude'].mean(),
            lon=heatmap_data['longitude'].mean()
        ),
        zoom=10,
        mapbox_style="open-street-map",
        # Choose a color scale that transitions from light to dark red
        color_continuous_scale='YlOrRd',
        title='Crime Density Heatmap'
    )

    heatmap_fig.update_layout(
        paper_bgcolor='#121212',
        plot_bgcolor='#121212',
        font_color='#e0e0e0',
        margin={"r": 0, "t": 50, "l": 0, "b": 0},
        coloraxis_colorbar=dict(
            title="Crime Density",
            titleside="right",
            titlefont=dict(color="#e0e0e0"),
            tickfont=dict(color="#e0e0e0")
        )
    )

    return heatmap_fig


def generate_time_series(filtered_data):
    if 'month' not in filtered_data.columns:
        logging.warning("'month' column not found for time series plot.")
        return {}
    if filtered_data.empty:
        logging.warning("Filtered data is empty, cannot generate time series.")
        return go.Figure()
    time_series_filtered = data_processing.get_time_series_data(filtered_data)
    logging.info(f"Generating Time Series Plot with data:\n{time_series_filtered.head()}")
    return px.line(
        time_series_filtered,
        x='month',
        y='Count',
        title='Crime Incidents Over Time',
        labels={'Count': 'Number of Crimes', 'month': 'Month'},
        template='plotly_dark'
    ).update_layout(
        paper_bgcolor='#121212',
        plot_bgcolor='#121212',
        font_color='#e0e0e0'
    )

def generate_outcome_bar_chart(filtered_data):
    if 'outcome_type' not in filtered_data.columns:
        logging.warning("'outcome_type' column not found for outcome bar chart.")
        return {}
    if filtered_data.empty:
        logging.warning("Filtered data is empty, cannot generate outcome bar chart.")
        return go.Figure()
    outcome_counts_filtered = data_processing.get_outcome_counts(filtered_data)
    logging.info(f"Generating Outcome Bar Chart with data:\n{outcome_counts_filtered.head()}")
    return px.bar(
        outcome_counts_filtered,
        x='outcome_type',
        y='Count',
        title='Crimes per Outcome Type',
        labels={'outcome_type': 'Outcome Type', 'Count': 'Number of Crimes'},
        template='plotly_dark'
    ).update_layout(xaxis_tickangle=-45)

def generate_crime_type_bar_chart(filtered_data):
    if 'crime_type' not in filtered_data.columns:
        logging.warning("'crime_type' column not found for crime type bar chart.")
        return {}
    if filtered_data.empty:
        logging.warning("Filtered data is empty, cannot generate crime type bar chart.")
        return go.Figure()
    crime_type_counts_filtered = data_processing.get_crime_type_counts(filtered_data)
    logging.info(f"Generating Crime Type Bar Chart with data:\n{crime_type_counts_filtered.head()}")
    return px.bar(
        crime_type_counts_filtered,
        x='crime_type',
        y='Count',
        title='Most Common Crime Types',
        labels={'crime_type': 'Crime Type', 'Count': 'Number of Crimes'},
        template='plotly_dark'
    ).update_layout(xaxis_tickangle=-45)

def generate_yearly_comparison_chart(filtered_data):
    if 'month' not in filtered_data.columns or 'crime_type' not in filtered_data.columns:
        logging.warning("'month' or 'crime_type' column not found for yearly comparison chart.")
        return {}
    if filtered_data.empty:
        logging.warning("Filtered data is empty, cannot generate yearly comparison chart.")
        return go.Figure()
    yearly_comparison_data = data_processing.get_yearly_comparison(filtered_data)
    logging.info(f"Generating Yearly Comparison Chart with data:\n{yearly_comparison_data.head()}")
    return px.bar(
        yearly_comparison_data,
        x='Year',
        y='Count',
        color='crime_type',  # Correct column name
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
        (crime_data['outcome_type'].isin(selected_outcomes)) &
        (crime_data['crime_type'].isin(selected_crimes))
    ]

    logging.info(f"Filtered data contains {len(filtered_data)} records.")

    # Cap the number of points loaded for the map
    if len(filtered_data) > MAX_POINTS:
        map_data = filtered_data.sample(MAX_POINTS)
        logging.info(f"Sampling {MAX_POINTS} points from filtered data for the map.")
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
# Summary Statistics Callback
# -------------------------------

@app.callback(
    Output('summary-statistics', 'children'),
    [
        Input('outcome-type-dropdown', 'value'),
        Input('crime-type-dropdown', 'value')
    ]
)
def update_summary_statistics(selected_outcomes, selected_crimes):
    # Filter data based on selected outcomes and crimes
    filtered_data = crime_data[
        (crime_data['outcome_type'].isin(selected_outcomes)) &
        (crime_data['crime_type'].isin(selected_crimes))
    ]

    logging.info(f"Summary Statistics - Filtered data contains {len(filtered_data)} records.")

    if filtered_data.empty:
        return [
            html.H2('Summary Statistics', style={'color': '#e0e0e0'}),
            html.Ul([
                html.Li("Total number of crimes: 0", style={'color': '#e0e0e0'}),
                html.Li("Most common crime type: N/A", style={'color': '#e0e0e0'}),
                html.Li("Most common outcome type: N/A", style={'color': '#e0e0e0'}),
                html.Li("Data covers from N/A to N/A", style={'color': '#e0e0e0'}),
            ])
        ]

    # Calculate summary statistics
    total_crimes = len(filtered_data)

    # Most common crime type
    crime_type_counts = data_processing.get_crime_type_counts(filtered_data)
    if not crime_type_counts.empty:
        most_common_crime_type = crime_type_counts.iloc[0]['crime_type']
    else:
        most_common_crime_type = "N/A"

    # Most common outcome type
    outcome_counts = data_processing.get_outcome_counts(filtered_data)
    if not outcome_counts.empty:
        most_common_outcome_type = outcome_counts.iloc[0]['outcome_type']
    else:
        most_common_outcome_type = "N/A"

    # Data coverage period
    min_month = filtered_data['month'].min().strftime('%B %Y') if 'month' in filtered_data.columns else "N/A"
    max_month = filtered_data['month'].max().strftime('%B %Y') if 'month' in filtered_data.columns else "N/A"

    return [
        html.H2('Summary Statistics', style={'color': '#e0e0e0'}),
        html.Ul([
            html.Li(f"Total number of crimes: {total_crimes}", style={'color': '#e0e0e0'}),
            html.Li(f"Most common crime type: {most_common_crime_type}", style={'color': '#e0e0e0'}),
            html.Li(f"Most common outcome type: {most_common_outcome_type}", style={'color': '#e0e0e0'}),
            html.Li(f"Data covers from {min_month} to {max_month}", style={'color': '#e0e0e0'}),
        ])
    ]


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))  # Cloud Run provides PORT
    app.run(host="0.0.0.0", port=port, debug=True)
