import dash
import dash_bootstrap_components as dbc
from dash import dcc, html, Input, Output, State
from cache_config import cache
from data_loader import reset_cache
from dash.dependencies import ClientsideFunction
# Import your page modules
from pages import dashboard, comparison, feedback

external_stylesheets = [dbc.themes.DARKLY]
app = dash.Dash(__name__, external_stylesheets=external_stylesheets, suppress_callback_exceptions=True)
app.title = "UK Crime Data Dashboard"
server = app.server

# Initialize Memurai/Redis cache
cache.init_app(server)

app.layout = html.Div(
    id="theme-container",
    className="dark-theme",  # start in dark theme
    **{'data-theme': 'dark'},  # Add this attribute for clientside callback
    children=[
        dcc.Location(id="url", refresh=False),
        
        # Navigation Bar
        html.Div(
            className="navbar",
            children=[
                html.Div(
                    className="nav-links",
                    children=[
                        dcc.Link("Dashboard", href="/dashboard", className="nav-link", id="nav-dashboard"),
                        dcc.Link("Comparison", href="/comparison", className="nav-link", id="nav-comparison"),
                        dcc.Link("Models", href="/feedback", className="nav-link", id="nav-feedback"),
                    ]
                ),
                html.Div(
                    className="nav-toggles",
                    children=[
                        # Live Viewing switch for heatmap animations
                        dbc.Switch(
                            id="heatmap-mode-switch",
                            label="Live Viewing",
                            value=False,
                            className="toggle-switch"  # for consistent styling
                        ),
                        # Dark/Light theme toggle via button + icon
                        html.Button(
                            [html.Img(id="theme-toggle-icon", src="/assets/dark-mode-toggle-icon.png", className="toggle-icon")],
                            id="theme-toggle-btn",
                            n_clicks=0,
                            className="theme-toggle-btn"
                        ),
                        # Reset Cache
                        dbc.Button(
                            "Reset Cache",
                            id="reset-cache-btn",
                            color="secondary",
                            size="sm",
                            className="reset-button ms-2"
                        )
                    ],
                    style={"display": "flex", "alignItems": "center", "gap": "15px"}
                )
            ]
        ),

        # Main Page Content
        html.Div(id="page-content", style={"padding": "10px"})
    ]
)

# Routing for multi-page
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

# Callback: Reset Cache
@app.callback(
    Output("reset-cache-btn", "children"),
    [Input("reset-cache-btn", "n_clicks")]
)
def clear_cache(n_clicks):
    if n_clicks and n_clicks > 0:
        reset_cache()
        return "✅ Cache Cleared!"
    return "Reset Cache"

# Callback: Highlight active navbar link
@app.callback(
    [Output("nav-dashboard", "className"),
     Output("nav-comparison", "className"),
     Output("nav-feedback", "className")],
    [Input("url", "pathname")]
)
def update_navbar(pathname):
    dashboard_class = "nav-link active" if pathname in ["/", "/dashboard"] else "nav-link"
    comparison_class = "nav-link active" if pathname == "/comparison" else "nav-link"
    feedback_class = "nav-link active" if pathname == "/feedback" else "nav-link"
    return dashboard_class, comparison_class, feedback_class

# Register client-side callback for theme toggle without server refresh
app.clientside_callback(
    ClientsideFunction(
        namespace='clientside',
        function_name='updateTheme'
    ),
    Output('theme-container', 'data-theme'),
    [Input('theme-toggle-btn', 'n_clicks')],
    [State('theme-container', 'data-theme')]
)

# Register page callbacks
dashboard.register_callbacks(app)
comparison.register_callbacks(app)
feedback.register_callbacks(app)

if __name__ == "__main__":
    app.run_server(debug=True)