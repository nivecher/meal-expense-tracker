/**
 * Initialize search page functionality
 * Handles setting up the search form with any URL parameters
 */

/**
 * Initialize the search form with URL parameters
 */
function initSearchForm() {
    // Check if we have a search query in the URL
    const urlParams = new URLSearchParams(window.location.search);
    const searchQuery = urlParams.get('q');

    // If there's a search query, set it in the search input
    if (searchQuery) {
        const searchForm = document.getElementById('restaurant-search-form');
        if (searchForm) {
            const searchInput = searchForm.querySelector('input[name="q"]');
            if (searchInput) {
                searchInput.value = searchQuery;
                // The search will be triggered by the main module
            }
        }
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', initSearchForm);

// Export the function for use in other modules
export { initSearchForm };
