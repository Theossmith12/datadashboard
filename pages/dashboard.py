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

from data_loader import load_data, load_lsoa_lookup
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
    Main layout for the dashboard page.
    """
    crime_data = load_data()

    outcome_options = [{'label': i, 'value': i} for i in crime_data['outcome_type'].dropna().unique()]
    crime_type_options = [{'label': i, 'value': i} for i in crime_data['crime_type'].dropna().unique()]

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
            min_date_allowed=crime_data['month'].min().date() if not crime_data.empty else None,
            max_date_allowed=crime_data['month'].max().date() if not crime_data.empty else None,
            start_date=crime_data['month'].min().date() if not crime_data.empty else None,
            end_date=crime_data['month'].max().date() if not crime_data.empty else None,
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
        is_open=True
    )

    header_section = html.Div(
        [
            html.H1("UK Crime Data Dashboard", style={'textAlign': 'center', 'marginBottom': '10px'}),
            html.P(
                "Explore interactive visualizations of street-level crime data across the UK. "
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
                    xs=12, sm=12, md=12, lg=6
                ),
                dbc.Col(
                    dcc.Loading(
                        html.Div([
                            html.Div(id="borough-title", className="borough-title"),
                            dcc.Graph(id="relative-crime-distribution", config={"displayModeBar": False},
                                    style={"height": "460px"})
                        ]),
                        type="circle"
                    ),
                    xs=12, sm=12, md=12, lg=6
                )
            ], className="my-3 mb-5"),

            # Row 2: Heatmap with embedded controls
            html.H3("Geographic Crime Distribution", className="section-title mt-5 mb-3", 
                    style={"borderBottom": "2px solid #1E90FF", "paddingBottom": "10px"}),
            html.P("Visualize crime density across London. Darker areas indicate higher concentration of criminal activity.", 
                className="text-muted mb-3"),
            # Heatmap controls
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
                        dcc.Graph(id="crime-heatmap", config={"displayModeBar": False, "scrollZoom": True}),
                        type="circle"
                    ),
                    width=12
                )
            ], className="mb-5"),

            # Row 3: Time Series & Outcome Bar
            html.H3("Temporal Patterns and Outcomes", className="section-title mt-5 mb-3", 
                    style={"borderBottom": "2px solid #1E90FF", "paddingBottom": "10px"}),
            html.P("Analyze how crime rates change over time and the distribution of case outcomes.", 
                className="text-muted mb-3"),
            dbc.Row([
                dbc.Col(
                    dcc.Loading(
                        dcc.Graph(id="time-series-plot", config={"displayModeBar": False}),
                        type="circle"
                    ),
                    xs=12, sm=12, md=6, lg=6
                ),
                dbc.Col(
                    dcc.Loading(
                        dcc.Graph(id="outcome-bar-chart", config={"displayModeBar": False}),
                        type="circle"
                    ),
                    xs=12, sm=12, md=6, lg=6
                )
            ], className="mb-5"),

            # Row 4: Crime-Type Bar & Yearly Comparison
            html.H3("Crime Types and Yearly Trends", className="section-title mt-5 mb-3", 
                    style={"borderBottom": "2px solid #1E90FF", "paddingBottom": "10px"}),
            html.P("Explore the distribution of crime types and how they've changed over the years.", 
                className="text-muted mb-3"),
            dbc.Row([
                dbc.Col(
                    dcc.Loading(
                        dcc.Graph(id="crime-type-bar-chart", config={"displayModeBar": False}),
                        type="circle"
                    ),
                    xs=12, sm=12, md=6, lg=6
                ),
                dbc.Col(
                    dcc.Loading(
                        dcc.Graph(id="yearly-comparison-chart", config={"displayModeBar": False}),
                        type="circle"
                    ),
                    xs=12, sm=12, md=6, lg=6
                )
            ], className="mb-5"),

            # Summary Statistics
            html.H3("Key Findings", className="section-title mt-5 mb-3", 
                    style={"borderBottom": "2px solid #1E90FF", "paddingBottom": "10px"}),
            html.P("Summary of the current data selection and key statistics.", 
                className="text-muted mb-3"),
            dbc.Row([
                dbc.Col(html.Div(id="summary-statistics", className="summary"), width=12)
            ], className="mb-4"),
            
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
        children=[header_section, filters_container, scroll_container]
    )


# ---------------------------------------------------------------------------------
# Figures & Charts
# ---------------------------------------------------------------------------------
def generate_borough_map(filtered_data, is_light_mode, show_labels=True):
    """
    Generate a choropleth map with distinct shaded segments and labels for each borough.
    """
    if filtered_data.empty:
        return go.Figure(), None

    df = filtered_data.copy()

    # Determine which column to use for borough grouping
    if 'lad_name' in df.columns:
        logger.info("Using 'lad_name' as borough field")
        borough_field = 'lad_name'
    elif 'borough' in df.columns:
        logger.info("Using 'borough' as borough field")
        borough_field = 'borough'
    else:
        if 'lsoa_name' in df.columns:
            df['borough'] = df['lsoa_name'].str.split().str[0]
            borough_field = 'borough'
            logger.info("Extracted borough from 'lsoa_name'")
        else:
            df['borough'] = df['lsoa_code'].str[:3]
            borough_field = 'borough'
            logger.info("Using first 3 chars of LSOA code as borough")

    # Aggregate crime counts by borough
    borough_data = df.groupby(borough_field, observed=True).agg(
        crime_count=('lsoa_code', 'size')
    ).reset_index()
    logger.info(f"Borough data: {borough_data.head().to_dict()}")

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
        fig.add_trace(go.Choroplethmapbox(
            geojson=borough_geojson,
            locations=borough_data[borough_field],
            z=borough_data['crime_count'],
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
            colorbar_title="Crime Count",
            featureidkey="properties.name",
            hovertemplate="<b>%{location}</b><br>Crime Count: %{z}<extra></extra>",
            customdata=borough_data[borough_field],
            name=''
        ))

        # Optional: show borough labels
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
                        size=10,
                        color='black',
                        family="Arial, sans-serif",
                    ),
                    hoverinfo='none',
                    showlegend=False
                ))

        fig.update_layout(
            mapbox=dict(
                style="open-street-map",
                zoom=9.5,
                center={"lat": 51.5074, "lon": -0.1278}
            ),
            margin={"r": 0, "t": 40, "l": 0, "b": 0},
            title=dict(
                text="London Borough Crime Distribution - Click to view relative crime patterns",
                font=dict(size=16)
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
        crime_counts_by_borough = df.groupby([borough_field, 'crime_type'], observed=True).size().reset_index(name='count')
        total_crimes_by_borough = df.groupby(borough_field, observed=True).size().reset_index(name='total_crimes')
        total_crimes_by_type = df.groupby('crime_type', observed=True).size().reset_index(name='total_type_crimes')
        total_crimes = len(df)

        for b_name in df[borough_field].unique():
            borough_total = total_crimes_by_borough.loc[
                total_crimes_by_borough[borough_field] == b_name, 'total_crimes'
            ].values[0]
            sub_df = crime_counts_by_borough[crime_counts_by_borough[borough_field] == b_name].copy()

            if not sub_df.empty:
                results = []
                for _, row in sub_df.iterrows():
                    crime_type = row['crime_type']
                    count_val = row['count']
                    total_for_type = total_crimes_by_type.loc[
                        total_crimes_by_type['crime_type'] == crime_type, 'total_type_crimes'
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


def generate_relative_crime_distribution(borough_crime_data, borough_name, is_light_mode):
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
            font=dict(size=16)
        )
        fig = update_fig_layout(fig, is_light_mode)
        return fig

    crime_data = borough_crime_data[borough_name]
    sorted_data = sorted(crime_data, key=lambda x: x['relative_frequency'], reverse=True)

    # Show top 5 and bottom 5
    top_5 = sorted_data[:5]
    bottom_5 = sorted_data[-5:] if len(sorted_data) > 5 else []
    display_data = top_5 + bottom_5

    crime_types = [item['crime_type'] for item in display_data]
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
    fig.update_layout(
        title=f"Crimes Relative to London Average in {borough_name}",
        xaxis_title="Relative Frequency (1.0 = Average)",
        yaxis_title="Crime Type",
        height=460,
        xaxis=dict(
            zeroline=False,
            gridcolor='lightgray',
            tickformat='.1f',
            ticksuffix='x'
        ),
        yaxis=dict(autorange="reversed")
    )
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
    return fig


def generate_static_heatmap(filtered_data, is_light_mode):
    """Generate a static density heatmap of crimes."""
    if filtered_data.empty:
        return go.Figure()

    df = filtered_data.copy()
    df["density_val"] = 1
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
    return fig


def generate_animated_heatmap(filtered_data, is_light_mode):
    """Generate an animated density heatmap by month."""
    if filtered_data.empty:
        return go.Figure()

    df = filtered_data.copy()
    if not pd.api.types.is_datetime64_any_dtype(df["month"]):
        df["month"] = pd.to_datetime(df["month"])
    df["month_str"] = df["month"].dt.strftime("%Y-%m")
    df["density_val"] = 1

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
    fig.update_layout(transition={"duration": 500})
    fig = update_fig_layout(fig, is_light_mode)
    fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})
    return fig


def generate_time_series(filtered_data, is_light_mode):
    """Generate a line chart of total crimes over time."""
    if filtered_data.empty:
        return go.Figure()

    grouped = filtered_data.groupby("month", observed=True).size().reset_index(name="Count")
    grouped.sort_values("month", inplace=True)

    fig = px.line(grouped, x="month", y="Count", title="Crime Over Time")
    fig = update_fig_layout(fig, is_light_mode)
    fig.update_layout(margin={"r": 0, "t": 40, "l": 0, "b": 0})
    return fig


def generate_outcome_bar_chart(filtered_data, is_light_mode):
    """Generate a bar chart showing the counts of each outcome type."""
    if filtered_data.empty:
        return go.Figure()

    grouped = filtered_data.groupby("outcome_type", observed=True).size().reset_index(name="Count")
    fig = px.bar(
        grouped,
        x="outcome_type",
        y="Count",
        title="Outcome Types",
        labels={"outcome_type": "Outcome", "Count": "Number of Crimes"}
    )
    fig = update_fig_layout(fig, is_light_mode)
    fig.update_layout(xaxis_tickangle=-45)
    return fig


def generate_crime_type_bar_chart(filtered_data, is_light_mode):
    """Generate a bar chart showing distribution of crime types."""
    if filtered_data.empty:
        return go.Figure()

    grouped = filtered_data.groupby("crime_type", observed=True).size().reset_index(name="Count")
    fig = px.bar(
        grouped,
        x="crime_type",
        y="Count",
        title="Crime Type Distribution",
        labels={"crime_type": "Crime Type", "Count": "Number of Crimes"}
    )
    fig = update_fig_layout(fig, is_light_mode)
    fig.update_layout(xaxis_tickangle=-45)
    return fig


def generate_yearly_comparison_chart(filtered_data, is_light_mode):
    """Generate a bar chart comparing crime types across different years."""
    if filtered_data.empty or "month" not in filtered_data.columns:
        return go.Figure()

    df = filtered_data.copy()
    df["year"] = df["month"].dt.year
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
    return fig

# ---------------------------------------------------------------------------------
# Main Dashboard Callback
# ---------------------------------------------------------------------------------
@dash.callback(
    [
        Output("borough-map", "figure"),
        Output("relative-crime-distribution", "figure"),
        Output("borough-title", "children"),
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
        Input("show-borough-labels", "value")
    ],
    [
        State("borough-map", "relayoutData"),
        State("theme-container", "data-theme")  # Using as State to avoid excessive triggers
    ]
)
def update_dashboard(outcomes, crimes, start_date, end_date, heatmap_switch,
                     click_data, show_labels, relayout_data, data_theme):
    """
    Main callback for updating the dashboard components.
    'data-theme' attribute determines whether we're in light or dark mode.
    """
    # Log which input changed
    ctx = dash.callback_context
    if ctx.triggered:
        logger.info(f"Main callback triggered by: {ctx.triggered[0]['prop_id']}")
    else:
        logger.info("Main callback triggered without a specific input change.")

    # interpret data_theme
    is_light_mode = (data_theme == 'light')
    logger.info(f"is_light_mode={is_light_mode}")

    # Log the states of key inputs
    logger.info(f"Current filter states -> Outcomes: {outcomes}, Crimes: {crimes}, "
                f"Date Range: {start_date} to {end_date}, Heatmap Switch: {heatmap_switch}, "
                f"Show Labels: {show_labels}, clickData: {click_data}")

    # Load and filter data
    crime_data = load_data()
    df = crime_data[
        crime_data["outcome_type"].isin(outcomes) &
        crime_data["crime_type"].isin(crimes)
    ]
    if start_date and end_date:
        sdate = pd.to_datetime(start_date)
        edate = pd.to_datetime(end_date)
        df = df[(df["month"] >= sdate) & (df["month"] <= edate)]
    df = df.sort_values("month")
    logger.info(f"Dashboard update: {len(df)} records after filtering.")

    # Create borough map + borough_crime_data
    borough_map_fig, borough_crime_data = generate_borough_map(df, is_light_mode, show_labels)

    selected_borough = None
    borough_title = html.H4("Click on a borough to see relative crime distribution", className="text-center")

    # Process clickData to find which borough was clicked
    if click_data and isinstance(click_data, dict) and "points" in click_data:
        try:
            points = click_data["points"][0]
            curve_number = points.get("curveNumber", -1)

            # Log the points data
            logger.info(f"Click event details: {points}")

            # If user clicked the main choropleth trace
            if curve_number == 0:
                if "location" in points:
                    selected_borough = points["location"]
                    logger.info(f"Found borough in location: {selected_borough}")
                elif "customdata" in points:
                    selected_borough = points["customdata"]
                    logger.info(f"Found borough in customdata: {selected_borough}")
                else:
                    logger.warning("Choropleth trace clicked, but no 'location' or 'customdata' found.")

            # If user clicked the label text trace
            elif curve_number == 1:
                if "text" in points:
                    selected_borough = points["text"]
                    logger.info(f"Found borough in text (label trace): {selected_borough}")
                else:
                    logger.warning("Label trace clicked, but no 'text' found.")

            # If there's another trace or something unexpected
            else:
                logger.warning(f"Unknown curveNumber clicked: {curve_number}. Points: {points}")

            if selected_borough and borough_crime_data:
                # Confirm that selected_borough is actually in the data
                all_boroughs = list(borough_crime_data.keys())
                logger.info(f"Boroughs in the data: {all_boroughs}")
                if selected_borough in all_boroughs:
                    borough_title = html.H4(f"Crime Pattern Analysis: {selected_borough}", className="text-center")
                else:
                    logger.warning(f"Selected borough '{selected_borough}' not found in borough_crime_data.")
                    selected_borough = None

        except (KeyError, IndexError) as e:
            logger.error(f"Error processing clickData: {e}")
            selected_borough = None
            borough_title = html.H4("Error processing borough selection", className="text-center")

    # Generate the relative crime distribution figure
    crime_distribution_fig = generate_relative_crime_distribution(borough_crime_data, selected_borough, is_light_mode)

    # Heatmap (animated or static)
    if heatmap_switch:
        heatmap_fig = generate_animated_heatmap(df, is_light_mode)
    else:
        heatmap_fig = generate_static_heatmap(df, is_light_mode)

    ts_fig = generate_time_series(df, is_light_mode)
    outcome_bar_fig = generate_outcome_bar_chart(df, is_light_mode)
    crime_type_bar_fig = generate_crime_type_bar_chart(df, is_light_mode)
    yearly_comp_fig = generate_yearly_comparison_chart(df, is_light_mode)

    # Summary Statistics
    total = len(df)
    if total > 0:
        common_crime = df["crime_type"].value_counts().idxmax()
        common_outcome = df["outcome_type"].value_counts().idxmax()
        date_min = df["month"].min().date()
        date_max = df["month"].max().date()
    else:
        common_crime = "N/A"
        common_outcome = "N/A"
        date_min = "N/A"
        date_max = "N/A"

    summary = html.Div([
        html.H2("Summary Statistics"),
        html.Ul([
            html.Li(f"Total number of crimes: {total}"),
            html.Li(f"Most common crime type: {common_crime}"),
            html.Li(f"Most common outcome type: {common_outcome}"),
            html.Li(f"Data covers from {date_min} to {date_max}")
        ])
    ], className="summary")

    return (
        borough_map_fig,
        crime_distribution_fig,
        borough_title,
        heatmap_fig,
        ts_fig,
        outcome_bar_fig,
        crime_type_bar_fig,
        yearly_comp_fig,
        summary
    )


# ---------------------------------------------------------------------------------
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
