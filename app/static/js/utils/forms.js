/**
 * Form handling and validation
 */

// Use IIFE to prevent global scope pollution and multiple initializations
(function() {
    // Skip if already initialized
    if (window.formsInitialized) return;
    window.formsInitialized = true;

    // Wait for DOM to be fully loaded
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initForms);
    } else {
        // DOM already loaded, initialize immediately
        initForms();
    }

    function initForms() {
        // Initialize form validation for all forms with data-validate attribute
        const forms = document.querySelectorAll('form[data-validate]');
        forms.forEach(form => setupFormValidation(form));

        // Handle form submissions with loading states
        document.addEventListener('submit', async function(e) {
            const form = e.target.closest('form');
            if (!form) return;

            // Skip if already submitting
            if (form.classList.contains('is-submitting')) {
                e.preventDefault();
                return;
            }

            // Handle forms with data-confirm attribute
            const confirmMessage = form.getAttribute('data-confirm');
            if (confirmMessage && !window.confirm(confirmMessage)) {
                e.preventDefault();
                return;
            }

            // For regular form submissions (non-AJAX), let them proceed normally
            if (!form.hasAttribute('data-ajax')) {
                // Just ensure we're not in a submitting state
                if (form.classList.contains('is-submitting')) {
                    e.preventDefault();
                }
                return;
            }

            // Prevent default for AJAX forms
            e.preventDefault();

            // Validate form if needed
            if (form.hasAttribute('data-validate')) {
                if (!form.checkValidity()) {
                    e.stopPropagation();
                    form.classList.add('was-validated');
                    return;
                }
            }

            // Set loading state
            setFormLoading(form, true);

            try {
                const formData = new FormData(form);
                const method = form.method.toUpperCase();
                const url = form.action;

                // For GET requests, convert form data to URL parameters
                let fetchUrl = url;
                const fetchOptions = {
                    method: method,
                    headers: {
                        'Accept': 'application/json',
                        'X-Requested-With': 'XMLHttpRequest'
                    },
                    credentials: 'same-origin'
                };

                if (method === 'GET') {
                    const params = new URLSearchParams();
                    formData.forEach((value, key) => {
                        params.append(key, value);
                    });
                    fetchUrl = `${url}${url.includes('?') ? '&' : '?'}${params.toString()}`;
                } else {
                    // For POST/PUT/DELETE, include form data in the body
                    fetchOptions.body = formData;
                }

                const response = await fetch(fetchUrl, fetchOptions);

                // Check if the response is JSON or HTML
                const contentType = response.headers.get('content-type');
                let data;

                if (contentType && contentType.includes('application/json')) {
                    data = await response.json();

                    if (!response.ok) {
                        throw new Error(data.message || 'Server returned an error');
                    }

                    // Handle successful form submission
                    if (data.redirect) {
                        window.location.href = data.redirect;
                        return;
                    }

                    // Handle form-specific redirects
                    if (form.dataset.redirect) {
                        window.location.href = form.dataset.redirect;
                        return;
                    }

                    // Show success message if available
                    if (data.message && window.showToast) {
                        showToast.success(data.message);
                    }

                    // Reset form if needed
                    if (form.hasAttribute('data-reset-on-success')) {
                        form.reset();
                        resetFormValidation(form);
                    }

                } else {
                    // Handle HTML response (likely a redirect or error page)
                    const text = await response.text();

                    // If it's a redirect, follow it
                    if (response.redirected) {
                        window.location.href = response.url;
                        return;
                    }

                    // Otherwise, show the HTML response (likely a server error page)
                    document.open();
                    document.write(text);
                    document.close();
                }

            } catch (error) {
                console.error('Form submission error:', error);
                // Check if the error is due to HTML being returned instead of JSON
                if (error instanceof SyntaxError && error.message.includes('JSON')) {
                    console.error('Server returned HTML instead of JSON. This might be a server error page.');
                    if (window.showToast) {
                        showToast.error('An error occurred while processing your request. Please try again.');
                    } else {
                        alert('An error occurred while processing your request. Please try again.');
                    }
                } else if (window.showToast) {
                    showToast.error(error.message || 'Network error or server unreachable.');
                } else {
                    alert(error.message || 'Network error or server unreachable.');
                }
            } finally {
                setFormLoading(form, false);
            }
        });
    }

    /**
     * Set up form validation
     */
    function setupFormValidation(form) {
        form.setAttribute('novalidate', '');

        form.addEventListener('submit', function(e) {
            if (!form.checkValidity()) {
                e.preventDefault();
                e.stopPropagation();
                showFormValidationErrors(form);
            }
            form.classList.add('was-validated');
        }, false);

        // Real-time validation on input
        form.querySelectorAll('input, select, textarea').forEach(input => {
            input.addEventListener('input', function() {
                validateField(this);
            });
        });
    }

    /**
     * Show form validation errors
     */
    function showFormValidationErrors(form) {
        const invalidFields = form.querySelectorAll(':invalid');

        invalidFields.forEach(field => {
            const feedback = field.nextElementSibling;
            if (feedback && feedback.classList.contains('invalid-feedback')) {
                field.classList.add('is-invalid');

                if (field.validity.valueMissing) {
                    feedback.textContent = field.getAttribute('data-required-message') || 'This field is required';
                } else if (field.validity.typeMismatch) {
                    feedback.textContent = field.getAttribute('data-type-message') || 'Please enter a valid value';
                } else if (field.validity.patternMismatch) {
                    feedback.textContent = field.getAttribute('data-pattern-message') || 'Please match the requested format';
                } else if (field.validity.tooShort || field.validity.tooLong) {
                    feedback.textContent = field.getAttribute('data-length-message') ||
                        `Please enter between ${field.minLength} and ${field.maxLength} characters`;
                } else {
                    feedback.textContent = field.validationMessage;
                }
            }
        });

        // Focus on first invalid field
        if (invalidFields.length > 0) {
            const firstInvalid = invalidFields[0];
            firstInvalid.focus();

            // Scroll to the first error
            firstInvalid.scrollIntoView({
                behavior: 'smooth',
                block: 'center'
            });
        }
    }

    /**
     * Validate a single field
     */
    function validateField(field) {
        const form = field.closest('form');
        if (!form) return;

        const feedback = field.nextElementSibling;
        if (!feedback || !feedback.classList.contains('invalid-feedback')) {
            return;
        }

        if (field.checkValidity()) {
            field.classList.remove('is-invalid');
            feedback.textContent = '';
        } else {
            field.classList.add('is-invalid');

            if (field.validity.valueMissing) {
                feedback.textContent = field.getAttribute('data-required-message') || 'This field is required';
            } else if (field.validity.typeMismatch) {
                feedback.textContent = field.getAttribute('data-type-message') || 'Please enter a valid value';
            } else if (field.validity.patternMismatch) {
                feedback.textContent = field.getAttribute('data-pattern-message') || 'Please match the requested format';
            } else if (field.validity.tooShort || field.validity.tooLong) {
                feedback.textContent = field.getAttribute('data-length-message') ||
                    `Please enter between ${field.minLength} and ${field.maxLength} characters`;
            } else {
                feedback.textContent = field.validationMessage;
            }
        }
    }

    /**
     * Reset form validation state
     */
    function resetFormValidation(form) {
        form.classList.remove('was-validated');
        form.querySelectorAll('.is-invalid').forEach(field => {
            field.classList.remove('is-invalid');
            const feedback = field.nextElementSibling;
            if (feedback && feedback.classList.contains('invalid-feedback')) {
                feedback.textContent = '';
            }
        });
    }

    /**
     * Set or reset the loading state of a form
     * @param {HTMLFormElement} form - The form element
     * @param {boolean} isLoading - Whether to show or hide loading state
     */
    function setFormLoading(form, isLoading) {
        const submitButton = form.querySelector('button[type="submit"]');
        if (!submitButton) return;

        if (isLoading) {
            // Save original button state
            if (!submitButton.hasAttribute('data-original-text')) {
                submitButton.setAttribute('data-original-text', submitButton.innerHTML);
            }

            // Disable button and show spinner
            submitButton.disabled = true;
            submitButton.innerHTML = `
                <span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
                ${submitButton.getAttribute('data-loading-text') || 'Processing...'}
            `;
            form.classList.add('is-submitting');
        } else {
            // Restore original button state
            if (submitButton.hasAttribute('data-original-text')) {
                submitButton.disabled = false;
                submitButton.innerHTML = submitButton.getAttribute('data-original-text');
                submitButton.removeAttribute('data-original-text');
            }
            form.classList.remove('is-submitting');
        }
    }

    // Export public functions
    window.FormUtils = {
        setupFormValidation,
        validateField,
        resetFormValidation,
        setFormLoading,
        showFormValidationErrors,
        // Deprecated, use setFormLoading(form, false) instead
        resetFormLoading: function(form) {
            console.warn('resetFormLoading is deprecated. Use setFormLoading(form, false) instead.');
            setFormLoading(form, false);
        }
    };
})();

// Export functions for use in other modules
if (typeof window !== 'undefined' && !window.FormUtils) {
    // This is a fallback in case the main initialization didn't run
    // The actual implementation is already provided in the IIFE above
    const noop = () => console.warn('FormUtils functions should be called after the DOM is fully loaded.');

    window.FormUtils = {
        setupFormValidation: noop,
        validateField: noop,
        resetFormValidation: noop,
        setFormLoading: noop,
        showFormValidationErrors: noop,
        resetFormLoading: () => console.warn('FormUtils.resetFormLoading is deprecated. Use setFormLoading(form, false) instead.')
    };
}
