import os
import pathlib
import requests
from flask import session, redirect, url_for, request, render_template_string, make_response
from google_auth_oauthlib.flow import Flow
import google.auth.transport.requests
import dash
import dash_bootstrap_components as dbc
from dash import dcc, html, Input, Output, State
import logging
import urllib.parse  

# Set up logging for troubleshooting
logging.basicConfig(level=logging.DEBUG, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('crime_dashboard')

# Allow insecure transport for local testing (DO NOT USE IN PRODUCTION)
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# Set the redirect URI
REDIRECT_URI = "http://127.0.0.1:8050/oauth2callback"

# Create the Dash app and get the Flask server
external_stylesheets = [dbc.themes.DARKLY]
app = dash.Dash(__name__, external_stylesheets=external_stylesheets, suppress_callback_exceptions=True)
app.title = "UK Crime Data Dashboard"
server = app.server
server.static_folder = 'assets'  # Path to assets folder

# Set secret key and cookie configuration for session management
SECRET_KEY = os.getenv('SECRET_KEY', 'your-very-secret-key-change-in-production')
server.secret_key = SECRET_KEY
server.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
server.config['SESSION_COOKIE_DOMAIN'] = None  # Ensure this matches your URL for local testing
logger.info(f"Server secret key configured. Cookie domain set to {server.config['SESSION_COOKIE_DOMAIN']}.")

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

if not os.path.exists(GOOGLE_CLIENT_SECRETS_FILE):
    logger.error(f"Client secrets file not found: {GOOGLE_CLIENT_SECRETS_FILE}")
else:
    logger.info(f"Client secrets file loaded from: {GOOGLE_CLIENT_SECRETS_FILE}")

# ---------------------------
# Login Page HTML with Styles
# ---------------------------
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

# ---------------------------
# Routes
# ---------------------------
@server.route('/login')
def login():
    logger.debug("Login route accessed.")
    logger.debug(f"Current session keys before login: {list(session.keys())}")
    
    if session.get('logged_in'):
        logger.debug(f"User already logged in: {session.get('user', {}).get('email', 'no-email')}")
        return redirect('/dashboard')
    
    try:
        flow = Flow.from_client_secrets_file(
            GOOGLE_CLIENT_SECRETS_FILE,
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI
        )
        extra_params = {
            'access_type': 'offline',
            'include_granted_scopes': 'true',
            'hd': '*'
        }
        user_agent = request.user_agent.string.lower() if request.user_agent else ""
        logger.debug(f"User agent: {user_agent}")
        is_mobile = any(x in user_agent for x in ['android', 'iphone', 'ipad', 'mobile'])
        if is_mobile:
            extra_params.update({
                'prompt': 'consent',
                'approval_prompt': 'force'
            })
            logger.debug("Detected mobile browser; added mobile-specific OAuth parameters.")
            
        authorization_url, state = flow.authorization_url(**extra_params)
        session['state'] = state
        logger.debug(f"OAuth state saved in session: {state}")
        return redirect(authorization_url)
    except Exception as e:
        logger.error(f"Error in login route: {e}")
        return render_template_string("<h1>Authentication Error</h1><p>Please try again later.</p>")

@server.route('/oauth2callback')
def oauth2callback():
    logger.debug("OAuth callback route accessed.")
    logger.debug(f"Session keys at callback entry: {list(session.keys())}")
    
    try:
        state = session.get('state')
        if not state:
            logger.error("No state found in session. Possible CSRF issue or session expiration.")
            return redirect('/')
        
        flow = Flow.from_client_secrets_file(
            GOOGLE_CLIENT_SECRETS_FILE,
            scopes=SCOPES,
            state=state,
            redirect_uri=REDIRECT_URI
        )
        flow.fetch_token(authorization_response=request.url)
        credentials = flow.credentials
        logger.debug("Fetched token from Google OAuth.")
        
        response = requests.get(
            'https://www.googleapis.com/oauth2/v2/userinfo',
            headers={'Authorization': f'Bearer {credentials.token}'}
        )
        user_info = response.json()
        logger.debug(f"User info received: {user_info}")
        
        session['user'] = user_info
        session['logged_in'] = True
        session['token'] = credentials.token
        logger.debug(f"Session updated after login: {list(session.keys())}")
        
        return redirect('/dashboard')
    except Exception as e:
        logger.error(f"Error in OAuth callback: {e}")
        session.clear()
        return redirect('/')

@server.route('/logout')
def logout():
    logger.debug(f"Logout route accessed. Session keys before logout: {list(session.keys())}")
    user_email = session.get('user', {}).get('email', 'unknown')
    logger.debug(f"Logging out user: {user_email}")
    session.clear()
    logger.debug("Session cleared on logout.")
    
    response = make_response(redirect('/'))
    response.set_cookie('session', '', expires=0, path='/', samesite='Lax')
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    
    logger.debug("Logout response prepared with expired cookies and cache control headers.")
    return response

@server.before_request
def require_login():
    logger.debug(f"Before request: path={request.path}, method={request.method}")
    logger.debug(f"Session keys: {list(session.keys())}")
    
    if any([
        request.path.startswith('/assets/'),
        request.path.startswith('/_dash/'),
        request.path in ['/login', '/oauth2callback', '/logout', '/check-session'],
        request.path.startswith('/favicon'),
    ]):
        return
    
    if request.path == '/' and not session.get('logged_in'):
        logger.debug("User not logged in; serving login page at root.")
        return render_template_string(login_page_html)
    
    if not session.get('logged_in'):
        logger.info(f"Unauthorized access attempt to {request.path}; redirecting to login.")
        if request.path.startswith('/api/') or request.headers.get('Accept') == 'application/json':
            return make_response({"error": "Unauthorized", "redirect": "/"}, 401)
        return redirect('/')

@server.route('/check-session', methods=['GET'])
def check_session():
    logged_in = session.get('logged_in', False)
    email = session.get('user', {}).get('email', 'not logged in')
    logger.debug(f"Session check: logged_in={logged_in}, email={email}, keys={list(session.keys())}")
    return {
        "logged_in": logged_in,
        "email": email if logged_in else None,
        "session_keys": list(session.keys()),
    }

@server.route('/')
def index():
    if session.get('logged_in') or os.getenv('SKIP_AUTH', '0') == '1':
        logger.debug("Index route: user logged in, redirecting to dashboard.")
        return redirect('/dashboard')
    logger.debug("Index route: user not logged in, serving login page.")
    return render_template_string(login_page_html)

@server.route('/dashboard')
def dash_app_route():
    logger.debug(f"Dashboard route accessed. Session keys: {list(session.keys())}")
    logger.debug(f"User info in session: {session.get('user', {}).get('email', 'not logged in')}")
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8" />
      <title>London Crime Dashboard</title>
      <meta http-equiv="refresh" content="3;url=/" />
      <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        html, body { height: 100%; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #121212; color: #fff; display: flex; align-items: center; justify-content: center; }
        .loader { text-align: center; }
        .spinner { width: 80px; height: 80px; border: 8px solid rgba(255, 255, 255, 0.2); border-top: 8px solid #ffffff; border-radius: 50%; animation: spin 1.5s linear infinite; margin: 0 auto; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        .loading-text { margin-top: 20px; font-size: 1.2rem; letter-spacing: 0.05rem; }
      </style>
    </head>
    <body>
      <div class="loader">
        <div class="spinner"></div>
        <div class="loading-text">Loading dashboard...</div>
      </div>
    </body>
    </html>
    """

# ---------------------------
# Dash App Layout and Callbacks
# ---------------------------
app.layout = html.Div(
    id="theme-container",
    className="dark-theme",
    **{'data-theme': 'dark'},
    children=[
        dcc.Location(id="url", refresh=False),
        html.Div(id="session-status", style={"display": "none"}),
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
    logger.debug(f"Rendering page for pathname: {pathname}")
    if pathname in ["/", "/dashboard"]:
        from pages import dashboard
        return dashboard.layout()
    elif pathname == "/comparison":
        from pages import comparison
        return comparison.layout()
    elif pathname == "/feedback":
        from pages import feedback
        return feedback.layout()
    elif pathname == "/settings":
        return html.Div([
            html.H2("Settings", style={"textAlign": "center"}),
            html.Div([
                html.Button("Toggle Dark/Light Mode", id="theme-toggle-btn-settings", className="btn btn-secondary", style={"width": "100%", "marginBottom": "10px"}),
                html.Button("Logout", id="logout-btn-settings", className="btn btn-danger", style={"width": "100%"})
            ], style={"maxWidth": "400px", "margin": "auto"}),
            html.Div([
                dcc.Link("Back to Dashboard", href="/dashboard", className="btn btn-primary", style={"width": "100%", "marginTop": "20px"})
            ], style={"maxWidth": "400px", "margin": "auto", "textAlign": "center"})
        ])
    logger.debug("Page not found; returning 404.")
    return "404 Page Not Found"

# Client-side callbacks for logout and theme toggling
app.clientside_callback(
    """
    function(n_clicks) {
        if (n_clicks > 0) {
            localStorage.removeItem('dash_app_state');
            sessionStorage.clear();
            var logoutForm = document.createElement('form');
            logoutForm.method = 'GET';
            logoutForm.action = '/logout';
            document.body.appendChild(logoutForm);
            logoutForm.submit();
            return 'logout-btn logging-out';
        }
        return 'logout-btn';
    }
    """,
    Output('logout-btn', 'className'),
    Input('logout-btn', 'n_clicks')
)

app.clientside_callback(
    """
    function(n_clicks) {
        if (n_clicks > 0) {
            localStorage.removeItem('dash_app_state');
            sessionStorage.clear();
            var logoutForm = document.createElement('form');
            logoutForm.method = 'GET';
            logoutForm.action = '/logout';
            document.body.appendChild(logoutForm);
            logoutForm.submit();
        }
        return '';
    }
    """,
    Output('logout-btn-settings', 'className'),
    Input('logout-btn-settings', 'n_clicks')
)

app.clientside_callback(
    """
    function(n_intervals) {
        if (n_intervals > 0 && n_intervals % 300 === 0) {
            fetch('/check-session')
                .then(response => response.json())
                .then(data => {
                    if (!data.logged_in) {
                        window.location.href = '/';
                    }
                })
                .catch(error => console.error('Session check error:', error));
        }
        return '';
    }
    """,
    Output('session-status', 'children'),
    Input('interval-component', 'n_intervals')
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
        return currentTheme === 'dark' ? 'light' : 'dark';
    }
    """,
    Output('theme-container', 'data-theme'),
    Input('theme-toggle-btn', 'n_clicks'),
    State('theme-container', 'data-theme')
)

# Interval component for session checks
app.layout.children.append(dcc.Interval(
    id='interval-component',
    interval=1000,  # 1 second
    n_intervals=0
))

# Register page callbacks from modules
from pages import dashboard, comparison, feedback
dashboard.register_callbacks(app)
comparison.register_callbacks(app)
feedback.register_callbacks(app)

if __name__ == "__main__":
    logger.info(f"Starting Crime Dashboard app with SKIP_AUTH={os.getenv('SKIP_AUTH', '0')}")
    logger.info(f"Using REDIRECT_URI: {REDIRECT_URI}")
    logger.info(f"Client secrets file: {GOOGLE_CLIENT_SECRETS_FILE}")
    app.run_server(debug=False)
