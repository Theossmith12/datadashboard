import plotly.express as px
import pandas as pd
from dash import Dash, dcc, html, Output, Input

# Sample data
df = px.data.iris()

# Create the Dash app
app = Dash(__name__)

app.layout = html.Div([
    dcc.Dropdown(
        id='x-axis',
        options=[{'label': col, 'value': col} for col in df.columns],
        value='sepal_width'
    ),
    dcc.Dropdown(
        id='y-axis',
        options=[{'label': col, 'value': col} for col in df.columns],
        value='sepal_length'
    ),
    dcc.Graph(id='scatter-plot'),
    html.Div(id='summary-text', style={'marginTop': 20, 'fontSize': 18})  # New text output
])

@app.callback(
    [Output('scatter-plot', 'figure'),  # First output: Update the graph
     Output('summary-text', 'children')],  # Second output: Update text
    [Input('x-axis', 'value'),
     Input('y-axis', 'value')]
)
def update_outputs(x_col, y_col):
    # Generate the scatter plot
    fig = px.scatter(df, x=x_col, y=y_col, title=f'Scatter Plot: {x_col} vs {y_col}')

    # Create a summary text
    summary = f"Currently selected: X-axis = {x_col}, Y-axis = {y_col}"
    
    return fig, summary  # Returning two outputs

if __name__ == '__main__':
    app.run_server(debug=True)
