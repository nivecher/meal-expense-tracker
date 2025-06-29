/**
 * Restaurant Search Initialization
 * Handles the initialization of the restaurant search page
 */

/**
 * Initialize the restaurant search page
 */
function init() {
    // The restaurant-search.js module will be loaded by the module-loader
    // based on the data-module="restaurant-search" attribute on the form
    console.log('Restaurant search page initialized');
}

// Initialize when the DOM is fully loaded
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    // DOMContentLoaded has already fired
    init();
}

// Export for testing
export { init };
