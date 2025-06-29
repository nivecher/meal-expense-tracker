/**
 * Restaurant List View Module
 * Handles view mode toggling, sorting, and other UI interactions for the restaurant list page
 */

/**
 * Toggle the sort order and submit the form
 */
function toggleSortOrder() {
    const sortOrder = document.getElementById('sortOrder');
    if (sortOrder) {
        sortOrder.value = sortOrder.value === 'asc' ? 'desc' : 'asc';
        document.querySelector('form')?.submit();
    }
}

/**
 * Initialize sort order toggle button
 */
function initSortOrderToggle() {
    const toggleButton = document.getElementById('toggleSortOrder');
    if (toggleButton) {
        toggleButton.addEventListener('click', toggleSortOrder);
    }
}

/**
 * Initialize the restaurant list view functionality
 */
function initRestaurantListView() {
    // Get view mode from URL parameter, then localStorage, or default to 'card'
    const urlParams = new URLSearchParams(window.location.search);
    const urlViewMode = urlParams.get('view');
    const savedViewMode = urlParams.get('view') || localStorage.getItem('restaurantViewMode') || 'card';

    // Update the radio button and view
    const viewRadio = document.getElementById(`${savedViewMode}View`);
    if (viewRadio) {
        viewRadio.checked = true;
    }

    // Show the correct view
    document.querySelectorAll('.view-mode').forEach(el => {
        if (el.id === `${savedViewMode}View`) {
            el.classList.remove('d-none');
        } else {
            el.classList.add('d-none');
        }
    });

    // Update localStorage with current view mode
    localStorage.setItem('restaurantViewMode', savedViewMode);

    // Add event listeners for view mode toggles
    document.querySelectorAll('input[name="viewMode"]').forEach(radio => {
        radio.addEventListener('change', function() {
            const viewMode = this.id.replace('View', '');
            localStorage.setItem('restaurantViewMode', viewMode);

            // Update the URL with the view parameter and reload
            const url = new URL(window.location.href);
            url.searchParams.set('view', viewMode);
            window.location.href = url.toString();
        });
    });

    // Make table rows clickable
    document.querySelectorAll('.restaurant-table tbody tr').forEach(row => {
        row.addEventListener('click', function(e) {
            // Don't navigate if the click was on a button or link
            if (!e.target.closest('a, button, .btn, [data-bs-toggle]')) {
                const link = this.querySelector('a[href]');
                if (link) {
                    window.location.href = link.href;
                }
            }
        });
    });

    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.forEach(tooltipTriggerEl => {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize sort order toggle
    initSortOrderToggle();
}

// Initialize when the DOM is fully loaded
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initRestaurantListView);
} else {
    // DOMContentLoaded has already fired
    initRestaurantListView();
}

// Export for testing
export { initRestaurantListView };
