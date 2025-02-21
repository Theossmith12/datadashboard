import logging
import dash_bootstrap_components as dbc
from dash import dcc, html
from dash.dependencies import Input, Output, State
import plotly.express as px
import plotly.graph_objs as go
import json
import pandas as pd
import os

from data_loader import crime_data, lsoa_lookup
from dotenv import load_dotenv

load_dotenv()

# Set logging to DEBUG level so we can troubleshoot easily.
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')

# If you have a Mapbox token, load it; otherwise open-street-map style.
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

MAP_CENTER_LON = -0.1278  # Used as the default map center (London)

def layout():
    """
    We display a two-row layout:
      - First row: The map (8 columns) and the demographic bar chart (4 columns).
      - Second row: The top-10 bar chart.
    """

    header = html.Div([
        html.H1("UK Crime Data Comparison", style={"textAlign": "center"}),
        html.P(
            "Explore aggregated LSOA crime data across the UK. "
            "Use the filters below to select a crime type and view data for a specific year or for all years. "
            "Hover over a map location to see a demographic breakdown on the right.",
            style={"textAlign": "center"}
        )
    ], className="page-header", style={"marginBottom": "30px"})

    # Prepare Year & Crime Type dropdown options
    available_years = sorted(crime_data["year"].dropna().unique())
    year_options = [{"label": "All Years", "value": "all"}] + [
        {"label": str(y), "value": str(y)} for y in available_years
    ]
    crime_type_options = [
        {"label": ct, "value": ct}
        for ct in crime_data["crime_type"].dropna().unique()
    ]

    return dbc.Container(
        fluid=True,
        children=[
            header,
            dbc.Row([
                dbc.Col([
                    html.Label("Select Year"),
                    dcc.Dropdown(
                        id="lsoa-year-dropdown",
                        options=year_options,
                        value="all",  # default: all years
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

            # Row for the map + demographic bar chart
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

            # Row for top-10 LSOA bar
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
            ], className="my-2"),

            # Hidden store for aggregated data
            dcc.Store(id="aggregated-data")
        ]
    )

def register_callbacks(app):
    """Register all callbacks for the Comparison page."""

    @app.callback(
        [
            Output("lsoa-choropleth-map", "figure"),
            Output("top-10-lsoa-bar", "figure"),
            Output("aggregated-data", "data")
        ],
        [
            Input("lsoa-year-dropdown", "value"),
            Input("lsoa-crime-dropdown", "value"),
            Input("theme-toggle-switch", "value")
        ]
    )
    def update_map_and_bar(selected_year, selected_crime_type, is_light_mode):
        logging.debug("update_map_and_bar triggered:")
        logging.debug(f"  selected_year={selected_year}, selected_crime_type={selected_crime_type}, is_light_mode={is_light_mode}")

        # If user didn't select a crime type, return empty figs
        if not selected_crime_type:
            logging.debug("No crime type selected. Returning empty.")
            return go.Figure(), go.Figure(), None

        # Filter the DataFrame based on year & crime type
        if str(selected_year).lower() == "all":
            df_filtered = crime_data[crime_data["crime_type"] == selected_crime_type]
        else:
            df_filtered = crime_data[
                (crime_data["year"] == int(selected_year)) &
                (crime_data["crime_type"] == selected_crime_type)
            ]
        logging.debug(f"Filtered rows: {len(df_filtered)}")

        if df_filtered.empty:
            logging.debug("No data after filtering => returning empty.")
            return go.Figure(), go.Figure(), None

        # Group/aggregate by LSOA
        grouped = df_filtered.groupby("lsoa_code").agg(
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
        logging.debug(f"Grouped sample:\n{grouped.head()}")

        # Merge with LSOA lookup for lsoa_name
        merged = pd.merge(grouped, lsoa_lookup, on="lsoa_code", how="left")
        logging.debug(f"Merged sample:\n{merged.head()}")

        # Build the map figure
        lsoa_codes = merged["lsoa_code"].dropna().unique().tolist()
        filtered_geojson = {
            "type": "FeatureCollection",
            "features": [
                feat for feat in lsoa_geojson["features"]
                if feat["properties"].get("LSOA21CD") in lsoa_codes
            ]
        }
        logging.debug(f"Filtered GeoJSON => {len(filtered_geojson.get('features', []))} features")

        try:
            fig_map = px.choropleth_mapbox(
                merged,
                geojson=filtered_geojson,
                locations="lsoa_code",
                color="crime_count",
                featureidkey="properties.LSOA21CD",
                hover_name="lsoa_name",
                hover_data={"crime_count": True},
                mapbox_style="open-street-map",
                zoom=10,
                center={"lat": 51.5074, "lon": MAP_CENTER_LON},
                opacity=0.6,
                color_continuous_scale="YlOrRd"
            )
            fig_map.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                margin={"l": 0, "r": 0, "t": 0, "b": 0},
                coloraxis_showscale=False
            )
            logging.debug("Map created successfully.")
        except Exception as ex:
            logging.error(f"Error creating map => {ex}")
            fig_map = go.Figure()

        # Build the top-10 bar chart
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
            logging.debug("Top-10 bar chart created successfully.")
        except Exception as ex:
            logging.error(f"Error creating top-10 bar => {ex}")
            fig_bar = go.Figure()

        # Return the map, top-10 bar, & aggregated data as a dict
        return fig_map, fig_bar, merged.to_dict('records')

    @app.callback(
        Output("demographic-bar", "figure"),
        [
            Input("lsoa-choropleth-map", "hoverData"),
            Input("theme-toggle-switch", "value")
        ],
        [State("aggregated-data", "data")]
    )
    def update_demo_bar(hoverData, is_light_mode, aggregated_data):
        """
        This callback updates the demographic bar chart in the second column.
        If user hovers over a valid LSOA => show a horizontal bar chart of age/gender distribution.
        Otherwise => show an empty figure or a small placeholder text.
        """
        logging.debug("update_demo_bar triggered.")
        logging.debug(f"  hoverData => {hoverData}, is_light_mode => {is_light_mode}")

        # If there's no hover or no data, just return an empty figure
        if not hoverData or not aggregated_data:
            logging.debug("No hoverData or aggregated_data => empty figure.")
            return go.Figure()

        # Attempt to extract the lsoa_code from hoverData
        points = hoverData.get("points", [])
        if not points:
            logging.debug("hoverData has no points => empty figure.")
            return go.Figure()

        point = points[0]
        lsoa_code = point.get("location")
        if not lsoa_code:
            logging.debug("No location in hover point => empty figure.")
            return go.Figure()

        # Look up the aggregated record for that LSOA
        df_agg = pd.DataFrame(aggregated_data)
        record_df = df_agg[df_agg["lsoa_code"] == lsoa_code]
        if record_df.empty:
            logging.debug("No matching record in aggregated data => empty figure.")
            return go.Figure()

        record = record_df.iloc[0]
        logging.debug(f"Matched LSOA record => {record}")
        # We'll display the lsoa_name in the chart title
        lsoa_name = record.get("lsoa_name", lsoa_code)

        # Build the demographic distribution as a bar chart
        demo_dict = {
            "Youth Male": record.get("youth_male_percent", 0),
            "Youth Female": record.get("youth_female_percent", 0),
            "Young Adult Male": record.get("young_adult_male_percent", 0),
            "Young Adult Female": record.get("young_adult_female_percent", 0),
            "Adult Male": record.get("adult_male_percent", 0),
            "Adult Female": record.get("adult_female_percent", 0),
            "Senior Male": record.get("senior_male_percent", 0),
            "Senior Female": record.get("senior_female_percent", 0)
        }
        demo_df = pd.DataFrame(list(demo_dict.items()), columns=["Group", "Percentage"])
        demo_df = demo_df.sort_values(by="Percentage", ascending=False)

        fig = px.bar(
            demo_df,
            x="Percentage",
            y="Group",
            orientation="h",
            text="Percentage"
        )
        fig.update_traces(
            texttemplate='%{text:.2f}%',
            textposition='outside',
            marker_color='lightskyblue'
        )
        font_color = "#000000" if is_light_mode else "#e0e0e0"
        fig.update_layout(
            title=f"Demographics for {lsoa_name}",
            title_font=dict(size=14, family='Poppins, sans-serif', color=font_color, weight='bold'),
            xaxis_title="Percentage",
            yaxis_title="Group",
            font=dict(size=12, family='Poppins, sans-serif', color=font_color),
            margin=dict(l=20, r=20, t=40, b=20),
            plot_bgcolor="#FFFFFF" if is_light_mode else "#121212",
            paper_bgcolor="#FFFFFF" if is_light_mode else "#121212"
        )
        fig.update_yaxes(autorange="reversed")

        return fig
