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
def apply_mobile_layout(fig, is_mobile, title=None):
    """
    Apply mobile-specific layout adjustments to a figure.
    
    Parameters:
    -----------
    fig : plotly.Figure
        The figure to update
    is_mobile : bool
        Whether the client is on a mobile device
    title : str, optional
        Title for the chart (shortened for mobile)
    
    Returns:
    --------
    plotly.Figure
        The updated figure
    """
    if is_mobile:
        # Mobile optimizations
        layout_updates = dict(
            height=350,  # Smaller height for mobile
            dragmode=False,  # Disable dragging
            showlegend=False,  # Hide legend
            margin=dict(l=40, r=10, t=40, b=40),  # Tighter margins
            xaxis=dict(
                tickangle=-45,  # Angled labels
                nticks=5  # Fewer ticks
            ),
            yaxis=dict(
                nticks=5  # Fewer ticks
            ),
            title=dict(
                text=title[:30] + "..." if title and len(title) > 30 else title,
                font=dict(size=14)
            ) if title else None
        )
        fig.update_layout(**layout_updates)
        
        # Simplify traces for mobile
        for trace in fig.data:
            if hasattr(trace, 'marker'):
                # Smaller markers on mobile
                if hasattr(trace.marker, 'size'):
                    if isinstance(trace.marker.size, (int, float)):
                        trace.marker.size = max(4, trace.marker.size * 0.7)
        
    return fig