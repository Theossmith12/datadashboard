import dash
import dash_bootstrap_components as dbc
from dash import dcc, html
from dash.dependencies import Input, Output

# Import your pages
from pages import dashboard, comparison, feedback

external_stylesheets = [dbc.themes.DARKLY]
app = dash.Dash(__name__, external_stylesheets=external_stylesheets, suppress_callback_exceptions=True)
app.title = "UK Crime Data Dashboard"
server = app.server

app.layout = html.Div(
    id="theme-container",             # This container's class will toggle between dark-theme and light-theme.
    className="dark-theme",           # Default to dark-theme.
    children=[
        dcc.Location(id="url", refresh=False),
        
        # Custom Navbar with left nav-links and right toggles.
        html.Div(
            className="navbar",
            children=[
                # Left container for navigation links
                html.Div(
                    className="nav-links",
                    children=[
                        dcc.Link("Dashboard", href="/dashboard", className="nav-link"),
                        dcc.Link("Comparison", href="/comparison", className="nav-link"),
                        dcc.Link("Models", href="/feedback", className="nav-link"),
                    ]
                ),
                # Right container for toggles
                html.Div(
                    className="nav-toggles",
                    children=[
                        dbc.Switch(
                            id="theme-toggle-switch",
                            label="Light Theme",
                            value=False,  # false = dark theme by default
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
        
        html.Div(
            id="page-content",
            style={"padding": "10px"}
        )
    ]
)

# ----------------------------
# Theme Toggling Callback
# ----------------------------
@app.callback(
    Output("theme-container", "className"),
    [Input("theme-toggle-switch", "value")]
)
def update_theme(is_light_mode):
    return "light-theme" if is_light_mode else "dark-theme"

# ----------------------------
# Routing Callback
# ----------------------------
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

# ----------------------------
# Register Page Callbacks
# ----------------------------
dashboard.register_callbacks(app)
comparison.register_callbacks(app)
feedback.register_callbacks(app)

if __name__ == "__main__":
    app.run_server(debug=True)
