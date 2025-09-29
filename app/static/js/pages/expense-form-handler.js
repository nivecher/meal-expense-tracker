/**
 * Handles form submission for expense forms using Fetch API
 */

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
  if (errors.errorKey || (typeof errors === 'object' && !Array.isArray(errors) && Object.keys(errors).length > 0)) {
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
    if (errors.errorKey) {
      const errorMessages = Array.isArray(errors.errorKey) ? errors.errorKey : [errors.errorKey];
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
    if (fieldName === 'errorKey' || fieldName === 'status' || fieldName === 'message') {
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
        [errorDiv.textContent] = errorMessages;
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

// Utility functions - defined first
function validateFormDataInternal(formData) {
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
    } else if (!value || (typeof value === 'string' && value.trim() === '')) {
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
  if (dateValue && !/^\d{4}-\d{2}-\d{2}$/u.test(dateValue)) {
    errors.date = ['Please enter a valid date in YYYY-MM-DD format'];
  }

  // Tags will be added during form submission, not validation

  console.log('Validation errors:', errors);
  return Object.keys(errors).length === 0 ? null : errors;
}

function validateFormData(formData) {
  const validationErrors = validateFormDataInternal(formData);
  return {
    isValid: !validationErrors,
    errors: validationErrors,
  };
}

function cacheFormElements(form) {
  return {
    form,
    submitButton: form.querySelector('button[type="submit"]'),
    alertContainer: document.getElementById('alert-container'),
  };
}

function clearPreviousErrors(alertContainer) {
  if (alertContainer) {
    alertContainer.innerHTML = '';
  }
}

function setLoadingState(submitButton) {
  if (submitButton) {
    submitButton.disabled = true;
    submitButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Processing...';
  }
}

function prepareFormDataForSubmission(form, formData) {
  console.log('Submitting form data:', Object.fromEntries(formData.entries()));

  const csrfToken = document.querySelector('input[name="csrf_token"]')?.value;

  // Add CSRF token if not already in form
  if (csrfToken && !formData.has('csrf_token')) {
    formData.append('csrf_token', csrfToken);
  }

  return formData;
}

function logSubmissionDetails(form, formData) {
  const formDataObj = Object.fromEntries(formData.entries());
  console.log('Form data being sent:', formDataObj);
  console.log('Sending request to:', form.action);
  console.log('Request method:', 'POST');
  console.log('Request headers:', {
    'X-Requested-With': 'XMLHttpRequest',
    Accept: 'application/json',
  });
}

async function submitFormToServer(form, formData) {
  const response = await fetch(form.action, {
    method: 'POST',
    body: formData,
    headers: {
      'X-Requested-With': 'XMLHttpRequest',
      Accept: 'application/json',
    },
  });

  console.log('Response status:', response.status);
  return response;
}

function showSuccessAlert(result) {
  const alertContainer = document.getElementById('alert-container');
  if (alertContainer) {
    const message = result.message || 'Expense added successfully!';
    alertContainer.innerHTML = `
      <div class="alert alert-success alert-dismissible fade show" role="alert">
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
      </div>
    `;
  }
}

function handleSuccessfulSubmission(result) {
  console.log('Form submission successful');

  showSuccessAlert(result);

  const redirectUrl = result.redirect || result.redirect_url || '/expenses';
  console.log('Form submitted successfully, redirecting to:', redirectUrl);
  window.location.href = redirectUrl;
}

function handleSubmissionError(form, response, result) {
  console.error('Form submission failed with status:', response.status);

  if (result.errors) {
    console.error('Form validation errors:', JSON.stringify(result.errors, null, 2));
    showFormErrors(form, result.errors);
  } else if (result.message) {
    console.error('Server error:', result.message);
    showFormErrors(form, { errorKey: [result.message] });
  } else {
    console.error('No error details provided in response');
    showFormErrors(form, {
      errorKey: [`An error occurred (${response.status}): ${response.statusText || 'Unknown error'}`],
    });
  }
}

function handleSubmissionException(form, error) {
  console.error('Error during form submission:', error);
  showFormErrors(form, {
    errorKey: ['An error occurred while submitting the form. Please try again.'],
  });
}

function restoreButtonState(submitButton, originalText) {
  if (submitButton && originalText) {
    submitButton.disabled = false;
    submitButton.innerHTML = originalText;
  }
}

function handleValidationErrors(form, errors, formData) {
  console.error('Client-side validation failed:', errors);
  console.log('Form data being validated:', Object.fromEntries(formData.entries()));
  showFormErrors(form, errors);
}

async function processFormSubmission(formElements, formData) {
  const { form, submitButton } = formElements;
  const originalButtonText = submitButton?.innerHTML;

  try {
    setLoadingState(submitButton);

    const preparedData = prepareFormDataForSubmission(form, formData);
    logSubmissionDetails(form, preparedData);

    const response = await submitFormToServer(form, preparedData);
    const result = await response.json();

    console.log('Response data:', result);

    if (response.ok && result.success) {
      handleSuccessfulSubmission(result);
    } else {
      handleSubmissionError(form, response, result);
    }

  } catch {
    handleSubmissionException(form, error);
  } finally {
    restoreButtonState(submitButton, originalButtonText);
  }
}

// Main form handling functions
async function handleFormSubmit(event) {
  event.preventDefault();
  console.log('Form submission started');

  const formElements = cacheFormElements(event.target);
  const formData = new FormData(formElements.form);

  // Add tags to form data if available (Tagify)
  const tagsInput = document.getElementById('tagsInput');
  if (tagsInput && window.tagifyInstance) {
    const selectedTags = window.tagifyInstance.value;
    if (selectedTags && selectedTags.length > 0) {
      const tagsJson = JSON.stringify(selectedTags.map((tag) => tag.value));
      formData.set('tags', tagsJson); // Use set() to replace any existing value
    }
  }

  clearPreviousErrors(formElements.alertContainer);

  const validationResult = validateFormData(formData);
  if (!validationResult.isValid) {
    handleValidationErrors(formElements.form, validationResult.errors, formData);
    return;
  }

  await processFormSubmission(formElements, formData);
}

/**
 * Set up category and restaurant type handling
 */
function setupCategoryRestaurantHandling(form) {
  const categorySelect = form.querySelector('select[name="category_id"]');
  const restaurantSelect = form.querySelector('select[name="restaurant_id"]');

  if (!categorySelect || !restaurantSelect) return;

  // Track if category was manually changed
  let categoryManuallyChanged = false;

  // Function to update category based on restaurant type
  function updateCategory(restaurantId) {
    if (categoryManuallyChanged) return;
    if (!restaurantId) return;

    // Reset to default selection
    categorySelect.value = '';
  }

  // Handle restaurant change
  restaurantSelect.addEventListener('change', function() {
    updateCategory(this.value);
  });

  // Track manual category changes
  categorySelect.addEventListener('change', function() {
    categoryManuallyChanged = this.value !== '';
  });
}

/**
 * Initialize the expense form
 */
function initializeExpenseForm() {
  const form = document.getElementById('expenseForm');
  if (!form) return;

  // Set up form submission handler
  form.addEventListener('submit', handleFormSubmit);

  // Set up category and restaurant type handling
  setupCategoryRestaurantHandling(form);

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
