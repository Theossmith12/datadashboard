import logging
import pandas as pd
import dash
import dash_bootstrap_components as dbc
from dash import dcc, html, Input, Output, State
import plotly.express as px
import plotly.graph_objs as go
import numpy as np
import json
import os
from pages.theme_utils import register_theme_callbacks


from data_loader import *
from utils import update_fig_layout

MAX_POINTS = 10000

# ---------------------------------------------------------------------------------
# Setup Logging
# ---------------------------------------------------------------------------------
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
if not logger.handlers:
    # Add a console handler so logs show up in stdout
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter("[%(levelname)s] %(name)s - %(message)s")
    ch.setFormatter(formatter)
    logger.addHandler(ch)

print("Current working directory:", os.getcwd())

# ---------------------------------------------------------------------------------
# Load GeoJSON Data
# ---------------------------------------------------------------------------------
with open("data/alt_lsoa_boundaries.geojson", "r") as f:
    lsoa_geojson = json.load(f)
logger.info(f"Loaded LSOA GeoJSON with {len(lsoa_geojson.get('features', []))} features.")

# Load London Borough boundaries
try:
    with open("data/london_boroughs.geojson", "r") as f:
        borough_geojson = json.load(f)
    logger.info(f"Successfully loaded Borough GeoJSON with {len(borough_geojson.get('features', []))} features.")
except Exception as e:
    logger.error(f"Error loading london_boroughs.geojson: {e}")
    borough_geojson = {"type": "FeatureCollection", "features": []}

# ---------------------------------------------------------------------------------
# Extract Borough Centroids
# ---------------------------------------------------------------------------------
borough_centroids = {}
for feature in borough_geojson['features']:
    try:
        borough_name = feature['properties']['name']
        geometry_type = feature['geometry']['type']
        coords_data = feature['geometry']['coordinates']

        if geometry_type == 'Polygon':
            coords = np.array(coords_data[0])
            lon_center = coords[:, 0].mean()
            lat_center = coords[:, 1].mean()
            borough_centroids[borough_name] = {'lon': lon_center, 'lat': lat_center}

        elif geometry_type == 'MultiPolygon':
            # For multi-polygons, find the largest polygon
            areas = []
            centroids = []
            for polygon in coords_data:
                coords = np.array(polygon[0])
                area = 0
                for i in range(len(coords) - 1):
                    area += 0.5 * abs(coords[i, 0] * coords[i+1, 1] - coords[i+1, 0] * coords[i, 1])
                areas.append(area)
                centroids.append((coords[:, 0].mean(), coords[:, 1].mean()))

            if areas:  # pick the largest polygon
                largest_idx = np.argmax(areas)
                borough_centroids[borough_name] = {
                    'lon': centroids[largest_idx][0],
                    'lat': centroids[largest_idx][1]
                }

        logger.info(f"Generated centroid for borough: {borough_name}")

    except Exception as e:
        logger.error(f"Error processing borough geometry: {e}")


# ---------------------------------------------------------------------------------
# Dashboard Layout
# ---------------------------------------------------------------------------------
def layout():
    """
    Main layout for the dashboard page with improved components and responsive design.
    """
    # Mobile detection components: hidden Store and Interval for polling window width
    mobile_detection = html.Div([
        dcc.Store(id="is_mobile", storage_type="memory"),
        dcc.Interval(id="mobile_interval", interval=1000, n_intervals=0)
    ])

    # Load data for dropdowns using optimized queries
    unique_outcomes = load_unique_values('outcome_type')
    unique_crimes = load_unique_values('crime_type')
    
    # Get date range with census_year filter
    date_range_query = """
        SELECT MIN(month) as min_date, MAX(month) as max_date 
        FROM crime_records_enriched 
        WHERE census_year = 2015
    """
    date_range = run_custom_query(date_range_query)
    min_date = date_range['min_date'].iloc[0] if not date_range.empty else None
    max_date = date_range['max_date'].iloc[0] if not date_range.empty else None
    
    # Create dropdown options
    outcome_options = [{'label': str(i), 'value': str(i)} for i in unique_outcomes]
    crime_type_options = [{'label': str(i), 'value': str(i)} for i in unique_crimes]

    # Filters
    outcome_dropdown = html.Div(className="filter-label-input", children=[
        html.Label("Select Outcome Type:"),
        dcc.Dropdown(
            id="outcome-type-dropdown",
            options=outcome_options,
            value=[o['value'] for o in outcome_options],
            multi=True,
            className="filter-input filter-item"
        ),
        html.Div([
            dbc.Button("Show All", id="show-all-outcomes", color="secondary", size="sm", style={"margin-right": "5px"}),
            dbc.Button("Remove All", id="remove-all-outcomes", color="secondary", size="sm")
        ], style={"textAlign": "center", "marginTop": "5px"})
    ])

    crime_dropdown = html.Div(className="filter-label-input", children=[
        html.Label("Select Crime Type(s):"),
        dcc.Dropdown(
            id="crime-type-dropdown",
            options=crime_type_options,
            value=[o['value'] for o in crime_type_options],
            multi=True,
            className="filter-input filter-item"
        ),
        html.Div([
            dbc.Button("Show All", id="show-all-crimes", color="secondary", size="sm", style={"margin-right": "5px"}),
            dbc.Button("Remove All", id="remove-all-crimes", color="secondary", size="sm")
        ], style={"textAlign": "center", "marginTop": "5px"})
    ])

    date_picker = html.Div(className="filter-label-input", children=[
        html.Label("Select Date Range:"),
        dcc.DatePickerRange(
            id="date-picker-range",
            min_date_allowed=min_date,  # Use the min_date from the query above
            max_date_allowed=max_date,  # Use the max_date from the query above
            start_date=min_date,  # Use min_date as starting date 
            end_date=max_date,  # Use max_date as ending date
            display_format="MMMM Y",
            className="filter-input date-picker-range filter-item",
            style={"width": "100%"}
        )
    ])

    label_toggle = html.Div(className="filter-label-input", children=[
        html.Label("Borough Labels:"),
        dbc.Switch(
            id="show-borough-labels",
            label="Show Labels",
            value=True,
            className="toggle-switch"
        )
    ])

    filters_container = dbc.Collapse(
        html.Div(
            [
                dbc.Row([dbc.Col(outcome_dropdown), dbc.Col(crime_dropdown), dbc.Col(date_picker)]),
                dbc.Row([dbc.Col(label_toggle, width=3)], className="mt-2")
            ],
            className="filters-container"
        ),
        id="dashboard-filters-collapse",
        is_open=False
    )

    header_section = html.Div(
        [
            html.H1("UK Crime Data Dashboard", style={'textAlign': 'center', 'marginBottom': '10px'}),
            html.P(
                "Explore interactive visualizations of street-level crime data across the UK with real-time filtering and dynamic insights. Analyze crime trends by adjusting outcome types, crime categories, and date ranges to uncover patterns and key statistics. Gain a deeper understanding of crime distribution in different regions through intuitive visual dashboards."
                "Use the filters below to adjust outcome types, crime types, and date ranges.",
                style={'textAlign': 'center'}
            ),
            dbc.Button("Toggle Filters", id="toggle-filters-btn", color="info", size="sm",
                       className="mb-2", style={"display": "block", "margin": "0 auto"})
        ],
        style={'padding': '20px', 'borderRadius': '10px', 'marginBottom': '20px'}
    )
    
    scroll_container = html.Div(
        children=[
            # Row 1: Borough Map & Relative Crime Distribution
            html.H3("Borough Analysis", className="section-title mt-4 mb-3", 
                    style={"borderBottom": "2px solid #1E90FF", "paddingBottom": "10px"}),
            html.P("Click on a borough to see how crime types differ from the London average. Blue bars indicate higher rates, red bars show lower rates.", 
                   className="text-muted mb-3"),
            dbc.Row([
                dbc.Col(
                    dcc.Loading(
                        dcc.Graph(id="borough-map", config={"displayModeBar": False, "scrollZoom": True},
                                  style={"height": "500px"}),
                        type="circle"
                    ),
                    xs=12, sm=12, md=12, lg=6,
                    className="dashboard-col"
                ),
                dbc.Col(
                    dcc.Loading(
                        html.Div([
                            html.Div(id="borough-title", className="borough-title"),
                            dcc.Graph(id="relative-crime-distribution", config={"displayModeBar": False, "scrollZoom": False, "staticPlot": True},
                                      style={"height": "460px"})
                        ]),
                        type="circle"
                    ),
                    xs=12, sm=12, md=12, lg=6,
                    className="dashboard-col"
                )
            ], className="my-3 mb-5 dashboard-row"),

            # NEW SECTION: Income Crime Correlation
            html.H3("Crime and Income Analysis", className="section-title mt-5 mb-3", 
                    style={"borderBottom": "2px solid #1E90FF", "paddingBottom": "10px"}),
            html.P("Explore the relationship between average income levels and crime rates across London boroughs.", 
                   className="text-muted mb-3"),
            dbc.Row([
                dbc.Col(
                    dcc.Loading(
                        dcc.Graph(id="income-crime-correlation", config={"displayModeBar": False, "scrollZoom": False, "staticPlot": True}),
                        type="circle"
                    ),
                    width=12
                )
            ], className="mb-5 dashboard-row"),

            # NEW SECTION: Demographic Analysis
            html.H3("Demographic Analysis", className="section-title mt-5 mb-3", 
                    style={"borderBottom": "2px solid #1E90FF", "paddingBottom": "10px"}),
            html.P("Explore relationships between demographic factors and crime patterns.", 
                   className="text-muted mb-3"),
            dbc.Row([
                dbc.Col([
                    html.Label("Select Demographic Factor:"),
                    dcc.Dropdown(
                        id="demographic-dropdown",
                        options=[
                            {'label': 'Youth Male %', 'value': 'youth_male_percent'},
                            {'label': 'Youth Female %', 'value': 'youth_female_percent'},
                            {'label': 'Young Adult Male %', 'value': 'young_adult_male_percent'},
                            {'label': 'Young Adult Female %', 'value': 'young_adult_female_percent'},
                            {'label': 'Adult Male %', 'value': 'adult_male_percent'},
                            {'label': 'Adult Female %', 'value': 'adult_female_percent'},
                            {'label': 'Senior Male %', 'value': 'senior_male_percent'},
                            {'label': 'Senior Female %', 'value': 'senior_female_percent'}
                        ],
                        value='adult_male_percent',
                        clearable=False
                    ),
                ], width=4),
                dbc.Col([
                    html.Label("Reference Borough for Similarity:"),
                    dcc.Dropdown(
                        id="reference-lsoa-dropdown",
                        placeholder="Select an LSOA to find similar areas"
                    )
                ], width=8)
            ], className="mb-3"),
            dbc.Row([
                dbc.Col(
                    dcc.Loading(
                        dcc.Graph(id="demographic-correlation", config={"displayModeBar": False, "scrollZoom": False, "staticPlot": True}),
                        type="circle"
                    ),
                    xs=12, sm=12, md=12, lg=6,
                    className="dashboard-col"
                ),
                dbc.Col(
                    dcc.Loading(
                        dcc.Graph(id="similarity-map", config={"displayModeBar": False, "scrollZoom": False, "staticPlot": True}),
                        type="circle"
                    ),
                    xs=12, sm=12, md=12, lg=6,
                    className="dashboard-col"
                )   
            ], className="mb-5 dashboard-row"),

            # Row 2: Heatmap with embedded controls
            html.H3("Geographic Crime Distribution", className="section-title mt-5 mb-3", 
                    style={"borderBottom": "2px solid #1E90FF", "paddingBottom": "10px"}),
            html.P("Visualize crime density across London. Darker areas indicate higher concentration of criminal activity.", 
                   className="text-muted mb-3"),
            dbc.Row([
                dbc.Col(
                    dbc.Switch(
                        id="heatmap-mode-switch",
                        label="Live Viewing (Animate Over Time)",
                        value=False,
                        className="mb-3"
                    ),
                    width={"size": 6, "offset": 3},
                    style={"textAlign": "center"}
                )
            ]),
            dbc.Row([
                dbc.Col(
                    dcc.Loading(
                        dcc.Graph(id="crime-heatmap", config={"displayModeBar": True, "scrollZoom": True, "staticPlot": False}),
                        type="circle"
                    ),
                    width=12
                )
            ], className="mb-5 dashboard-row"),

            # Row 3: Time Series & Outcome Bar
            html.H3("Temporal Patterns and Outcomes", className="section-title mt-5 mb-3", 
                    style={"borderBottom": "2px solid #1E90FF", "paddingBottom": "10px"}),
            html.P("Analyze how crime rates change over time and the distribution of case outcomes.", 
                   className="text-muted mb-3"),
            dbc.Row([
                dbc.Col(
                    dcc.Loading(
                        dcc.Graph(id="time-series-plot", config={"displayModeBar": False, "scrollZoom": False, "staticPlot": True}),
                        type="circle"
                    ),
                    xs=12, sm=12, md=6, lg=6,
                    className="dashboard-col"
                ),
                dbc.Col(
                    dcc.Loading(
                        dcc.Graph(id="outcome-bar-chart", config={"displayModeBar": False, "scrollZoom": False, "staticPlot": True}),
                        type="circle"
                    ),
                    xs=12, sm=12, md=6, lg=6,
                    className="dashboard-col"
                )
            ], className="mb-5 dashboard-row"),

            # Row 4: Crime-Type Bar & Yearly Comparison
            html.H3("Crime Types and Yearly Trends", className="section-title mt-5 mb-3", 
                    style={"borderBottom": "2px solid #1E90FF", "paddingBottom": "10px"}),
            html.P("Explore the distribution of crime types and how they've changed over the years.", 
                   className="text-muted mb-3"),
            dbc.Row([
                dbc.Col(
                    dcc.Loading(
                        dcc.Graph(id="crime-type-bar-chart", config={"displayModeBar": False, "scrollZoom": False, "staticPlot": True}),
                        type="circle"
                    ),
                    xs=12, sm=12, md=6, lg=6,
                    className="dashboard-col"
                ),
                dbc.Col(
                    dcc.Loading(
                        dcc.Graph(id="yearly-comparison-chart", config={"displayModeBar": False, "scrollZoom": False, "staticPlot": True}),
                        type="circle"
                    ),
                    xs=12, sm=12, md=6, lg=6,
                    className="dashboard-col"
                )
            ], className="mb-5 dashboard-row"),

            # Summary Statistics
            html.H3("Key Findings", className="section-title mt-5 mb-3", 
                    style={"borderBottom": "2px solid #1E90FF", "paddingBottom": "10px"}),
            html.P("Summary of the current data selection and key statistics.", 
                   className="text-muted mb-3"),
            dbc.Row([
                dbc.Col(html.Div(id="summary-statistics", className="summary"), width=12)
            ], className="mb-4 dashboard-row"),
            
            # Reset Cache Button at bottom
            dbc.Row([
                dbc.Col(
                    dbc.Button(
                        "Reset Cache",
                        id="reset-cache-btn",
                        color="secondary",
                        size="sm",
                        className="mx-auto d-block mt-4 mb-4"
                    ),
                    width={"size": 2, "offset": 5}
                )
            ], className="mt-3 mb-5")
        ],
        className="dashboard-scroll-container"
    )

    return dbc.Container(
        fluid=True,
        children=[mobile_detection, header_section, filters_container, scroll_container]
    )




# ---------------------------------------------------------------------------------
# Figures & Charts
# ---------------------------------------------------------------------------------

def generate_borough_map(filtered_data, is_light_mode, show_labels=True, is_mobile=False):
    """
    Generate a choropleth map with distinct shaded segments and labels for each borough.
    Uses database-side aggregation for improved performance.
    """
    # Determine which column to use for borough grouping
    if 'lad_name' in filtered_data.columns:
        logger.info("Using 'lad_name' as borough field")
        borough_field = 'lad_name'
    elif 'borough' in filtered_data.columns:
        logger.info("Using 'borough' as borough field")
        borough_field = 'borough'
    else:
        if 'lsoa_name' in filtered_data.columns:
            borough_field = 'lsoa_name'
            logger.info("Using 'lsoa_name' as borough field")
        else:
            borough_field = 'lsoa_code'
            logger.info("Using 'lsoa_code' as borough field")
    
    # Create filters from the filtered data
    filters = {}
    if not filtered_data.empty:
        if 'outcome_type' in filtered_data.columns:
            filters['outcome_type'] = filtered_data['outcome_type'].unique().tolist()
        if 'crime_type' in filtered_data.columns:
            filters['crime_type'] = filtered_data['crime_type'].unique().tolist()
        
        # Get date range if available
        if 'month' in filtered_data.columns:
            start_date = filtered_data['month'].min()
            end_date = filtered_data['month'].max()
            filters['start_date'] = start_date
            filters['end_date'] = end_date
    
    # Get aggregated borough data directly from database
    logger.info(f"Getting aggregated borough data with filters: {filters}")
    
    # Define metric columns to aggregate
    metric_columns = {'income': 'AVG'}
    
    # Use database-side aggregation
    borough_data = load_aggregated_data(
        group_by_columns=[borough_field],
        metric_columns=metric_columns, 
        filters=filters
    )
    
    # Rename columns for consistency
    if 'count' in borough_data.columns:
        borough_data = borough_data.rename(columns={'count': 'Count'})
        
    logger.info(f"Borough data from DB: {borough_data.head().to_dict()}")
    
    if borough_data.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="No borough data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=16)
        )
        return fig, None

    # Build the choropleth
    fig = go.Figure()
    try:
        # Set showscale based on mobile flag
        choropleth_trace = go.Choroplethmapbox(
            geojson=borough_geojson,
            locations=borough_data[borough_field],
            z=borough_data['Count'],
            colorscale=[
                [0, 'rgb(221,242,253)'],
                [0.2, 'rgb(167,199,231)'],
                [0.4, 'rgb(105,158,207)'],
                [0.6, 'rgb(58,115,180)'],
                [0.8, 'rgb(8,81,156)'],
                [1, 'rgb(8,48,107)']
            ],
            marker_opacity=0.7,
            marker_line_width=1.5,
            marker_line_color='white',
            featureidkey="properties.name",
            hovertemplate="<b>%{location}</b><br>Crime Count: %{z}<extra></extra>",
            customdata=borough_data[borough_field],
            name='',
            showscale=(not is_mobile),  # Hide the colorbar on mobile
            colorbar_title=None if is_mobile else "Crime Count"
        )
        fig.add_trace(choropleth_trace)

        # Optional: show borough labels (smaller or hidden on mobile)
        if show_labels and borough_centroids:
            label_boroughs = []
            label_lons = []
            label_lats = []
            for b_name, centroid in borough_centroids.items():
                label_boroughs.append(b_name)
                label_lons.append(centroid['lon'])
                label_lats.append(centroid['lat'])

            if label_boroughs:
                fig.add_trace(go.Scattermapbox(
                    lon=label_lons,
                    lat=label_lats,
                    mode='text',
                    text=label_boroughs,
                    textfont=dict(
                        size=10 if not is_mobile else 8,  # Smaller text on mobile
                        color='black',
                        family="Arial, sans-serif",
                    ),
                    hoverinfo='none',
                    showlegend=False
                ))
        
        # Different map settings for mobile vs desktop
        zoom_level = 9.5 if not is_mobile else 8.5  # Zoomed out slightly on mobile
        fig.update_layout(
            mapbox=dict(
                style="open-street-map",
                zoom=zoom_level,
                center={"lat": 51.5074, "lon": -0.1278}
            ),
            margin={"r": 0, "t": 40, "l": 0, "b": 0},
            title=dict(
                text="London Borough Crime Distribution" if not is_mobile else "London Boroughs",
                font=dict(size=16 if not is_mobile else 14)
            ),
            # Mobile-specific layout settings
            clickmode='event+select' if is_mobile else 'event',
            dragmode=False if is_mobile else 'pan',
            # Ensure the map is interactive
            uirevision=True,
            # Make sure clicks are captured
            hovermode='closest'
        )
        
        # Mobile-specific adjustments
        if is_mobile:
            fig.update_layout(
                height=350,
                # Additional mobile-specific settings
                modebar=dict(
                    remove=['pan', 'zoom', 'select', 'lasso2d', 'zoomIn2d', 'zoomOut2d', 'autoScale2d', 'resetScale2d']
                )
            )
    except Exception as e:
        logger.error(f"Error generating borough map: {e}")
        fig = go.Figure()
        fig.add_annotation(
            text=f"Error generating borough map: {str(e)}",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=16)
        )

    fig = update_fig_layout(fig, is_light_mode)

    # Prepare crime data by borough & crime_type for relative comparison
    borough_crime_stats = {}
    try:
        # Use aggregated data for crime type stats by borough
        crime_type_agg = load_aggregated_data(
            group_by_columns=[borough_field, 'crime_type'],
            filters=filters
        )
        if 'count' in crime_type_agg.columns and 'Count' not in crime_type_agg.columns:
            crime_type_agg = crime_type_agg.rename(columns={'count': 'Count'})
        
        # Get total crimes by borough
        borough_totals = crime_type_agg.groupby(borough_field)['Count'].sum().reset_index()
        borough_totals.columns = [borough_field, 'total_crimes']
        
        # Get total crimes by type
        type_totals = crime_type_agg.groupby('crime_type')['Count'].sum().reset_index()
        type_totals.columns = ['crime_type', 'total_type_crimes']
        
        # Calculate total crimes
        total_crimes = crime_type_agg['Count'].sum()

        for b_name in crime_type_agg[borough_field].unique():
            borough_total = borough_totals.loc[
                borough_totals[borough_field] == b_name, 'total_crimes'
            ].values[0]
            sub_df = crime_type_agg[crime_type_agg[borough_field] == b_name].copy()

            if not sub_df.empty:
                results = []
                for _, row in sub_df.iterrows():
                    crime_type = row['crime_type']
                    count_val = row['Count']
                    total_for_type = type_totals.loc[
                        type_totals['crime_type'] == crime_type, 'total_type_crimes'
                    ].values[0]
                    actual_proportion = count_val / borough_total
                    expected_proportion = total_for_type / total_crimes if total_crimes else 0

                    relative_frequency = (
                        actual_proportion / expected_proportion
                        if expected_proportion != 0
                        else np.nan
                    )

                    results.append({
                        'crime_type': crime_type,
                        'count': count_val,
                        'proportion': actual_proportion,
                        'expected_proportion': expected_proportion,
                        'relative_frequency': relative_frequency
                    })
                borough_crime_stats[b_name] = sorted(results, key=lambda x: x['relative_frequency'], reverse=True)
    except Exception as e:
        logger.error(f"Error calculating borough crime stats: {e}")

    return fig, borough_crime_stats








def generate_borough_similarity_map(borough_data, reference_borough, selected_demographic, is_light_mode, is_mobile=False):
    """
    Generate a map showing boroughs with similar demographic profiles to the selected reference borough.
    """
    if borough_data.empty or not reference_borough:
        fig = go.Figure()
        fig.add_annotation(
            text="Select a reference borough to find similar areas",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False
        )
        return fig
    
    try:
        # Create a copy for analysis
        df = borough_data.copy()
        
        # Check if reference borough exists
        if reference_borough not in df['lad_name'].values:
            fig = go.Figure()
            fig.add_annotation(
                text=f"Reference borough '{reference_borough}' not found in data",
                xref="paper", yref="paper",
                x=0.5, y=0.5,
                showarrow=False
            )
            return fig
        
        # Get reference borough data
        ref_data = df[df['lad_name'] == reference_borough].iloc[0]
        
        # Calculate demographic similarity based on selected demographic
        df['diff'] = abs(df[selected_demographic] - ref_data[selected_demographic])
        max_diff = df['diff'].max()
        df['similarity'] = 100 * (1 - df['diff'] / max_diff)
        
        # Create choropleth map
        title = f'Boroughs with Similar {selected_demographic.replace("_percent", "").replace("_", " ").title()} % to {reference_borough}'
        
        # Create shorter title for mobile
        if is_mobile:
            title = f'Similar {selected_demographic.replace("_percent", "").replace("_", " ").title()} to {reference_borough}'
        
        fig = px.choropleth_mapbox(
            df,
            geojson=borough_geojson,
            locations='lad_name',
            color='similarity',
            featureidkey="properties.name",
            center={"lat": 51.5074, "lon": -0.1278},
            zoom=9 if not is_mobile else 8.5,  # Zoomed out slightly on mobile
            mapbox_style="open-street-map",
            opacity=0.7,
            labels={'similarity': 'Similarity %'},
            color_continuous_scale="Viridis",
            range_color=[0, 100],
            title=title
        )
        
        fig = update_fig_layout(fig, is_light_mode)
        
        # Mobile-specific adjustments
        if is_mobile:
            fig.update_layout(
                height=350,  # Smaller height for mobile
                dragmode=False,  # Disable dragging/panning
                showlegend=False,  # Hide legend
                margin={"r": 10, "t": 40, "l": 10, "b": 10},  # Tighter margins
                title=dict(
                    font=dict(size=14)  # Smaller title font
                ),
                coloraxis_colorbar=dict(
                    len=0.7,  # Shorter colorbar
                    thickness=15,  # Thicker for touch targets
                    x=1.0,  # Position further right
                    y=0.5  # Center vertically
                )
            )
        
        return fig
        
    except Exception as e:
        logger.error(f"Error generating borough similarity map: {e}")
        fig = go.Figure()
        fig.add_annotation(
            text=f"Error: {str(e)}",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False
        )
        return fig

def generate_relative_crime_distribution(borough_crime_data, borough_name, is_light_mode, is_mobile=False):
    """
    Generate a bar chart that shows how crimes in a borough differ from the overall average.
    """
    logger.info(f"generate_relative_crime_distribution called with borough: {borough_name}")
    if borough_crime_data:
        logger.info(f"borough_crime_data contains {len(borough_crime_data)} boroughs")
    else:
        logger.info("borough_crime_data is empty or None.")

    # Guard: No selection or borough not in data
    if not borough_name or not borough_crime_data or borough_name not in borough_crime_data:
        logger.debug("No valid borough was selected (or data is missing). Returning default figure.")
        fig = go.Figure()
        fig.add_annotation(
            text="Click on a borough to see relative crime distribution",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=16 if not is_mobile else 14)
        )
        fig = update_fig_layout(fig, is_light_mode)
        
        if is_mobile:
            fig.update_layout(
                height=350,
                showlegend=False,
                dragmode=False
            )
            
        return fig

    crime_data = borough_crime_data[borough_name]
    sorted_data = sorted(crime_data, key=lambda x: x['relative_frequency'], reverse=True)

    # Determine how many items to show based on mobile vs desktop
    if is_mobile:
        # Show fewer items on mobile - top 3 and bottom 2
        top_n = 3
        bottom_n = 2
    else:
        # Desktop - show more items
        top_n = 5
        bottom_n = 5
        
    # Show top N and bottom N
    top_items = sorted_data[:top_n]
    bottom_items = sorted_data[-bottom_n:] if len(sorted_data) > bottom_n else []
    display_data = top_items + bottom_items

    crime_types = [item['crime_type'] for item in display_data]
    # Truncate long crime type names on mobile
    if is_mobile:
        crime_types = [ct[:20] + "..." if len(ct) > 20 else ct for ct in crime_types]
        
    rel_frequencies = [item['relative_frequency'] for item in display_data]
    counts = [item['count'] for item in display_data]
    proportions = [f"{item['proportion']*100:.1f}%" for item in display_data]
    expected = [f"{item['expected_proportion']*100:.1f}%" for item in display_data]

    hover_texts = [
        f"Crime Type: {ct}<br>Count: {count}<br>Borough %: {prop}<br>Average %: {exp}<br>RF: {rf:.2f}x"
        for ct, count, prop, exp, rf in zip(crime_types, counts, proportions, expected, rel_frequencies)
    ]

    colors = ['rgba(65, 105, 225, 0.7)' if rf >= 1.0 else 'rgba(220, 20, 60, 0.7)' for rf in rel_frequencies]

    fig = go.Figure()
    # Reference line at 1.0
    fig.add_shape(
        type="line",
        x0=0.5,
        y0=1.0,
        x1=len(crime_types)+0.5,
        y1=1.0,
        line=dict(color="gray", width=2, dash="dash")
    )
    fig.add_trace(go.Bar(
        y=crime_types,
        x=rel_frequencies,
        orientation='h',
        marker_color=colors,
        text=[f"{rf:.2f}x" for rf in rel_frequencies],
        textposition='outside',
        hovertext=hover_texts,
        hoverinfo='text'
    ))
    
    # Create title - shorter for mobile
    title = f"Crimes Relative to London Average in {borough_name}"
    if is_mobile:
        title = f"{borough_name} vs London Avg"
        
    fig.update_layout(
        title=title,
        xaxis_title="Relative Frequency (1.0 = Average)" if not is_mobile else "Rel. Frequency",
        yaxis_title="Crime Type",
        height=460 if not is_mobile else 350,
        xaxis=dict(
            zeroline=False,
            gridcolor='lightgray',
            tickformat='.1f',
            ticksuffix='x'
        ),
        yaxis=dict(autorange="reversed")
    )
    
    # Add annotation - simpler for mobile
    if not is_mobile:
        fig.add_annotation(
            x=0.5,
            y=1.05,
            xref="paper",
            yref="paper",
            text="Shows how crime types compare to London average (1.0 = average occurrence)",
            showarrow=False,
            font=dict(size=12),
            align="center"
        )

    fig = update_fig_layout(fig, is_light_mode)
    
    # Mobile-specific adjustments
    if is_mobile:
        fig.update_layout(
            showlegend=False,
            dragmode=False,
            margin={"r": 10, "t": 40, "l": 10, "b": 40},
            title=dict(
                font=dict(size=14)
            ),
            xaxis=dict(
                title=dict(font=dict(size=12)),
                tickfont=dict(size=10)
            ),
            yaxis=dict(
                title=dict(font=dict(size=12)),
                tickfont=dict(size=10)
            )
        )
    
    return fig

def generate_static_heatmap(filtered_data, is_light_mode, is_mobile=False):
    """Generate a static density heatmap of crimes with memory optimization."""
    if filtered_data.empty:
        return go.Figure()
    
    # Memory optimization: If dataset is large, sample it
    df = filtered_data.copy()
    
    # If more than MAX_POINTS, sample down
    # Use fewer points on mobile for better performance
    MAX_POINTS = 10000
    if is_mobile:
        MAX_POINTS = 5000  # Use fewer points on mobile for better performance
    
    if len(df) > MAX_POINTS:
        logger.info(f"Sampling heatmap data from {len(df)} to {MAX_POINTS} points")
        df = df.sample(n=MAX_POINTS, random_state=42)
    
    # Select only necessary columns for the heatmap
    if 'latitude' in df.columns and 'longitude' in df.columns:
        df = df[['latitude', 'longitude']]
        df["density_val"] = 1
    else:
        logger.error("Missing required columns for heatmap")
        return go.Figure()
    
    # Create the heatmap
    fig = px.density_mapbox(
        df,
        lat="latitude",
        lon="longitude",
        z="density_val",
        radius=25,
        center={"lat": df["latitude"].mean(), "lon": df["longitude"].mean()},
        zoom=8,
        mapbox_style="open-street-map",
        color_continuous_scale="YlOrRd"
    )
    
    fig.update_traces(opacity=0.5)
    fig = update_fig_layout(fig, is_light_mode)
    fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})
    
    # Mobile-specific adjustments - only hide labels, keep interactivity
    if is_mobile:
        # Hide color scale
        fig.update_layout(
            coloraxis_showscale=False,
        )
        
        # Remove any title or annotations
        if hasattr(fig, 'layout') and hasattr(fig.layout, 'annotations'):
            fig.layout.annotations = []
        
        if hasattr(fig, 'layout') and hasattr(fig.layout, 'title'):
            fig.layout.title = None
    
    return fig
def generate_animated_heatmap(filtered_data, is_light_mode, is_mobile=False):
    """Generate an animated density heatmap by month with memory optimization."""
    if filtered_data.empty:
        return go.Figure()
    
    # Memory optimization: If dataset is large, sample it
    df = filtered_data.copy()
    
    # Aim for MAX_POINTS per month - use fewer points on mobile
    MAX_POINTS_PER_MONTH = 2000
    if is_mobile:
        MAX_POINTS_PER_MONTH = 1000  # Fewer points on mobile for better performance
    
    # Convert to datetime if needed
    if not pd.api.types.is_datetime64_any_dtype(df["month"]):
        df["month"] = pd.to_datetime(df["month"])
    
    # Add month string column for animation
    df["month_str"] = df["month"].dt.strftime("%Y-%m")
    
    # Sample data if necessary, ensuring each month has representative data
    unique_months = df["month_str"].unique()
    if len(unique_months) > 0:
        points_per_month = min(MAX_POINTS_PER_MONTH, len(df) // len(unique_months))
        
        # If we need to sample
        if points_per_month < len(df) // len(unique_months):
            logger.info(f"Sampling animated heatmap from {len(df)} points to {points_per_month} points per month")
            sampled_dfs = []
            for month in unique_months:
                month_df = df[df["month_str"] == month]
                if len(month_df) > points_per_month:
                    month_df = month_df.sample(n=points_per_month, random_state=42)
                sampled_dfs.append(month_df)
            df = pd.concat(sampled_dfs)
    
    # Select only necessary columns
    df = df[['latitude', 'longitude', 'month_str']]
    df["density_val"] = 1
    
    # Create animated heatmap
    fig = px.density_mapbox(
        df,
        lat="latitude",
        lon="longitude",
        z="density_val",
        radius=25,
        center={"lat": df["latitude"].mean(), "lon": df["longitude"].mean()},
        zoom=8,
        mapbox_style="open-street-map",
        color_continuous_scale="YlOrRd",
        animation_frame="month_str"
    )
    
    fig.update_traces(opacity=0.5)
    
    # Adjust animation speed - slightly faster on mobile
    transition_duration = 500
    if is_mobile:
        transition_duration = 400  # Slightly faster transitions on mobile
    
    fig.update_layout(transition={"duration": transition_duration})
    fig = update_fig_layout(fig, is_light_mode)
    fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})
    
    # Mobile-specific adjustments - only hide labels, keep interactivity
    if is_mobile:
        # Hide color scale
        fig.update_layout(
            coloraxis_showscale=False,
        )
        
        # Simplify animation controls for mobile
        fig.update_layout(
            updatemenus=[{
                "buttons": [
                    {
                        "args": [None, {"frame": {"duration": transition_duration, "redraw": True}}],
                        "label": "▶",  # Simpler play button
                        "method": "animate"
                    }
                ],
                "showactive": False,
                "type": "buttons",
                "y": 0,
                "x": 0.1,
                "xanchor": "right",
                "yanchor": "top",
                "pad": {"t": 0, "r": 10},
                "font": {"size": 16}  # Larger button for mobile
            }]
        )
        
        # Remove any title or annotations
        if hasattr(fig, 'layout') and hasattr(fig.layout, 'annotations'):
            fig.layout.annotations = []
        
        if hasattr(fig, 'layout') and hasattr(fig.layout, 'title'):
            fig.layout.title = None
    
    return fig
# Add to dashboard.py

def generate_demographic_analyzer(filtered_data, selected_demographic, is_light_mode, is_mobile=False):
    """
    Generate a visualization showing correlation between selected demographic groups and crime types.
    
    Parameters:
    -----------
    filtered_data : pandas.DataFrame
        Filtered crime data
    selected_demographic : str
        Selected demographic column (e.g., 'youth_male_percent')
    is_light_mode : bool
        Whether the dashboard is in light mode
    is_mobile : bool
        Whether the client is on a mobile device
    """
    if filtered_data.empty or not selected_demographic:
        return go.Figure()
    
    # Get aggregated data for demographic correlations
    demographic_cols = {
        selected_demographic: 'AVG'
    }
    
    filters = {'census_year': 2015}
    demo_crime_data = load_aggregated_data(
        group_by_columns=['crime_type', 'lsoa_code'],
        metric_columns=demographic_cols,
        filters=filters
    )
    
    # Calculate correlation for each crime type with the selected demographic
    crime_correlations = []
    
    for crime in demo_crime_data['crime_type'].unique():
        crime_df = demo_crime_data[demo_crime_data['crime_type'] == crime]
        
        # Only include if we have enough data points
        if len(crime_df) > 5:
            correlation = crime_df[[selected_demographic, 'Count']].corr().iloc[0, 1]
            crime_correlations.append({
                'crime_type': crime,
                'correlation': correlation,
                'avg_demographic': crime_df[selected_demographic].mean(),
                'total_count': crime_df['Count'].sum()
            })
    
    if not crime_correlations:
        return go.Figure()
    
    # Create DataFrame for visualization
    corr_df = pd.DataFrame(crime_correlations)
    corr_df = corr_df.sort_values('correlation')
    
    # On mobile, limit to top and bottom correlations if there are many
    if is_mobile and len(corr_df) > 10:
        # Get the 5 highest and 5 lowest correlations
        high_corr = corr_df.nlargest(5, 'correlation')
        low_corr = corr_df.nsmallest(5, 'correlation')
        corr_df = pd.concat([low_corr, high_corr]).sort_values('correlation')
    
    # Create title - shorten for mobile
    title = f'Correlation of {selected_demographic} with Different Crime Types'
    if is_mobile:
        title = f'Correlation: {selected_demographic.replace("_percent", "").replace("_", " ")}'
    
    # Create bar chart of correlations
    fig = px.bar(
        corr_df,
        y='crime_type',
        x='correlation',
        color='correlation',
        color_continuous_scale='RdBu',
        title=title,
        labels={
            'crime_type': 'Crime Type',
            'correlation': 'Correlation Coefficient',
            'avg_demographic': f'Average {selected_demographic}',
            'total_count': 'Total Crimes'
        },
        hover_data=['avg_demographic', 'total_count'],
        orientation='h'
    )
    
    # Add reference line at zero
    fig.add_shape(
        type="line",
        x0=0, y0=-0.5,
        x1=0, y1=len(corr_df)-0.5,
        line=dict(color="black", width=1, dash="dash")
    )
    
    # Add annotations for interpretation (only on desktop)
    if not is_mobile:
        fig.add_annotation(
            x=0.5, y=1.05,
            xref="paper", yref="paper",
            text="Positive values indicate higher crime rates in areas with higher demographic percentages",
            showarrow=False,
            font=dict(size=10),
            align="center"
        )
    
    fig = update_fig_layout(fig, is_light_mode)
    
    # Mobile-specific adjustments
    if is_mobile:
        fig.update_layout(
            height=350,  # Reduced height
            showlegend=False,  # Hide legend
            dragmode=False,  # Disable interactivity
            coloraxis_showscale=False,  # Hide color scale
            margin={"r": 10, "t": 40, "l": 10, "b": 40},  # Tighter margins
            title=dict(
                font=dict(size=14)  # Smaller title
            ),
            xaxis=dict(
                title=dict(
                    text="Correlation",  # Shorter axis title
                    font=dict(size=12)
                ),
                tickfont=dict(size=10)  # Smaller tick labels
            ),
            yaxis=dict(
                title=dict(
                    font=dict(size=12)
                ),
                tickfont=dict(size=10)  # Smaller tick labels
            )
        )
        
        # Truncate long crime type names on mobile
        for i, d in enumerate(fig.data):
            if hasattr(d, 'y') and isinstance(d.y, list):
                d.y = [y[:15] + '...' if isinstance(y, str) and len(y) > 15 else y for y in d.y]
    
    return fig

def generate_similarity_map(filtered_data, reference_lsoa, is_light_mode, is_mobile=False):
    """
    Generate a map showing areas with similar demographic profiles to the selected reference LSOA.
    
    Parameters:
    -----------
    filtered_data : pandas.DataFrame
        Filtered crime data
    reference_lsoa : str
        The LSOA code to use as reference
    is_light_mode : bool
        Whether the dashboard is in light mode
    is_mobile : bool
        Whether the client is on a mobile device
    """
    if filtered_data.empty or not reference_lsoa:
        return go.Figure()
    
    # Get demographic data for all LSOAs
    demographic_cols = [
        'youth_male_percent', 'youth_female_percent',
        'young_adult_male_percent', 'young_adult_female_percent',
        'adult_male_percent', 'adult_female_percent',
        'senior_male_percent', 'senior_female_percent'
    ]
    
    try:
        # Get unique demographic values by LSOA
        lsoa_demographics = filtered_data.groupby('lsoa_code')[demographic_cols].mean().reset_index()
        
        # Get reference LSOA demographics
        if reference_lsoa in lsoa_demographics['lsoa_code'].values:
            ref_demo = lsoa_demographics[lsoa_demographics['lsoa_code'] == reference_lsoa].iloc[0]
        else:
            fig = go.Figure()
            fig.add_annotation(
                text=f"Reference LSOA {reference_lsoa} not found in current data",
                xref="paper", yref="paper",
                x=0.5, y=0.5,
                showarrow=False
            )
            return fig
        
        # Calculate similarity (Euclidean distance) for each LSOA
        for col in demographic_cols:
            lsoa_demographics[f'{col}_diff'] = (lsoa_demographics[col] - ref_demo[col])**2
        
        # Calculate overall similarity score (lower is more similar)
        lsoa_demographics['similarity_score'] = np.sqrt(
            lsoa_demographics[[f'{col}_diff' for col in demographic_cols]].sum(axis=1)
        )
        
        # Normalize to 0-100 scale (100 is most similar)
        max_score = lsoa_demographics['similarity_score'].max()
        lsoa_demographics['similarity_index'] = 100 * (1 - lsoa_demographics['similarity_score'] / max_score)
        
        # Create title - shortened for mobile
        title = f'Areas with Similar Demographic Profile to {reference_lsoa}'
        if is_mobile:
            title = f'Similar to {reference_lsoa}'
        
        # Create choropleth map
        fig = px.choropleth_mapbox(
            lsoa_demographics,
            geojson=lsoa_geojson,
            locations='lsoa_code',
            color='similarity_index',
            featureidkey="properties.LSOA21CD",
            mapbox_style="open-street-map",
            zoom=9 if not is_mobile else 8.5,  # Slightly more zoomed out on mobile
            center={"lat": 51.5074, "lon": -0.1278},
            opacity=0.7,
            color_continuous_scale="Viridis",
            range_color=[0, 100],
            labels={'similarity_index': 'Similarity (%)'},
            title=title
        )
        
        fig = update_fig_layout(fig, is_light_mode)
        
        # Mobile-specific adjustments
        if is_mobile:
            fig.update_layout(
                height=350,  # Reduced height
                coloraxis_showscale=False,  # Hide color scale
                margin={"r": 10, "t": 40, "l": 10, "b": 10},  # Tighter margins
                title=dict(
                    font=dict(size=14)  # Smaller title font
                )
            )
            
            # Focus on the most similar areas (highlight top matches)
            # This helps make the map more readable on mobile
            top_matches = lsoa_demographics.nlargest(10, 'similarity_index')['lsoa_code'].tolist()
            
            # Add markers for top matches
            if top_matches:
                # Get coordinates for top matches (assuming they're in the geojson)
                marker_lats = []
                marker_lons = []
                
                for feature in lsoa_geojson['features']:
                    lsoa_code = feature['properties'].get('LSOA21CD')
                    if lsoa_code in top_matches:
                        # Try to get centroid coordinates
                        try:
                            coords = feature['geometry']['coordinates']
                            if feature['geometry']['type'] == 'Polygon':
                                # Calculate rough centroid for polygon
                                points = coords[0]  # Outer ring
                                lat_sum = sum(point[1] for point in points)
                                lon_sum = sum(point[0] for point in points)
                                marker_lats.append(lat_sum / len(points))
                                marker_lons.append(lon_sum / len(points))
                        except (KeyError, IndexError, TypeError):
                            continue
                
                # Add markers for top matches if we found coordinates
                if marker_lats and marker_lons:
                    fig.add_trace(go.Scattermapbox(
                        lat=marker_lats,
                        lon=marker_lons,
                        mode='markers',
                        marker=dict(
                            size=8,
                            color='yellow',
                            opacity=0.8
                        ),
                        hoverinfo='skip'
                    ))
        
        return fig
        
    except Exception as e:
        logger.error(f"Error generating similarity map: {e}")
        fig = go.Figure()
        fig.add_annotation(
            text=f"Error generating similarity map: {str(e)}",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False
        )
        return fig


def generate_income_crime_correlation(filtered_data, is_light_mode, is_mobile):
    """Generate a scatter plot showing correlation between income and crime rates by borough."""
    if filtered_data.empty:
        return go.Figure()
    
    # Standardize count column name.
    if 'count' in filtered_data.columns:
        filtered_data = filtered_data.rename(columns={'count': 'crime_count'})
    elif 'Count' in filtered_data.columns:
        filtered_data = filtered_data.rename(columns={'Count': 'crime_count'})
    
    borough_data = load_aggregated_data(
        group_by_columns=['lad_name'],
        metric_columns={'income': 'AVG'},
        filters={'census_year': 2015}
    )
    if borough_data.empty:
        return go.Figure()
    
    if 'count' in borough_data.columns:
        borough_data = borough_data.rename(columns={'count': 'crime_count'})
    elif 'Count' in borough_data.columns:
        borough_data = borough_data.rename(columns={'Count': 'crime_count'})
    
    fig = px.scatter(
        borough_data,
        x='income',
        y='crime_count',
        hover_name='lad_name',
        text='lad_name',
        title='Crime Count vs. Average Income by Borough',
        labels={
            'income': 'Average Income (£)',
            'crime_count': 'Number of Street Level Crimes',
            'lad_name': 'Borough'
        },
        size='crime_count',
        color='income',
        color_continuous_scale='RdBu_r'
    )
    
    if len(borough_data) > 2 and not is_mobile:
        try:
            from scipy import stats
            slope, intercept, r_value, p_value, std_err = stats.linregress(borough_data['income'], borough_data['crime_count'])
            x_range = [borough_data['income'].min(), borough_data['income'].max()]
            y_predicted = [slope * x + intercept for x in x_range]
            fig.add_trace(
                go.Scatter(
                    x=x_range,
                    y=y_predicted,
                    mode='lines',
                    name=f'Trend (r²={r_value**2:.2f})',
                    line=dict(color='rgba(0,0,0,0.7)', width=2, dash='dash')
                )
            )
        except Exception as e:
            logger.error(f"Error generating regression line: {e}")
    
    fig = update_fig_layout(fig, is_light_mode)
    
    if is_mobile:
        fig.update_layout(
            coloraxis_showscale=False,
            showlegend=False,
            height=350,
            margin={"r": 10, "t": 40, "l": 40, "b": 40},
            title=dict(
                font=dict(size=14)
            ),
            xaxis=dict(
                title=dict(
                    text="Average Income (£)",
                    font=dict(size=12)
                ),
                tickfont=dict(size=10)
            ),
            yaxis=dict(
                title=dict(
                    text="Number of Crimes",
                    font=dict(size=12)
                ),
                tickfont=dict(size=10)
            )
        )
    
    return fig






def generate_demographic_correlation(filtered_data, selected_demographic, is_light_mode):
    """
    Generate a visualization showing correlation between selected demographic groups and crime types.
    """
    if filtered_data.empty or not selected_demographic:
        fig = go.Figure()
        fig.add_annotation(
            text="Select a demographic factor and filter data to view correlations",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False
        )
        return fig
    
    # Get aggregated data for demographic correlations
    demographic_cols = {
        selected_demographic: 'AVG'
    }
    
    filters = {'census_year': 2015}
    demo_crime_data = load_aggregated_data(
        group_by_columns=['crime_type', 'lsoa_code'],
        metric_columns=demographic_cols,
        filters=filters
    )
    
    # Check what columns are actually available
    logger.info(f"Demo crime data columns: {demo_crime_data.columns.tolist()}")
    
    # Standardize count column name
    count_col = None
    if 'count' in demo_crime_data.columns:
        count_col = 'count'
    elif 'Count' in demo_crime_data.columns:
        count_col = 'Count'
    else:
        # If neither exists, create a default message
        fig = go.Figure()
        fig.add_annotation(
            text="Count data not available",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False
        )
        return fig
    
    # Calculate correlation for each crime type with the selected demographic
    crime_correlations = []
    
    for crime in demo_crime_data['crime_type'].unique():
        crime_df = demo_crime_data[demo_crime_data['crime_type'] == crime]
        
        # Only include if we have enough data points
        if len(crime_df) > 5:
            try:
                correlation = crime_df[[selected_demographic, count_col]].corr().iloc[0, 1]
                crime_correlations.append({
                    'crime_type': crime,
                    'correlation': correlation,
                    'avg_demographic': crime_df[selected_demographic].mean(),
                    'total_count': crime_df[count_col].sum()
                })
            except Exception as e:
                logger.error(f"Error calculating correlation for {crime}: {e}")
    
    if not crime_correlations:
        fig = go.Figure()
        fig.add_annotation(
            text="Not enough data to calculate correlations",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False
        )
        return fig
    
    # Create DataFrame for visualization
    corr_df = pd.DataFrame(crime_correlations)
    corr_df = corr_df.sort_values('correlation')
    
    # Create bar chart of correlations
    fig = px.bar(
        corr_df,
        y='crime_type',
        x='correlation',
        color='correlation',
        color_continuous_scale='RdBu',
        title=f'Correlation of {selected_demographic} with Different Crime Types',
        labels={
            'crime_type': 'Crime Type',
            'correlation': 'Correlation Coefficient',
            'avg_demographic': f'Average {selected_demographic}',
            'total_count': 'Total Crimes'
        },
        hover_data=['avg_demographic', 'total_count'],
        orientation='h'
    )
    
    # Add reference line at zero
    fig.add_shape(
        type="line",
        x0=0, y0=-0.5,
        x1=0, y1=len(corr_df)-0.5,
        line=dict(color="black", width=1, dash="dash")
    )
    
    # Add annotations for interpretation
    fig.add_annotation(
        x=0.5, y=1.05,
        xref="paper", yref="paper",
        text="Positive values indicate higher crime rates in areas with higher demographic percentages",
        showarrow=False,
        font=dict(size=10),
        align="center"
    )
    
    fig = update_fig_layout(fig, is_light_mode)
    return fig





def generate_similarity_map(filtered_data, reference_lsoa, is_light_mode):
    """
    Generate a map showing areas with similar demographic profiles to the selected reference LSOA.
    """
    if filtered_data.empty or not reference_lsoa:
        fig = go.Figure()
        fig.add_annotation(
            text="Select a reference LSOA to find similar areas",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False
        )
        return fig
    
    # Get demographic data for all LSOAs
    demographic_cols = [
        'youth_male_percent', 'youth_female_percent',
        'young_adult_male_percent', 'young_adult_female_percent',
        'adult_male_percent', 'adult_female_percent',
        'senior_male_percent', 'senior_female_percent'
    ]
    
    try:
        # Get unique demographic values by LSOA
        lsoa_demographics = filtered_data.groupby('lsoa_code')[demographic_cols].mean().reset_index()
        
        # Get reference LSOA demographics
        if reference_lsoa in lsoa_demographics['lsoa_code'].values:
            ref_demo = lsoa_demographics[lsoa_demographics['lsoa_code'] == reference_lsoa].iloc[0]
        else:
            fig = go.Figure()
            fig.add_annotation(
                text=f"Reference LSOA {reference_lsoa} not found in current data",
                xref="paper", yref="paper",
                x=0.5, y=0.5,
                showarrow=False
            )
            return fig
        
        # Calculate similarity (Euclidean distance) for each LSOA
        for col in demographic_cols:
            lsoa_demographics[f'{col}_diff'] = (lsoa_demographics[col] - ref_demo[col])**2
        
        # Calculate overall similarity score (lower is more similar)
        lsoa_demographics['similarity_score'] = np.sqrt(
            lsoa_demographics[[f'{col}_diff' for col in demographic_cols]].sum(axis=1)
        )
        
        # Normalize to 0-100 scale (100 is most similar)
        max_score = lsoa_demographics['similarity_score'].max()
        lsoa_demographics['similarity_index'] = 100 * (1 - lsoa_demographics['similarity_score'] / max_score)
        
        # Create choropleth map
        fig = px.choropleth_mapbox(
            lsoa_demographics,
            geojson=lsoa_geojson,
            locations='lsoa_code',
            color='similarity_index',
            featureidkey="properties.LSOA21CD",
            mapbox_style="open-street-map",
            zoom=9,
            center={"lat": 51.5074, "lon": -0.1278},
            opacity=0.7,
            color_continuous_scale="Viridis",
            range_color=[0, 100],
            labels={'similarity_index': 'Similarity (%)'},
            title=f'Areas with Similar Demographic Profile to {reference_lsoa}'
        )
        
        fig = update_fig_layout(fig, is_light_mode)
        return fig
        
    except Exception as e:
        logger.error(f"Error generating similarity map: {e}")
        fig = go.Figure()
        fig.add_annotation(
            text=f"Error generating similarity map: {str(e)}",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False
        )
        return fig


def generate_time_series(filtered_data, is_light_mode, is_mobile):
    """Generate a line chart of total crimes over time."""
    if filtered_data.empty:
        return go.Figure()
    
    grouped = filtered_data.groupby("month", observed=True).size().reset_index(name="Count")
    grouped.sort_values("month", inplace=True)
    
    fig = px.line(grouped, x="month", y="Count", title="Crime Over Time")
    fig = update_fig_layout(fig, is_light_mode)
    fig.update_layout(margin={"r": 0, "t": 40, "l": 0, "b": 0})
    
    if is_mobile:
        fig.update_layout(showlegend=False, dragmode=False)
    
    return fig

def generate_outcome_bar_chart(filtered_data, is_light_mode, is_mobile):
    """Generate a bar chart showing the counts of each outcome type."""
    if filtered_data.empty:
        return go.Figure()
    
    # Group by outcome type
    grouped = filtered_data.groupby("outcome_type", observed=True).size().reset_index(name="Count")
    
    # If on mobile, limit the number of outcomes shown
    if is_mobile and len(grouped) > 8:
        # Sort by count and keep top categories
        grouped = grouped.sort_values("Count", ascending=False)
        top_outcomes = grouped.head(7)
        other_sum = grouped.iloc[7:]["Count"].sum()
        
        # Add "Other" category for the rest
        other_row = pd.DataFrame({"outcome_type": ["Other"], "Count": [other_sum]})
        grouped = pd.concat([top_outcomes, other_row], ignore_index=True)
    
    # Create title - shorter for mobile
    title = "Outcome Types"
    if is_mobile:
        title = "Outcomes"
    
    fig = px.bar(
        grouped,
        x="outcome_type" if not is_mobile else "Count",
        y="Count" if not is_mobile else "outcome_type",
        title=title,
        labels={"outcome_type": "Outcome", "Count": "Number of Crimes"},
        orientation='v' if not is_mobile else 'h'  # Horizontal bars on mobile
    )
    
    fig = update_fig_layout(fig, is_light_mode)
    
    # Layout adjustments
    if is_mobile:
        # Mobile-specific adjustments
        fig.update_layout(
            height=350,
            showlegend=False,
            dragmode=False,
            margin={"r": 10, "t": 40, "l": 120, "b": 40},  # More left margin for category names
            title=dict(
                font=dict(size=14)
            ),
            yaxis=dict(  # Categories on y-axis for mobile (horizontal bars)
                title=None,  # Remove y-axis title
                autorange="reversed"  # Put highest values at top
            ),
            xaxis=dict(
                title=dict(
                    text="Number of Crimes",
                    font=dict(size=12)
                ),
                tickfont=dict(size=10)
            )
        )
        
        # Truncate long category names on mobile
        if hasattr(fig.data[0], 'y') and isinstance(fig.data[0].y, list):
            fig.data[0].y = [str(y)[:15] + '...' if isinstance(y, str) and len(y) > 15 else y for y in fig.data[0].y]
    else:
        # Desktop layout
        fig.update_layout(
            xaxis_tickangle=-45,
            height=500
        )
    
    return fig


def generate_crime_type_bar_chart(filtered_data, is_light_mode, is_mobile):
    """Generate a bar chart showing distribution of crime types."""
    if filtered_data.empty:
        return go.Figure()
    
    # Group by crime type
    grouped = filtered_data.groupby("crime_type", observed=True).size().reset_index(name="Count")
    
    # If on mobile, limit the number of crime types shown
    if is_mobile and len(grouped) > 8:
        # Sort by count and keep top categories
        grouped = grouped.sort_values("Count", ascending=False)
        top_crimes = grouped.head(7)
        other_sum = grouped.iloc[7:]["Count"].sum()
        
        # Add "Other" category for the rest
        other_row = pd.DataFrame({"crime_type": ["Other"], "Count": [other_sum]})
        grouped = pd.concat([top_crimes, other_row], ignore_index=True)
    
    # Sort by count for better visualization
    grouped = grouped.sort_values("Count", ascending=False)
    
    # Create title - shorter for mobile
    title = "Crime Type Distribution"
    if is_mobile:
        title = "Crime Types"
    
    fig = px.bar(
        grouped,
        x="crime_type" if not is_mobile else "Count",
        y="Count" if not is_mobile else "crime_type",
        title=title,
        labels={"crime_type": "Crime Type", "Count": "Number of Crimes"},
        orientation='v' if not is_mobile else 'h'  # Horizontal bars on mobile
    )
    
    fig = update_fig_layout(fig, is_light_mode)
    
    # Layout adjustments
    if is_mobile:
        # Mobile-specific adjustments
        fig.update_layout(
            height=350,
            showlegend=False,
            dragmode=False,
            margin={"r": 10, "t": 40, "l": 120, "b": 40},  # More left margin for category names
            title=dict(
                font=dict(size=14)
            ),
            yaxis=dict(  # Categories on y-axis for mobile (horizontal bars)
                title=None,  # Remove y-axis title
                autorange="reversed"  # Put highest values at top
            ),
            xaxis=dict(
                title=dict(
                    text="Number of Crimes",
                    font=dict(size=12)
                ),
                tickfont=dict(size=10)
            )
        )
        
        # Truncate long category names on mobile
        if hasattr(fig.data[0], 'y') and isinstance(fig.data[0].y, list):
            fig.data[0].y = [str(y)[:15] + '...' if isinstance(y, str) and len(y) > 15 else y for y in fig.data[0].y]
    else:
        # Desktop layout
        fig.update_layout(
            xaxis_tickangle=-45,
            height=500
        )
    
    return fig


def generate_yearly_comparison_chart(filtered_data, is_light_mode, is_mobile):
    """Generate a bar chart comparing crime types across different years."""
    if filtered_data.empty or "month" not in filtered_data.columns:
        return go.Figure()
    
    df = filtered_data.copy()
    df["year"] = df["month"].dt.year
    
    # For mobile, we need a simpler visualization
    if is_mobile:
        # Just show total counts by year
        yearly_totals = df.groupby("year").size().reset_index(name="Count")
        
        fig = px.bar(
            yearly_totals,
            x="year",
            y="Count",
            title="Crimes by Year",
            labels={"year": "Year", "Count": "Number of Crimes"}
        )
    else:
        # For desktop, show the full breakdown by crime type
        grouped = df.groupby(["year", "crime_type"], observed=True).size().reset_index(name="Count")
        
        if grouped.empty:
            return go.Figure()
        
        fig = px.bar(
            grouped,
            x="year",
            y="Count",
            color="crime_type",
            barmode="group",
            title="Yearly Comparison of Crime Types"
        )
    
    fig = update_fig_layout(fig, is_light_mode)
    
    # Mobile-specific adjustments
    if is_mobile:
        fig.update_layout(
            height=350,
            showlegend=False,
            dragmode=False,
            margin={"r": 10, "t": 40, "l": 40, "b": 40},
            title=dict(
                font=dict(size=14)
            ),
            xaxis=dict(
                title=dict(
                    text="Year",
                    font=dict(size=12)
                ),
                tickfont=dict(size=10)
            ),
            yaxis=dict(
                title=dict(
                    text="Number of Crimes",
                    font=dict(size=12)
                ),
                tickfont=dict(size=10)
            )
        )
        
        # Add value labels on bars for mobile
        for data in fig.data:
            fig.add_trace(go.Scatter(
                x=data.x,
                y=data.y,
                mode='text',
                text=[f"{y:,}" for y in data.y],
                textposition='top center',
                textfont=dict(size=10),
                showlegend=False
            ))
    
    return fig


# ---------------------------------------------------------------------------------
# Main Dashboard Callback
# ---------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------
# Main Dashboard Callback
# ---------------------------------------------------------------------------------

@dash.callback(
    [
        Output("borough-map", "figure"),
        Output("relative-crime-distribution", "figure"),
        Output("borough-title", "children"),
        Output("income-crime-correlation", "figure"),
        Output("crime-heatmap", "figure"),
        Output("time-series-plot", "figure"),
        Output("outcome-bar-chart", "figure"),
        Output("crime-type-bar-chart", "figure"),
        Output("yearly-comparison-chart", "figure"),
        Output("summary-statistics", "children")
    ],
    [
        Input("outcome-type-dropdown", "value"),
        Input("crime-type-dropdown", "value"),
        Input("date-picker-range", "start_date"),
        Input("date-picker-range", "end_date"),
        Input("heatmap-mode-switch", "value"),
        Input("borough-map", "clickData"),
        Input("show-borough-labels", "value"),
        Input("is_mobile", "data")   # NEW: Mobile flag input
    ],
    [
        State("borough-map", "relayoutData"),
        State("theme-container", "data-theme")
    ]
)
def update_dashboard(outcomes, crimes, start_date, end_date, heatmap_switch,
                     click_data, show_labels, is_mobile, relayout_data, data_theme):
    """
    Main callback for updating the dashboard components.
    'data-theme' determines light/dark mode.
    is_mobile indicates if the client is on a mobile device.
    """
    ctx = dash.callback_context
    if ctx.triggered:
        logger.info(f"Main callback triggered by: {ctx.triggered[0]['prop_id']}")
    else:
        logger.info("Main callback triggered without a specific input change.")

    is_light_mode = (data_theme == 'light')
    logger.info(f"is_light_mode={is_light_mode}, is_mobile={is_mobile}")

    filters = {
        'outcome_type': outcomes,
        'crime_type': crimes,
        'census_year': 2015
    }
    if start_date and end_date:
        filters['start_date'] = start_date
        filters['end_date'] = end_date

    crime_data = load_data()
    df = crime_data[crime_data["outcome_type"].isin(outcomes) & crime_data["crime_type"].isin(crimes)]
    if start_date and end_date:
        sdate = pd.to_datetime(start_date)
        edate = pd.to_datetime(end_date)
        df = df[(df["month"] >= sdate) & (df["month"] <= edate)]
    df = df.sort_values("month")
    logger.info(f"Dashboard update: {len(df)} records after filtering.")

    borough_map_fig, borough_crime_data = generate_borough_map(df, is_light_mode, show_labels, is_mobile)
    selected_borough = None
    borough_title = html.H4("Click on a borough to see relative crime distribution", className="text-center")

    if click_data and isinstance(click_data, dict) and "points" in click_data:
        try:
            points = click_data["points"][0]
            logger.info(f"Click event details: {points}")
            
            # Try different ways to get the borough name
            if "location" in points:
                selected_borough = points["location"]
            elif "customdata" in points and points["customdata"]:
                # Handle both single value and array customdata
                selected_borough = points["customdata"][0] if isinstance(points["customdata"], list) else points["customdata"]
            elif "text" in points:
                selected_borough = points["text"]
            elif "hovertext" in points:
                selected_borough = points["hovertext"]
                
            # Log the selected borough for debugging
            logger.info(f"Selected borough: {selected_borough}")
            
            if selected_borough and borough_crime_data and selected_borough in borough_crime_data:
                borough_title = html.H4(f"Crime Pattern Analysis: {selected_borough}", className="text-center")
                logger.info(f"Successfully updated title for borough: {selected_borough}")
            else:
                selected_borough = None
                logger.warning(f"Borough not found in crime data: {selected_borough}")
        except Exception as e:
            logger.error(f"Error processing clickData: {e}")
            selected_borough = None
            borough_title = html.H4("Error processing borough selection", className="text-center")

    # Generate all figures with mobile flag
    crime_distribution_fig = generate_relative_crime_distribution(borough_crime_data, selected_borough, is_light_mode, is_mobile)
    income_correlation_fig = generate_income_crime_correlation(df, is_light_mode, is_mobile)
    heatmap_fig = generate_animated_heatmap(df, is_light_mode, is_mobile) if heatmap_switch else generate_static_heatmap(df, is_light_mode, is_mobile)
    ts_fig = generate_time_series(df, is_light_mode, is_mobile)
    outcome_bar_fig = generate_outcome_bar_chart(df, is_light_mode, is_mobile)
    crime_type_bar_fig = generate_crime_type_bar_chart(df, is_light_mode, is_mobile)
    yearly_comp_fig = generate_yearly_comparison_chart(df, is_light_mode, is_mobile)

    total = len(df)
    if total > 0:
        common_crime = df["crime_type"].value_counts().idxmax()
        common_outcome = df["outcome_type"].value_counts().idxmax()
        date_min = df["month"].min().date()
        date_max = df["month"].max().date()
        avg_income = df["income"].mean() if "income" in df.columns else "N/A"
    else:
        common_crime = "N/A"
        common_outcome = "N/A"
        date_min = "N/A"
        date_max = "N/A"
        avg_income = "N/A"

    summary = html.Div([
        html.H2("Summary Statistics"),
        html.Ul([
            html.Li(f"Total number of crimes: {total}"),
            html.Li(f"Most common crime type: {common_crime}"),
            html.Li(f"Most common outcome type: {common_outcome}"),
            html.Li(f"Average income: £{avg_income:.2f}" if isinstance(avg_income, (int, float)) else f"Average income: {avg_income}"),
            html.Li(f"Data covers from {date_min} to {date_max}")
        ])
    ], className="summary")

    return (
        borough_map_fig,
        crime_distribution_fig,
        borough_title,
        income_correlation_fig,
        heatmap_fig,
        ts_fig,
        outcome_bar_fig,
        crime_type_bar_fig,
        yearly_comp_fig,
        summary
    )


def generate_borough_map(filtered_data, is_light_mode, show_labels=True, is_mobile=False):
    """
    Generate a choropleth map with distinct shaded segments and labels for each borough.
    Uses database-side aggregation for improved performance.
    """
    # Determine which column to use for borough grouping
    if 'lad_name' in filtered_data.columns:
        logger.info("Using 'lad_name' as borough field")
        borough_field = 'lad_name'
    elif 'borough' in filtered_data.columns:
        logger.info("Using 'borough' as borough field")
        borough_field = 'borough'
    else:
        if 'lsoa_name' in filtered_data.columns:
            borough_field = 'lsoa_name'
            logger.info("Using 'lsoa_name' as borough field")
        else:
            borough_field = 'lsoa_code'
            logger.info("Using 'lsoa_code' as borough field")
    
    # Create filters from the filtered data
    filters = {}
    if not filtered_data.empty:
        if 'outcome_type' in filtered_data.columns:
            filters['outcome_type'] = filtered_data['outcome_type'].unique().tolist()
        if 'crime_type' in filtered_data.columns:
            filters['crime_type'] = filtered_data['crime_type'].unique().tolist()
        
        # Get date range if available
        if 'month' in filtered_data.columns:
            start_date = filtered_data['month'].min()
            end_date = filtered_data['month'].max()
            filters['start_date'] = start_date
            filters['end_date'] = end_date
    
    # Get aggregated borough data directly from database
    logger.info(f"Getting aggregated borough data with filters: {filters}")
    
    # Define metric columns to aggregate
    metric_columns = {'income': 'AVG'}
    
    # Use database-side aggregation
    borough_data = load_aggregated_data(
        group_by_columns=[borough_field],
        metric_columns=metric_columns, 
        filters=filters
    )
    
    # Rename columns for consistency
    if 'count' in borough_data.columns:
        borough_data = borough_data.rename(columns={'count': 'Count'})
        
    logger.info(f"Borough data from DB: {borough_data.head().to_dict()}")
    
    if borough_data.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="No borough data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=16)
        )
        return fig, None

    # Build the choropleth
    fig = go.Figure()
    try:
        # Set showscale based on mobile flag
        choropleth_trace = go.Choroplethmapbox(
            geojson=borough_geojson,
            locations=borough_data[borough_field],
            z=borough_data['Count'],
            colorscale=[
                [0, 'rgb(221,242,253)'],
                [0.2, 'rgb(167,199,231)'],
                [0.4, 'rgb(105,158,207)'],
                [0.6, 'rgb(58,115,180)'],
                [0.8, 'rgb(8,81,156)'],
                [1, 'rgb(8,48,107)']
            ],
            marker_opacity=0.7,
            marker_line_width=1.5,
            marker_line_color='white',
            featureidkey="properties.name",
            hovertemplate="<b>%{location}</b><br>Crime Count: %{z}<extra></extra>",
            customdata=borough_data[borough_field],
            name='',
            showscale=(not is_mobile),  # Hide the colorbar on mobile
            colorbar_title=None if is_mobile else "Crime Count"
        )
        fig.add_trace(choropleth_trace)

        # Optional: show borough labels (smaller or hidden on mobile)
        if show_labels and borough_centroids:
            label_boroughs = []
            label_lons = []
            label_lats = []
            for b_name, centroid in borough_centroids.items():
                label_boroughs.append(b_name)
                label_lons.append(centroid['lon'])
                label_lats.append(centroid['lat'])

            if label_boroughs:
                fig.add_trace(go.Scattermapbox(
                    lon=label_lons,
                    lat=label_lats,
                    mode='text',
                    text=label_boroughs,
                    textfont=dict(
                        size=10 if not is_mobile else 8,  # Smaller text on mobile
                        color='black',
                        family="Arial, sans-serif",
                    ),
                    hoverinfo='none',
                    showlegend=False
                ))
        
        # Different map settings for mobile vs desktop
        zoom_level = 9.5 if not is_mobile else 8.5  # Zoomed out slightly on mobile
        fig.update_layout(
            mapbox=dict(
                style="open-street-map",
                zoom=zoom_level,
                center={"lat": 51.5074, "lon": -0.1278}
            ),
            margin={"r": 0, "t": 40, "l": 0, "b": 0},
            title=dict(
                text="London Borough Crime Distribution" if not is_mobile else "London Boroughs",
                font=dict(size=16 if not is_mobile else 14)
            ),
            # Mobile-specific layout settings
            clickmode='event+select' if is_mobile else 'event',
            dragmode=False if is_mobile else 'pan',
            # Ensure the map is interactive
            uirevision=True,
            # Make sure clicks are captured
            hovermode='closest'
        )
        
        # Mobile-specific adjustments
        if is_mobile:
            fig.update_layout(
                height=350,
                # Additional mobile-specific settings
                modebar=dict(
                    remove=['pan', 'zoom', 'select', 'lasso2d', 'zoomIn2d', 'zoomOut2d', 'autoScale2d', 'resetScale2d']
                )
            )
    except Exception as e:
        logger.error(f"Error generating borough map: {e}")
        fig = go.Figure()
        fig.add_annotation(
            text=f"Error generating borough map: {str(e)}",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=16)
        )

    fig = update_fig_layout(fig, is_light_mode)

    # Prepare crime data by borough & crime_type for relative comparison
    borough_crime_stats = {}
    try:
        # Use aggregated data for crime type stats by borough
        crime_type_agg = load_aggregated_data(
            group_by_columns=[borough_field, 'crime_type'],
            filters=filters
        )
        if 'count' in crime_type_agg.columns and 'Count' not in crime_type_agg.columns:
            crime_type_agg = crime_type_agg.rename(columns={'count': 'Count'})
        
        # Get total crimes by borough
        borough_totals = crime_type_agg.groupby(borough_field)['Count'].sum().reset_index()
        borough_totals.columns = [borough_field, 'total_crimes']
        
        # Get total crimes by type
        type_totals = crime_type_agg.groupby('crime_type')['Count'].sum().reset_index()
        type_totals.columns = ['crime_type', 'total_type_crimes']
        
        # Calculate total crimes
        total_crimes = crime_type_agg['Count'].sum()

        for b_name in crime_type_agg[borough_field].unique():
            borough_total = borough_totals.loc[
                borough_totals[borough_field] == b_name, 'total_crimes'
            ].values[0]
            sub_df = crime_type_agg[crime_type_agg[borough_field] == b_name].copy()

            if not sub_df.empty:
                results = []
                for _, row in sub_df.iterrows():
                    crime_type = row['crime_type']
                    count_val = row['Count']
                    total_for_type = type_totals.loc[
                        type_totals['crime_type'] == crime_type, 'total_type_crimes'
                    ].values[0]
                    actual_proportion = count_val / borough_total
                    expected_proportion = total_for_type / total_crimes if total_crimes else 0

                    relative_frequency = (
                        actual_proportion / expected_proportion
                        if expected_proportion != 0
                        else np.nan
                    )

                    results.append({
                        'crime_type': crime_type,
                        'count': count_val,
                        'proportion': actual_proportion,
                        'expected_proportion': expected_proportion,
                        'relative_frequency': relative_frequency
                    })
                borough_crime_stats[b_name] = sorted(results, key=lambda x: x['relative_frequency'], reverse=True)
    except Exception as e:
        logger.error(f"Error calculating borough crime stats: {e}")

    return fig, borough_crime_stats

# Fix for the update_dashboard function




#-----------------------------------------------------------
# Demographic Analysis Callbacks
# ---------------------------------------------------------------------------------
@dash.callback(
    Output("reference-borough-dropdown", "options"),  # Changed from reference-lsoa-dropdown
    [Input("outcome-type-dropdown", "value"),
     Input("crime-type-dropdown", "value")]
)
def update_borough_options(outcomes, crimes):  # Changed function name
    """Update borough dropdown options based on filtered data."""
    # Get unique borough names
    filters = {
        'outcome_type': outcomes,
        'crime_type': crimes,
        'census_year': 2015
    }
    
    # Use load_unique_values to get all unique borough names
    borough_names = load_unique_values('lad_name')
    
    # Create dropdown options
    options = [{'label': borough, 'value': borough} for borough in borough_names]
    
    return options




@dash.callback(
    [Output("demographic-correlation", "figure"),
     Output("similarity-map", "figure")],
    [Input("demographic-dropdown", "value"),
     Input("reference-lsoa-dropdown", "value"),  # Changed from reference-lsoa-dropdown
     Input("outcome-type-dropdown", "value"),
     Input("crime-type-dropdown", "value"),
     Input("theme-toggle-btn", "n_clicks")],
    [State("theme-container", "data-theme")]
)
def update_demographic_analysis(selected_demographic, reference_borough,  # Changed parameter name
                               outcomes, crimes, _n_clicks, data_theme):
    """Update demographic analysis charts based on selections."""
    is_light_mode = (data_theme == 'light')
    
    try:
        # Load aggregated data by borough with demographic information
        demographic_cols = {
            selected_demographic: 'AVG',
            'income': 'AVG'  # Include income for additional context
        }
        
        filters = {
            'outcome_type': outcomes,
            'crime_type': crimes,
            'census_year': 2015
        }
        
        # Get borough-level aggregation with normalization for population
        borough_demo_data = load_aggregated_data(
            group_by_columns=['lad_name'],
            metric_columns=demographic_cols,
            filters=filters
        )
        
        # Generate the charts with borough-level data
        correlation_fig = generate_demographic_correlation(
            borough_demo_data, selected_demographic, is_light_mode
        )
        similarity_fig = generate_borough_similarity_map(
            borough_demo_data, reference_borough, selected_demographic, is_light_mode
        )
        
        return correlation_fig, similarity_fig
    except Exception as e:
        logger.error(f"Error in demographic analysis: {e}")
        import traceback
        logger.error(traceback.format_exc())
        error_fig = go.Figure()
        error_fig.add_annotation(
            text=f"Error generating analysis: {str(e)}",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False
        )
        return error_fig, error_fig







#---------------------------------------------------------------------------------
# Toggle Filters Collapse
# ---------------------------------------------------------------------------------
@dash.callback(
    Output("dashboard-filters-collapse", "is_open"),
    [Input("toggle-filters-btn", "n_clicks")],
    [State("dashboard-filters-collapse", "is_open")]
)
def toggle_filters(n_clicks, is_open):
    """Expand/Collapse the filters section."""
    if n_clicks:
        return not is_open
    return is_open


# ---------------------------------------------------------------------------------
# Show/Remove All (Outcomes & Crime Types)
# ---------------------------------------------------------------------------------
@dash.callback(
    Output("outcome-type-dropdown", "value"),
    [Input("show-all-outcomes", "n_clicks"),
     Input("remove-all-outcomes", "n_clicks")],
    [State("outcome-type-dropdown", "options")]
)
def update_outcome_selection(show_all, remove_all, options):
    """
    Handle Show All / Remove All for outcome dropdown.
    """
    ctx = dash.callback_context
    if not ctx.triggered:
        return dash.no_update

    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    if button_id == "show-all-outcomes":
        return [o['value'] for o in options]
    elif button_id == "remove-all-outcomes":
        return []
    return dash.no_update


@dash.callback(
    Output("crime-type-dropdown", "value"),
    [Input("show-all-crimes", "n_clicks"),
     Input("remove-all-crimes", "n_clicks")],
    [State("crime-type-dropdown", "options")]
)
def update_crime_selection(show_all, remove_all, options):
    """
    Handle Show All / Remove All for crime dropdown.
    """
    ctx = dash.callback_context
    if not ctx.triggered:
        return dash.no_update

    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    if button_id == "show-all-crimes":
        return [o['value'] for o in options]
    elif button_id == "remove-all-crimes":
        return []
    return dash.no_update


# ---------------------------------------------------------------------------------
# Debug Callback for Click Data
# ---------------------------------------------------------------------------------
@dash.callback(
    Output("borough-title", "children", allow_duplicate=True),
    [Input("borough-map", "clickData")],
    prevent_initial_call=True
)
def debug_click_data(click_data):
    """
    This callback displays the raw click data under the borough title,
    so you can debug exactly what's being returned by the map click.
    """
    if not click_data:
        return dash.no_update

    click_str = json.dumps(click_data, indent=2)
    logger.info(f"CLICK DEBUG - Raw data: {click_str}")

    return html.Div([
        html.H4("Click Data Debug"),
        html.Pre(click_str, style={
            "whiteSpace": "pre-wrap",
            "backgroundColor": "#f8f9fa",
            "padding": "10px",
            "border": "1px solid #ddd",
            "borderRadius": "5px",
            "fontSize": "12px",
            "maxHeight": "200px",
            "overflow": "auto"
        })
    ])


def register_callbacks(app):
    """
    Register any theme or additional callbacks needed by the dashboard.
    """
    register_theme_callbacks(app)