(function() {
  // Global flags and storage
  let mutationTimeout;
  window.splashScreenShown = false;
  window.initialLoadComplete = false;
  window.mapInstructionsShown = {};

  // ---------------------------
  // Initialization
  // ---------------------------
  document.addEventListener('DOMContentLoaded', function() {
    console.log('All Features script loaded');
    // Give Dash time to initialize components
    setTimeout(setupCustomFeatures, 500);
    // Set up mutation observer to re-run features on DOM changes
    setupMutationObserver();
  });

  // ---------------------------
  // Main Setup Function
  // ---------------------------
  function setupCustomFeatures() {
    fixHamburgerMenu();
    setupScrollAnimations();
    hideDebugMenu();
    adjustNavbarLayout(); // On mobile, this will hide the top navbar
    adjustPlotlyForMobile();
    if (window.innerWidth <= 768) {
      initMobileOptimizations();
    }
    lazyLoadGraphs();
    fixBoroughClickOnMobile();
    improveDoubleTapInteraction();
    restoreAnimations();
    enhanceShowAllButtons();
    console.log('Custom features initialized');
  }

  // ---------------------------
  // Lazy Load Graphs
  // ---------------------------
  function lazyLoadGraphs() {
    const graphContainers = document.querySelectorAll('.graph-container');
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          const graphElem = entry.target.querySelector('[id^="graph-"]');
          if (graphElem && window.dash_clientside && window.dash_clientside.clientside.loadGraph) {
            window.dash_clientside.clientside.loadGraph(graphElem.id);
          }
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.1 });
    graphContainers.forEach(container => observer.observe(container));
  }

  // ---------------------------
  // Map Interaction Overlay
  // ---------------------------
  function addMapInteractionOverlay(map) {
    if (map.querySelector('.double-tap-overlay') || window.mapInstructionsShown[map.id]) return;
    window.mapInstructionsShown[map.id] = true;
    const overlay = document.createElement('div');
    overlay.className = 'double-tap-overlay';
    overlay.innerHTML = `
      <div class="tap-instruction">
        <div class="tap-icon">
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M8 13v4m0 0l4 4m-4-4l-4 4"/>
            <path d="M13 13v4m0 0l4 4m-4-4l-4 4"/>
            <circle cx="12" cy="7" r="4"/>
          </svg>
        </div>
        <div class="tap-text">Double-Tap to Interact</div>
      </div>
    `;
    overlay.style.position = 'absolute';
    overlay.style.top = '0';
    overlay.style.left = '0';
    overlay.style.width = '100%';
    overlay.style.height = '100%';
    overlay.style.backgroundColor = 'rgba(0,0,0,0.5)';
    overlay.style.display = 'flex';
    overlay.style.alignItems = 'center';
    overlay.style.justifyContent = 'center';
    overlay.style.color = '#fff';
    overlay.style.zIndex = '999';
    overlay.style.borderRadius = '8px';

    // Ensure the container is positioned relatively
    const container = map.closest('.dash-graph') || map.parentElement;
    if (container) {
      container.style.position = 'relative';
      container.appendChild(overlay);
    } else {
      map.style.position = 'relative';
      map.appendChild(overlay);
    }
    // Inject overlay CSS if not already present
    if (!document.getElementById('double-tap-styles')) {
      const style = document.createElement('style');
      style.id = 'double-tap-styles';
      style.textContent = `
        .double-tap-overlay {
          transition: opacity 0.5s ease;
        }
        .tap-instruction {
          background-color: rgba(30, 144, 255, 0.8);
          padding: 15px 20px;
          border-radius: 12px;
          text-align: center;
          box-shadow: 0 4px 12px rgba(0,0,0,0.3);
          animation: pulse-overlay 2s infinite;
        }
        .tap-icon {
          margin: 0 auto 10px;
          animation: tap-animation 2s infinite;
        }
        .tap-text {
          font-size: 18px;
          font-weight: bold;
        }
        @keyframes pulse-overlay {
          0% { transform: scale(1); }
          50% { transform: scale(1.05); }
          100% { transform: scale(1); }
        }
        @keyframes tap-animation {
          0% { transform: translateY(0); opacity: 0.7; }
          50% { transform: translateY(3px); opacity: 1; }
          100% { transform: translateY(0); opacity: 0.7; }
        }
      `;
      document.head.appendChild(style);
    }
    let lastTap = 0;
    overlay.addEventListener('click', function(e) {
      const currentTime = new Date().getTime();
      if (currentTime - lastTap < 500 && currentTime - lastTap > 0) {
        overlay.style.opacity = '0';
        setTimeout(() => overlay.remove(), 500);
      }
      lastTap = currentTime;
    });
    // Auto-remove overlay after 6 seconds if still present
    setTimeout(() => {
      if (overlay.parentElement) {
        overlay.style.opacity = '0';
        setTimeout(() => overlay.remove(), 500);
      }
    }, 6000);
  }

  // ---------------------------
  // Map Touch Interactions
  // ---------------------------
  function improveMapTouchInteractions() {
    const maps = document.querySelectorAll('.js-plotly-plot');
    maps.forEach(map => {
      if (!map.dataset.touchOptimized) {
        let startDist = 0;
        let lastTapTime = 0;
        // Double-tap to zoom
        map.addEventListener('touchend', (e) => {
          const currentTime = new Date().getTime();
          if (currentTime - lastTapTime < 500 && currentTime - lastTapTime > 0) {
            if (map._fullLayout && map._fullLayout.mapbox) {
              const currentZoom = map._fullLayout.mapbox.zoom || 9;
              Plotly.relayout(map, {'mapbox.zoom': currentZoom + 1});
            }
            e.preventDefault();
          }
          lastTapTime = currentTime;
        });
        // Pinch-to-zoom gesture
        map.addEventListener('touchstart', (e) => {
          if (e.touches.length === 2) {
            startDist = Math.hypot(
              e.touches[0].pageX - e.touches[1].pageX,
              e.touches[0].pageY - e.touches[1].pageY
            );
          }
        });
        map.addEventListener('touchmove', (e) => {
          if (e.touches.length === 2 && startDist > 0) {
            const currentDist = Math.hypot(
              e.touches[0].pageX - e.touches[1].pageX,
              e.touches[0].pageY - e.touches[1].pageY
            );
            const scale = currentDist / startDist;
            if (map._fullLayout && scale !== 1) {
              const zoomLevel = scale > 1 ? 1.1 : 0.9;
              Plotly.relayout(map, {'mapbox.zoom': (map._fullLayout.mapbox.zoom || 9) * zoomLevel});
              startDist = currentDist;
            }
          }
        });
        map.dataset.touchOptimized = "true";
        if ((map.id === "borough-map" || map.id.includes("map")) && !map.dataset.overlayAdded) {
          addMapInteractionOverlay(map);
          map.dataset.overlayAdded = "true";
        }
      }
    });
  }

  // ---------------------------
  // Bottom Sheet Navigation (Mobile)
  // ---------------------------
  function addBottomSheetNavigation() {
    if (document.querySelector('.mobile-bottom-nav')) return;
    const bottomNav = document.createElement('div');
    bottomNav.className = 'mobile-bottom-nav';
    bottomNav.innerHTML = `
      <div class="mobile-nav-item" data-page="dashboard" role="button" tabindex="0">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <rect x="3" y="3" width="7" height="9" />
          <rect x="14" y="3" width="7" height="5" />
          <rect x="14" y="12" width="7" height="9" />
          <rect x="3" y="16" width="7" height="5" />
        </svg>
        <span>Dashboard</span>
      </div>
      <div class="mobile-nav-item" data-page="comparison" role="button" tabindex="0">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="18" y1="20" x2="18" y2="10" />
          <line x1="12" y1="20" x2="12" y2="4" />
          <line x1="6" y1="20" x2="6" y2="14" />
        </svg>
        <span>Compare</span>
      </div>
      <div class="mobile-nav-item" data-page="feedback" role="button" tabindex="0">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"></path>
        </svg>
        <span>Models</span>
      </div>
      <div class="mobile-nav-item" data-page="settings" role="button" tabindex="0">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="3"></circle>
          <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
        </svg>
        <span>Settings</span>
      </div>
    `;
    document.body.appendChild(bottomNav);
    if (!document.getElementById('mobile-bottom-nav-styles')) {
      const style = document.createElement('style');
      style.id = 'mobile-bottom-nav-styles';
      style.textContent = `
        .mobile-bottom-nav {
          display: none;
          position: fixed;
          bottom: 0;
          left: 0;
          right: 0;
          height: 60px;
          background-color: #2c3035;
          box-shadow: 0 -2px 10px rgba(0,0,0,0.1);
          z-index: 1000;
          justify-content: space-around;
          align-items: center;
          padding-bottom: env(safe-area-inset-bottom);
        }
        .mobile-nav-item {
          display: flex;
          flex-direction: column;
          align-items: center;
          color: #e0e0e0;
          padding: 8px 12px;
          opacity: 0.7;
          transition: opacity 0.3s;
        }
        .mobile-nav-item.active {
          opacity: 1;
          color: #1E90FF;
        }
        .mobile-nav-item span {
          font-size: 12px;
          margin-top: 4px;
        }
        .dark-theme .mobile-bottom-nav {
          background-color: #2c3035;
        }
        .light-theme .mobile-bottom-nav {
          background-color: #ffffff;
          border-top: 1px solid #eaeaea;
        }
        .light-theme .mobile-nav-item {
          color: #333;
        }
        @media (max-width: 768px) {
          /* Hide top navbar on mobile */
          .navbar { display: none !important; }
          .mobile-bottom-nav { display: flex; }
          #page-content { padding-top: 0 !important; padding-bottom: 70px !important; }
        }
      `;
      document.head.appendChild(style);
    }
    document.querySelectorAll('.mobile-nav-item').forEach(item => {
      item.addEventListener('click', function() {
        const page = this.getAttribute('data-page');
        window.location.href = '/' + page;
      });
      item.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          const page = this.getAttribute('data-page');
          window.location.href = '/' + page;
        }
      });
    });
    const currentPath = window.location.pathname;
    document.querySelectorAll('.mobile-nav-item').forEach(item => {
      const page = item.getAttribute('data-page');
      if (currentPath === '/' + page || (currentPath === '/' && page === 'dashboard')) {
        item.classList.add('active');
      }
    });
  }

  // Enhance mobile filters with proper modal toggling (attach listener only once)
  function enhanceMobileFilters() {
    if (window.innerWidth > 768) return;
    const filtersBtn = document.getElementById('toggle-filters-btn');
    if (!filtersBtn) return;
    if (!filtersBtn.dataset.listenerAdded) {
      filtersBtn.addEventListener('click', function() {
        let filterModal = document.getElementById('filter-modal');
        if (filterModal && filterModal.style.display === 'block') {
          filterModal.classList.remove('active');
          setTimeout(() => { filterModal.style.display = 'none'; }, 300);
          return;
        }
        if (!filterModal) {
          filterModal = document.createElement('div');
          filterModal.id = 'filter-modal';
          filterModal.className = 'filter-modal';
          filterModal.innerHTML = `
            <div class="filter-modal-content" role="dialog" aria-modal="true" aria-labelledby="filterModalTitle">
              <div class="filter-modal-header">
                <h3 id="filterModalTitle">Filters</h3>
                <button class="close-modal" aria-label="Close Filters Modal">×</button>
              </div>
              <div class="filter-modal-body">
                <!-- Filters will be moved here -->
              </div>
              <div class="filter-modal-footer">
                <button id="apply-filters" class="reset-button">Apply Filters</button>
              </div>
            </div>
          `;
          document.body.appendChild(filterModal);
          if (!document.getElementById('filter-modal-styles')) {
            const modalStyle = document.createElement('style');
            modalStyle.id = 'filter-modal-styles';
            modalStyle.textContent = `
              .filter-modal {
                display: none;
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                z-index: 2000;
                background-color: rgba(0,0,0,0.5);
                overflow: hidden;
              }
              .filter-modal-content {
                position: absolute;
                bottom: 0;
                left: 0;
                right: 0;
                max-height: 80vh;
                background-color: #121212;
                border-top-left-radius: 16px;
                border-top-right-radius: 16px;
                overflow-y: auto;
                transform: translateY(100%);
                transition: transform 0.3s ease;
              }
              .filter-modal.active .filter-modal-content {
                transform: translateY(0);
              }
              .filter-modal-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 16px;
                border-bottom: 1px solid rgba(255,255,255,0.1);
              }
              .close-modal {
                background: none;
                border: none;
                color: #e0e0e0;
                font-size: 24px;
                cursor: pointer;
              }
              .filter-modal-body {
                padding: 16px;
              }
              .filter-modal-footer {
                padding: 16px;
                border-top: 1px solid rgba(255,255,255,0.1);
                text-align: center;
              }
              .light-theme .filter-modal-content {
                background-color: #ffffff;
              }
              .light-theme .close-modal {
                color: #333;
              }
              .light-theme .filter-modal-header,
              .light-theme .filter-modal-footer {
                border-color: rgba(0,0,0,0.1);
              }
            `;
            document.head.appendChild(modalStyle);
          }
          filterModal.addEventListener('click', function(e) {
            if (e.target === filterModal) {
              filterModal.classList.remove('active');
              setTimeout(() => { filterModal.style.display = 'none'; }, 300);
            }
          });
          filterModal.querySelector('.close-modal').addEventListener('click', function() {
            filterModal.classList.remove('active');
            setTimeout(() => { filterModal.style.display = 'none'; }, 300);
          });
          document.getElementById('apply-filters').addEventListener('click', function() {
            filterModal.classList.remove('active');
            setTimeout(() => { filterModal.style.display = 'none'; }, 300);
          });
        }
        filterModal.style.display = 'block';
        setTimeout(() => { filterModal.classList.add('active'); }, 10);
      });
      filtersBtn.dataset.listenerAdded = "true";
    }
  }
  
  function addPullToRefresh() {
    const container = document.querySelector('.dashboard-scroll-container');
    if (!container) return;
    if (container.querySelector('.pull-indicator')) return;
    const pullIndicator = document.createElement('div');
    pullIndicator.className = 'pull-indicator';
    pullIndicator.innerHTML = `
        <div class="pull-icon"></div>
        <div class="pull-text">Pull to refresh</div>
    `;
    container.prepend(pullIndicator);
    if (!document.getElementById('pull-indicator-styles')) {
      const pullStyles = document.createElement('style');
      pullStyles.id = 'pull-indicator-styles';
      pullStyles.textContent = `
          .pull-indicator {
            height: 0;
            overflow: hidden;
            text-align: center;
            transition: height 0.2s;
            color: #1E90FF;
          }
          .pull-icon {
            margin: 10px auto;
            width: 24px;
            height: 24px;
            border: 2px solid #1E90FF;
            border-top-color: transparent;
            border-radius: 50%;
          }
          .pull-icon.refreshing {
            animation: spin 1s linear infinite;
          }
          @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
          }
          .pull-text {
            margin: 5px 0 10px;
            font-size: 14px;
          }
      `;
      document.head.appendChild(pullStyles);
    }
    let startY = 0, distY = 0;
    const threshold = 70;
    container.addEventListener('touchstart', (e) => {
      if (container.scrollTop === 0) {
        startY = e.touches[0].pageY;
      }
    });
    container.addEventListener('touchmove', (e) => {
      if (startY > 0 && container.scrollTop === 0) {
        distY = e.touches[0].pageY - startY;
        if (distY > 0) {
          e.preventDefault();
          const height = Math.min(distY, threshold);
          pullIndicator.style.height = `${height}px`;
          pullIndicator.querySelector('.pull-text').textContent = height >= threshold ? 'Release to refresh' : 'Pull to refresh';
        }
      }
    });
    container.addEventListener('touchend', () => {
      if (distY >= threshold) {
        pullIndicator.querySelector('.pull-icon').classList.add('refreshing');
        pullIndicator.querySelector('.pull-text').textContent = 'Refreshing...';
        if (window.dash_clientside && window.dash_clientside.clientside.resetCache) {
          window.dash_clientside.clientside.resetCache().then(() => {
            setTimeout(() => {
              pullIndicator.style.height = '0';
              pullIndicator.querySelector('.pull-icon').classList.remove('refreshing');
              startY = 0;
              distY = 0;
            }, 1000);
          });
        } else {
          setTimeout(() => {
            pullIndicator.style.height = '0';
            pullIndicator.querySelector('.pull-icon').classList.remove('refreshing');
            startY = 0;
            distY = 0;
          }, 1000);
        }
      } else {
        pullIndicator.style.height = '0';
        startY = 0;
        distY = 0;
      }
    });
  }
  
  function createSimplifiedMobileView() {
    if (window.innerWidth > 768) return;
    const dashboardContent = document.querySelector('.dashboard-scroll-container');
    if (!dashboardContent) return;
    if (dashboardContent.querySelector('.mobile-summary-card')) return;
    const mobileSummary = document.createElement('div');
    mobileSummary.className = 'mobile-summary-card';
    mobileSummary.innerHTML = `
        <div class="mobile-stats-container">
          <h3>Quick Stats</h3>
          <div class="mobile-stats-grid">
            <div class="mobile-stat">
              <span class="stat-value" id="mobile-total-crimes">...</span>
              <span class="stat-label">Total Crimes</span>
            </div>
            <div class="mobile-stat">
              <span class="stat-value" id="mobile-top-crime">...</span>
              <span class="stat-label">Top Crime</span>
            </div>
            <div class="mobile-stat">
              <span class="stat-value" id="mobile-top-borough">...</span>
              <span class="stat-label">Highest Borough</span>
            </div>
            <div class="mobile-stat">
              <span class="stat-value" id="mobile-trend">...</span>
              <span class="stat-label">Month Trend</span>
            </div>
          </div>
        </div>
        <div class="mobile-quick-filters">
          <h3>Quick Filters</h3>
          <div class="mobile-filter-chips">
            <span class="filter-chip active" data-filter="all">All Crimes</span>
            <span class="filter-chip" data-filter="robbery">Robbery</span>
            <span class="filter-chip" data-filter="violence">Violence</span>
            <span class="filter-chip" data-filter="burglary">Burglary</span>
            <span class="filter-chip" data-filter="vehicle">Vehicle Crime</span>
          </div>
        </div>
    `;
    dashboardContent.insertBefore(mobileSummary, dashboardContent.firstChild);
    if (!document.getElementById('mobile-summary-styles')) {
      const mobileStyles = document.createElement('style');
      mobileStyles.id = 'mobile-summary-styles';
      mobileStyles.textContent = `
          .mobile-summary-card {
            margin: 10px 5px 20px;
            padding: 15px;
            border-radius: 12px;
            background-color: #1f1f1f;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
          }
          .light-theme .mobile-summary-card {
            background-color: #ffffff;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
          }
          .mobile-stats-container h3,
          .mobile-quick-filters h3 {
            margin-top: 0;
            margin-bottom: 12px;
            font-size: 16px;
            color: #1E90FF;
          }
          .mobile-stats-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
          }
          .mobile-stat {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 10px;
            background-color: rgba(30, 144, 255, 0.1);
            border-radius: 8px;
            text-align: center;
          }
          .stat-value {
            font-size: 18px;
            font-weight: bold;
            margin-bottom: 4px;
          }
          .stat-label {
            font-size: 12px;
            opacity: 0.7;
          }
          .mobile-quick-filters {
            margin-top: 15px;
          }
          .mobile-filter-chips {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
          }
          .filter-chip {
            display: inline-block;
            padding: 6px 12px;
            background-color: rgba(255,255,255,0.1);
            border-radius: 20px;
            font-size: 12px;
            cursor: pointer;
          }
          .light-theme .filter-chip {
            background-color: rgba(0,0,0,0.05);
          }
          .filter-chip.active {
            background-color: #1E90FF;
            color: white;
          }
      `;
      document.head.appendChild(mobileStyles);
    }
    document.querySelectorAll('.filter-chip').forEach(chip => {
      chip.addEventListener('click', function() {
        document.querySelectorAll('.filter-chip').forEach(c => c.classList.remove('active'));
        this.classList.add('active');
        const filterValue = this.getAttribute('data-filter');
        // TODO: Implement filtering logic based on filterValue
      });
    });
    document.getElementById('mobile-total-crimes').textContent = "12,345";
    document.getElementById('mobile-top-crime').textContent = "Theft";
    document.getElementById('mobile-top-borough').textContent = "Westminster";
    document.getElementById('mobile-trend').textContent = "↑ 3.2%";
}
function optimizeMobileCharts() {
  if (window.innerWidth > 768) return;
  const charts = document.querySelectorAll('.js-plotly-plot');
  charts.forEach(chart => {
    if (!chart.dataset.chartOptimized) {
      // Disable double click zoom
      chart.on('plotly_doubleclick', () => false);
      
      // Configure the chart for mobile
      if (chart._context) {
        chart._context.scrollZoom = false;
        chart._context.modeBarButtonsToRemove = ['zoomIn', 'zoomOut', 'pan'];
        chart._context.displayModeBar = false;
      }

      // Update layout for mobile
      const mobileLayout = {
        'dragmode': false,
        'fixedrange': true,
        'yaxis.fixedrange': true,
        'xaxis.fixedrange': true,
        'coloraxis.showscale': false,  // Hide colorbar
        'showscale': false  // Hide colorbar (alternative property)
      };

      // Add specific layout updates for different chart types
      if (chart.id === 'borough-map' || chart.id === 'crime-heatmap') {
        Object.assign(mobileLayout, {
          'mapbox.style': 'carto-positron',
          'colorbar': { visible: false },
          'coloraxis.colorbar': { visible: false }
        });
      }

      // Apply the layout changes
      Plotly.relayout(chart, mobileLayout);

      // Hide any existing colorbars using CSS
      const colorbars = chart.querySelectorAll('.colorbar');
      colorbars.forEach(colorbar => {
        colorbar.style.display = 'none';
      });

      // Add touch-action CSS to allow scrolling
      chart.style.touchAction = 'pan-y';
      const mainSvg = chart.querySelector('.main-svg');
      if (mainSvg) {
        mainSvg.style.touchAction = 'pan-y';
      }
      
      // Add specific handling for borough map
      if (chart.id === 'borough-map') {
        let touchStartY = 0;
        let isTouchScrolling = false;

        chart.addEventListener('touchstart', (e) => {
          if (e.touches.length === 1) {
            touchStartY = e.touches[0].clientY;
            isTouchScrolling = false;
          }
        }, { passive: true });

        chart.addEventListener('touchmove', (e) => {
          if (e.touches.length === 1) {
            const touchY = e.touches[0].clientY;
            const deltaY = Math.abs(touchY - touchStartY);
            
            // If vertical movement is significant, mark as scrolling
            if (deltaY > 10) {
              isTouchScrolling = true;
            }
            
            // Only prevent default if it's not a scroll attempt
            if (!isTouchScrolling) {
              e.preventDefault();
            }
          }
        }, { passive: false });

        // Handle click/tap events separately
        chart.addEventListener('touchend', (e) => {
          if (!isTouchScrolling && e.changedTouches.length === 1) {
            const touch = e.changedTouches[0];
            const targetElement = document.elementFromPoint(touch.clientX, touch.clientY);
            
            if (targetElement && targetElement.closest('.choroplethlayer')) {
              // Handle borough selection
              const boroughElement = targetElement.closest('.choroplethlayer');
              const boroughName = boroughElement.getAttribute('text') || 
                                boroughElement.getAttribute('data-borough');
              
              if (boroughName) {
                const clickEvent = new CustomEvent('plotly_click', {
                  bubbles: true,
                  detail: {
                    points: [{
                      curveNumber: 1,
                      pointNumber: 0,
                      pointIndex: 0,
                      text: boroughName,
                      customdata: boroughName
                    }]
                  }
                });
                chart.dispatchEvent(clickEvent);
              }
            }
          }
        });
      }

      // Add CSS to hide colorbars on mobile
      if (!document.getElementById('mobile-chart-styles')) {
        const style = document.createElement('style');
        style.id = 'mobile-chart-styles';
        style.textContent = `
          @media (max-width: 768px) {
            .js-plotly-plot .colorbar {
              display: none !important;
            }
          }
        `;
        document.head.appendChild(style);
      }

      chart.dataset.chartOptimized = "true";
    }
  });
}

function addSplashScreen() {
    if (document.querySelector('.splash-screen') || window.splashScreenShown) return;
    window.splashScreenShown = true;
    const splash = document.createElement('div');
    splash.className = 'splash-screen';
    splash.id = 'main-splash-screen';
    splash.innerHTML = `
        <div class="splash-content">
          <div class="splash-logo" role="img" aria-label="UK Crime Data Logo">
            <svg width="80" height="80" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <title>UK Crime Data Logo</title>
              <circle cx="12" cy="12" r="10" />
              <path d="M8 14s1.5 2 4 2 4-2 4-2" />
              <line x1="9" y1="9" x2="9.01" y2="9" />
              <line x1="15" y1="9" x2="15.01" y2="9" />
            </svg>
          </div>
          <div class="splash-title">UK Crime Data</div>
          <div class="splash-spinner"></div>
        </div>
    `;
    document.body.appendChild(splash);
    if (!document.getElementById('splash-screen-styles')) {
        const splashStyles = document.createElement('style');
        splashStyles.id = 'splash-screen-styles';
        splashStyles.textContent = `
          .splash-screen {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background-color: #121212;
            z-index: 10000;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: opacity 0.5s ease;
          }
          .light-theme .splash-screen {
            background-color: #ffffff;
          }
          .splash-content {
            text-align: center;
          }
          .splash-logo {
            color: #1E90FF;
            animation: pulse 2s infinite;
          }
          .splash-title {
            margin-top: 20px;
            font-size: 24px;
            font-weight: bold;
            color: #e0e0e0;
          }
          .light-theme .splash-title {
            color: #333;
          }
          .splash-spinner {
            margin: 20px auto 0;
            width: 40px;
            height: 40px;
            border: 4px solid rgba(30, 144, 255, 0.2);
            border-top-color: #1E90FF;
            border-radius: 50%;
            animation: spin 1s linear infinite;
          }
          @keyframes pulse {
            0% { transform: scale(1); }
            50% { transform: scale(1.1); }
            100% { transform: scale(1); }
          }
          @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
          }
          @keyframes pulse-overlay {
            0% { transform: scale(1); opacity: 1; }
            50% { transform: scale(1.05); opacity: 0.7; }
            100% { transform: scale(1); opacity: 1; }
          }
        `;
        document.head.appendChild(splashStyles);
    }
    const removeSplash = () => {
        const splashElement = document.querySelector('.splash-screen');
        if (splashElement) {
            splashElement.style.opacity = '0';
            setTimeout(() => {
                if (splashElement.parentElement) {
                    splashElement.remove();
                }
            }, 500);
        }
    };
    if (document.readyState === 'complete') {
        setTimeout(removeSplash, 1000);
    } else {
        window.addEventListener('load', () => {
            setTimeout(removeSplash, 1000);
        }, { once: true });
    }
}
  
function initMobileOptimizations() {
    requestAnimationFrame(() => {
        if (window.innerWidth <= 768) {
            addBottomSheetNavigation();
            enhanceMobileFilters();
            addPullToRefresh();
            createSimplifiedMobileView();
            optimizeMobileCharts();
            improveMapTouchInteractions();
            enhanceMobileBorough();
        }
        if (!window.initialLoadComplete) {
            addSplashScreen();
            window.initialLoadComplete = true;
        }
        lazyLoadGraphs();
    });
}
  
window.addEventListener('DOMContentLoaded', initMobileOptimizations);
  
const mobileObserver = new MutationObserver((mutations) => {
    const significantChanges = mutations.some(mutation => {
        return mutation.type === 'childList' && 
               (mutation.addedNodes.length > 0 || mutation.removedNodes.length > 0);
    });
    if (significantChanges) {
        if (mutationTimeout) clearTimeout(mutationTimeout);
        mutationTimeout = setTimeout(() => {
            lazyLoadGraphs();
            if (window.innerWidth <= 768) {
                optimizeMobileCharts();
                improveMapTouchInteractions();
                enhanceMobileBorough();
            }
        }, 300);
    }
});
  
mobileObserver.observe(document.body, { childList: true, subtree: true });

// ---------------------------
// NEW FIX #1: Borough Click on Mobile
// ---------------------------
function fixBoroughClickOnMobile() {
  const maps = document.querySelectorAll('.js-plotly-plot');
  maps.forEach(map => {
    if (map.id === 'borough-map' && !map.dataset.mobileClickFixed) {
      let touchStartTime = 0;
      let touchStartX = 0;
      let touchStartY = 0;
      const CLICK_THRESHOLD = 200; // ms
      const MOVE_THRESHOLD = 10; // pixels

      function createPlotlyClickEvent(element, touch, boroughName) {
        // Get the map's layout data
        const layout = map._fullLayout;
        const mapbox = layout.mapbox;
        
        // Calculate relative coordinates
        const rect = map.getBoundingClientRect();
        const x = touch.clientX - rect.left;
        const y = touch.clientY - rect.top;
        
        // Create bbox similar to Plotly's format
        const bbox = {
          x0: x - 1,
          x1: x + 1,
          y0: y - 1,
          y1: y + 1
        };

        // Create the event that matches Plotly's format exactly
        return new CustomEvent('plotly_click', {
          bubbles: true,
          detail: {
            points: [{
              curveNumber: 1,  // This matches the desktop format
              pointNumber: 0,
              pointIndex: 0,
              lon: mapbox ? mapbox.center.lon : -0.1278,
              lat: mapbox ? mapbox.center.lat : 51.5074,
              text: boroughName,
              bbox: bbox,
              customdata: boroughName
            }]
          }
        });
      }

      // Function to find the borough name
      function findBoroughName(element) {
        // Try various methods to get the borough name
        return element.getAttribute('data-borough') || 
               element.getAttribute('text') ||
               element.textContent ||
               element.closest('[data-borough]')?.getAttribute('data-borough') ||
               element.closest('[text]')?.getAttribute('text');
      }

      map.addEventListener('touchstart', function(e) {
        if (e.touches.length === 1) {
          const touch = e.touches[0];
          touchStartTime = Date.now();
          touchStartX = touch.clientX;
          touchStartY = touch.clientY;
        }
      });

      map.addEventListener('touchend', function(e) {
        if (e.changedTouches.length === 1) {
          const touch = e.changedTouches[0];
          const touchEndTime = Date.now();
          const touchDuration = touchEndTime - touchStartTime;
          
          // Calculate movement
          const moveX = Math.abs(touch.clientX - touchStartX);
          const moveY = Math.abs(touch.clientY - touchStartY);
          
          // If touch was short and didn't move much, treat as a click
          if (touchDuration < CLICK_THRESHOLD && moveX < MOVE_THRESHOLD && moveY < MOVE_THRESHOLD) {
            const targetElement = document.elementFromPoint(touch.clientX, touch.clientY);
            if (targetElement) {
              // Find the borough name
              const boroughName = findBoroughName(targetElement);
              if (boroughName) {
                // Create and dispatch the Plotly click event
                const plotlyEvent = createPlotlyClickEvent(targetElement, touch, boroughName);
                map.dispatchEvent(plotlyEvent);
                
                // Log the event for debugging
                console.log('Dispatched Plotly click event:', plotlyEvent.detail);
                
                // Force update of the relative crime distribution graph
                const relativeDistGraph = document.getElementById('relative-crime-distribution');
                if (relativeDistGraph) {
                  setTimeout(() => {
                    relativeDistGraph.classList.add('highlight-update');
                    setTimeout(() => relativeDistGraph.classList.remove('highlight-update'), 1000);
                    if (window.Plotly) {
                      window.Plotly.redraw(relativeDistGraph);
                    }
                  }, 100);
                }
                
                // Prevent default behavior
                e.preventDefault();
              }
            }
          }
        }
      });
      
      // Prevent unwanted touch behaviors
      map.addEventListener('touchmove', function(e) {
        if (e.touches.length === 1) {
          const touch = e.touches[0];
          const moveX = Math.abs(touch.clientX - touchStartX);
          const moveY = Math.abs(touch.clientY - touchStartY);
          
          // If movement is small, prevent scrolling
          if (moveX < MOVE_THRESHOLD && moveY < MOVE_THRESHOLD) {
            e.preventDefault();
          }
        }
      }, { passive: false });

      // Disable the plotly tester's pointer events
      const plotlyTester = map.querySelector('.js-plotly-tester');
      if (plotlyTester) {
        plotlyTester.style.pointerEvents = 'none';
      }
      
      map.dataset.mobileClickFixed = "true";
      console.log("Enhanced mobile borough click handler attached");
    }
  });
}

// ---------------------------
// NEW FIX #2: Double-Tap Interaction
// ---------------------------
function improveDoubleTapInteraction() {
  const maps = document.querySelectorAll('.js-plotly-plot');
  maps.forEach(map => {
    if (!map.dataset.doubleTapFixed) {
      let tapCount = 0;
      let lastTap = 0;
      const DOUBLE_TAP_THRESHOLD = 300; // ms
      
      // Add tap counter
      map.addEventListener('touchstart', function(e) {
        // Only count single-finger taps
        if (e.touches.length === 1) {
          const now = new Date().getTime();
          const timeDiff = now - lastTap;
          
          if (timeDiff < DOUBLE_TAP_THRESHOLD && timeDiff > 0) {
            // This is a double tap - enable interactions
            if (map.style.pointerEvents === 'none') {
              map.style.pointerEvents = 'auto';
              
              // Show a quick confirmation visual
              const confirmEl = document.createElement('div');
              confirmEl.className = 'interaction-confirmed';
              confirmEl.textContent = 'Interaction Enabled';
              confirmEl.style.position = 'absolute';
              confirmEl.style.top = '50%';
              confirmEl.style.left = '50%';
              confirmEl.style.transform = 'translate(-50%, -50%)';
              confirmEl.style.backgroundColor = 'rgba(30, 144, 255, 0.8)';
              confirmEl.style.color = 'white';
              confirmEl.style.padding = '10px 15px';
              confirmEl.style.borderRadius = '20px';
              confirmEl.style.fontWeight = 'bold';
              confirmEl.style.zIndex = '1000';
              confirmEl.style.animation = 'fadeOut 1.5s forwards';
              
              const container = map.closest('.dash-graph') || map;
              container.appendChild(confirmEl);
              
              setTimeout(() => {
                if (confirmEl.parentNode) {
                  confirmEl.parentNode.removeChild(confirmEl);
                }
              }, 1500);
              
              // Remove overlay if present
              const overlay = map.querySelector('.double-tap-overlay');
              if (overlay) {
                overlay.style.opacity = '0';
                setTimeout(() => {
                  if (overlay.parentNode) overlay.remove();
                }, 500);
              }
            }
            
            tapCount = 0;
          } else {
            // This is a first tap or too slow for double tap
            tapCount = 1;
          }
          
          lastTap = now;
        }
      });
      
      // Initially disable interactions until double-tapped
      if (map.id === "borough-map" || 
          map.id === "crime-heatmap" || 
          map.id === "lsoa-choropleth-map" ||
          map.id.includes("map")) {
        // Only add overlay if not already added
        if (!map.querySelector('.double-tap-overlay') && !window.mapInstructionsShown[map.id]) {
          addMapInteractionOverlay(map);
        }
      }
      
      map.dataset.doubleTapFixed = "true";
      console.log(`Double-tap handler attached to map: ${map.id || 'unnamed'}`);
    }
  });
  
  // Add CSS animation for confirmation message
  if (!document.getElementById('interaction-styles')) {
    const style = document.createElement('style');
    style.id = 'interaction-styles';
    style.textContent = `
      @keyframes fadeOut {
        0% { opacity: 1; }
        80% { opacity: 0.9; }
        100% { opacity: 0; }
      }
      .highlight-update {
        animation: highlight-pulse 1s ease;
      }
      @keyframes highlight-pulse {
        0% { box-shadow: 0 0 0 0 rgba(30, 144, 255, 0.5); }
        50% { box-shadow: 0 0 0 10px rgba(30, 144, 255, 0.5); }
        100% { box-shadow: 0 0 0 0 rgba(30, 144, 255, 0); }
      }
    `;
    document.head.appendChild(style);
  }
}

// ---------------------------
// NEW FIX #3: Restore Animations
// ---------------------------
function restoreAnimations() {
  // Check if animations are already in the document
  if (!document.getElementById('mobile-animations')) {
    const style = document.createElement('style');
    style.id = 'mobile-animations';
    style.textContent = `
      /* Add back missing animations */
      @keyframes fadeInUp {
        from {
          opacity: 0;
          transform: translateY(30px);
        }
        to {
          opacity: 1;
          transform: translateY(0);
        }
      }
      
      @keyframes pulse {
        0% { transform: scale(1); }
        50% { transform: scale(1.1); }
        100% { transform: scale(1); }
      }
      
      @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
      }
      
      @keyframes pulse-overlay {
        0% { transform: scale(1); opacity: 1; }
        50% { transform: scale(1.05); opacity: 0.7; }
        100% { transform: scale(1); opacity: 1; }
      }
      
      @keyframes tap-animation {
        0% { transform: translateY(0); opacity: 0.7; }
        50% { transform: translateY(3px); opacity: 1; }
        100% { transform: translateY(0); opacity: 0.7; }
      }
      
      /* Apply animations to elements */
      .mobile-summary-card, .summary, .filters-container {
        animation: fadeInUp 0.6s ease-out;
      }
      
      .splash-logo, .mobile-stat {
        animation: pulse 2s infinite;
      }
      
      .splash-spinner, .pull-icon.refreshing {
        animation: spin 1s linear infinite;
      }
      
      .tap-instruction {
        animation: pulse-overlay 2s infinite;
      }
      
      .tap-icon {
        animation: tap-animation 2s infinite;
      }
      
      .reveal {
        opacity: 0;
        visibility: hidden;
        transition: opacity 0.6s ease-out, transform 0.6s ease-out;
        transform: translateY(20px);
      }
      
      .reveal.active {
        opacity: 1;
        visibility: visible;
        transform: translateY(0);
        animation-fill-mode: forwards;
      }
    `;
    document.head.appendChild(style);
    console.log("Restored animations");
  }
  
  // Add intersection observer to create reveal animations
  if (!window.animationObserver) {
    window.animationObserver = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('active');
          window.animationObserver.unobserve(entry.target);
        }
      });
    }, { threshold: 0.1 });
    
    // Apply to dashboard sections that should animate
    document.querySelectorAll('.dashboard-row, .section-title, .summary').forEach(el => {
      if (!el.classList.contains('reveal')) {
        el.classList.add('reveal');
        window.animationObserver.observe(el);
      }
    });
    
    console.log("Set up animation observer");
  }
}

// ---------------------------
// NEW FIX #4: Show All Buttons Enhancement
// ---------------------------
function enhanceShowAllButtons() {
  // Find all Show All and Remove All buttons
  const showAllButtons = [
    ...document.querySelectorAll('[id="show-all-outcomes"]'),
    ...document.querySelectorAll('[id="show-all-crimes"]')
  ];
  
  const removeAllButtons = [
    ...document.querySelectorAll('[id="remove-all-outcomes"]'),
    ...document.querySelectorAll('[id="remove-all-crimes"]')
  ];
  
  // Enhanced click handler for Show All buttons
  showAllButtons.forEach(button => {
    if (!button.dataset.enhancedClickHandler) {
      button.addEventListener('click', function(e) {
        // Find the associated dropdown
        const buttonId = this.id;
        let dropdownId;
        
        if (buttonId === 'show-all-outcomes') {
          dropdownId = 'outcome-type-dropdown';
        } else if (buttonId === 'show-all-crimes') {
          dropdownId = 'crime-type-dropdown';
        }
        
        if (dropdownId) {
          const dropdown = document.getElementById(dropdownId);
          if (dropdown && dropdown._selectInfo) {
            // Get all options from the Dash dropdown
            const options = dropdown._selectInfo.options || [];
            const values = options.map(opt => opt.value);
            
            // Manually set the selected values in the dropdown
            if (window.dash_clientside && window.dash_clientside.callback_context) {
              // Try to trigger a client-side update
              window.updateDropdownSelection(dropdownId, values);
            }
            
            // Visual feedback for users
            button.classList.add('btn-success');
            setTimeout(() => {
              button.classList.remove('btn-success');
            }, 500);
          }
        }
      });
      button.dataset.enhancedClickHandler = 'true';
    }
  });
  
  // Enhanced click handler for Remove All buttons
  removeAllButtons.forEach(button => {
    if (!button.dataset.enhancedClickHandler) {
      button.addEventListener('click', function(e) {
        // Find the associated dropdown
        const buttonId = this.id;
        let dropdownId;
        
        if (buttonId === 'remove-all-outcomes') {
          dropdownId = 'outcome-type-dropdown';
        } else if (buttonId === 'remove-all-crimes') {
          dropdownId = 'crime-type-dropdown';
        }
        
        if (dropdownId) {
          const dropdown = document.getElementById(dropdownId);
          if (dropdown) {
            // Manually clear the dropdown selection
            if (window.dash_clientside && window.dash_clientside.callback_context) {
              // Try to trigger a client-side update
              window.updateDropdownSelection(dropdownId, []);
            }
            
            // Visual feedback for users
            button.classList.add('btn-danger');
            setTimeout(() => {
              button.classList.remove('btn-danger');
            }, 500);
          }
        }
      });
      button.dataset.enhancedClickHandler = 'true';
    }
  });
}

// Helper function to update dropdown selection
window.updateDropdownSelection = function(dropdownId, values) {
  const dropdown = document.getElementById(dropdownId);
  if (!dropdown) return;
  
  // Update the React component's state if possible
  if (dropdown._component && dropdown._component.setProps) {
    dropdown._component.setProps({value: values});
  } else {
    // Fallback: Try to manually trigger a change event
    if (dropdown._selectInfo) {
      dropdown._selectInfo.value = values;
      
      // Dispatch a custom event that Dash might be listening for
      const changeEvent = new CustomEvent('change', {
        bubbles: true,
        detail: {values: values}
      });
      dropdown.dispatchEvent(changeEvent);
    }
  }
};

// Set up the mutation observer to watch for DOM changes
function setupMutationObserver() {
  const observer = new MutationObserver((mutations) => {
    const shouldCheck = mutations.some(mutation => {
      return mutation.type === 'childList' && mutation.addedNodes.length > 0;
    });
    
    if (shouldCheck) {
      if (mutationTimeout) clearTimeout(mutationTimeout);
      mutationTimeout = setTimeout(() => {
        fixBoroughClickOnMobile();
        improveDoubleTapInteraction();
        enhanceShowAllButtons();
        
        // Re-apply animations to new elements
        document.querySelectorAll('.dashboard-row:not(.reveal), .section-title:not(.reveal), .summary:not(.reveal)').forEach(el => {
          el.classList.add('reveal');
          if (window.animationObserver) {
            window.animationObserver.observe(el);
          }
        });
      }, 300);
    }
  });
  
  observer.observe(document.body, {
    childList: true,
    subtree: true
  });
}

// Fix Hamburger Menu (implement if needed)
function fixHamburgerMenu() {
  // Implementation here if needed
}

// Setup Scroll Animations
function setupScrollAnimations() {
  restoreAnimations();
}

// Hide Debug Menu
function hideDebugMenu() {
  // Implementation here if needed
}

// Adjust Navbar Layout
function adjustNavbarLayout() {
  // Implementation here if needed
}

// Adjust Plotly For Mobile
function adjustPlotlyForMobile() {
  // Implementation here if needed
}

// ---------------------------
// Mobile Borough Selection
// ---------------------------
function enhanceMobileBorough() {
  const maps = document.querySelectorAll('.js-plotly-plot');
  maps.forEach(map => {
    if (map.id === 'borough-map' && !map.dataset.mobileEnhanced) {
      // Configure the map for mobile
      if (map._context) {
        map._context.scrollZoom = false;
        map._context.doubleClick = false;
        map._context.displayModeBar = false;
      }

      // Update layout for mobile interaction
      Plotly.relayout(map, {
        'dragmode': false,
        'fixedrange': true,
        'mapbox.scrollZoom': false,
        'clickmode': 'event',
        'hovermode': 'closest',
        'hoverdistance': 5
      });

      // Add touch-action CSS to allow scrolling
      map.style.touchAction = 'pan-y';
      const mainSvg = map.querySelector('.main-svg');
      if (mainSvg) {
        mainSvg.style.touchAction = 'pan-y';
      }

      // Rest of the existing dropdown code...
      // ... (keep the existing dropdown creation code)

      map.dataset.mobileEnhanced = 'true';
    }
  });
}

})();