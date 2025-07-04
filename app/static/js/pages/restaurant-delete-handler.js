/**
 * Restaurant Delete Handler
 * Handles restaurant deletion with confirmation and AJAX
 */

/**
 * Initialize delete buttons with confirmation and AJAX handling
 */
function initRestaurantDeleteHandler() {
    // Add event listeners to all delete buttons
    document.addEventListener('click', async function(event) {
        const deleteButton = event.target.closest('.btn-delete-restaurant');
        if (!deleteButton) return;

        event.preventDefault();
        event.stopPropagation();

        const restaurantId = deleteButton.dataset.restaurantId;
        const restaurantName = deleteButton.dataset.restaurantName || 'this restaurant';

        // Show confirmation dialog
        const confirmed = await showDeleteConfirmation(restaurantName);
        if (!confirmed) return;

        // Show loading state
        const originalContent = deleteButton.innerHTML;
        deleteButton.disabled = true;
        deleteButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Deleting...';

        try {
            const response = await fetch(`/restaurants/delete/${restaurantId}`, {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCSRFToken()
                },
                credentials: 'same-origin'
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();

            if (data.success) {
                showToast('Restaurant deleted successfully', 'success');

                // Remove the restaurant card/row from the DOM
                const restaurantElement = deleteButton.closest('.restaurant-card, tr');
                if (restaurantElement) {
                    restaurantElement.style.opacity = '0';
                    setTimeout(() => {
                        restaurantElement.remove();
                        // If no restaurants left, show empty state
                        if (document.querySelectorAll('.restaurant-card, .restaurant-table tbody tr').length === 0) {
                            window.location.reload();
                        }
                    }, 300);
                } else {
                    window.location.reload();
                }
            } else {
                throw new Error(data.message || 'Failed to delete restaurant');
            }
        } catch (error) {
            console.error('Error deleting restaurant:', error);
            showToast(error.message || 'An error occurred while deleting the restaurant', 'error');
            deleteButton.innerHTML = originalContent;
            deleteButton.disabled = false;
        }
    });
}

/**
 * Show a confirmation dialog for deletion
 * @param {string} name - The name of the restaurant to delete
 * @returns {Promise<boolean>} - Whether the user confirmed the deletion
 */
function showDeleteConfirmation(name) {
    return new Promise((resolve) => {
        // Use the browser's built-in confirmation dialog
        const confirmed = confirm(`Are you sure you want to delete ${name}? This action cannot be undone.`);
        resolve(confirmed);

        // Alternative: Use a more sophisticated modal if available
        // const modal = new bootstrap.Modal(document.getElementById('deleteConfirmationModal'));
        // const modalElement = document.getElementById('deleteConfirmationModal');
        // const confirmButton = modalElement.querySelector('.btn-confirm-delete');
        //
        // return new Promise((resolve) => {
        //     const confirmHandler = () => {
        //         modal.hide();
        //         resolve(true);
        //     };
        //
        //     confirmButton.addEventListener('click', confirmHandler, { once: true });
        //     modalElement.addEventListener('hidden.bs.modal', () => resolve(false));
        //     modal.show();
        // });
    });
}

/**
 * Get the CSRF token from the page's meta tags
 * @returns {string} The CSRF token
 */
function getCSRFToken() {
    return document.querySelector('meta[name="csrf-token"]')?.content || '';
}

/**
 * Show a toast notification
 * @param {string} message - The message to display
 * @param {string} type - The type of toast (success, error, warning, info)
 */
function showToast(message, type = 'info') {
    // Use Bootstrap's toast if available
    if (typeof bootstrap !== 'undefined' && bootstrap.Toast) {
        const toastContainer = document.getElementById('toastContainer') || createToastContainer();
        const toastId = `toast-${Date.now()}`;

        const toastElement = document.createElement('div');
        toastElement.id = toastId;
        toastElement.className = `toast align-items-center text-white bg-${type} border-0`;
        toastElement.setAttribute('role', 'alert');
        toastElement.setAttribute('aria-live', 'assertive');
        toastElement.setAttribute('aria-atomic', 'true');

        toastElement.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">
                    ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        `;

        toastContainer.appendChild(toastElement);
        const toast = new bootstrap.Toast(toastElement, { autohide: true, delay: 5000 });
        toast.show();

        // Remove toast from DOM after it's hidden
        toastElement.addEventListener('hidden.bs.toast', () => {
            toastElement.remove();
        });
    } else {
        // Fallback to browser alert
        alert(`${type.toUpperCase()}: ${message}`);
    }
}

/**
 * Create a toast container if it doesn't exist
 * @returns {HTMLElement} The toast container element
 */
function createToastContainer() {
    const container = document.createElement('div');
    container.id = 'toastContainer';
    container.className = 'toast-container position-fixed bottom-0 end-0 p-3';
    container.style.zIndex = '1100'; // Above modals
    document.body.appendChild(container);
    return container;
}

// Initialize when the DOM is fully loaded
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initRestaurantDeleteHandler);
} else {
    // DOMContentLoaded has already fired
    initRestaurantDeleteHandler();
}

// Export for testing
export { initRestaurantDeleteHandler, showDeleteConfirmation, showToast };
