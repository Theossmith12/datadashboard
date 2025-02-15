import logging
import pandas as pd
import dash
import dash_bootstrap_components as dbc
from dash import dcc, html
from dash.dependencies import Input, Output, State
import plotly.express as px
import plotly.graph_objs as go
from plotly.subplots import make_subplots

from data_loader import crime_data  # The loaded data
# If you have constants from data_loader, you can also import them here.
MAX_POINTS = 10000

# ---------------------------
# Dashboard Layout
# ---------------------------
def layout():
    """
    Returns the layout (UI) for the Dashboard page.
    """

    # Prepare dropdown options
    outcome_options = [{'label': i, 'value': i} for i in crime_data['outcome_type'].dropna().unique()]
    crime_type_options = [{'label': i, 'value': i} for i in crime_data['crime_type'].dropna().unique()]

    outcome_dropdown = html.Div([
        html.Label("Select Outcome Type:", style={'textAlign': 'center'}),
        dcc.Dropdown(
            id="outcome-type-dropdown",
            options=outcome_options,
            value=[o['value'] for o in outcome_options],
            multi=True,
            className="filter-item"
        ),
        html.Div([
            dbc.Button("Show All", id="show-all-outcomes", color="secondary", size="sm", style={"margin-right": "5px"}),
            dbc.Button("Remove All", id="remove-all-outcomes", color="secondary", size="sm")
        ], style={"textAlign": "center", "marginTop": "5px"})
    ])

    crime_dropdown = html.Div([
        html.Label("Select Crime Type(s):", style={'textAlign': 'center'}),
        dcc.Dropdown(
            id="crime-type-dropdown",
            options=crime_type_options,
            value=[o['value'] for o in crime_type_options],
            multi=True,
            className="filter-item"
        ),
        html.Div([
            dbc.Button("Show All", id="show-all-crimes", color="secondary", size="sm", style={"margin-right": "5px"}),
            dbc.Button("Remove All", id="remove-all-crimes", color="secondary", size="sm")
        ], style={"textAlign": "center", "marginTop": "5px"})
    ])

    date_picker = html.Div([
        html.Label("Select Date Range:", style={'textAlign': 'center'}),
        dcc.DatePickerRange(
            id="date-picker-range",
            min_date_allowed=crime_data['month'].min().date() if not crime_data.empty else None,
            max_date_allowed=crime_data['month'].max().date() if not crime_data.empty else None,
            start_date=crime_data['month'].min().date() if not crime_data.empty else None,
            end_date=crime_data['month'].max().date() if not crime_data.empty else None,
            display_format="MMMM Y",
            className="date-picker-range filter-item",
            style={"width": "100%"}
        )
    ])

    filters_container = html.Div(
        [
            dbc.Col(outcome_dropdown, className="filter-item"),
            dbc.Col(crime_dropdown, className="filter-item"),
            dbc.Col(date_picker, className="filter-item")
        ],
        className="filters-container"
    )

    header_section = html.Div(
        [
            html.H1("UK Crime Data Dashboard", style={'textAlign': 'center', 'marginBottom': '10px'}),
            html.P(
                "Explore interactive visualizations of street-level crime data across the UK. "
                "Use the filters below to adjust outcome types, crime types, and date ranges.",
                style={'textAlign': 'center'}
            )
        ],
        style={'padding': '20px', 'borderRadius': '10px', 'marginBottom': '20px'}
    )

    return dbc.Container(
        fluid=True,
        children=[
            header_section,
            filters_container,
            dbc.Row([
                dbc.Col(
                    dcc.Loading(
                        dcc.Graph(id="crime-scatter-map", config={"displayModeBar": False}),
                        type="circle"
                    ),
                    xs=12, sm=12, md=12, lg=6
                ),
                dbc.Col(
                    dcc.Loading(
                        dcc.Graph(id="crime-heatmap", config={"displayModeBar": False, "scrollZoom": True}),
                        type="circle"
                    ),
                    xs=12, sm=12, md=12, lg=6
                )
            ], className="my-2"),
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
            ], className="my-2"),
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
            ], className="my-2"),
            dbc.Row([
                dbc.Col(html.Div(id="summary-statistics", className="summary"), width=12)
            ], className="my-2")
        ]
    )

# ---------------------------
# Dashboard Callbacks
# ---------------------------
def register_callbacks(app):
    """
    Register all callbacks needed for the Dashboard page.
    """

    # Show/Remove All in Dropdowns
    @app.callback(
        [
            Output("outcome-type-dropdown", "value"),
            Output("crime-type-dropdown", "value")
        ],
        [
            Input("show-all-outcomes", "n_clicks"),
            Input("remove-all-outcomes", "n_clicks"),
            Input("show-all-crimes", "n_clicks"),
            Input("remove-all-crimes", "n_clicks")
        ],
        [
            State("outcome-type-dropdown", "options"),
            State("crime-type-dropdown", "options")
        ]
    )
    def update_dropdowns(
        show_all_outcomes,
        remove_all_outcomes,
        show_all_crimes,
        remove_all_crimes,
        outcome_options,
        crime_options
    ):
        ctx = dash.callback_context
        if not ctx.triggered:
            raise dash.exceptions.PreventUpdate

        triggered_ids = [trigger['prop_id'].split('.')[0] for trigger in ctx.triggered]

        # Default: select all options for both dropdowns.
        outcome_value = [option['value'] for option in outcome_options]
        crime_value = [option['value'] for option in crime_options]

        if "remove-all-outcomes" in triggered_ids:
            outcome_value = []
        elif "show-all-outcomes" in triggered_ids:
            outcome_value = [option['value'] for option in outcome_options]

        if "remove-all-crimes" in triggered_ids:
            crime_value = []
        elif "show-all-crimes" in triggered_ids:
            crime_value = [option['value'] for option in crime_options]

        return outcome_value, crime_value

    # ---------------------------
    # Helper Visualization Functions
    # ---------------------------
    def _update_fig_layout(fig, is_light_mode):
        """Update figure layout colors based on theme."""
        if is_light_mode:
            fig.update_layout(
                paper_bgcolor="white",
                plot_bgcolor="white",
                font_color="black"
            )
        else:
            fig.update_layout(
                paper_bgcolor="#121212",
                plot_bgcolor="#121212",
                font_color="#e0e0e0"
            )
        return fig

    def generate_map(filtered_data, map_view, is_light_mode):
        if filtered_data.empty:
            logging.warning("No data for scatter map.")
            return go.Figure()

        center = {'lat': filtered_data['latitude'].mean(), 'lon': filtered_data['longitude'].mean()}
        zoom = 6
        if map_view:
            if 'mapbox.center' in map_view:
                center = map_view['mapbox.center']
            if 'mapbox.zoom' in map_view:
                zoom = map_view['mapbox.zoom']

        fig = px.scatter_mapbox(
            filtered_data,
            lat="latitude",
            lon="longitude",
            color="crime_type",
            hover_data=["outcome_type"],
            zoom=zoom,
            center=center,
            mapbox_style="open-street-map",
            height=500
        )
        fig = _update_fig_layout(fig, is_light_mode)
        fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})
        return fig

    def generate_static_heatmap(filtered_data, is_light_mode):
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
        fig = _update_fig_layout(fig, is_light_mode)
        fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})
        return fig

    def generate_animated_heatmap(filtered_data, is_light_mode):
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
        fig = _update_fig_layout(fig, is_light_mode)
        fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})
        return fig

    def generate_time_series(filtered_data, is_light_mode):
        if filtered_data.empty:
            return go.Figure()
        grouped = filtered_data.groupby("month").size().reset_index(name="Count")
        grouped.sort_values("month", inplace=True)
        fig = px.line(grouped, x="month", y="Count", title="Crime Over Time")
        fig = _update_fig_layout(fig, is_light_mode)
        fig.update_layout(margin={"r": 0, "t": 40, "l": 0, "b": 0})
        return fig

    def generate_outcome_bar_chart(filtered_data, is_light_mode):
        if filtered_data.empty:
            return go.Figure()
        grouped = filtered_data.groupby("outcome_type").size().reset_index(name="Count")
        fig = px.bar(
            grouped,
            x="outcome_type",
            y="Count",
            title="Outcome Types",
            labels={"outcome_type": "Outcome", "Count": "Number of Crimes"}
        )
        fig = _update_fig_layout(fig, is_light_mode)
        fig.update_layout(xaxis_tickangle=-45)
        return fig

    def generate_crime_type_bar_chart(filtered_data, is_light_mode):
        if filtered_data.empty:
            return go.Figure()
        grouped = filtered_data.groupby("crime_type").size().reset_index(name="Count")
        fig = px.bar(
            grouped,
            x="crime_type",
            y="Count",
            title="Crime Type Distribution",
            labels={"crime_type": "Crime Type", "Count": "Number of Crimes"}
        )
        fig = _update_fig_layout(fig, is_light_mode)
        fig.update_layout(xaxis_tickangle=-45)
        return fig

    def generate_yearly_comparison_chart(filtered_data, is_light_mode):
        if filtered_data.empty or "month" not in filtered_data.columns:
            return go.Figure()
        df = filtered_data.copy()
        df["year"] = df["month"].dt.year
        grouped = df.groupby(["year", "crime_type"]).size().reset_index(name="Count")
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
        fig = _update_fig_layout(fig, is_light_mode)
        return fig

    # ---------------------------
    # Main Dashboard Update Callback
    # ---------------------------
    @app.callback(
        [
            Output("crime-scatter-map", "figure"),
            Output("crime-heatmap", "figure"),
            Output("time-series-plot", "figure"),
            Output("outcome-bar-chart", "figure"),
            Output("crime-type-bar-chart", "figure"),
            Output("yearly-comparison-chart", "figure"),
            Output("summary-statistics", "children"),
        ],
        [
            Input("outcome-type-dropdown", "value"),
            Input("crime-type-dropdown", "value"),
            Input("date-picker-range", "start_date"),
            Input("date-picker-range", "end_date"),
            Input("heatmap-mode-switch", "value"),
            Input("theme-toggle-switch", "value")
        ],
        [State("crime-scatter-map", "relayoutData")]
    )
    def update_dashboard(outcomes, crimes, start_date, end_date, heatmap_switch, is_light_mode, relayout_data):
        df = crime_data[
            crime_data["outcome_type"].isin(outcomes) &
            crime_data["crime_type"].isin(crimes)
        ]
        if start_date and end_date:
            sdate = pd.to_datetime(start_date)
            edate = pd.to_datetime(end_date)
            df = df[(df["month"] >= sdate) & (df["month"] <= edate)]

        # Ensure data is in chronological order
        df = df.sort_values("month")

        logging.info(f"Dashboard update: {len(df)} records after filtering.")

        # Map data sample
        map_df = df if len(df) <= MAX_POINTS else df.sample(MAX_POINTS)

        map_view = {}
        if relayout_data:
            if "mapbox.center" in relayout_data:
                map_view["mapbox.center"] = relayout_data["mapbox.center"]
            if "mapbox.zoom" in relayout_data:
                map_view["mapbox.zoom"] = relayout_data["mapbox.zoom"]
        scatter_map = generate_map(map_df, map_view, is_light_mode)

        if heatmap_switch:
            heatmap_fig = generate_animated_heatmap(df, is_light_mode)
        else:
            heatmap_fig = generate_static_heatmap(df, is_light_mode)

        ts_fig = generate_time_series(df, is_light_mode)
        outcome_bar_fig = generate_outcome_bar_chart(df, is_light_mode)
        crime_type_bar_fig = generate_crime_type_bar_chart(df, is_light_mode)
        yearly_comp_fig = generate_yearly_comparison_chart(df, is_light_mode)

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
                html.Li(f"Data covers from {date_min} to {date_max}"),
            ])
        ], className="summary")

        return scatter_map, heatmap_fig, ts_fig, outcome_bar_fig, crime_type_bar_fig, yearly_comp_fig, summary
