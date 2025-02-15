import logging
import dash_bootstrap_components as dbc
from dash import dcc, html
from dash.dependencies import Input, Output, State

def layout():
    return dbc.Container(
        fluid=True,
        children=[
            dbc.Row(
                dbc.Col(html.H2("Feedback", className="text-center text-primary"), width=12),
                className="my-2"
            ),
            dbc.Row(
                dbc.Col(
                    dcc.Textarea(
                        id="feedback-textarea",
                        placeholder="Enter your feedback here...",
                        style={"width": "100%", "height": "150px"}
                    ),
                    width=12
                ),
                className="my-2"
            ),
            dbc.Row(
                dbc.Col(
                    dbc.Button("Submit Feedback", id="submit-feedback", color="primary", className="d-block mx-auto"),
                    width=12
                ),
                className="my-2"
            ),
            dbc.Row(
                dbc.Col(html.Div(id="feedback-response", className="text-center"), width=12),
                className="my-2"
            )
        ]
    )

def register_callbacks(app):
    @app.callback(
        Output("feedback-response", "children"),
        [Input("submit-feedback", "n_clicks")],
        [State("feedback-textarea", "value")]
    )
    def submit_feedback(n_clicks, feedback_text):
        if n_clicks and feedback_text:
            logging.info(f"Feedback received: {feedback_text}")
            return "Thank you for your feedback!"
        return ""
