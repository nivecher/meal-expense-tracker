/**
 * Expense Form Module
 * Handles initialization and behavior for expense forms (add/edit)
 */

/**
 * Handle form submission using Fetch API
 */
async function handleFormSubmit(event) {
    event.preventDefault();

    const form = event.target;
    const formData = new FormData(form);
    const submitButton = form.querySelector('button[type="submit"]');
    const originalButtonText = submitButton?.innerHTML;

    try {
        // Show loading state
        if (submitButton) {
            submitButton.disabled = true;
            submitButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Saving...';
        }

        const response = await fetch(form.action, {
            method: 'POST',
            body: formData,
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': formData.get('csrf_token')
            }
        });

        const data = await response.json();

        if (response.ok) {
            // Success - redirect to the expense details or list page
            window.location.href = data.redirect_url || '{{ url_for("expenses.list_expenses") }}';
        } else {
            // Show validation errors
            showFormErrors(form, data.errors || { message: 'An error occurred while saving the expense.' });
        }
    } catch (error) {
        console.error('Error submitting form:', error);
        showFormErrors(form, { message: 'Network error. Please try again.' });
    } finally {
        // Reset button state
        if (submitButton) {
            submitButton.disabled = false;
            submitButton.innerHTML = originalButtonText;
        }
    }
}

/**
 * Display form validation errors
 */
function showFormErrors(form, errors) {
    // Clear previous errors
    const errorElements = form.querySelectorAll('.is-invalid, .invalid-feedback');
    errorElements.forEach(el => {
        el.classList.remove('is-invalid');
        if (el.classList.contains('invalid-feedback')) {
            el.remove();
        }
    });

    // Show field-specific errors
    if (errors.fields) {
        Object.entries(errors.fields).forEach(([fieldName, errorMessages]) => {
            const input = form.querySelector(`[name="${fieldName}"]`);
            if (input) {
                input.classList.add('is-invalid');
                const errorDiv = document.createElement('div');
                errorDiv.className = 'invalid-feedback';
                errorDiv.textContent = Array.isArray(errorMessages) ? errorMessages[0] : errorMessages;
                input.closest('.mb-3')?.appendChild(errorDiv);
            }
        });
    }

    // Show general error message if no field-specific errors
    const errorContainer = form.querySelector('#formErrors');
    if (errorContainer && (!errors.fields || Object.keys(errors.fields).length === 0)) {
        errorContainer.textContent = errors.message || 'Please correct the errors below.';
        errorContainer.classList.remove('d-none');
    }

    // Scroll to first error
    const firstError = form.querySelector('.is-invalid');
    if (firstError) {
        firstError.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
}

/**
 * Initialize the expense form
 */
function initExpenseForm() {
    const form = document.getElementById('expenseForm');
    if (!form) return;

    // Set up form submission handler
    form.addEventListener('submit', handleFormSubmit);

    // Handle date input formatting
    const dateInput = form.querySelector('input[type="date"]');
    if (dateInput) {
        // For edit forms, ensure the date is in the correct format
        if (dateInput.value) {
            try {
                const dateValue = new Date(dateInput.value);
                if (!isNaN(dateValue)) {
                    dateInput.value = dateValue.toISOString().split('T')[0];
                }
            } catch (e) {
                console.warn('Could not parse date:', e);
            }
        }
        // For add forms, set default to today if empty
        else if (!dateInput.value) {
            dateInput.value = new Date().toISOString().split('T')[0];
        }
    }

    // Focus the first visible form field
    const firstInput = form.querySelector('input:not([type="hidden"]):not([readonly]):not([disabled])');
    if (firstInput) {
        firstInput.focus();
    }
}

// Initialize when the DOM is fully loaded
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initExpenseForm);
} else {
    // DOMContentLoaded has already fired
    initExpenseForm();
}

// Export for testing
export { initExpenseForm };
