import logging
import dash_bootstrap_components as dbc
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.express as px
import plotly.graph_objs as go
import json
import pandas as pd
import os

from shapely.geometry import shape, mapping, box
from shapely.ops import unary_union

from data_loader import crime_data, lsoa_lookup
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# If you have a Mapbox token, you can still load it; 
# but for "open-street-map" style it is not strictly needed.
mapbox_token = os.getenv('MAPBOX_TOKEN')
if mapbox_token:
    px.set_mapbox_access_token(mapbox_token)
    logging.info("✅ Mapbox token loaded (not required for open-street-map).")
else:
    logging.info("No Mapbox token found. Using open-street-map style without a token.")

# Load LSOA GeoJSON
with open("data/lsoa_boundaries.geojson", "r") as f:
    lsoa_geojson = json.load(f)
logging.info(f"Loaded GeoJSON with {len(lsoa_geojson.get('features', []))} features.")

DEBUG = True

def layout():
    available_years = sorted(crime_data["month"].dt.year.unique())
    year_options = [{"label": str(y), "value": str(y)} for y in available_years]

    crime_type_options = [
        {"label": ct, "value": ct}
        for ct in crime_data["crime_type"].dropna().unique()
    ]

    return dbc.Container(
        fluid=True,
        children=[
            dbc.Row([
                dbc.Col([
                    html.Label("Select Year"),
                    dcc.Dropdown(
                        id="lsoa-year-dropdown",
                        options=year_options,
                        value=str(available_years[0]) if available_years else None,
                        clearable=False,
                        className="filter-item"
                    )
                ], width=6),
                dbc.Col([
                    html.Label("Select Crime Type"),
                    dcc.Dropdown(
                        id="lsoa-crime-dropdown",
                        options=crime_type_options,
                        value=crime_type_options[0]["value"] if crime_type_options else None,
                        clearable=False,
                        className="filter-item"
                    )
                ], width=6),
            ], className="my-2"),

            dbc.Row([
                dbc.Col(
                    dcc.Loading(
                        dcc.Graph(
                            id="lsoa-choropleth-map",
                            style={"width": "100%", "height": "800px"},  # Adjust as needed
                            config={"displayModeBar": False, "scrollZoom": True}
                        ),
                        type="circle"
                    ),
                    width=12
                )
            ], className="my-2"),

            dbc.Row([
                dbc.Col(
                    dcc.Loading(
                        dcc.Graph(
                            id="top-10-lsoa-bar",
                            config={"displayModeBar": False}
                        ),
                        type="circle"
                    ),
                    width=12
                )
            ], className="my-2")
        ]
    )

def register_callbacks(app):
    @app.callback(
        [
            Output("lsoa-choropleth-map", "figure"),
            Output("top-10-lsoa-bar", "figure")
        ],
        [
            Input("lsoa-year-dropdown", "value"),
            Input("lsoa-crime-dropdown", "value"),
            Input("theme-toggle-switch", "value")
        ]
    )
    def update_map_and_bar(selected_year, selected_crime_type, is_light_mode):
        logging.info(
            f"Callback triggered with year: {selected_year}, "
            f"crime type: {selected_crime_type}, is_light_mode: {is_light_mode}"
        )

        if not selected_year or not selected_crime_type:
            logging.info("⚠️ Missing selection(s); returning empty figures.")
            return go.Figure(), go.Figure()

        # 1. Filter the crime_data
        df_filtered = crime_data[
            (crime_data["crime_type"] == selected_crime_type)
            & (crime_data["month"].dt.year == int(selected_year))
        ]
        logging.info(f"Filtered crime data: {len(df_filtered)} rows.")
        if df_filtered.empty:
            logging.warning("No crime data found for the given selection.")
            return go.Figure(), go.Figure()

        # 2. Aggregate by LSOA
        grouped = df_filtered.groupby("lsoa_id").size().reset_index(name="crime_count")
        if DEBUG:
            logging.debug(f"Grouped data sample:\n{grouped.head()}")

        # 3. Merge with lsoa_lookup
        merged = pd.merge(grouped, lsoa_lookup, on="lsoa_id", how="left")
        if DEBUG:
            logging.debug(f"Merged data sample:\n{merged.head()}")
            logging.debug(f"Merged DataFrame columns: {merged.columns.tolist()}")

        # 4. Filter GeoJSON
        lsoa_codes = merged["lsoa_code"].dropna().unique().tolist()
        filtered_geojson = {
            "type": "FeatureCollection",
            "features": [
                feat for feat in lsoa_geojson["features"]
                if feat["properties"].get("LSOA21CD") in lsoa_codes
            ]
        }
        logging.info(f"Filtered GeoJSON has {len(filtered_geojson.get('features', []))} features.")
        if filtered_geojson["features"]:
            logging.debug(f"Sample filtered GeoJSON feature: {json.dumps(filtered_geojson['features'][0], indent=2)}")
        else:
            logging.warning("Filtered GeoJSON is empty.")

        # 5. Build the choropleth with a street-level map:
        #    - "open-street-map" requires no token, but offers tile-based street-level info.
        #    - Increase the zoom level or set center to your area of interest.
        try:
            fig_map = px.choropleth_mapbox(
                merged,
                geojson=filtered_geojson,
                locations="lsoa_code",
                color="crime_count",
                featureidkey="properties.LSOA21CD",
                hover_name="lsoa_name",
                mapbox_style="open-street-map",  # Street-level tile layer
                zoom=10,                         # Adjust zoom for street-level detail
                center={"lat": 51.5074, "lon": -0.1278},  # Example center (London)
                opacity=0.6,
                color_continuous_scale="YlOrRd"
            )
            fig_map.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                margin={"l":0, "r":0, "t":0, "b":0},
                coloraxis_showscale=False
            )
            logging.info("Choropleth map (street-level) created successfully.")
        except Exception as e:
            logging.error(f"Error creating street-level choropleth map: {e}")
            fig_map = go.Figure()

        # 6. Create top-10 LSOA bar chart
        try:
            top10 = merged.nlargest(10, "crime_count")
            font_color = "#000000" if is_light_mode else "#FFFFFF"
            axis_color = font_color
            gridcolor = "rgba(0,0,0,0.2)" if is_light_mode else "rgba(255,255,255,0.2)"

            fig_bar = px.bar(
                top10,
                x="lsoa_name",
                y="crime_count",
                title="Top 10 LSOAs by Crime Count",
                hover_data=["lsoa_code"],
                color_discrete_sequence=["#FF4B4B"]
            )
            fig_bar.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font_color=font_color,
                title_font_color=font_color,
                xaxis=dict(
                    title="LSOA Name",
                    color=axis_color,
                    linecolor=axis_color,
                    tickcolor=axis_color,
                    gridcolor=gridcolor
                ),
                yaxis=dict(
                    title="Crime Count",
                    color=axis_color,
                    linecolor=axis_color,
                    tickcolor=axis_color,
                    gridcolor=gridcolor
                ),
                hoverlabel=dict(
                    bgcolor="rgba(0,0,0,0.7)",
                    font_color="white"
                )
            )
            logging.info("Top 10 LSOA bar chart created successfully.")
        except Exception as e:
            logging.error(f"Error creating top 10 LSOA bar chart: {e}")
            fig_bar = go.Figure()

        return fig_map, fig_bar
