def update_fig_layout(fig, is_light_mode):
    """
    Updates a Plotly figure layout based on the current theme mode.
    This does NOT change the data or traces, only styling elements.
    
    Parameters:
    -----------
    fig : plotly.Figure
        The figure to update
    is_light_mode : bool
        True if in light mode, False if in dark mode
        
    Returns:
    --------
    plotly.Figure
        The updated figure
    """
    if is_light_mode:
        colors = {
            'bg': 'white',
            'text': 'black',
            'grid': '#ddd'
        }
    else:
        colors = {
            'bg': '#121212',
            'text': '#e0e0e0',
            'grid': '#333'
        }
    
    # Create a copy of the figure to avoid modifying the original
    updated_fig = fig
    
    # Update the layout parameters
    updated_fig.update_layout(
        paper_bgcolor=colors['bg'],
        plot_bgcolor=colors['bg'],
        font=dict(color=colors['text'])
    )
    
    # Update x and y axis properties if they exist
    if hasattr(updated_fig, 'update_xaxes'):
        updated_fig.update_xaxes(gridcolor=colors['grid'], color=colors['text'])
        
    if hasattr(updated_fig, 'update_yaxes'):
        updated_fig.update_yaxes(gridcolor=colors['grid'], color=colors['text'])
    
    return updated_fig