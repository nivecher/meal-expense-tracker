/**
 * Restaurant Detail Page Functionality
 * Handles progress bar initialization and edit mode navigation
 */

export function initRestaurantDetail() {
    // Set progress bar width from data attribute
    const progressBar = document.querySelector('[data-width]');
    if (progressBar) {
        progressBar.style.width = progressBar.dataset.width + '%';
    }

    // Handle edit button navigation
    const editBtn = document.getElementById('edit-btn');
    if (editBtn) {
        editBtn.addEventListener('click', function() {
            const restaurantId = editBtn.dataset.restaurantId;
            if (restaurantId) {
                window.location.href = `/restaurants/${restaurantId}?edit=True`;
            }
        });
    }

    // Handle cancel edit button navigation
    const cancelEditBtn = document.getElementById('cancel-edit');
    if (cancelEditBtn) {
        cancelEditBtn.addEventListener('click', function() {
            const restaurantId = cancelEditBtn.dataset.restaurantId;
            if (restaurantId) {
                window.location.href = `/restaurants/${restaurantId}`;
            }
        });
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', initRestaurantDetail);
