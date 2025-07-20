/**
 * Shows a toast notification
 * @param {string} message - The message to display
 * @param {string} type - The type of notification (success, error, info, warning)
 * @param {number} [duration=3000] - Duration in milliseconds to show the toast
 */
function showToast(message, type = 'info', duration = 3000) {
        // Ensure Bootstrap is available
        if (typeof bootstrap === 'undefined' || !bootstrap.Toast) {
            console.warn('Bootstrap Toast not available. Showing fallback notification.');
            alert(type.toUpperCase() + ': ' + message);
            return null;
        }

        // Check if toast container exists, if not create it
        let toastContainer = document.getElementById('toast-container');

        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.id = 'toast-container';
            toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
            document.body.appendChild(toastContainer);
        }

        // Create toast element
        const toastId = 'toast-' + Date.now();
        const toast = document.createElement('div');
        toast.id = toastId;
        toast.className = 'toast';
        toast.setAttribute('role', 'alert');
        toast.setAttribute('aria-live', 'assertive');
        toast.setAttribute('aria-atomic', 'true');

        // Set the toast content based on type
        const toastClass = type === 'error' ? 'bg-danger' : 'bg-' + type;
        toast.innerHTML = `
            <div class="toast-header ${toastClass} text-white">
                <strong class="me-auto">${type.charAt(0).toUpperCase() + type.slice(1)}</strong>
                <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
            <div class="toast-body">
                ${message}
            </div>
        `;

        // Add to container
        toastContainer.appendChild(toast);

        // Initialize and show the toast
        const bsToast = new bootstrap.Toast(toast, {
            autohide: true,
            delay: duration
        });
        bsToast.show();

        // Remove toast from DOM after it's hidden
        toast.addEventListener('hidden.bs.toast', function() {
            toast.remove();
            // Remove container if no more toasts
            if (toastContainer && toastContainer.children.length === 0) {
                toastContainer.remove();
            }
        });

        return bsToast;
    }

    /**
     * Gets the appropriate icon for the toast based on type
     * @param {string} type - The type of notification
     * @returns {string} The icon class
     */
    function getToastIcon(type) {
        const icons = {
            success: 'bi-check-circle-fill',
            error: 'bi-exclamation-triangle-fill',
            warning: 'bi-exclamation-triangle-fill',
            info: 'bi-info-circle-fill'
        };
        return icons[type] || 'bi-info-circle-fill';
    }

    /**
     * Shows a confirmation dialog
     * @param {Object} options - Configuration options
     * @param {string} options.title - Dialog title
     * @param {string} options.message - Dialog message
     * @param {string} [options.confirmText='Confirm'] - Confirm button text
     * @param {string} [options.cancelText='Cancel'] - Cancel button text
     * @param {string} [options.type='warning'] - Dialog type (warning, danger, info, success)
     * @returns {Promise<boolean>} Resolves to true if confirmed, false if cancelled
     */
    function showConfirmDialog({
        title = 'Are you sure?',
        message = 'This action cannot be undone.',
        confirmText = 'Confirm',
        cancelText = 'Cancel',
        type = 'warning'
    } = {}) {
        return new Promise((resolve) => {
            // Ensure Bootstrap is available
            if (typeof bootstrap === 'undefined' || !bootstrap.Modal) {
                console.warn('Bootstrap Modal not available. Using browser confirm dialog.');
                resolve(confirm(title + '\n\n' + message));
                return;
            }

            // Create modal element
            const modalId = 'confirm-modal-' + Date.now();
            const modal = document.createElement('div');
            modal.className = 'modal fade';
            modal.id = modalId;
            modal.tabIndex = '-1';
            modal.setAttribute('aria-labelledby', modalId + '-label');
            modal.setAttribute('aria-hidden', 'true');

            // Modal content
            modal.innerHTML = `
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title" id="${modalId}-label">${title}</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                        </div>
                        <div class="modal-body">
                            ${message}
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">${cancelText}</button>
                            <button type="button" class="btn btn-primary" id="${modalId}-confirm">${confirmText}</button>
                        </div>
                    </div>
                </div>
            `;

            // Add to body
            document.body.appendChild(modal);

            // Initialize modal
            const modalInstance = new bootstrap.Modal(modal);
            modalInstance.show();

            // Handle confirm button click
            const confirmButton = document.getElementById(modalId + '-confirm');
            confirmButton.addEventListener('click', function() {
                modalInstance.hide();
                resolve(true);
            });

            // Handle modal hidden event
            modal.addEventListener('hidden.bs.modal', function() {
                modal.remove();
            });
        });
    }

    /**
     * Shows a loading overlay
     * @param {string} [message='Loading...'] - The message to display
     * @param {boolean} [showSpinner=true] - Whether to show the spinner
     * @returns {Object} An object with hide() method to hide the overlay
     */
    function showLoadingOverlay(message = 'Loading...', showSpinner = true) {
        // Create overlay element
        const overlayId = 'loading-overlay-' + Date.now();
        const overlay = document.createElement('div');
        overlay.id = overlayId;
        overlay.className = 'loading-overlay position-fixed top-0 start-0 w-100 h-100 d-flex justify-content-center align-items-center';
        overlay.style.backgroundColor = 'rgba(0, 0, 0, 0.5)';
        overlay.style.zIndex = '9999';

        // Create spinner if needed
        const spinner = showSpinner ? `
            <div class="spinner-border text-primary me-3" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
        ` : '';

        // Set overlay content
        overlay.innerHTML = `
            <div class="bg-white rounded p-4 d-flex align-items-center">
                ${spinner}
                <span class="h5 mb-0">${message}</span>
            </div>
        `;

        // Add to body
        document.body.appendChild(overlay);
        document.body.style.overflow = 'hidden';

        // Return object with hide method
        return {
            hide: function() {
                if (overlay && overlay.parentNode) {
                    overlay.remove();
                    document.body.style.overflow = '';
                }
            }
        };
    }

// Helper functions for common toast types
function showErrorToast(message, duration = 5000) {
    return showToast(message, 'error', duration);
}

function showSuccessToast(message, duration = 3000) {
    return showToast(message, 'success', duration);
}

function showInfoToast(message, duration = 3000) {
    return showToast(message, 'info', duration);
}

function showWarningToast(message, duration = 4000) {
    return showToast(message, 'warning', duration);
}

// Export all functions as named exports
export {
    showToast,
    showErrorToast,
    showSuccessToast,
    showInfoToast,
    showWarningToast,
    getToastIcon,
    showConfirmDialog,
    showLoadingOverlay
};

// Also export as default for backward compatibility
const notifications = {
    showToast,
    showErrorToast,
    showSuccessToast,
    showInfoToast,
    showWarningToast,
    getToastIcon,
    showConfirmDialog,
    showLoadingOverlay
};

export default notifications;
