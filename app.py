import dash
import dash_bootstrap_components as dbc
from dash import dcc, html
from dash.dependencies import Input, Output

from pages import dashboard, comparison, feedback

external_stylesheets = [dbc.themes.DARKLY]
app = dash.Dash(__name__, external_stylesheets=external_stylesheets, suppress_callback_exceptions=True)
app.title = "UK Crime Data Dashboard"
server = app.server

app.layout = html.Div(
    id="theme-container",           
    className="dark-theme",
    children=[
        dcc.Location(id="url", refresh=False),
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

@app.callback(
    Output("theme-container", "className"),
    [Input("theme-toggle-switch", "value")]
)
def update_theme(is_light_mode):
    return "light-theme" if is_light_mode else "dark-theme"

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

dashboard.register_callbacks(app)
comparison.register_callbacks(app)
feedback.register_callbacks(app)

if __name__ == "__main__":
    app.run_server(debug=True)
