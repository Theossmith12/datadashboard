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
        },
        checkMobile: function() {
            const isMobile = window.innerWidth <= 768;
            if (isMobile) {
                // Show overlays initially on mobile
                setTimeout(() => {
                    document.querySelectorAll('.double-tap-overlay').forEach(overlay => {
                        overlay.style.display = 'flex';
                    });
                }, 1000); // Delay to ensure elements are loaded
            }
            return isMobile;
        }
    }
});

// Double tap detection
let lastTap = 0;
let tapTimeout;
let overlayTimeout;

function initializeMobileOverlays() {
    const isMobile = window.innerWidth <= 768;
    if (isMobile) {
        document.querySelectorAll('.map-container').forEach(container => {
            const overlay = container.querySelector('.double-tap-overlay');
            if (overlay) {
                overlay.style.display = 'flex';
                
                // Add touch event listeners
                container.addEventListener('touchstart', handleTap);
                container.addEventListener('touchend', handleTap);
                
                // Disable map interactions initially
                const graph = container.querySelector('.js-plotly-plot');
                if (graph && graph._context) {
                    graph._context.scrollZoom = false;
                    graph._context.dragmode = false;
                }
            }
        });
    }
}

function handleTap(event) {
    if (event.type === 'touchstart') {
        lastTap = new Date().getTime();
        return;
    }
    
    const currentTime = new Date().getTime();
    const tapLength = currentTime - lastTap;
    
    clearTimeout(tapTimeout);
    clearTimeout(overlayTimeout);
    
    if (tapLength < 500 && tapLength > 0) {
        // Double tap detected
        event.preventDefault();
        const container = event.currentTarget;
        const overlay = container.querySelector('.double-tap-overlay');
        const graph = container.querySelector('.js-plotly-plot');
        
        if (overlay) {
            overlay.style.display = 'none';
            
            // Re-enable map interactions
            if (graph && graph._context) {
                graph._context.scrollZoom = true;
                graph._context.dragmode = 'pan';
                
                // Update the layout to enable interactions
                Plotly.relayout(graph, {
                    dragmode: 'pan',
                    'mapbox.scrollZoom': true
                });
            }
        }
    } else {
        // Single tap
        const container = event.currentTarget;
        const overlay = container.querySelector('.double-tap-overlay');
        
        if (overlay) {
            overlay.style.display = 'flex';
            
            // Auto-hide overlay after 2 seconds
            overlayTimeout = setTimeout(() => {
                overlay.style.display = 'none';
            }, 2000);
        }
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', initializeMobileOverlays);

// Re-initialize on window resize
window.addEventListener('resize', initializeMobileOverlays);

// Re-initialize when new content is loaded (for Dash updates)
const observer = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
        if (mutation.addedNodes.length) {
            initializeMobileOverlays();
        }
    });
});

observer.observe(document.body, {
    childList: true,
    subtree: true
});
