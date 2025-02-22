import dash
import dash_bootstrap_components as dbc
from dash import dcc, html, Input, Output
from cache_config import cache  # Import caching configuration
from data_loader import reset_cache  # Import function to clear Memurai cache
from pages import dashboard, comparison, feedback  # Import pages

# Initialize the Dash app
external_stylesheets = [dbc.themes.DARKLY]
app = dash.Dash(__name__, external_stylesheets=external_stylesheets, suppress_callback_exceptions=True)
app.title = "UK Crime Data Dashboard"
server = app.server

# Initialize the cache (Memurai)
cache.init_app(server)

# Define app layout
app.layout = html.Div(
    id="theme-container",
    className="dark-theme",
    children=[
        dcc.Location(id="url", refresh=False),
        
        # Navigation Bar
        html.Div(
            className="navbar",
            children=[
                html.Div(
                    className="nav-links",
                    children=[
                        dcc.Link("Dashboard", href="/dashboard", className="nav-link"),
                        dcc.Link("Comparison", href="/comparison", className="nav-link"),
                        dcc.Link("Models", href="/feedback", className="nav-link"),
                    ]
                ),
                html.Div(
                    className="nav-toggles",
                    children=[
                        dbc.Switch(
                            id="theme-toggle-switch",
                            label="Light Theme",
                            value=False,  # Default: Dark theme
                            className="ms-3 me-2"
                        ),
                        dbc.Switch(
                            id="heatmap-mode-switch",
                            label="Live Viewing",
                            value=False,
                            className="ms-3 me-2"
                        )
                    ]
                )
            ]
        ),
        
        # Reset Cache Button
        html.Div(
            className="cache-reset-container",
            children=[
                html.Button("Reset Cache", id="reset-cache-btn", n_clicks=0, className="reset-button"),
                html.Div(id="cache-status", className="cache-status-text")
            ],
            style={"textAlign": "center", "marginTop": "20px"}
        ),

        # Main Page Content
        html.Div(
            id="page-content",
            style={"padding": "10px"}
        )
    ]
)

# Callback to update the theme
@app.callback(
    Output("theme-container", "className"),
    [Input("theme-toggle-switch", "value")]
)
def update_theme(is_light_mode):
    return "light-theme" if is_light_mode else "dark-theme"

# Callback to switch between pages
@app.callback(
    Output("page-content", "children"),
    [Input("url", "pathname")]
)
def render_page_content(pathname):
    if pathname in ["/", "/dashboard"]:
        return dashboard.layout()
    elif pathname == "/comparison":
        return comparison.layout()
    elif pathname == "/feedback":
        return feedback.layout()
    return dashboard.layout()

# Callback to reset Memurai cache when button is clicked
@app.callback(
    Output("cache-status", "children"),
    [Input("reset-cache-btn", "n_clicks")]
)
def clear_cache(n_clicks):
    if n_clicks > 0:
        reset_cache()  # Call the function to reset cache
        return "✅ Cache Cleared! Reloading data on next request."
    return "Click to clear cache"

# Register callbacks for each page
dashboard.register_callbacks(app)
comparison.register_callbacks(app)
feedback.register_callbacks(app)

# Run the app
if __name__ == "__main__":
    app.run_server(debug=True)
