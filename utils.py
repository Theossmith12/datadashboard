def update_fig_layout(fig, is_light_mode):
    """Apply theme to figures."""
    theme = {
        'paper_bgcolor': 'white' if is_light_mode else '#121212',
        'plot_bgcolor': 'white' if is_light_mode else '#121212',
        'font_color': 'black' if is_light_mode else '#e0e0e0'
    }
    fig.update_layout(**theme)
    return fig