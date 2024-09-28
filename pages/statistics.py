# pages/statistics.py

import logging  # Import the logging module
from dash import dcc, html
import plotly.express as px
from data_processing import get_yearly_comparison  # Import necessary functions

def statistics_layout(crime_data):
    # Check if data is available
    if crime_data.empty:
        return html.Div(
            "No data available.",
            style={
                'color': '#e0e0e0',
                'backgroundColor': '#121212',
                'height': '100vh',
                'display': 'flex',
                'justifyContent': 'center',
                'alignItems': 'center',
                'font-size': '24px'
            }
        )
    else:
        # Initialize an empty list to hold statistical sections
        stats_sections = []

        # Top Neighborhoods (Assuming 'Location' exists)
        if 'Location' in crime_data.columns:
            top_neighborhoods = crime_data['Location'].value_counts().head(10).reset_index()
            top_neighborhoods.columns = ['Neighborhood', 'Crime Count']
            neighborhood_graph = html.Div([
                html.H2('10 Most Common Crime Locations'),
                dcc.Graph(
                    figure=px.bar(
                        top_neighborhoods,
                        x='Neighborhood',
                        y='Crime Count',
                        labels={'Crime Count': 'Number of Crimes', 'Neighborhood': 'Neighborhood'},
                        template='plotly_dark'
                    )
                )
            ], className='graph-container')
            stats_sections.append(neighborhood_graph)
        else:
            logging.warning("'Location' column not found in the dataset.")  # Use logging.warning

        # Crime Type Distribution by LSOA
        if 'LSOA name' in crime_data.columns and 'Crime type' in crime_data.columns:
            lsoa_crime = crime_data.groupby(['LSOA name', 'Crime type']).size().reset_index(name='Count')
            # To avoid clutter, focus on top 10 LSOAs by crime count
            top_lsoas = crime_data['LSOA name'].value_counts().head(10).index
            lsoa_crime_top = lsoa_crime[lsoa_crime['LSOA name'].isin(top_lsoas)]
            lsoa_crime_graph = html.Div([
                html.H2('Crime Distribution by LSOA'),
                dcc.Graph(
                    figure=px.bar(
                        lsoa_crime_top,
                        x='LSOA name',
                        y='Count',
                        color='Crime type',
                        title='Crime Distribution across Top 10 LSOAs',
                        labels={'Count': 'Number of Crimes', 'LSOA name': 'LSOA'},
                        template='plotly_dark',
                        barmode='stack'
                    )
                )
            ], className='graph-container')
            stats_sections.append(lsoa_crime_graph)
        else:
            logging.warning("'LSOA name' or 'Crime type' column not found in the dataset.")

        # Monthly Crime Counts
        if 'Month' in crime_data.columns:
            monthly_counts = crime_data.groupby(crime_data['Month'].dt.to_period('M')).size().reset_index(name='Count')
            monthly_counts['Month'] = monthly_counts['Month'].dt.to_timestamp()
            monthly_graph = html.Div([
                html.H2('Monthly Crime Counts'),
                dcc.Graph(
                    figure=px.line(
                        monthly_counts,
                        x='Month',
                        y='Count',
                        title='Monthly Crime Counts Over Time',
                        labels={'Count': 'Number of Crimes', 'Month': 'Month'},
                        template='plotly_dark'
                    )
                )
            ], className='graph-container')
            stats_sections.append(monthly_graph)
        else:
            logging.warning("'Month' column not found in the dataset.")

        # Yearly Comparison of Crime Types
        if 'Month' in crime_data.columns and 'Crime type' in crime_data.columns:
            yearly_comparison_data = get_yearly_comparison(crime_data)
            yearly_comparison_graph = html.Div([
                html.H2('Yearly Comparison of Crime Types'),
                dcc.Graph(
                    figure=px.bar(
                        yearly_comparison_data,
                        x='Year',
                        y='Count',
                        color='Crime type',
                        barmode='group',
                        title='Yearly Comparison of Crime Types',
                        labels={'Count': 'Number of Crimes', 'Year': 'Year'},
                        template='plotly_dark'
                    )
                )
            ], className='graph-container')
            stats_sections.append(yearly_comparison_graph)
        else:
            logging.warning("'Month' or 'Crime type' column not found in the dataset.")

        # If no additional statistics sections were added
        if not stats_sections:
            stats_sections.append(
                html.Div(
                    "No additional statistical data available.",
                    style={
                        'color': '#e0e0e0',
                        'textAlign': 'center',
                        'font-size': '18px'
                    }
                )
            )

        return html.Div(
            style={'backgroundColor': '#121212', 'font-family': 'Segoe UI, Tahoma, Geneva, Verdana, sans-serif'},
            children=[
                html.Div(
                    className='header',
                    children=[
                        html.H1('Additional Statistical Insights'),
                        html.P('Explore more detailed statistical observations and analyses related to the crime data.')
                    ]
                ),

                # Add all statistical sections
                *stats_sections
            ]
        )
