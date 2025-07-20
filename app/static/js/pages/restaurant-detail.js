/**
 * Restaurant Detail Page JavaScript
 * Handles interactive elements on the restaurant detail page
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize elements
    const form = document.querySelector('form');

    if (!form) return;

    /**
     * Show alert message
     */
    function showAlert(type, message) {
        // Remove any existing alerts
        const existingAlerts = document.querySelectorAll('.alert');
        existingAlerts.forEach(alert => alert.remove());

        // Create new alert
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show mt-3`;
        alertDiv.role = 'alert';
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;

        // Insert after the form title or at the top of the form
        const formTitle = document.querySelector('h1, h2, h3');
        if (formTitle) {
            formTitle.after(alertDiv);
        } else {
            form.prepend(alertDiv);
        }

        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alertDiv);
            bsAlert.close();
        }, 5000);
    }
});
