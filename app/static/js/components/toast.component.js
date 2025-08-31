/**
 * Toast Component
 * Provides toast notification functionality for flash messages
 */

(function() {
    'use strict';

    // Create toast container if it doesn't exist
    function createToastContainer() {
        let container = document.getElementById('toast-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'toast-container';
            container.className = 'toast-container position-fixed top-0 end-0 p-3';
            container.style.zIndex = '1050';
            document.body.appendChild(container);
        }
        return container;
    }

    // Show a toast notification
    function showToast(message, type = 'info', duration = 5000) {
        const container = createToastContainer();

        // Create toast element
        const toast = document.createElement('div');
        toast.className = `toast align-items-center text-white bg-${getBootstrapClass(type)} border-0`;
        toast.setAttribute('role', 'alert');
        toast.setAttribute('aria-live', 'assertive');
        toast.setAttribute('aria-atomic', 'true');

        // Toast content
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">
                    <i class="fas fa-${getIcon(type)} me-2"></i>
                    ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        `;

        // Add to container
        container.appendChild(toast);

        // Initialize Bootstrap toast
        const bsToast = new bootstrap.Toast(toast, {
            autohide: true,
            delay: duration
        });

        // Remove from DOM after hidden
        toast.addEventListener('hidden.bs.toast', () => {
            toast.remove();
        });

        // Show the toast
        bsToast.show();
    }

    // Map message types to Bootstrap classes
    function getBootstrapClass(type) {
        const typeMap = {
            'success': 'success',
            'error': 'danger',
            'danger': 'danger',
            'warning': 'warning',
            'info': 'info',
            'primary': 'primary',
            'secondary': 'secondary'
        };
        return typeMap[type] || 'info';
    }

    // Map message types to Font Awesome icons
    function getIcon(type) {
        const iconMap = {
            'success': 'check-circle',
            'error': 'exclamation-triangle',
            'danger': 'exclamation-triangle',
            'warning': 'exclamation-triangle',
            'info': 'info-circle',
            'primary': 'info-circle',
            'secondary': 'info-circle'
        };
        return iconMap[type] || 'info-circle';
    }

    // Make showToast globally available
    window.showToast = showToast;

    // Also provide a more explicit API
    window.Toast = {
        show: showToast,
        success: (message, duration) => showToast(message, 'success', duration),
        error: (message, duration) => showToast(message, 'error', duration),
        warning: (message, duration) => showToast(message, 'warning', duration),
        info: (message, duration) => showToast(message, 'info', duration)
    };

})();
