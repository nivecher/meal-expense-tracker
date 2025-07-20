/**
 * Restaurant Details Page Functionality
 *
 * Handles the interactive elements of the restaurant details page,
 * including edit mode toggling and map initialization.
 */

document.addEventListener('DOMContentLoaded', function() {
    initializeTooltips();
    initializeMap();
    setupEditModeToggle();
});

/**
 * Initialize Bootstrap tooltips
 */
function initializeTooltips() {
    const tooltipTriggerList = [].slice.call(
        document.querySelectorAll('[data-bs-toggle="tooltip"]')
    );

    tooltipTriggerList.forEach(function(tooltipTriggerEl) {
        new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

/**
 * Initialize map if container exists
 */
function initializeMap() {
    const mapContainer = document.getElementById('map-container');
    if (!mapContainer) return;

    const lat = parseFloat(mapContainer.dataset.lat);
    const lng = parseFloat(mapContainer.dataset.lng);

    // This is a placeholder - in a real implementation, you would use a mapping library
    // like Leaflet or Google Maps to display an interactive map
    mapContainer.innerHTML = `
        <div class="ratio ratio-16x9 bg-light">
            <div class="d-flex align-items-center justify-content-center h-100">
                <div class="text-center">
                    <i class="fas fa-map-marker-alt fa-3x text-primary mb-2"></i>
                    <p class="mb-0">Map would be displayed here</p>
                    <small class="text-muted">(Interactive map implementation required)</small>
                </div>
            </div>
        </div>
    `;
}

/**
 * Set up the edit mode toggle functionality
 */
function setupEditModeToggle() {
    const editToggle = document.getElementById('edit-toggle');
    const viewMode = document.getElementById('view-mode');
    const editForm = document.getElementById('edit-form');
    const cancelEdit = document.getElementById('cancel-edit');

    if (!editToggle || !viewMode || !editForm || !cancelEdit) return;

    // Toggle to edit mode
    editToggle.addEventListener('click', function() {
        viewMode.classList.add('d-none');
        editForm.classList.remove('d-none');
        editToggle.classList.add('d-none');

        // Scroll to the form if needed
        editForm.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });

    // Cancel edit mode
    cancelEdit.addEventListener('click', function() {
        viewMode.classList.remove('d-none');
        editForm.classList.add('d-none');
        editToggle.classList.remove('d-none');
    });
}

/**
 * Format currency values consistently
 * @param {number} amount - The amount to format
 * @returns {string} Formatted currency string
 */
function formatCurrency(amount) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }).format(amount);
}

/**
 * Format date strings consistently
 * @param {string} dateString - ISO date string
 * @returns {string} Formatted date string
 */
function formatDate(dateString) {
    const options = { year: 'numeric', month: 'short', day: 'numeric' };
    return new Date(dateString).toLocaleDateString(undefined, options);
}

// Export functions for testing
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        initializeTooltips,
        initializeMap,
        setupEditModeToggle,
        formatCurrency,
        formatDate
    };
}
