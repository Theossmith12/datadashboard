import dash
from dash.dependencies import Input, Output, State
from dash import callback_context

def register_theme_callbacks(app):
    """
    Register the theme toggle callback with allow_duplicate=True to prevent conflicts.
    This should be called from your main app initialization.
    """
    # Theme toggle callback with allow_duplicate=True to fix the conflict
    app.clientside_callback(
        """
        function(n_clicks, currentTheme) {
            return window.dash_clientside.clientside.updateTheme(n_clicks, currentTheme);
        }
        """,
        Output("theme-container", "data-theme", allow_duplicate=True),
        Input("theme-toggle-btn", "n_clicks"),
        State("theme-container", "data-theme"),
        prevent_initial_call=True
    )