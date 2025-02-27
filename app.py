import os
import pathlib
import requests
from flask import session, redirect, url_for, request, render_template_string
from google_auth_oauthlib.flow import Flow
import google.auth.transport.requests
import dash
import dash_bootstrap_components as dbc
from dash import dcc, html, Input, Output, State

# Allow insecure transport for local testing (DO NOT USE IN PRODUCTION)
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

REDIRECT_URI = "http://127.0.0.1:8050/oauth2callback"

# Create the Dash app and get the Flask server
external_stylesheets = [dbc.themes.DARKLY]
app = dash.Dash(__name__, external_stylesheets=external_stylesheets, suppress_callback_exceptions=True)
app.title = "UK Crime Data Dashboard"
server = app.server
server.static_folder = 'assets'  # Path to assets folder

# Set the secret key for session management (replace with a strong key in production)
server.secret_key = os.getenv('SECRET_KEY', 'your-very-secret-key')

# Initialize the cache (make sure cache_config.py is in your project directory)
from cache_config import cache
cache.init_app(server)

# ---------------------------
# Google OAuth Configuration
# ---------------------------
SCOPES = [
    'openid',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile'
]
GOOGLE_CLIENT_SECRETS_FILE = os.path.join(pathlib.Path(__file__).parent, 'client_secret.json')

# Login page template
login_page_html = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>London Street-level Crime Data Dashboard - Login</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <!-- Google Font -->
  <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;700&display=swap" rel="stylesheet">
  <!-- Bootstrap CSS via CDN -->
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
  <style>
    :root {
      --primary-color: rgba(58, 107, 140, 0.8);
      --accent-color: rgba(79, 146, 199, 0.8);
      --text-color: rgba(240, 240, 240, 0.9);
      --secondary-text: rgba(194, 194, 194, 0.7);
      --bg-overlay: rgba(25, 25, 25, 0.3);
      --card-bg: rgba(40, 44, 52, 0.65);
      --card-border: rgba(255, 255, 255, 0.08);
    }
    
    /* Body Styling */
    body {
      margin: 0;
      padding: 0;
      font-family: 'Poppins', sans-serif;
      background: linear-gradient(var(--bg-overlay), var(--bg-overlay)),
        url("/assets/download.jpg") no-repeat center center fixed;
      background-size: cover;
      color: var(--text-color);
      height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      overflow: hidden;
    }
    
    /* Modern Glassmorphism Card with Increased Transparency */
    .glass-card {
      position: relative;
      background: var(--card-bg);
      border-radius: 24px;
      padding: 3rem;
      max-width: 520px;
      width: 90%;
      text-align: center;
      backdrop-filter: blur(8px);
      -webkit-backdrop-filter: blur(8px);
      border: 1px solid var(--card-border);
      box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
      animation: fadeInUp 0.8s ease-out;
    }
    
    .glass-card::before {
      content: '';
      position: absolute;
      top: -2px;
      left: -2px;
      right: -2px;
      bottom: -2px;
      border-radius: 24px;
      background: linear-gradient(45deg, 
        rgba(58, 107, 140, 0.4), 
        rgba(79, 146, 199, 0.4), 
        rgba(58, 107, 140, 0.4));
      background-size: 400% 400%;
      filter: blur(12px);
      opacity: 0.4;
      animation: glow 8s ease-in-out infinite;
      z-index: -1;
    }

    /* Animations */
    @keyframes glow {
      0%   { background-position: 0%   50%; opacity: 0.3; }
      50%  { background-position: 100% 50%; opacity: 0.5; }
      100% { background-position: 0%   50%; opacity: 0.3; }
    }
    
    @keyframes fadeInUp {
      from { opacity: 0; transform: translateY(20px); }
      to   { opacity: 1; transform: translateY(0); }
    }

    /* Typography with Gradient Fade */
    .card-title {
      font-size: 2.2rem;
      font-weight: 700;
      margin-bottom: 1rem;
      color: var(--text-color);
      text-shadow: 0 2px 10px rgba(0,0,0,0.2);
      background: linear-gradient(to bottom, 
        rgba(240, 240, 240, 0.95), 
        rgba(240, 240, 240, 0.8));
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
    }
    
    .card-subtitle {
      font-size: 1.3rem;
      font-weight: 500;
      margin-bottom: 1.5rem;
      color: var(--accent-color);
      opacity: 0.9;
    }
    
    .card-text {
      font-size: 1.05rem;
      margin-bottom: 2rem;
      color: var(--secondary-text);
      line-height: 1.5;
      background: linear-gradient(to bottom, 
        rgba(194, 194, 194, 0.85), 
        rgba(194, 194, 194, 0.65));
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
    }

    /* Login button with subtle fade */
    .login-button {
      display: inline-block;
      background: transparent;
      border: none;
      padding: 0;
      cursor: pointer;
      transition: transform 0.2s ease, opacity 0.3s ease;
      margin-top: 1rem;
      position: relative;
    }
    
    .login-button::after {
      content: '';
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: linear-gradient(to bottom, 
        rgba(255, 255, 255, 0), 
        rgba(255, 255, 255, 0.1));
      border-radius: 4px;
      opacity: 0;
      transition: opacity 0.3s ease;
    }
    
    .login-button:hover::after {
      opacity: 1;
    }
    
    .login-button img {
      width: 250px;
      height: auto;
      transition: opacity 0.3s ease, filter 0.3s ease;
      filter: drop-shadow(0 4px 6px rgba(0, 0, 0, 0.2));
    }
    
    .login-button:hover img {
      opacity: 0.9;
      filter: drop-shadow(0 6px 8px rgba(0, 0, 0, 0.3));
    }
    
    .login-button:active img {
      transform: scale(0.95);
      opacity: 0.7;
    }

    /* Footer text with fade effect */
    .footer-text {
      margin-top: 2rem;
      font-size: 0.9rem;
      opacity: 0.6;
      background: linear-gradient(to bottom, 
        rgba(194, 194, 194, 0.7), 
        rgba(194, 194, 194, 0.5));
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
      transition: opacity 0.3s ease;
    }
    
    /* Footer text hover effect */
    .footer-text:hover {
      opacity: 0.8;
    }
    
    /* Responsive adjustments */
    @media (max-width: 768px) {
      .glass-card {
        padding: 2rem;
        width: 85%;
      }
      
      .card-title {
        font-size: 1.8rem;
      }
      
      .card-subtitle {
        font-size: 1.1rem;
      }
      
      .login-button img {
        width: 200px;
      }
    }
  </style>
</head>
<body>
  <div class="glass-card">
    <h1 class="card-title">London Crime Data Dashboard</h1>
    <h2 class="card-subtitle">Predictive Analytics System</h2>
    <p class="card-text">
      Explore interactive data visualizations and insights into London's crime patterns.
      Sign in for secure access and stay informed.
    </p>
    
    <a href="{{ url_for('login') }}" class="login-button">
      <img src="/assets/sign_in.png" alt="Sign In with Google">
    </a>
    
    <p class="footer-text">Developed by: Theodoro Smith</p>
  </div>

  <!-- Bootstrap JS Bundle -->
  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""

# Authentication routes and middleware
@server.route('/login')
def login():
    # If already logged in, redirect to dashboard
    if 'logged_in' in session:
        return redirect('/dashboard')
        
    # Create the OAuth flow
    flow = Flow.from_client_secrets_file(
        GOOGLE_CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true'
    )
    session['state'] = state
    return redirect(authorization_url)

@server.route('/oauth2callback')
def oauth2callback():
    state = session.get('state')
    
    # Create the OAuth flow with the current state
    flow = Flow.from_client_secrets_file(
        GOOGLE_CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        state=state,
        redirect_uri=REDIRECT_URI
    )
    
    # Exchange auth code for access token
    flow.fetch_token(authorization_response=request.url)
    credentials = flow.credentials

    # Retrieve user info from Google
    response = requests.get(
        'https://www.googleapis.com/oauth2/v2/userinfo',
        headers={'Authorization': f'Bearer {credentials.token}'}
    )
    user_info = response.json()
    
    # Store user info in session
    session['user'] = user_info
    session['logged_in'] = True
    
    # Redirect to dashboard
    return redirect('/dashboard')

@server.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@server.before_request
def require_login():
    # Bypass authentication if SKIP_AUTH is set (for testing)
    if os.getenv('SKIP_AUTH', '0') == '1':
        return
    if request.path.startswith('/assets/'):
        return

    # List of paths that don't require authentication
    allowed_paths = ['/login', '/oauth2callback', '/logout']
    
    # Allow static assets and specific routes without authentication
    if request.path.startswith('/_dash/') or request.path.startswith('/assets/') or request.path in allowed_paths:
        return
        
    # If the root path ('/') is accessed and user is not logged in, render the login page
    if request.path == '/' and 'logged_in' not in session:
        return render_template_string(login_page_html)
        
    # For all other protected routes, redirect to login if not authenticated
    if 'logged_in' not in session:
        return redirect('/')

@server.route('/')
def index():
    # If user is logged in, redirect to the dashboard
    if 'logged_in' in session or os.getenv('SKIP_AUTH', '0') == '1':
        return redirect('/dashboard')
        
    # Otherwise, render the login page
    return render_template_string(login_page_html)

# Define a route for the dashboard to handle direct access
@server.route('/dashboard')
def dash_app_route():
    # Check if user is authenticated (handled by require_login middleware)
    # Return a basic HTML that loads the Dash app
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>London Crime Dashboard</title>
        <meta http-equiv="refresh" content="0;url=/" />
    </head>
    <body>
        <p>Loading dashboard...</p>
    </body>
    </html>
    """

# ---------------------------
# Dash App Layout and Routing
# ---------------------------
app.layout = html.Div(
    id="theme-container",
    className="dark-theme",  # Start in dark theme
    **{'data-theme': 'dark'},
    children=[
        dcc.Location(id="url", refresh=False),
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
                        html.Button(
                            [html.Img(id="theme-toggle-icon", src="/assets/dark-mode-toggle-icon.png", className="toggle-icon")],
                            id="theme-toggle-btn",
                            n_clicks=0,
                            className="theme-toggle-btn"
                        ),
                        html.Button(
                            "Logout",
                            id="logout-btn",
                            n_clicks=0,
                            className="logout-btn",
                            style={"marginLeft": "15px"}
                        )
                    ],
                    style={"display": "flex", "alignItems": "center", "gap": "15px"}
                )
            ]
        ),
        html.Div(id="page-content", style={"padding": "10px"})
    ]
)

@app.callback(
    Output("page-content", "children"),
    [Input("url", "pathname")]
)
def render_page_content(pathname):
    # Import page modules as needed (ensure these are imported only after cache initialization)
    if pathname in ["/", "/dashboard"]:
        from pages import dashboard
        return dashboard.layout()
    elif pathname == "/comparison":
        from pages import comparison
        return comparison.layout()
    elif pathname == "/feedback":
        from pages import feedback
        return feedback.layout()
    return "404 Page Not Found"

# Add a callback for the logout button
app.clientside_callback(
    """
    function(n_clicks) {
        if (n_clicks > 0) {
            window.location.href = '/logout';
        }
        return '';
    }
    """,
    Output('logout-btn', 'className'),  # We don't actually change the class, just need an output
    Input('logout-btn', 'n_clicks')
)

@app.callback(
    Output("reset-cache-btn", "children"),
    [Input("reset-cache-btn", "n_clicks")]
)
def clear_cache(n_clicks):
    if n_clicks and n_clicks > 0:
        from data_loader import reset_cache
        reset_cache()
        return "✅ Cache Cleared!"
    return "Reset Cache"

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

app.clientside_callback(
    """
    function(n_clicks, currentTheme) {
        if (n_clicks === 0) return currentTheme;
        if (currentTheme === 'dark') {
            return 'light';
        } else {
            return 'dark';
        }
    }
    """,
    Output('theme-container', 'data-theme'),
    Input('theme-toggle-btn', 'n_clicks'),
    State('theme-container', 'data-theme')
)

# Register page callbacks from your modules
from pages import dashboard, comparison, feedback
dashboard.register_callbacks(app)
comparison.register_callbacks(app)
feedback.register_callbacks(app)


if __name__ == "__main__":
    
    app.run_server(debug=False)