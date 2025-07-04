/**
 * Restaurant Search Initialization
 * Handles the initialization of the restaurant search page
 */

import { init as initRestaurantSearch } from './restaurant-search.js';

/**
 * Initialize the restaurant search page
 */
function init() {
    console.log('Initializing restaurant search page...');

    // Check if we're on a page that needs the restaurant search functionality
    const searchForm = document.getElementById('restaurant-search-form');
    const mapContainer = document.getElementById('map');
    const isRestaurantSearchPage = searchForm && mapContainer;

    if (!isRestaurantSearchPage) {
        console.log('Not on restaurant search page, skipping initialization');
        return;
    }

    // Initialize the restaurant search module
    initRestaurantSearch().catch(error => {
        console.error('Failed to initialize restaurant search:', error);

        // Show error message to the user
        const errorContainer = document.createElement('div');
        errorContainer.className = 'alert alert-danger m-3';
        errorContainer.innerHTML = `
            <h5 class="alert-heading">Initialization Error</h5>
            <p class="mb-2">Failed to initialize the restaurant search: ${error.message || 'Unknown error'}</p>
            <button class="btn btn-primary btn-sm mt-2" onclick="window.location.reload()">
                <i class="bi bi-arrow-clockwise me-1"></i> Try Again
            </button>
        `;

        // Insert at the top of the main content
        const mainContent = document.querySelector('main') || document.body;
        if (mainContent.firstChild) {
            mainContent.insertBefore(errorContainer, mainContent.firstChild);
        } else {
            mainContent.appendChild(errorContainer);
        }
    });
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
