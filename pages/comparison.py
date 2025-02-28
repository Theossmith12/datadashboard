import logging
import dash_bootstrap_components as dbc
from dash import dcc, html, Input, Output, State, clientside_callback
import plotly.express as px
import plotly.graph_objs as go
import json
import pandas as pd
import os
import dash
import traceback  # For better error logging

from data_loader import load_data, load_lsoa_lookup
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

load_dotenv()

# Load LSOA GeoJSON
try:
    with open("data/alt_lsoa_boundaries.geojson", "r") as f:
        lsoa_geojson = json.load(f)
    logger.info(f"Successfully loaded LSOA GeoJSON with {len(lsoa_geojson.get('features', []))} features")
    
    # Check if key properties exist
    if lsoa_geojson and lsoa_geojson.get('features'):
        feature = lsoa_geojson['features'][0]
        logger.debug(f"GeoJSON sample properties: {feature.get('properties', {}).keys()}")
        
        # Check for LSOA code property
        if 'LSOA21CD' in feature.get('properties', {}):
            logger.debug("LSOA21CD property exists in GeoJSON")
            lsoa_prop_name = "LSOA21CD"
        else:
            logger.warning("LSOA21CD property not found in GeoJSON!")
            # Try to find alternative property
            props = feature.get('properties', {}).keys()
            lsoa_prop_name = None
            for prop in props:
                if 'LSOA' in prop or 'lsoa' in prop.lower() or 'code' in prop.lower():
                    lsoa_prop_name = prop
                    logger.info(f"Found alternative LSOA property: {lsoa_prop_name}")
                    break
            
            if not lsoa_prop_name:
                logger.error("Could not find suitable LSOA property in GeoJSON")
            
except Exception as e:
    logger.error(f"Failed to load LSOA GeoJSON: {str(e)}")
    logger.error(traceback.format_exc())
    lsoa_geojson = {"type": "FeatureCollection", "features": []}
    lsoa_prop_name = None

# Load London Borough boundaries
try:
    with open("data/london_boroughs.geojson", "r") as f:
        borough_geojson = json.load(f)
    logger.info(f"Successfully loaded Borough GeoJSON with {len(borough_geojson.get('features', []))} features.")
except Exception as e:
    logger.error(f"Error loading london_boroughs.geojson: {e}")
    # Try alternative filename
    try:
        with open("data/london-boroughs_1179 (1).geojson", "r") as f:
            borough_geojson = json.load(f)
        logger.info(f"Successfully loaded alternative Borough GeoJSON with {len(borough_geojson.get('features', []))} features.")
    except Exception as e2:
        logger.error(f"Error loading alternative geojson: {e2}")
        logger.error(traceback.format_exc())
        borough_geojson = {"type": "FeatureCollection", "features": []}

MAP_CENTER_LON = -0.1278  # Default map center (London)
MAP_CENTER_LAT = 51.5074  # Default map center (London)

def create_map_container(map_id, loading_id):
    """Helper function to create a map container using Mapbox choropleth"""
    logger.debug(f"Creating map container with id: {map_id}")
    return html.Div([
        dcc.Loading(
            dcc.Graph(
                id=map_id,
                style={"width": "100%", "height": "100%"},
                config={
                    "displayModeBar": False,
                    "scrollZoom": True
                },
                clear_on_unhover=True,
                className="mobile-map"
            ),
            type="circle",
            id=loading_id
        ),
        dcc.Store(id=f"{map_id}-selected-borough")
    ], className="map-container", style={"height": "500px"})

def layout():
    """
    Comparison Layout:
    - Year + Crime Type dropdowns
    - Choropleth map (LSOA) using Mapbox
    - Demographic bar chart (on hover)
    - Hidden store for aggregated data
    """
    logger.debug("Initializing comparison layout")
    try:
        crime_data = load_data()
        lsoa_lookup = load_lsoa_lookup()
        logger.info(f"Successfully loaded initial data: {len(crime_data)} crime records, {len(lsoa_lookup)} LSOA records")
        
        available_years = sorted(crime_data["year"].dropna().unique())
        crime_types = crime_data["crime_type"].dropna().unique()
        logger.debug(f"Available years: {available_years}")
        logger.debug(f"Available crime types: {crime_types}")
        
        header = html.Div([
            html.H1("UK Crime Data Comparison", style={"textAlign": "center"}),
            html.P(
                "Explore aggregated LSOA crime data across the UK. Use the filters below to select a crime type "
                "and view data for a specific year or for all years. Hover over a map location to see a demographic breakdown.",
                style={"textAlign": "center"}
            )
        ], className="page-header", style={"marginBottom": "30px"})

        # Prepare the dropdown options
        year_options = [{"label": "All Years", "value": "all"}] + [
            {"label": str(y), "value": str(y)} for y in available_years
        ]
        crime_type_options = [{"label": "All Crimes", "value": "all"}] + [
            {"label": ct, "value": ct} for ct in crime_types
        ]

        return dbc.Container(
            fluid=True,
            children=[
                dcc.Store(id="is-mobile", data=False),
                dcc.Interval(id='mobile-check-interval', interval=1000),
                
                header,
                dbc.Row(
                    dbc.Col(
                        html.Div(
                            id="lsoa-count",
                            style={"textAlign": "center", "fontWeight": "bold", "marginBottom": "15px"}
                        ),
                        width=12
                    )
                ),
                dbc.Row([
                    dbc.Col([
                        html.Label("Select Year"),
                        dcc.Dropdown(
                            id="lsoa-year-dropdown",
                            options=year_options,
                            value="all",
                            clearable=False,
                            className="filter-item"
                        )
                    ], width=6),
                    dbc.Col([
                        html.Label("Select Crime Type"),
                        dcc.Dropdown(
                            id="lsoa-crime-dropdown",
                            options=crime_type_options,
                            value="all",
                            clearable=False,
                            className="filter-item"
                        )
                    ], width=6)
                ], className="my-2"),

                dbc.Row([
                    dbc.Col(
                        create_map_container("lsoa-choropleth-map", "lsoa-map-loading"),
                        width=8
                    ),
                    dbc.Col(
                        dcc.Loading(
                            dcc.Graph(
                                id="demographic-bar",
                                style={"width": "100%", "height": "500px"},
                                config={"displayModeBar": False}
                            ),
                            type="circle"
                        ),
                        width=4
                    )
                ], className="my-2"),

                dcc.Store(id="aggregated-data"),
                dcc.Store(id="comparison-aggregated-data"),
                
                # Debug information (you can remove this in production)
                html.Div(id="debug-info", style={"whiteSpace": "pre-wrap", "fontSize": "12px", "marginTop": "20px"})
            ]
        )

    except Exception as e:
        logger.error("Error initializing layout")
        logger.error(traceback.format_exc())
        return html.Div("Error initializing layout. Check console for details.")

def register_callbacks(app):
    """Comparison page callbacks."""
    logger.debug("Registering comparison page callbacks")
    
    app.clientside_callback(
        """
        function(n_intervals) {
            return window.innerWidth <= 768;
        }
        """,
        Output("is-mobile", "data"),
        Input("mobile-check-interval", "n_intervals")
    )

    @app.callback(
        [
            Output("lsoa-choropleth-map", "figure"),
            Output("aggregated-data", "data"),
            Output("lsoa-count", "children"),
            Output("debug-info", "children")
        ],
        [
            Input("lsoa-year-dropdown", "value"),
            Input("lsoa-crime-dropdown", "value"),
            Input("theme-toggle-btn", "n_clicks"),
            Input("is-mobile", "data")
        ],
        [State("theme-container", "className")]
    )
    def update_map(selected_year, selected_crime, _n_clicks, is_mobile, theme_class):
        logger.info("=== Starting update_map callback ===")
        logger.debug(f"Inputs - Year: {selected_year}, Crime: {selected_crime}, Mobile: {is_mobile}")
        logger.debug(f"Theme class: {theme_class}")
        
        debug_info = ""  # Initialize debug info
        
        try:
            crime_data = load_data()
            debug_info += f"Loaded raw data: {len(crime_data)} rows\n"
            debug_info += f"Raw data columns: {crime_data.columns.tolist()}\n"
            
            # Check if we have location data
            has_location_data = 'latitude' in crime_data.columns and 'longitude' in crime_data.columns
            debug_info += f"Has direct location data: {has_location_data}\n"
            
            # Filter data
            if selected_year != "all":
                year_val = int(selected_year)
                crime_data = crime_data[crime_data["year"] == year_val]
                debug_info += f"Filtered by year {selected_year}: {len(crime_data)} rows remain\n"
            
            if selected_crime != "all":
                crime_data = crime_data[crime_data["crime_type"] == selected_crime]
                debug_info += f"Filtered by crime {selected_crime}: {len(crime_data)} rows remain\n"
            
            if crime_data.empty:
                logger.warning("No data after filtering")
                return (
                    create_empty_figure("No data available for the selected filters"), 
                    None, 
                    "No LSOAs match the selected criteria",
                    "No data available after filtering"
                )
            
            # Simple aggregation to reduce data size
            grouped = crime_data.groupby("lsoa_code").agg({
                'lsoa_code': 'size',
                'youth_male_percent': 'mean',
                'youth_female_percent': 'mean',
                'young_adult_male_percent': 'mean',
                'young_adult_female_percent': 'mean',
                'adult_male_percent': 'mean',
                'adult_female_percent': 'mean',
                'senior_male_percent': 'mean',
                'senior_female_percent': 'mean'
            }).rename(columns={'lsoa_code': 'crime_count'}).reset_index()
            
            # If we have latitude/longitude, add those to our grouped data
            if has_location_data:
                # Create a mapping of LSOA codes to average lat/lon
                lsoa_coords = crime_data.groupby('lsoa_code').agg({
                    'latitude': 'mean',
                    'longitude': 'mean'
                }).reset_index()
                
                # Merge with our aggregated data
                grouped = pd.merge(grouped, lsoa_coords, on='lsoa_code', how='left')
                debug_info += f"Added location data to grouped dataframe\n"
            
            # Merge with LSOA lookup for names
            lsoa_lookup = load_lsoa_lookup()
            grouped.columns = grouped.columns.str.strip().str.lower()
            lsoa_lookup.columns = lsoa_lookup.columns.str.strip().str.lower()
            
            merged = pd.merge(grouped, lsoa_lookup, on="lsoa_code", how="left")
            debug_info += f"Merged data: {len(merged)} rows with {merged.columns.tolist()} columns\n"
            
            # Show a sample
            if not merged.empty:
                debug_info += f"Sample row:\n{merged.iloc[0].to_dict()}\n"
            
            # Create the map
            is_light_mode = theme_class and "light-theme" in theme_class
            fig_map = create_choropleth(merged, is_mobile, is_light_mode)
            
            return (
                fig_map, 
                merged.to_dict("records"), 
                f"Highlighted LSOAs: {len(merged)}",
                debug_info
            )
            
        except Exception as e:
            error_msg = f"Error in update_map callback: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            return (
                create_empty_figure(f"Error: {str(e)}"), 
                None, 
                "Error loading data",
                f"Error: {str(e)}\n{traceback.format_exc()}"
            )

    @app.callback(
        Output("demographic-bar", "figure"),
        [
            Input("lsoa-choropleth-map", "hoverData"),
            Input("theme-toggle-btn", "n_clicks")
        ],
        [
            State("theme-container", "className"),
            State("aggregated-data", "data")
        ]
    )
    def update_demo_bar(hoverData, _theme_clicks, theme_class, aggregated_data):
        logging.info("=== comparison -> update_demo_bar ===")

        is_light_mode = "light-theme" in theme_class if theme_class else False
        if not hoverData or not aggregated_data:
            logging.info("No hoverData or no aggregated_data => empty fig")
            return go.Figure()

        points = hoverData.get("points", [])
        if not points:
            logging.info("hoverData has no points => empty fig")
            return go.Figure()

        lsoa_code = points[0].get("location")
        if not lsoa_code:
            logging.info("No location in points => empty fig")
            return go.Figure()

        df_agg = pd.DataFrame(aggregated_data)
        logging.info(f"df_agg columns => {df_agg.columns.tolist()}")
        record_df = df_agg[df_agg["lsoa_code"] == lsoa_code]
        if record_df.empty:
            logging.info("No matching row in aggregated_data => empty fig")
            return go.Figure()

        rec = record_df.iloc[0]
        lsoa_name = rec.get("lsoa_name", lsoa_code)

        demo_dict = {
            "Youth Male": rec.get("youth_male_percent", 0),
            "Youth Female": rec.get("youth_female_percent", 0),
            "Young Adult Male": rec.get("young_adult_male_percent", 0),
            "Young Adult Female": rec.get("young_adult_female_percent", 0),
            "Adult Male": rec.get("adult_male_percent", 0),
            "Adult Female": rec.get("adult_female_percent", 0),
            "Senior Male": rec.get("senior_male_percent", 0),
            "Senior Female": rec.get("senior_female_percent", 0)
        }

        demo_df = pd.DataFrame(list(demo_dict.items()), columns=["Group", "Percentage"])
        demo_df.sort_values("Percentage", ascending=False, inplace=True)

        fig = px.bar(
            demo_df,
            x="Percentage",
            y="Group",
            orientation="h",
            title=f"Demographics for {lsoa_name}"
        )
        fig.update_traces(
            texttemplate='%{x:.2f}%',
            textposition='outside',
            marker_color='lightskyblue'
        )

        font_color = "#000000" if is_light_mode else "#e0e0e0"
        fig.update_layout(
            title_font=dict(size=14, family='Poppins, sans-serif', color=font_color, weight='bold'),
            xaxis_title="Percentage",
            yaxis_title="Group",
            font=dict(size=12, family='Poppins, sans-serif', color=font_color),
            margin=dict(l=20, r=20, t=40, b=20),
            plot_bgcolor="#FFFFFF" if is_light_mode else "#121212",
            paper_bgcolor="#FFFFFF" if is_light_mode else "#121212"
        )
        fig.update_yaxes(autorange="reversed")

        logging.info(f"Built demographics chart for LSOA {lsoa_code}")
        return fig

def create_empty_figure(message):
    """Helper function to create empty figure with message"""
    fig = go.Figure()
    fig.update_layout(
        annotations=[dict(
            text=message,
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(color="red", size=14)
        )],
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    return fig

def create_choropleth(data, is_mobile, is_light_mode=False):
    """Creates a simple mapbox visualization showing LSOA data"""
    logger.debug("Creating choropleth with parameters:")
    logger.debug(f"Data shape: {data.shape}")
    logger.debug(f"Is mobile: {is_mobile}")
    logger.debug(f"Is light mode: {is_light_mode}")
    
    try:
        # Basic map setup
        fig = go.Figure()
        
        # Try adding LSOA points based on crime data
        # This simple approach should work regardless of GeoJSON issues
        if 'latitude' in data.columns and 'longitude' in data.columns:
            # Use actual coordinates if available
            lat_lon_data = data.dropna(subset=['latitude', 'longitude'])
            
            if not lat_lon_data.empty:
                fig.add_trace(go.Scattermapbox(
                    lat=lat_lon_data['latitude'],
                    lon=lat_lon_data['longitude'],
                    mode='markers',
                    marker=dict(
                        size=8,
                        color=lat_lon_data['crime_count'],
                        colorscale='YlOrRd',
                        opacity=0.7,
                        showscale=True,
                        colorbar=dict(title="Crime Count")
                    ),
                    text=lat_lon_data['lsoa_name'],
                    hoverinfo='text',
                    hovertemplate="<b>%{text}</b><br>Crime Count: %{marker.color}<extra></extra>",
                ))
                logger.debug("Added point data based on latitude/longitude")
        
        # Try adding LSOA polygons using the GeoJSON
        try:
            # Create a trace specifically for the LSOA boundaries
            if lsoa_geojson and lsoa_geojson.get('features'):
                # Map LSOA codes to crime counts for coloring
                lsoa_crime_dict = {}
                for _, row in data.iterrows():
                    lsoa_crime_dict[row['lsoa_code']] = row['crime_count']
                
                # Find all LSOA polygons and draw them manually
                for feature in lsoa_geojson['features']:
                    # Get LSOA code using the property name we identified earlier
                    if lsoa_prop_name and lsoa_prop_name in feature['properties']:
                        lsoa_id = feature['properties'][lsoa_prop_name]
                        
                        # Check if this LSOA is in our data
                        if lsoa_id in data['lsoa_code'].values:
                            # Get info for this LSOA
                            lsoa_info = data[data['lsoa_code'] == lsoa_id].iloc[0]
                            
                            # Extract coordinates
                            if feature['geometry']['type'] == 'Polygon':
                                coords = feature['geometry']['coordinates'][0]  # Outer ring only
                                lons = [coord[0] for coord in coords]
                                lats = [coord[1] for coord in coords]
                                
                                # Create a polygon for this LSOA
                                fig.add_trace(go.Scattermapbox(
                                    lon=lons,
                                    lat=lats,
                                    mode='lines',
                                    line=dict(
                                        width=1,
                                        color='rgba(70,70,70,0.5)'
                                    ),
                                    fill='toself',
                                    fillcolor=f'rgba(255,0,0,{min(1.0, lsoa_info["crime_count"]/100)})',
                                    hoverinfo='text',
                                    hovertemplate=f"<b>{lsoa_info['lsoa_name']}</b><br>Crime Count: {lsoa_info['crime_count']}<extra></extra>",
                                    name=lsoa_info['lsoa_name'],
                                    showlegend=False
                                ))
                
                logger.debug("Added LSOA boundary polygons")
        except Exception as e:
            logger.error(f"Error adding LSOA polygons: {e}")
            logger.error(traceback.format_exc())
        
        # If we don't have coordinates to show, ensure we at least have a center point
        if not ('latitude' in data.columns and 'longitude' in data.columns):
            # Add a simple marker in London for reference
            fig.add_trace(go.Scattermapbox(
                lat=[51.5074],
                lon=[-0.1278],
                mode='markers',
                marker=dict(size=10, color='red'),
                text=['London Center'],
                hoverinfo='text'
            ))
            logger.debug("Added central London marker as fallback")
                
        # Add London borough outlines - simple approach
        try:
            if borough_geojson and borough_geojson.get('features'):
                for feature in borough_geojson['features']:
                    borough_name = feature['properties'].get('name', 'Borough')
                    
                    # Handle different geometry types
                    if feature['geometry']['type'] == 'Polygon':
                        coords = feature['geometry']['coordinates'][0]
                        lons = [coord[0] for coord in coords]
                        lats = [coord[1] for coord in coords]
                        
                        # Add borough outline
                        fig.add_trace(go.Scattermapbox(
                            lon=lons,
                            lat=lats,
                            mode='lines',
                            line=dict(width=2, color='black'),
                            hoverinfo='text',
                            hovertemplate=f"<b>{borough_name}</b><extra></extra>",
                            name=borough_name,
                            showlegend=False
                        ))
                    
                    elif feature['geometry']['type'] == 'MultiPolygon':
                        for poly in feature['geometry']['coordinates']:
                            coords = poly[0]
                            lons = [coord[0] for coord in coords]
                            lats = [coord[1] for coord in coords]
                            
                            # Add borough outline
                            fig.add_trace(go.Scattermapbox(
                                lon=lons,
                                lat=lats,
                                mode='lines',
                                line=dict(width=2, color='black'),
                                hoverinfo='text',
                                hovertemplate=f"<b>{borough_name}</b><extra></extra>",
                                name=borough_name,
                                showlegend=False
                            ))
                
                logger.debug("Added borough boundaries")
        except Exception as e:
            logger.error(f"Error adding borough boundaries: {e}")
            
        # Set up the mapbox configuration
        fig.update_layout(
            mapbox=dict(
                style="carto-positron",  # This style works without a token
                zoom=9,
                center=dict(lat=51.5074, lon=-0.1278)  # London center
            ),
            margin=dict(l=0, r=0, t=0, b=0),  # Remove margins
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(
                family="Poppins, sans-serif",
                color="#000000" if is_light_mode else "#e0e0e0"
            ),
            height=600,  # Make the map bigger for better visibility
            showlegend=False
        )
        
        logger.debug("Choropleth created successfully")
        return fig
    except Exception as e:
        logger.error(f"Error creating choropleth: {e}")
        logger.error(traceback.format_exc())
        # Return a map with an error message
        fig = go.Figure()
        fig.add_annotation(
            text=f"Error creating map: {str(e)}",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(color="red", size=14)
        )
        return fig