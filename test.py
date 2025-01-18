import pandas as pd
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.express as px
from sqlalchemy import create_engine
import os

# Initialize Dash app
app = dash.Dash(__name__)
app.title = 'Dynamic Crime Heatmap with Zoom'

# -------------------------------
# Database Connection & Data Load
# -------------------------------
def load_data():
    try:
        # PostgreSQL connection setup
        DATABASE_URL = "postgresql+psycopg2://postgres:Fluminense99@localhost:5432/crime_data"
        engine = create_engine(DATABASE_URL)
        
        # Query the data
        query = "SELECT latitude, longitude FROM crime_records"
        data = pd.read_sql(query, engine)
        return data

    except Exception as e:
        print(f"Error loading data: {e}")
        return pd.DataFrame()

# Load the crime data once at startup
crime_data = load_data()

# Drop rows with missing coordinates to prevent errors
crime_data = crime_data.dropna(subset=['latitude', 'longitude'])

# -------------------------------
# Custom Colorscale for Heatmap
# -------------------------------
custom_colorscale = [
    [0, "yellow"],    # Low crime density
    [0.5, "orange"],  # Medium density
    [1, "red"]        # High density
]

# -------------------------------
# App Layout
# -------------------------------
app.layout = html.Div([
    html.H1("Dynamic Crime Density Heatmap", style={'textAlign': 'center', 'color': '#1E90FF'}),

    # Zoom Slider
    html.Div([
        html.Label("Adjust Zoom Level:", style={'color': '#e0e0e0'}),
        dcc.Slider(
            id='zoom-slider',
            min=5,
            max=15,
            step=0.5,
            value=10,  # Default zoom level
            marks={i: str(i) for i in range(5, 16)},
            tooltip={"placement": "bottom", "always_visible": True}
        )
    ], style={'padding': '20px', 'backgroundColor': '#1f1f1f'}),

    # Heatmap Graph
    dcc.Graph(
        id='density-map',
        config={
            'scrollZoom': True,  # Enable scroll zoom
            'displayModeBar': True,
            'modeBarButtonsToAdd': ['zoomIn2d', 'zoomOut2d', 'resetScale2d'],
            'displaylogo': False
        },
        style={'height': '80vh'}
    )
], style={'backgroundColor': '#121212', 'font-family': 'Segoe UI, Tahoma, Geneva, Verdana, sans-serif'})

# -------------------------------
# Callback to Update Heatmap
# -------------------------------
@app.callback(
    Output('density-map', 'figure'),
    [Input('density-map', 'relayoutData'),
     Input('zoom-slider', 'value')]
)
def update_heatmap(relayout_data, slider_zoom):
    """
    Updates the heatmap based on the current viewport and zoom slider.
    """
    # Default map center (London)
    default_center = {'lat': 51.5074, 'lon': -0.1278}
    zoom = slider_zoom

    # Capture user zoom and center after interaction
    if relayout_data and 'mapbox.center' in relayout_data and 'mapbox.zoom' in relayout_data:
        center = relayout_data['mapbox.center']
        zoom = relayout_data['mapbox.zoom']
    else:
        center = default_center

    # Calculate approximate bounding box based on center and zoom
    # Note: This is a simplified estimation. For precise bounding boxes, consider using geospatial libraries.
    lat_delta = 0.05 / zoom
    lon_delta = 0.05 / zoom

    bbox = {
        'min_lat': center['lat'] - lat_delta,
        'max_lat': center['lat'] + lat_delta,
        'min_lon': center['lon'] - lon_delta,
        'max_lon': center['lon'] + lon_delta
    }

    # Filter data within the bounding box
    filtered_df = crime_data[
        (crime_data['latitude'] >= bbox['min_lat']) &
        (crime_data['latitude'] <= bbox['max_lat']) &
        (crime_data['longitude'] >= bbox['min_lon']) &
        (crime_data['longitude'] <= bbox['max_lon'])
    ]

    # Define the number of bins for binning
    bins = 1000  # Adjust this number based on performance/memory

    if not filtered_df.empty:
        # Bin the data using pandas
        filtered_df['lat_bin'] = pd.cut(filtered_df['latitude'], bins=bins)
        filtered_df['lon_bin'] = pd.cut(filtered_df['longitude'], bins=bins)

        # Count the number of points in each bin
        density = filtered_df.groupby(['lat_bin', 'lon_bin']).size().reset_index(name='count')

        # Find the maximum density for color scaling
        max_density = density['count'].max()

        # To avoid setting max_density to zero
        if max_density == 0:
            max_density = 1
    else:
        max_density = 1  # Prevent division by zero

    # Create density heatmap
    fig = px.density_mapbox(
        filtered_df,
        lat='latitude',
        lon='longitude',
        z=None,  # Counts of points
        radius=10,  # Controls smoothing
        center=center,
        zoom=zoom,
        mapbox_style="open-street-map",
        color_continuous_scale=custom_colorscale,
        opacity=0.6
    )

    # Update layout with dynamic color scaling
    fig.update_layout(
        coloraxis=dict(
            cmin=0,
            cmax=max_density
        ),
        margin={"r":0,"t":0,"l":0,"b":0},
        coloraxis_colorbar=dict(
            title="Crime Density",
            titleside="right",
            tickmode="array",
            tickvals=[0, max_density/2, max_density],
            ticktext=["Low", "Medium", "High"],
            lenmode="pixels",
            len=300,
            bgcolor='#1f1f1f',
            ticks="outside",
            tickfont=dict(color="#e0e0e0")
        ),
        paper_bgcolor='#121212',
        plot_bgcolor='#121212',
        font_color='white',
        hoverlabel=dict(
            bgcolor="white",
            font_size=12,
            font_family="Poppins"
        )
    )

    return fig

# -------------------------------
# Run the App
# -------------------------------
if __name__ == '__main__':
    app.run_server(debug=True, host="127.0.0.1", port=8050)
