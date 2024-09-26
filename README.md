# Crime Data Dashboard

This is an interactive data dashboard built using Dash and Plotly, designed to visualize UK crime data. The dashboard allows users to filter data by crime types, outcomes, locations, and more. It also provides time-series trends and geographical visualizations.

## Features
- Filterable crime data from City of London, Metropolitan, and Thames Valley police forces.
- Interactive heatmap and line/bar charts.
- Responsive dark and light mode themes.
- Downloadable filtered data.
- KPI display and trend analysis.

## Installation

1. Clone the repository:
    ```bash
    git clone https://github.com/Theossmith12/datadashboard.git
    cd datadashboard
    ```

2. Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

3. Run the app:
    ```bash
    python app.py
    ```

The app will be available at `http://127.0.0.1:8050/`.

## Deployment
The app is ready for deployment to services like Render, Heroku, or any other hosting platform that supports Python. Make sure to set up a `Procfile` and configure your server settings.

## Usage
- Select filters for crime type, outcome, and location.
- View crime trends over time through interactive charts.
- Download filtered data for further analysis.

## Contributing
Pull requests are welcome. For significant changes, please open an issue first to discuss what you'd like to change.

## License
This project is licensed under the MIT License.
