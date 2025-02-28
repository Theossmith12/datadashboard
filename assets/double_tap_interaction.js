// Function to initialize double-tap detection on a graph element
function initializeDoubleTap(graph) {
    addDoubleTapOverlay(graph);
    let lastTap = 0;
    const DOUBLE_TAP_THRESHOLD = 300; // ms
    graph.addEventListener('touchstart', function(e) {
        if (e.touches.length === 1) {  // Only consider single-finger taps
            const currentTime = new Date().getTime();
            if (currentTime - lastTap < DOUBLE_TAP_THRESHOLD && currentTime - lastTap > 0) {
                // Double-tap detected: enable interactions
                graph.style.pointerEvents = 'auto';
                const container = graph.parentElement;
                const overlay = container.querySelector('.double-tap-overlay');
                if (overlay) {
                    overlay.style.opacity = '0';
                    setTimeout(() => overlay.remove(), 300);
                }
            }
            lastTap = currentTime;
        }
    });
}

// Initial setup when the DOM loads
document.addEventListener('DOMContentLoaded', function() {
    // Initialize existing graphs
    const graphs = document.querySelectorAll('.js-plotly-plot');
    graphs.forEach(graph => {
        initializeDoubleTap(graph);
    });

    // Use MutationObserver to monitor for new graph elements or changes in the DOM
    const observer = new MutationObserver((mutationsList) => {
        mutationsList.forEach(mutation => {
            if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
                mutation.addedNodes.forEach(node => {
                    if (node.nodeType === 1) { // If it's an element
                        // If the added node is a graph element, initialize it
                        if (node.classList.contains('js-plotly-plot')) {
                            initializeDoubleTap(node);
                        }
                        // Also check for graph elements within the added node
                        const nestedGraphs = node.querySelectorAll && node.querySelectorAll('.js-plotly-plot');
                        if (nestedGraphs && nestedGraphs.length > 0) {
                            nestedGraphs.forEach(graph => {
                                initializeDoubleTap(graph);
                            });
                        }
                    }
                });
            }
        });
    });
    observer.observe(document.body, { childList: true, subtree: true });
});
