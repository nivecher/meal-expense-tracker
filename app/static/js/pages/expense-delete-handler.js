/**
 * Handles delete confirmation and submission for expense deletion
 */

document.addEventListener('DOMContentLoaded', () => {
    // Handle delete button clicks in the expense list
    const deleteButtons = document.querySelectorAll('.btn-delete-expense');
    deleteButtons.forEach(button => {
        button.addEventListener('click', handleDeleteClick);
    });

    // Handle delete form submission
    const deleteForm = document.getElementById('deleteExpenseForm');
    if (deleteForm) {
        deleteForm.addEventListener('submit', handleDeleteSubmit);
    }
});

/**
 * Handle click on delete button
 * @param {Event} event - The click event
 */
function handleDeleteClick(event) {
    event.preventDefault();

    const button = event.currentTarget;
    const expenseId = button.dataset.expenseId;
    const expenseName = button.dataset.expenseName || 'this expense';

    // Show confirmation dialog
    if (confirm(`Are you sure you want to delete ${expenseName}? This action cannot be undone.`)) {
        submitDeleteRequest(expenseId);
    }
}

/**
 * Handle delete form submission
 * @param {Event} event - The form submission event
 */
function handleDeleteSubmit(event) {
    event.preventDefault();

    const form = event.target;
    const expenseId = form.dataset.expenseId;

    submitDeleteRequest(expenseId);
}

/**
 * Submit delete request via Fetch API
 * @param {string} expenseId - The ID of the expense to delete
 */
async function submitDeleteRequest(expenseId) {
    const url = `/expenses/${expenseId}/delete`;
    const form = document.getElementById('deleteExpenseForm');
    const formData = form ? new FormData(form) : new FormData();
    const submitButton = document.querySelector('[type="submit"][form="deleteExpenseForm"]');
    const originalButtonText = submitButton?.innerHTML;

    try {
        // Show loading state
        if (submitButton) {
            submitButton.disabled = true;
            submitButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Deleting...';
        }

        const response = await fetch(url, {
            method: 'POST',
            body: formData,
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': formData.get('csrf_token')
            }
        });

        const data = await response.json();

        if (response.ok) {
            // If we're on the details page, redirect to list
            if (window.location.pathname.includes('/expenses/')) {
                window.location.href = data.redirect || '/expenses';
            } else {
                // If we're on the list page, remove the row
                const row = document.querySelector(`tr[data-expense-id="${expenseId}"]`);
                if (row) {
                    row.remove();
                    // Show success message
                    showAlert('Expense deleted successfully!', 'success');
                } else {
                    // If we can't find the row, just reload
                    window.location.reload();
                }
            }
        } else {
            throw new Error(data.message || 'Failed to delete expense');
        }
    } catch (error) {
        console.error('Error deleting expense:', error);
        showAlert('An error occurred while deleting the expense. Please try again.', 'danger');
    } finally {
        // Reset button state
        if (submitButton) {
            submitButton.disabled = false;
            submitButton.innerHTML = originalButtonText;
        }
    }
}

/**
 * Show a bootstrap alert message
 * @param {string} message - The message to display
 * @param {string} type - The alert type (e.g., 'success', 'danger')
 */
function showAlert(message, type = 'info') {
    // Create alert element
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.role = 'alert';
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;

    // Find alert container or create one
    let alertContainer = document.querySelector('.alert-container');
    if (!alertContainer) {
        alertContainer = document.createElement('div');
        alertContainer.className = 'alert-container';
        document.body.insertBefore(alertContainer, document.body.firstChild);
    }

    // Add alert to container and auto-remove after 5 seconds
    alertContainer.appendChild(alertDiv);

    // Initialize Bootstrap alert for dismiss
    const bsAlert = new bootstrap.Alert(alertDiv);

    // Auto-remove after 5 seconds
    setTimeout(() => {
        bsAlert.close();
    }, 5000);
}
