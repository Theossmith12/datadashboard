// assets/custom.js

// Wait for DOM to be fully loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('Custom script loaded');
    
    // Give Dash time to initialize components
    setTimeout(setupCustomFeatures, 500);
    
    // Also handle dynamic content changes
    setupMutationObserver();
});

// Main function to set up custom features
function setupCustomFeatures() {
    // Fix hamburger menu first
    fixHamburgerMenu();
    
    // Set up scroll animations
    setupScrollAnimations();
    
    // Hide debug menu
    hideDebugMenu();
    
    // Fix navbar for all screen sizes
    adjustNavbarLayout();
    
    // Move dark theme toggle to hamburger menu on mobile
    moveThemeToggleToHamburger();
    
    console.log('Custom features initialized');
}

// Function to fix hamburger menu
function fixHamburgerMenu() {
    console.log('Fixing hamburger menu');
    
    // Remove any existing hamburger menu
    const existingMenu = document.querySelector('.hamburger-menu');
    if (existingMenu) {
        existingMenu.remove();
    }
    
    // Create a new hamburger menu
    const hamburgerMenu = document.createElement('div');
    hamburgerMenu.className = 'hamburger-menu';
    hamburgerMenu.innerHTML = `
        <span></span>
        <span></span>
        <span></span>
    `;
    
    // Add to the navbar
    const navbar = document.querySelector('.navbar');
    if (navbar) {
        navbar.appendChild(hamburgerMenu);
        
        // Add click handler
        hamburgerMenu.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            const navLinks = document.querySelector('.nav-links');
            if (navLinks) {
                navLinks.classList.toggle('active');
                this.classList.toggle('active');
                console.log('Toggled nav links:', navLinks.classList.contains('active'));
            }
        });
        
        console.log('Hamburger menu added to navbar');
    }
    
    // Hide any dash-generated mobile menu buttons
    const toggleButtons = document.querySelectorAll('button[aria-label="Toggle Navigation"]');
    toggleButtons.forEach(btn => {
        btn.style.display = 'none';
    });
}

// Setup scroll reveal animations
function setupScrollAnimations() {
    console.log('Setting up scroll animations');
    
    // Target elements for reveal animations
    const sections = document.querySelectorAll('.section-title, .graph-container, .summary, .dashboard-row');
    
    // Add reveal class to elements that don't already have it
    sections.forEach(element => {
        if (!element.classList.contains('reveal')) {
            element.classList.add('reveal');
        }
    });
    
    // Function to check if element is in viewport
    function isInViewport(element) {
        const rect = element.getBoundingClientRect();
        return (
            rect.top <= (window.innerHeight || document.documentElement.clientHeight) * 0.85 && 
            rect.bottom >= 0
        );
    }
    
    // Function to handle scroll animation
    function handleScrollAnimation() {
        sections.forEach(element => {
            if (isInViewport(element)) {
                element.classList.add('active');
            }
        });
    }
    
    // Initial check
    handleScrollAnimation();
    
    // Remove existing scroll listeners to prevent duplicates
    window.removeEventListener('scroll', handleScrollAnimation);
    
    // Add scroll event listener
    window.addEventListener('scroll', handleScrollAnimation);
    
    console.log('Scroll animations setup complete');
}

// Hide Dash debug menu
function hideDebugMenu() {
    // Find all debug menu elements
    const debugMenus = document.querySelectorAll('.dash-debug-menu_outer, .dash-debug-menu_content, ._dash-loading-callback, ._dash-loading');
    
    // Hide them
    debugMenus.forEach(menu => {
        if (menu) {
            menu.style.display = 'none';
            menu.style.visibility = 'hidden';
            menu.style.opacity = '0';
            menu.style.pointerEvents = 'none';
        }
    });
    
    // Also add some CSS to make sure they stay hidden
    if (!document.getElementById('debug-menu-css')) {
        const style = document.createElement('style');
        style.id = 'debug-menu-css';
        style.textContent = `
            .dash-debug-menu_outer,
            .dash-debug-menu_content,
            ._dash-loading-callback,
            ._dash-loading,
            button[aria-label="Toggle Navigation"] {
                display: none !important;
                visibility: hidden !important;
                opacity: 0 !important;
                pointer-events: none !important;
                height: 0 !important;
                width: 0 !important;
            }
        `;
        document.head.appendChild(style);
    }
}

// Adjust navbar layout for different screen sizes
function adjustNavbarLayout() {
    const navbar = document.querySelector('.navbar');
    if (!navbar) return;
    
    // Handle responsive layout
    function updateLayout() {
        const isMobile = window.innerWidth <= 768;
        
        // Handle mobile-specific adjustments
        if (isMobile) {
            // Make sure hamburger menu is visible
            const hamburgerMenu = document.querySelector('.hamburger-menu');
            if (hamburgerMenu) {
                hamburgerMenu.style.display = 'flex';
            } else {
                fixHamburgerMenu();
            }
            
            // Ensure nav links has proper classes
            const navLinks = document.querySelector('.nav-links');
            if (navLinks) {
                navLinks.style.display = navLinks.classList.contains('active') ? 'flex' : 'none';
                navLinks.style.flexDirection = 'column';
                navLinks.style.width = '100%';
                navLinks.style.paddingTop = '50px';
            }
            
            // Ensure charts take full width
            const graphContainers = document.querySelectorAll('.graph-container');
            graphContainers.forEach(container => {
                container.style.width = '100%';
                container.style.maxWidth = 'none';
            });
        } else {
            // For desktop, ensure nav links are visible
            const navLinks = document.querySelector('.nav-links');
            if (navLinks) {
                navLinks.style.display = 'flex';
                navLinks.style.flexDirection = 'row';
            }
        }
        moveThemeToggleToHamburger();
    }
    
    updateLayout();
    window.removeEventListener('resize', updateLayout);
    window.addEventListener('resize', updateLayout);
}

// Fix Plotly legends on mobile
function adjustPlotlyLegends() {
    const isMobile = window.innerWidth <= 768;
    
    if (isMobile) {
        // Hide legends on mobile
        const legends = document.querySelectorAll('.js-plotly-plot .legend');
        legends.forEach(legend => {
            if (legend) {
                legend.style.display = 'none';
            }
        });
    }
}

// Function to move the dark theme toggle into the hamburger menu on mobile
function moveThemeToggleToHamburger() {
    const themeToggleBtn = document.getElementById('theme-toggle-btn');
    const navLinks = document.querySelector('.nav-links');
    const navToggles = document.querySelector('.nav-toggles');
    if (window.innerWidth <= 768 && themeToggleBtn && navLinks) {
        if (!document.getElementById('mobile-theme-toggle')) {
            const mobileContainer = document.createElement('div');
            mobileContainer.id = 'mobile-theme-toggle';
            mobileContainer.style.marginTop = '10px';
            mobileContainer.style.display = 'flex';
            mobileContainer.style.justifyContent = 'center';
            mobileContainer.appendChild(themeToggleBtn);
            navLinks.appendChild(mobileContainer);
            console.log('Theme toggle moved to hamburger menu');
        }
    } else {
        // On desktop, move it back to its original container if necessary
        if (themeToggleBtn && navToggles && themeToggleBtn.parentNode && themeToggleBtn.parentNode.id === 'mobile-theme-toggle') {
            navToggles.appendChild(themeToggleBtn);
            const mobileContainer = document.getElementById('mobile-theme-toggle');
            if (mobileContainer) {
                mobileContainer.remove();
            }
            console.log('Theme toggle moved back to navbar');
        }
    }
}

// Watch for Dash updating the DOM
function setupMutationObserver() {
    // Create an observer instance
    const observer = new MutationObserver(function(mutations) {
        let shouldRefresh = false;
        
        mutations.forEach(function(mutation) {
            if (mutation.addedNodes.length) {
                // Check if any of the added nodes are relevant to our features
                mutation.addedNodes.forEach(node => {
                    // Check if node is an element and has a className property
                    if (node.nodeType === 1 && node.className) {
                        // Check for dashboard or graph related elements
                        if (
                            (typeof node.className === 'string' && (
                                node.className.includes('navbar') ||
                                node.className.includes('nav-') ||
                                node.className.includes('graph') ||
                                node.className.includes('dashboard')
                            )) ||
                            node.tagName === 'BUTTON' ||
                            (node.getAttribute && node.getAttribute('aria-label') === 'Toggle Navigation')
                        ) {
                            shouldRefresh = true;
                        }
                    }
                });
            }
        });
        
        if (shouldRefresh) {
            // Wait a moment for rendering to complete
            setTimeout(function() {
                setupCustomFeatures();
                adjustPlotlyLegends();
            }, 100);
        }
    });
    
    // Start observing the document body
    observer.observe(document.body, {
        childList: true,
        subtree: true
    });
    
    console.log('Mutation observer setup complete');
}

// Initialize on load
window.addEventListener('load', function() {
    // Apply custom features once the page is fully loaded
    setTimeout(function() {
        setupCustomFeatures();
        adjustPlotlyLegends();
        
        // Also ensure theme toggle works when loaded
        const themeToggleBtn = document.getElementById('theme-toggle-btn');
        if (themeToggleBtn) {
            themeToggleBtn.addEventListener('click', function() {
                // Let clientside.js handle the actual theme change
                // This is just to ensure we re-apply our custom features after theme change
                setTimeout(function() {
                    adjustPlotlyLegends();
                    fixHamburgerMenu();
                }, 100);
            });
        }
    }, 1000);
});

// Also run the fix when the window resizes
window.addEventListener('resize', function() {
    if (window.innerWidth <= 768) {
        fixHamburgerMenu();
    }
});
