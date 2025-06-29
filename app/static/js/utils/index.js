/**
 * Utility functions
 */

/**
 * Show a flash message
 * @param {string} message - The message to display
 * @param {string} type - The message type (success, danger, warning, info)
 */
function showFlashMessage(message, type = 'info') {
    const flashContainer = document.getElementById('flash-messages');
    if (!flashContainer) return;

    const alert = document.createElement('div');
    alert.className = `alert alert-${type} alert-dismissible fade show`;
    alert.role = 'alert';
    alert.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;

    flashContainer.appendChild(alert);

    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        const bsAlert = new bootstrap.Alert(alert);
        bsAlert.close();
    }, 5000);
}

/**
 * Toggle sort order in a form
 * @param {string} formId - The ID of the form
 * @param {string} sortField - The field to sort by
 */
function toggleSortOrder(formId, sortField) {
    const form = document.getElementById(formId);
    if (!form) return;

    const sortFieldInput = form.querySelector('input[name="sort"]');
    const sortOrderInput = form.querySelector('input[name="order"]');

    if (sortFieldInput && sortOrderInput) {
        // Toggle order if sorting the same field
        if (sortFieldInput.value === sortField) {
            sortOrderInput.value = sortOrderInput.value === 'asc' ? 'desc' : 'asc';
        } else {
            // Default to descending for new sort fields
            sortOrderInput.value = 'desc';
        }
        sortFieldInput.value = sortField;
        form.submit();
    }
}

/**
 * Submit a form when a select element changes
 * @param {HTMLElement} selectElement - The select element that triggered the change
 */
function submitOnChange(selectElement) {
    if (selectElement.form) {
        selectElement.form.submit();
    }
}

// Export functions for use in other modules
window.utils = {
    showFlashMessage,
    toggleSortOrder,
    submitOnChange
};
