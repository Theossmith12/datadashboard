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
    - Demographic bar chart (on hover)
    - Hidden store for aggregated data
    """
    crime_data = load_data()
    lsoa_lookup = load_lsoa_lookup()

    header = html.Div([
        html.H1("UK Crime Data Comparison", style={"textAlign": "center"}),
        html.P(
            "Explore aggregated LSOA crime data across the UK. Use the filters below to select a crime type "
            "and view data for a specific year or for all years. Hover over a map location to see a demographic breakdown. "
            "London borough boundaries and their names are overlaid using 'london_borough.geojson'.",
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

            dbc.Row([
                dbc.Col(
                    dcc.Loading(
                        dcc.Graph(
                            id="lsoa-choropleth-map",
                            style={"width": "100%", "height": "600px"},
                            config={"displayModeBar": False, "scrollZoom": True}
                        ),
                        type="circle"
                    ),
                    width=8
                ),
                dbc.Col(
                    dcc.Loading(
                        dcc.Graph(
                            id="demographic-bar",
                            style={"width": "100%", "height": "600px"},
                            config={"displayModeBar": False}
                        ),
                        type="circle"
                    ),
                    width=4
                )
            ], className="my-2"),

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
        """
        Builds a bar chart of demographic info for the hovered LSOA.
        """
        logging.info("=== comparison -> update_demo_bar ===")

        is_light_mode = "light-theme" in theme_class
        if not hoverData or not aggregated_data:
            logging.info("No hoverData or no aggregated_data => empty fig")
            return go.Figure()

        # Attempt to parse the hovered LSOA code
        points = hoverData.get("points", [])
        if not points:
            logging.info("hoverData has no points => empty fig")
            return go.Figure()

        lsoa_code = points[0].get("location")
        if not lsoa_code:
            logging.info("No location in points => empty fig")
            return go.Figure()

        df_agg = pd.DataFrame(aggregated_data)
        # Verify columns
        logging.info(f"df_agg columns => {df_agg.columns.tolist()}")
        record_df = df_agg[df_agg["lsoa_code"] == lsoa_code]
        if record_df.empty:
            logging.info("No matching row in aggregated_data => empty fig")
            return go.Figure()

        rec = record_df.iloc[0]
        lsoa_name = rec.get("lsoa_name", lsoa_code)

        # Build your demographic dict
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

        # Adjust theme
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
