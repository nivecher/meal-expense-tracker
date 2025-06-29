/**
 * Handles form submission for expense forms using Fetch API
 */

document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('expenseForm');
    if (!form) return;

    form.addEventListener('submit', handleFormSubmit);
});

/**
 * Handle form submission with Fetch API
 * @param {Event} event - The form submission event
 */
function validateFormData(formData) {
    const errors = {};
    const amount = parseFloat(formData.get('amount'));

    if (isNaN(amount) || amount <= 0) {
        errors.amount = ['Please enter a valid amount greater than 0'];
    }

    if (!formData.get('restaurant_id')) {
        errors.restaurant_id = ['Please select a restaurant'];
    }

    if (!formData.get('date')) {
        errors.date = ['Please select a date'];
    }

    return Object.keys(errors).length === 0 ? null : errors;
}

async function handleFormSubmit(event) {
    event.preventDefault();

    const form = event.target;
    const formData = new FormData(form);
    const submitButton = form.querySelector('button[type="submit"]');
    const originalButtonText = submitButton?.innerHTML;

    // Client-side validation
    const validationErrors = validateFormData(formData);
    if (validationErrors) {
        console.error('Client-side validation failed:', validationErrors);
        showFormErrors(form, validationErrors);
        return;
    }

    try {
        // Show loading state
        if (submitButton) {
            submitButton.disabled = true;
            submitButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Processing...';
        }

        // Log form data for debugging
        const formDataObj = {};
        for (let [key, value] of formData.entries()) {
            formDataObj[key] = value;
        }
        console.log('Submitting form data:', formDataObj);

        const response = await fetch(form.action, {
            method: 'POST',
            body: formData,
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': formData.get('csrf_token')
            }
        });

        const data = await response.json();
        console.log('Server response:', data);

        if (response.ok) {
            // Success - redirect to the provided URL or default to expenses list
            const redirectUrl = data.redirect || data.redirect_url || url_for('expenses.list_expenses');
            window.location.href = redirectUrl;
        } else {
            // Show validation errors
            if (data.errors) {
                console.error('Form validation errors:', data.errors);
                showFormErrors(form, data.errors);
            } else if (data.message) {
                console.error('Server error:', data.message);
                showFormErrors(form, { _error: [data.message] });
            } else {
                console.error('Unknown error occurred');
                showFormErrors(form, { _error: ['An unknown error occurred while processing the form.'] });
            }
        }
    } catch (error) {
        console.error('Error submitting form:', error);
        showFormErrors(form, {
            _error: ['A network error occurred. Please check your connection and try again.']
        });
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
 * @param {HTMLFormElement} form - The form element
 * @param {Object} errors - Object containing error messages
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
        const errorMsg = errors.message || 'Please correct the errors below.';
        errorContainer.textContent = Array.isArray(errorMsg) ? errorMsg[0] : errorMsg;
        errorContainer.classList.remove('d-none');
    }

    // Scroll to first error
    const firstError = form.querySelector('.is-invalid');
    if (firstError) {
        firstError.scrollIntoView({ behavior: 'smooth', block: 'center' });
        firstError.focus();
    }
}
