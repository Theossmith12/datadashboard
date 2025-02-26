window.dash_clientside = Object.assign({}, window.dash_clientside, {
    clientside: {
        updateTheme: function(n_clicks, currentTheme) {
            // If no clicks have occurred, keep the current theme
            if (n_clicks === 0) return currentTheme;
            
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            
            // Update all plots with the new theme without triggering a full redraw
            const plots = document.querySelectorAll('.js-plotly-plot');
            const colors = newTheme === 'dark' ? 
                {bgcolor: '#121212', color: '#e0e0e0'} : 
                {bgcolor: 'white', color: 'black'};
            
            plots.forEach(plot => {
                try {
                    if (plot && plot._fullLayout) {
                        const update = {
                            paper_bgcolor: colors.bgcolor,
                            plot_bgcolor: colors.bgcolor,
                            font: {color: colors.color}
                        };
                        
                        // Apply theme to axes
                        if (plot._fullLayout.xaxis) {
                            update['xaxis.gridcolor'] = newTheme === 'dark' ? '#333' : '#ddd';
                            update['xaxis.color'] = colors.color;
                        }
                        
                        if (plot._fullLayout.yaxis) {
                            update['yaxis.gridcolor'] = newTheme === 'dark' ? '#333' : '#ddd';
                            update['yaxis.color'] = colors.color;
                        }
                        
                        // Update layout without triggering a re-render
                        Plotly.relayout(plot, update);
                    }
                } catch (e) {
                    console.warn("Error updating plot theme:", e);
                }
            });
            
            // Update the theme class on the theme container
            const themeContainer = document.getElementById('theme-container');
            if (themeContainer) {
                themeContainer.setAttribute('data-theme', newTheme);
                themeContainer.className = newTheme === 'dark' ? 'dark-theme' : 'light-theme';
            }
            
            // Update the toggle icon source
            const toggleIcon = document.getElementById('theme-toggle-icon');
            if (toggleIcon) {
                toggleIcon.src = newTheme === 'dark' ? 
                    '/assets/dark-mode-toggle-icon.png' : 
                    '/assets/light-mode-toggle-icon.png';
            }
            
            // Update body class
            document.body.className = newTheme === 'dark' ? 'dark-theme' : 'light-theme';
            
            return newTheme;
        }
    }
});
