import logging
import dash_bootstrap_components as dbc
from dash import dcc, html
from dash.dependencies import Input, Output, State
import plotly.express as px
import plotly.graph_objs as go
import json
import pandas as pd
import os
import geopandas as gpd  # For computing centroids

from data_loader import load_data, load_lsoa_lookup
from dotenv import load_dotenv

load_dotenv()

# Load LSOA GeoJSON
with open("data/alt_lsoa_boundaries.geojson", "r") as f:
    lsoa_geojson = json.load(f)
logging.info(f"Loaded LSOA GeoJSON with {len(lsoa_geojson.get('features', []))} features.")

# Load London Borough boundaries from "data/london_borough.geojson"
with open("data/london-boroughs_1179 (1).geojson", "r") as f:
    borough_geojson = json.load(f)
logging.info(f"Loaded Borough GeoJSON with {len(borough_geojson.get('features', []))} features.")

MAP_CENTER_LON = -0.1278  # Default map center (London)

def layout():
    """
    Comparison Layout:
    - Year + Crime Type dropdowns
    - Choropleth map (LSOA)
    - Top 10 LSOA bar chart (below the map)
    - Hidden store for aggregated data
    """
    crime_data = load_data()
    lsoa_lookup = load_lsoa_lookup()

    header = html.Div([
        html.H1("UK Crime Data Comparison", style={"textAlign": "center"}),
        html.P(
            "Explore aggregated LSOA crime data across the UK. Use the filters below to select a crime type "
            "and view data for a specific year or for all years. The choropleth map displays the crime counts per LSOA, "
            "and the top 10 LSOAs by crime count are shown below.",
            style={"textAlign": "center"}
        )
    ], className="page-header", style={"marginBottom": "30px"})

    # Prepare the dropdown options
    available_years = sorted(crime_data["year"].dropna().unique())
    year_options = [{"label": "All Years", "value": "all"}] + [
        {"label": str(y), "value": str(y)} for y in available_years
    ]
    crime_type_options = [{"label": "All Crimes", "value": "all"}] + [
        {"label": ct, "value": ct} for ct in crime_data["crime_type"].dropna().unique()
    ]

    return dbc.Container(
        fluid=True,
        children=[
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
            # Choropleth map row (full width)
            dbc.Row(
                dbc.Col(
                    dcc.Loading(
                        dcc.Graph(
                            id="lsoa-choropleth-map",
                            style={"width": "100%", "height": "600px"},
                            config={"displayModeBar": False, "scrollZoom": True}
                        ),
                        type="circle"
                    ),
                    width=12
                ),
                className="my-2"
            ),
            # New row: Top 10 LSOA bar chart below the map
            dbc.Row(
                dbc.Col(
                    dcc.Loading(
                        dcc.Graph(
                            id="top10-lsoa-bar",
                            style={"width": "100%", "height": "400px"},
                            config={"displayModeBar": False}
                        ),
                        type="circle"
                    ),
                    width=12
                ),
                className="my-2"
            ),
            # Hidden store for aggregated data
            dcc.Store(id="aggregated-data")
        ]
    )

def register_callbacks(app):
    """Comparison page callbacks."""

    @app.callback(
        [
            Output("lsoa-choropleth-map", "figure"),
            Output("aggregated-data", "data"),
            Output("lsoa-count", "children")
        ],
        [
            Input("lsoa-year-dropdown", "value"),
            Input("lsoa-crime-dropdown", "value"),
            Input("theme-toggle-btn", "n_clicks")  # replaced the old theme-toggle-switch reference
        ],
        [State("theme-container", "className")]
    )
    def update_map(selected_year, selected_crime, _n_clicks, theme_class):
        """
        1) Filter the crime data by selected_year, selected_crime
        2) Group by LSOA => aggregator
        3) Build the choropleth map
        4) Store aggregated data
        5) Return a text count for the # of LSOAs
        """
        logging.info("=== Comparison -> update_map callback ===")
        logging.info(f"Selected year={selected_year}, selected_crime={selected_crime}")

        is_light_mode = "light-theme" in theme_class
        logging.info(f"is_light_mode={is_light_mode}")

        # Load the raw data
        crime_data = load_data()
        logging.info(f"Raw data => {len(crime_data)} rows, columns => {crime_data.columns.tolist()}")

        # Filter by year
        if selected_year != "all":
            year_val = int(selected_year)
            crime_data = crime_data[crime_data["year"] == year_val]
            logging.info(f"Filtered by year => {len(crime_data)} rows remain")

        # Filter by crime type
        if selected_crime != "all":
            crime_data = crime_data[crime_data["crime_type"] == selected_crime]
            logging.info(f"Filtered by crime => {len(crime_data)} rows remain")

        if crime_data.empty:
            logging.warning("No data after filtering => returning empty figure")
            return go.Figure(), None, "Highlighted LSOAs: 0"

        # Group by LSOA code & aggregator
        grouped = crime_data.groupby("lsoa_code").agg(
            crime_count=('lsoa_code', 'size'),
            youth_male_percent=('youth_male_percent', 'mean'),
            youth_female_percent=('youth_female_percent', 'mean'),
            young_adult_male_percent=('young_adult_male_percent', 'mean'),
            young_adult_female_percent=('young_adult_female_percent', 'mean'),
            adult_male_percent=('adult_male_percent', 'mean'),
            adult_female_percent=('adult_female_percent', 'mean'),
            senior_male_percent=('senior_male_percent', 'mean'),
            senior_female_percent=('senior_female_percent', 'mean')
        ).reset_index()

        logging.info(f"grouped => {len(grouped)} rows, columns => {grouped.columns.tolist()}")

        # Merge with LSOA lookup => get "lsoa_name"
        lsoa_lookup = load_lsoa_lookup()
        grouped.columns = grouped.columns.str.strip().str.lower()  # ensure consistency
        lsoa_lookup.columns = lsoa_lookup.columns.str.strip().str.lower()

        merged = pd.merge(grouped, lsoa_lookup, on="lsoa_code", how="left")
        logging.info(f"merged => {len(merged)} rows, columns => {merged.columns.tolist()}")

        num_lsoa = merged["lsoa_code"].nunique()
        lsoa_count_text = f"Highlighted LSOAs: {num_lsoa}"

        # Filter LSOAs for the GeoJSON
        lsoa_codes = merged["lsoa_code"].dropna().unique().tolist()
        logging.info(f"Unique LSOAs => {len(lsoa_codes)}, sample => {lsoa_codes[:5]}")

        filtered_geojson = {
            "type": "FeatureCollection",
            "features": [
                feat for feat in lsoa_geojson["features"]
                if feat["properties"].get("LSOA21CD") in lsoa_codes
            ]
        }
        logging.info(f"filtered_geojson => {len(filtered_geojson['features'])} features remain")

        # Decide map style
        mapbox_style = "open-street-map"

        # Build the map
        try:
            fig_map = px.choropleth_mapbox(
                merged,
                geojson=filtered_geojson,
                locations="lsoa_code",
                color="crime_count",
                featureidkey="properties.LSOA21CD",
                hover_name="lsoa_name",
                hover_data={"crime_count": True},
                mapbox_style=mapbox_style,
                zoom=10,
                center={"lat": 51.5074, "lon": -0.1278},
                opacity=0.6,
                color_continuous_scale="YlOrRd"
            )
            # Overlay borough boundaries
            fig_map.update_layout(
                mapbox=dict(
                    layers=[
                        {
                            "source": borough_geojson,
                            "type": "line",
                            "below": "traces",
                            "color": "black",
                            "line": {"width": 2}
                        }
                    ]
                ),
                margin={"l": 0, "r": 0, "t": 0, "b": 0}
            )
            logging.info("Choropleth map created successfully.")
        except Exception as e:
            logging.error(f"Error building map => {e}")
            fig_map = go.Figure()

        return fig_map, merged.to_dict("records"), lsoa_count_text

    @app.callback(
        Output("top10-lsoa-bar", "figure"),
        [
            Input("aggregated-data", "data"),
            Input("theme-toggle-btn", "n_clicks")
        ],
        [State("theme-container", "className")]
    )
    def update_top10_bar(aggregated_data, _theme_clicks, theme_class):
        """
        Builds a bar chart of the top 10 LSOAs (by crime count) using the aggregated data.
        """
        if not aggregated_data:
            return go.Figure()

        df = pd.DataFrame(aggregated_data)
        # Sort by crime_count and take top 10
        top10 = df.sort_values("crime_count", ascending=False).head(10)

        fig = px.bar(
            top10,
            x="lsoa_name",
            y="crime_count",
            text="crime_count",
            title="Top 10 LSOAs by Crime Count"
        )
        # Adjust theme based on mode
        is_light_mode = "light-theme" in theme_class
        font_color = "#000000" if is_light_mode else "#e0e0e0"
        fig.update_layout(
            title_font=dict(size=16, family="Poppins, sans-serif", color=font_color),
            xaxis_title="LSOA Name",
            yaxis_title="Crime Count",
            font=dict(color=font_color),
            plot_bgcolor="#FFFFFF" if is_light_mode else "#121212",
            paper_bgcolor="#FFFFFF" if is_light_mode else "#121212",
            margin=dict(l=40, r=40, t=40, b=40)
        )
        fig.update_traces(textposition='outside')
        return fig
