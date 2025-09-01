/**
 * Handles form submission for expense forms using Fetch API
 */

/**
 * Initialize the expense form
 */
function initializeExpenseForm() {
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
function validateFormData(formData) {
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

  // Add tags to form data if available
  const tagsInput = document.querySelector('[data-tags-input]');
  if (tagsInput && window.tagsInputInstance) {
    const tags = window.tagsInputInstance.getTags();
    if (tags.length > 0) {
      formData.append('tags', JSON.stringify(tags));
    }
  }

  console.log('Validation errors:', errors);
  return Object.keys(errors).length === 0 ? null : errors;
}

async function handleFormSubmit(event) {
  event.preventDefault();
  console.log('Form submission started');

  const form_elements = cache_form_elements(event.target);
  const form_data = new FormData(form_elements.form);

  clear_previous_errors(form_elements.alertContainer);

  const validation_result = validate_form_data(form_data);
  if (!validation_result.isValid) {
    handle_validation_errors(form_elements.form, validation_result.errors, form_data);
    return;
  }

  await process_form_submission(form_elements, form_data);
}

function cache_form_elements(form) {
  return {
    form,
    submitButton: form.querySelector('button[type="submit"]'),
    alertContainer: document.getElementById('alert-container'),
  };
}

function clear_previous_errors(alert_container) {
  if (alert_container) {
    alert_container.innerHTML = '';
  }
}

function validate_form_data(form_data) {
  const validation_errors = validateFormData(form_data);
  return {
    isValid: !validation_errors,
    errors: validation_errors,
  };
}

function handle_validation_errors(form, errors, form_data) {
  console.error('Client-side validation failed:', errors);
  console.log('Form data being validated:', Object.fromEntries(form_data.entries()));
  showFormErrors(form, errors);
}

/**
 * Display form validation errors
 * @param {HTMLFormElement} form - The form element
 * @param {Object} errors - Object containing error messages
 */
function showFormErrors(form, errors) {
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

// Helper functions for form submission processing
async function process_form_submission(form_elements, form_data) {
  const { form, submitButton } = form_elements;
  const original_button_text = submitButton?.innerHTML;

  try {
    set_loading_state(submitButton);

    const prepared_data = prepare_form_data_for_submission(form, form_data);
    log_submission_details(form, prepared_data);

    const response = await submit_form_to_server(form, prepared_data);
    const result = await response.json();

    console.log('Response data:', result);

    if (response.ok && result.success) {
      handle_successful_submission(result);
    } else {
      handle_submission_error(form, response, result);
    }

  } catch (error) {
    handle_submission_exception(form, error);
  } finally {
    restore_button_state(submitButton, original_button_text);
  }
}

function set_loading_state(submit_button) {
  if (submit_button) {
    submit_button.disabled = true;
    submit_button.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Processing...';
  }
}

function prepare_form_data_for_submission(form, form_data) {
  console.log('Submitting form data:', Object.fromEntries(form_data.entries()));

  const csrf_token = document.querySelector('input[name="csrf_token"]')?.value;

  // Add CSRF token if not already in form
  if (csrf_token && !form_data.has('csrf_token')) {
    form_data.append('csrf_token', csrf_token);
  }

  return form_data;
}

function log_submission_details(form, form_data) {
  const form_data_obj = Object.fromEntries(form_data.entries());
  console.log('Form data being sent:', form_data_obj);
  console.log('Sending request to:', form.action);
  console.log('Request method:', 'POST');
  console.log('Request headers:', {
    'X-Requested-With': 'XMLHttpRequest',
    Accept: 'application/json',
  });
}

async function submit_form_to_server(form, form_data) {
  const response = await fetch(form.action, {
    method: 'POST',
    body: form_data,
    headers: {
      'X-Requested-With': 'XMLHttpRequest',
      Accept: 'application/json',
    },
  });

  console.log('Response status:', response.status);
  return response;
}

function handle_successful_submission(result) {
  console.log('Form submission successful');

  show_success_alert(result);

  const redirect_url = result.redirect || result.redirect_url || '/expenses';
  console.log('Form submitted successfully, redirecting to:', redirect_url);
  window.location.href = redirect_url;
}

function show_success_alert(result) {
  const alert_container = document.getElementById('alert-container');
  if (alert_container) {
    const message = result.message || 'Expense added successfully!';
    alert_container.innerHTML = `
      <div class="alert alert-success alert-dismissible fade show" role="alert">
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
      </div>
    `;
  }
}

function handle_submission_error(form, response, result) {
  console.error('Form submission failed with status:', response.status);

  if (result.errors) {
    console.error('Form validation errors:', JSON.stringify(result.errors, null, 2));
    showFormErrors(form, result.errors);
  } else if (result.message) {
    console.error('Server error:', result.message);
    showFormErrors(form, { _error: [result.message] });
  } else {
    console.error('No error details provided in response');
    showFormErrors(form, {
      _error: [`An error occurred (${response.status}): ${response.statusText || 'Unknown error'}`],
    });
  }
}

function handle_submission_exception(form, error) {
  console.error('Error during form submission:', error);
  showFormErrors(form, {
    _error: ['An error occurred while submitting the form. Please try again.'],
  });
}

function restore_button_state(submit_button, original_text) {
  if (submit_button && original_text) {
    submit_button.disabled = false;
    submit_button.innerHTML = original_text;
  }
}
