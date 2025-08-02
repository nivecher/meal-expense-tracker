/**
 * Handles form submission for expense forms using Fetch API
 */

/**
 * Initialize the expense form
 */
function initializeExpenseForm () {
  const form = document.getElementById('expenseForm');
  if (!form) return;

  // Set up form submission handler
  form.addEventListener('submit', handleFormSubmit);

  // Check if we're editing an existing expense
  const restaurantSelect = form.querySelector('select[name="restaurant_id"]');
  if (restaurantSelect) {
    // If there's a data-restaurant-id attribute, use it to set the selected option
    const { restaurantId } = restaurantSelect.dataset;
    if (restaurantId) {
      const optionToSelect = restaurantSelect.querySelector(`option[value="${restaurantId}"]`);
      if (optionToSelect) {
        optionToSelect.selected = true;
        console.log('Set selected restaurant:', restaurantId);
      } else {
        console.warn('Could not find restaurant option with value:', restaurantId);
      }
    }
  }
}

// Initialize the form when the DOM is fully loaded
document.addEventListener('DOMContentLoaded', initializeExpenseForm);

/**
 * Handle form submission with Fetch API
 * @param {Event} event - The form submission event
 */
/**
 * Validate form data before submission
 * @param {FormData} formData - The form data to validate
 * @returns {Object|null} Validation errors or null if valid
 */
function validateFormData (formData) {
  const errors = {};
  const requiredFields = ['amount', 'restaurant_id', 'date'];

  requiredFields.forEach((field) => {
    const value = formData.get(field);
    console.log(`Validating ${field}:`, value);

    // Special handling for restaurant_id which should be a number > 0
    if (field === 'restaurant_id') {
      const restaurantId = parseInt(value, 10);
      if (isNaN(restaurantId) || restaurantId <= 0) {
        errors[field] = ['Please select a valid restaurant'];
      }
    }
    // Standard required field validation
    else if (!value || (typeof value === 'string' && value.trim() === '')) {
      const fieldName = field.replace(/_/g, ' ');
      errors[field] = [`Please enter a valid ${fieldName}`];
    }
  });

  // Additional validation for amount
  const amount = parseFloat(formData.get('amount'));
  if (!isNaN(amount) && amount <= 0) {
    errors.amount = ['Please enter an amount greater than 0'];
  }

  // Additional validation for date format (YYYY-MM-DD)
  const dateValue = formData.get('date');
  if (dateValue && !/^\d{4}-\d{2}-\d{2}$/.test(dateValue)) {
    errors.date = ['Please enter a valid date in YYYY-MM-DD format'];
  }

  console.log('Validation errors:', errors);
  return Object.keys(errors).length === 0 ? null : errors;
}

async function handleFormSubmit (event) {
  event.preventDefault();
  console.log('Form submission started');

  const form = event.target;
  const formData = new FormData(form);
  const submitButton = form.querySelector('button[type="submit"]');
  const originalButtonText = submitButton?.innerHTML;
  const alertContainer = document.getElementById('alert-container');

  // Clear previous errors
  if (alertContainer) {
    alertContainer.innerHTML = '';
  }

  // Client-side validation
  const validationErrors = validateFormData(formData);
  if (validationErrors) {
    console.error('Client-side validation failed:', validationErrors);
    console.log('Form data being validated:', Object.fromEntries(formData.entries()));
    showFormErrors(form, validationErrors);
    return;
  }

  try {
    // Show loading state
    if (submitButton) {
      submitButton.disabled = true;
      submitButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Processing...';
    }

    // Log the form data
    console.log('Submitting form data:', Object.fromEntries(formData.entries()));

    // Get CSRF token from the form
    const csrfToken = document.querySelector('input[name="csrf_token"]')?.value;

    // Ensure all form data is properly formatted
    const formDataObj = {};
    for (const [key, value] of formData.entries()) {
      formDataObj[key] = value;
    }

    // Add CSRF token if not already in form
    if (csrfToken && !formData.has('csrf_token')) {
      formData.append('csrf_token', csrfToken);
      formDataObj.csrf_token = csrfToken;
    }

    // Log the form data being sent
    console.log('Form data being sent:', formDataObj);

    // Log the request details
    console.log('Sending request to:', form.action);
    console.log('Request method:', 'POST');
    console.log('Request headers:', {
      'X-Requested-With': 'XMLHttpRequest',
      Accept: 'application/json',
    });

    const response = await fetch(form.action, {
      method: 'POST',
      body: formData,
      headers: {
        'X-Requested-With': 'XMLHttpRequest',
        Accept: 'application/json',
        'X-CSRF-Token': csrfToken,
      },
      credentials: 'same-origin',  // Important for including cookies
    });

    // Get response as text first to handle both JSON and non-JSON responses
    const responseText = await response.text();
    let data;

    try {
      data = responseText ? JSON.parse(responseText) : {};
      console.log('Server response:', data);
    } catch (_e) {
      console.error('Failed to parse JSON response:', responseText);
      throw new Error(`Invalid server response: ${responseText.substring(0, 100)}...`);
    }

    if (response.ok) {
      // Success - redirect to the provided URL or default to expenses list
      const redirectUrl = data.redirect || data.redirect_url || '/expenses';
      console.log('Form submitted successfully, redirecting to:', redirectUrl);
      window.location.href = redirectUrl;
      return;
    }

    // Handle error response
    console.error('Form submission failed with status:', response.status);

    // Show validation errors if available
    if (data.errors) {
      console.error('Form validation errors:', JSON.stringify(data.errors, null, 2));
      showFormErrors(form, data.errors);
    } else if (data.message) {
      console.error('Server error:', data.message);
      showFormErrors(form, { _error: [data.message] });
    } else {
      console.error('No error details provided in response');
      showFormErrors(form, {
        _error: [`An error occurred (${response.status}): ${response.statusText || 'Unknown error'}`],
      });
    }
  } catch (error) {
    console.error('Error submitting form:', error);
    showFormErrors(form, {
      _error: ['A network error occurred. Please check your connection and try again.'],
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
function showFormErrors (form, errors) {
  console.log('Showing form errors:', errors);

  // Clear previous errors
  const errorElements = form.querySelectorAll('.is-invalid, .invalid-feedback');
  errorElements.forEach((el) => {
    el.classList.remove('is-invalid');
    if (el.classList.contains('invalid-feedback')) {
      el.remove();
    }
  });

  // Show general errors at the top of the form
  if (errors._error || (typeof errors === 'object' && !Array.isArray(errors) && Object.keys(errors).length > 0)) {
    const errorContainer = form.querySelector('#formErrors') || document.createElement('div');
    if (!errorContainer.id) {
      errorContainer.id = 'formErrors';
      errorContainer.className = 'alert alert-danger';
      form.prepend(errorContainer);
    }

    // Clear previous messages
    errorContainer.innerHTML = '';
    errorContainer.classList.remove('d-none');

    // Add new error messages
    if (errors._error) {
      const errorMessages = Array.isArray(errors._error) ? errors._error : [errors._error];
      errorMessages.forEach((msg) => {
        const p = document.createElement('p');
        p.className = 'mb-0';
        p.textContent = msg;
        errorContainer.appendChild(p);
      });
    }
  }

  // Show field-specific errors
  Object.entries(errors).forEach(([fieldName, errorMessages]) => {
    // Skip non-field specific errors
    if (fieldName === '_error' || fieldName === 'status' || fieldName === 'message') {
      return;
    }

    const input = form.querySelector(`[name="${fieldName}"]`);
    if (input) {
      const formGroup = input.closest('.mb-3') || input.closest('.form-group') || input.parentElement;
      input.classList.add('is-invalid');

      // Create or update error message
      let errorDiv = formGroup.querySelector('.invalid-feedback');
      if (!errorDiv) {
        errorDiv = document.createElement('div');
        errorDiv.className = 'invalid-feedback';
        formGroup.appendChild(errorDiv);
      }

      // Set error message
      if (Array.isArray(errorMessages)) {
        errorDiv.textContent = errorMessages[0];
      } else if (typeof errorMessages === 'object' && errorMessages !== null) {
        errorDiv.textContent = Object.values(errorMessages)[0]?.[0] || 'Invalid value';
      } else {
        errorDiv.textContent = errorMessages || 'Invalid value';
      }
    } else {
      console.warn(`Could not find input field for error: ${fieldName}`);
    }
  });

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
