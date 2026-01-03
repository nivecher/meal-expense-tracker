/**
 * Handles form submission for expense forms using Fetch API
 */

// Import security utilities for XSS prevention
let escapeHtml;
if (typeof window !== 'undefined' && window.SecurityUtils) {
  ({ escapeHtml } = window.SecurityUtils);
} else {
  // Fallback escapeHtml implementation
  escapeHtml = function(text) {
    if (text === null || text === undefined) {
      return '';
    }
    const textString = String(text);
    const map = {
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#x27;',
      '/': '&#x2F;',
    };
    return textString.replace(/[&<>"'/]/g, (char) => map[char]);
  };
}

/**
 * Escape value for safe use in HTML data attributes
 * @param {string} value - Value to escape
 * @returns {string} Escaped value safe for data attributes
 */
function escapeDataAttribute(value) {
  if (value === null || value === undefined) {
    return '';
  }
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#x27;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

/**
 * Validate redirect URL to prevent open redirect vulnerabilities.
 * Only allows relative URLs or same-origin absolute URLs.
 * Uses whitelist approach for security.
 * @param {string} url - URL to validate
 * @returns {string|null} - Validated URL or null if invalid
 */
function validateRedirectUrl(url) {
  if (!url || typeof url !== 'string') {
    return null;
  }

  // Whitelist approach: Only allow relative URLs starting with /
  // This prevents open redirect vulnerabilities
  if (url.startsWith('/')) {
    // Ensure it doesn't contain protocol or host indicators
    if (!url.includes('://') && !url.includes('//')) {
      // Additional validation: ensure it's a valid path
      // Reject URLs with suspicious patterns
      if (!url.match(/^\/[a-zA-Z0-9\-_\/?=&]*$/)) {
        return null;
      }
      return url;
    }
    return null;
  }

  // Allow same-origin absolute URLs only
  try {
    const urlObj = new URL(url, window.location.origin);
    if (urlObj.origin === window.location.origin) {
      return urlObj.pathname + urlObj.search + urlObj.hash;
    }
  } catch {
    // Invalid URL
  }

  return null;
}

/**
 * Get browser timezone - uses shared utility if available, otherwise detects it.
 * @returns {string} IANA timezone string (e.g., 'America/New_York') or 'UTC' as fallback
 */
async function getBrowserTimezone() {
  try {
    // Try to import from shared utility
    const { detectBrowserTimezone } = await import('../utils/timezone-handler.js');
    return detectBrowserTimezone();
  } catch {
    // Fallback to inline detection if import fails
    try {
      if (typeof Intl !== 'undefined' && Intl.DateTimeFormat) {
        // eslint-disable-next-line new-cap
        const options = Intl.DateTimeFormat().resolvedOptions();
        if (options && options.timeZone && typeof options.timeZone === 'string') {
          return options.timeZone;
        }
      }
    } catch (error) {
      console.warn('Timezone detection failed:', error);
    }
    return 'UTC';
  }
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
  if (errors.errorKey || errors.message || (typeof errors === 'object' && !Array.isArray(errors) && Object.keys(errors).length > 0)) {
    const errorContainer = form.querySelector('#formErrors') || document.createElement('div');
    if (!errorContainer.id) {
      errorContainer.id = 'formErrors';
      errorContainer.className = 'alert alert-danger';
      form.prepend(errorContainer);
    }

    // Clear previous messages
    errorContainer.innerHTML = '';
    errorContainer.classList.remove('d-none');

    // Add new error messages - prioritize errorKey, then message
    const messagesToShow = errors.errorKey || errors.message || [];
    const errorMessages = Array.isArray(messagesToShow) ? messagesToShow : [messagesToShow];
    errorMessages.forEach((msg) => {
      if (msg) {
        const p = document.createElement('p');
        p.className = 'mb-0';
        p.textContent = msg;
        errorContainer.appendChild(p);
      }
    });
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

  // Show general error message if no field-specific errors and no errorKey/message already shown
  const errorContainer = form.querySelector('#formErrors');
  if (errorContainer && (!errors.fields || Object.keys(errors.fields).length === 0) && !errors.errorKey && !errors.message) {
    const errorMsg = 'Please correct the errors below.';
    errorContainer.textContent = errorMsg;
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
function parseExistingTags(tagsInput) {
  const existingTagsData = tagsInput.getAttribute('data-existing-tags');
  if (existingTagsData) {
    try {
      const parsedTags = JSON.parse(existingTagsData);
      return parsedTags.map((tag) => tag.name);
    } catch (error) {
      console.warn('Failed to parse existing tags data:', error);
    }
  }

  // Fallback: parse comma-separated value
  const existingValue = tagsInput.value;
  return existingValue ? existingValue.split(',').map((tag) => tag.trim()).filter((tag) => tag) : [];
}

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

async function prepareFormDataForSubmission(form, formData) {
  console.log('Submitting form data:', Object.fromEntries(formData.entries()));

  const csrfToken = document.querySelector('input[name="csrf_token"]')?.value;

  // Add CSRF token if not already in form
  if (csrfToken && !formData.has('csrf_token')) {
    formData.append('csrf_token', csrfToken);
  }

  // Add browser timezone if not already in form
  const browserTimezone = await getBrowserTimezone();
  if (!formData.has('browser_timezone')) {
    formData.append('browser_timezone', browserTimezone);
  } else {
    // Update existing timezone field with current browser timezone
    formData.set('browser_timezone', browserTimezone);
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
    credentials: 'include', // Include cookies for authentication (required for CORS)
  });

  console.log('Response status:', response.status);
  return response;
}

function showSuccessAlert(result) {
  const alertContainer = document.getElementById('alert-container');
  if (alertContainer) {
    // Escape message to prevent XSS
    const message = escapeHtml(result.message || 'Expense added successfully!');
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

  // Validate redirect URL to prevent open redirect vulnerabilities
  // Security: validateRedirectUrl() uses whitelist approach - only allows relative URLs
  // starting with '/' or same-origin URLs. This prevents open redirect attacks.
  const requestedUrl = result.redirect || result.redirect_url || '/expenses';
  const redirectUrl = validateRedirectUrl(requestedUrl) || '/expenses';
  console.log('Form submitted successfully, redirecting to:', redirectUrl);
  // Security: redirectUrl is validated and sanitized by validateRedirectUrl()
  window.location.href = redirectUrl;
}

function handleSubmissionError(form, response, result) {
  console.error('Form submission failed with status:', response.status);
  console.error('Response result:', result);

  // Handle 401/403 authentication errors specially
  if (response.status === 401 || response.status === 403) {
    const authMessage = result.message || result.error || 'Authentication required. Please log in to continue.';
    console.error('Authentication error:', authMessage);

    // Show error and redirect to login
    showFormErrors(form, { errorKey: [authMessage] });

    // Redirect to login page after a short delay
    setTimeout(() => {
      const loginUrl = '/auth/login';
      window.location.href = loginUrl;
    }, 2000);
    return;
  }

  // Handle form validation errors
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

    const preparedData = await prepareFormDataForSubmission(form, formData);
    logSubmissionDetails(form, preparedData);

    const response = await submitFormToServer(form, preparedData);

    let result;
    try {
      result = await response.json();
    } catch (_e) {
      // If response is not JSON, create error result
      result = {
        status: 'error',
        message: `Server returned ${response.status}: ${response.statusText}`,
        code: response.status,
      };
    }

    console.log('Response data:', result);

    if (response.ok && result.success) {
      handleSuccessfulSubmission(result);
    } else {
      handleSubmissionError(form, response, result);
    }

  } catch (error) {
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

  // Add tags to form data - ensure consistent JSON format for both add and edit
  const tagsInput = document.getElementById('tagsInput');
  if (tagsInput) {
    let tagsToSend = [];

    // First try to get tags from Tagify instance (user has interacted with the field)
    if (window.tagifyInstance) {
      const selectedTags = window.tagifyInstance.value;
      if (selectedTags && selectedTags.length > 0) {
        tagsToSend = selectedTags.map((tag) => tag.value);
      }
    }

    // If no tags from Tagify, try to parse existing tags from data attribute (for editing)
    if (tagsToSend.length === 0) {
      tagsToSend = parseExistingTags(tagsInput);
    }

    // Always send tags as JSON array, even if empty
    const tagsJson = JSON.stringify(tagsToSend);
    formData.set('tags', tagsJson);
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
/**
 * Show notification (using existing notification system if available)
 */
function showNotification(message, type) {
  // Try to use existing notification system
  if (typeof window.showToast === 'function') {
    window.showToast(message, type);
  } else if (typeof window.showNotification === 'function') {
    window.showNotification(message, type);
  } else {
    // Fallback to alert
    alert(message);
  }
}

/**
 * Hide restaurant address display
 */
function hideRestaurantAddress() {
  const addressDisplay = document.getElementById('restaurant-address-display');
  if (addressDisplay) {
    addressDisplay.style.display = 'none';
    addressDisplay.innerHTML = '';
  }
}

/**
 * Display restaurant address
 */
function displayRestaurantAddress(restaurant) {
  const addressDisplay = document.getElementById('restaurant-address-display');
  if (!addressDisplay) return;

  let addressLine1 = '';
  let addressLine2 = '';

  // Prefer individual fields over full_address for two-line display
  const streetParts = [];
  if (restaurant.address_line_1) streetParts.push(restaurant.address_line_1);
  if (restaurant.address_line_2) streetParts.push(restaurant.address_line_2);
  if (streetParts.length > 0) {
    addressLine1 = streetParts.join(', ');
  }

  const locationParts = [];
  if (restaurant.city) locationParts.push(restaurant.city);
  if (restaurant.state) locationParts.push(restaurant.state);
  if (restaurant.postal_code) locationParts.push(restaurant.postal_code);
  if (locationParts.length > 0) {
    addressLine2 = locationParts.join(', ');
  }

  // Fallback to full_address if we don't have individual fields
  if (!addressLine1 && !addressLine2 && restaurant.full_address) {
    addressLine1 = restaurant.full_address;
  }

  if (addressLine1 || addressLine2) {
    let addressHtml = '<div class="text-muted small d-flex">';
    addressHtml += '<i class="fas fa-map-marker-alt me-1 mt-1"></i>';
    addressHtml += '<div>';
    if (addressLine1) {
      addressHtml += `<div>${escapeHtml(addressLine1)}</div>`;
    }
    if (addressLine2) {
      addressHtml += `<div>${escapeHtml(addressLine2)}</div>`;
    }
    addressHtml += '</div>';
    addressHtml += '</div>';
    addressDisplay.innerHTML = addressHtml;
    addressDisplay.style.display = 'block';
  } else {
    hideRestaurantAddress();
  }
}

/**
 * Fetch restaurant address for reconciliation (returns address string)
 */
async function fetchRestaurantAddressForReconciliation(restaurantId) {
  if (!restaurantId) {
    return 'Not set';
  }

  try {
    // Get CSRF token
    let csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
    if (!csrfToken) {
      const csrfInput = document.querySelector('input[name="csrf_token"]');
      csrfToken = csrfInput ? csrfInput.value : '';
    }

    const response = await fetch(`/api/v1/restaurants/${restaurantId}`, {
      method: 'GET',
      headers: {
        'X-CSRFToken': csrfToken,
        'X-Requested-With': 'XMLHttpRequest',
        Accept: 'application/json',
      },
      credentials: 'include', // Include cookies for authentication (required for CORS)
    });

    if (response.ok) {
      const result = await response.json();
      if (result.status === 'success' && result.data) {
        const restaurant = result.data;
        const addressParts = [];
        if (restaurant.full_address) {
          return restaurant.full_address;
        }
        if (restaurant.address_line_1) addressParts.push(restaurant.address_line_1);
        if (restaurant.address_line_2) addressParts.push(restaurant.address_line_2);
        if (restaurant.city) addressParts.push(restaurant.city);
        if (restaurant.state) addressParts.push(restaurant.state);
        if (restaurant.postal_code) addressParts.push(restaurant.postal_code);
        if (addressParts.length > 0) {
          return addressParts.join(', ');
        }

      }
    }
  } catch (error) {
    console.warn('Failed to fetch restaurant address for reconciliation:', error);
  }
  return 'Not set';
}

/**
 * Fetch restaurant address and display it
 */
async function fetchRestaurantAddress(restaurantId) {
  if (!restaurantId) {
    hideRestaurantAddress();
    return;
  }

  const addressDisplay = document.getElementById('restaurant-address-display');
  if (!addressDisplay) return;

  try {
    // Show loading state
    addressDisplay.innerHTML = '<small class="text-muted"><i class="fas fa-spinner fa-spin"></i> Loading address...</small>';
    addressDisplay.style.display = 'block';

    // Get CSRF token
    let csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
    if (!csrfToken) {
      const csrfInput = document.querySelector('input[name="csrf_token"]');
      csrfToken = csrfInput ? csrfInput.value : '';
    }

    const response = await fetch(`/api/v1/restaurants/${restaurantId}`, {
      method: 'GET',
      headers: {
        'X-CSRFToken': csrfToken,
        'X-Requested-With': 'XMLHttpRequest',
        Accept: 'application/json',
      },
      credentials: 'include', // Include cookies for authentication (required for CORS)
    });

    if (response.ok) {
      const result = await response.json();
      if (result.status === 'success' && result.data) {
        const restaurant = result.data;
        displayRestaurantAddress(restaurant);
      } else {
        hideRestaurantAddress();
      }
    } else {
      hideRestaurantAddress();
    }
  } catch (error) {
    console.warn('Failed to fetch restaurant address:', error);
    hideRestaurantAddress();
  }
}

async function fetchRestaurantDefaultCategory(restaurantId) {
  if (!restaurantId) {
    return null;
  }

  try {
    // Get CSRF token
    let csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
    if (!csrfToken) {
      const csrfInput = document.querySelector('input[name="csrf_token"]');
      csrfToken = csrfInput ? csrfInput.value : '';
    }

    const response = await fetch(`/api/v1/restaurants/${restaurantId}/default-category`, {
      method: 'GET',
      headers: {
        'X-CSRFToken': csrfToken,
        'X-Requested-With': 'XMLHttpRequest',
        Accept: 'application/json',
      },
      credentials: 'include', // Include cookies for authentication (required for CORS)
    });

    if (response.ok) {
      const result = await response.json();
      if (result.status === 'success' && result.data && result.data.category_id) {
        return result.data.category_id;
      }
    }
  } catch (error) {
    console.warn('Failed to fetch restaurant default category:', error);
  }
  return null;
}

/**
 * Map restaurant type to category name
 */
function mapRestaurantTypeToCategory(restaurantType) {
  if (!restaurantType || typeof restaurantType !== 'string') {
    return 'Other';
  }

  const typeLower = restaurantType.toLowerCase().trim();

  // Fast Food Restaurant -> Fast Food (check this first before general Restaurant check)
  if (typeLower.includes('fast food restaurant') || typeLower === 'fast food') {
    return 'Fast Food';
  }

  // Coffee Shop -> Coffee Shops (or Drinks as fallback)
  if (typeLower.includes('coffee shop') || typeLower === 'coffee shop' || typeLower === 'cafe') {
    return 'Coffee Shops';
  }

  // Grocery Store -> Groceries
  if (typeLower.includes('grocery store') || typeLower === 'grocery store' || typeLower === 'supermarket') {
    return 'Groceries';
  }

  // Any type containing "Restaurant" -> Restaurants
  if (typeLower.includes('restaurant')) {
    return 'Restaurants';
  }

  // Default fallback
  return 'Other';
}

/**
 * Find category ID by category name, with fallback options
 */
function findCategoryIdByName(categorySelect, categoryName) {
  if (!categorySelect || !categoryName) {
    return null;
  }

  // Search through all options to find matching category name
  for (const option of categorySelect.options) {
    if (option.text.trim() === categoryName) {
      return option.value;
    }
  }

  // Fallback: If "Coffee Shops" not found, try "Drinks"
  if (categoryName === 'Coffee Shops') {
    for (const option of categorySelect.options) {
      if (option.text.trim() === 'Drinks') {
        return option.value;
      }
    }
  }

  return null;
}

function setupCategoryRestaurantHandling(form) {
  const categorySelect = form.querySelector('select[name="category_id"]');
  const restaurantSelect = form.querySelector('select[name="restaurant_id"]');

  if (!categorySelect || !restaurantSelect) return;

  // Track if category was manually changed
  let categoryManuallyChanged = false;
  // Flag to track programmatic category changes (to avoid marking them as manual)
  let isProgrammaticChange = false;

  // Helper function to set category by ID
  function setCategoryById(categoryIdValue) {
    const optionExists = Array.from(categorySelect.options).some(
      (option) => option.value === String(categoryIdValue),
    );
    if (optionExists) {
      isProgrammaticChange = true;
      categorySelect.value = String(categoryIdValue);
      categorySelect.dispatchEvent(new Event('change', { bubbles: true }));
      isProgrammaticChange = false;
      return true;
    }
    return false;
  }

  // Helper function to try setting default category as fallback
  async function trySetDefaultCategory(restaurantId) {
    const defaultCategoryId = await fetchRestaurantDefaultCategory(restaurantId);
    if (defaultCategoryId) {
      return setCategoryById(defaultCategoryId);
    }
    return false;
  }

  // Function to update category based on restaurant type
  async function updateCategory(restaurantId) {
    if (categoryManuallyChanged) return;
    if (!restaurantId) {
      categorySelect.value = '';
      return;
    }

    try {
      // Get CSRF token
      let csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
      if (!csrfToken) {
        const csrfInput = document.querySelector('input[name="csrf_token"]');
        csrfToken = csrfInput ? csrfInput.value : '';
      }

      // Fetch restaurant data to get the type
      const response = await fetch(`/api/v1/restaurants/${restaurantId}`, {
        method: 'GET',
        headers: {
          'X-CSRFToken': csrfToken,
          'X-Requested-With': 'XMLHttpRequest',
          Accept: 'application/json',
        },
      });

      if (!response.ok) {
        await trySetDefaultCategory(restaurantId);
        return;
      }

      const result = await response.json();
      if (result.status !== 'success' || !result.data) {
        await trySetDefaultCategory(restaurantId);
        return;
      }

      const restaurant = result.data;
      const restaurantType = restaurant.type || '';

      // Map restaurant type to category name
      const categoryName = mapRestaurantTypeToCategory(restaurantType);

      // Find category ID by name
      const categoryId = findCategoryIdByName(categorySelect, categoryName);

      if (categoryId) {
        setCategoryById(categoryId);
      } else {
        // Category name not found in options, try fallback to default category
        await trySetDefaultCategory(restaurantId);
      }
    } catch (error) {
      console.warn('Failed to update category based on restaurant type:', error);
      // Fallback to default category if restaurant fetch fails
      await trySetDefaultCategory(restaurantId);
    }
  }

  // Handle restaurant change
  restaurantSelect.addEventListener('change', function() {
    // Reset manual change flag when restaurant changes (allows auto-setting again)
    categoryManuallyChanged = false;
    updateCategory(this.value);
    // Fetch and display restaurant address
    if (this.value) {
      fetchRestaurantAddress(this.value);
    } else {
      hideRestaurantAddress();
    }
  });

  // Track manual category changes (only if not programmatic)
  categorySelect.addEventListener('change', function() {
    if (!isProgrammaticChange) {
      categoryManuallyChanged = this.value !== '';
    }
  });

  // If category is already set (e.g., in edit mode), mark it as manually changed
  if (categorySelect.value) {
    categoryManuallyChanged = true;
  }

  // Initialize restaurant address display and category if restaurant is pre-selected
  // Note: This happens during setup, but address will also be fetched in initializeExpenseForm
  // if the restaurant value is set after this function runs
  if (restaurantSelect.value) {
    fetchRestaurantAddress(restaurantSelect.value);
    // Only auto-set category if it's not already set (new expense, not edit)
    if (!categorySelect.value) {
      updateCategory(restaurantSelect.value);
    }
  }
}

/**
 * Initialize the expense form
 */
async function initializeExpenseForm() {
  const form = document.getElementById('expenseForm');
  if (!form) return;

  // Set browser timezone in hidden field
  const timezoneInput = document.getElementById('browser_timezone');
  if (timezoneInput) {
    try {
      const detectedTimezone = await getBrowserTimezone();
      timezoneInput.value = detectedTimezone;
    } catch (error) {
      console.warn('Failed to detect timezone:', error);
      timezoneInput.value = 'UTC';
    }
  }

  // Set up form submission handler
  form.addEventListener('submit', handleFormSubmit);

  // Set up category and restaurant type handling
  setupCategoryRestaurantHandling(form);

  // Auto-save draft functionality has been removed - it was causing confusion
  // and overwriting correct server-provided values (especially date/time in browser timezone)

  // Check if we're editing an existing expense or if restaurant is pre-selected
  const restaurantSelect = form.querySelector('select[name="restaurant_id"]');
  if (restaurantSelect) {
    // If there's a data-restaurant-id attribute, use it to set the selected option
    const { restaurantId } = restaurantSelect.dataset;
    if (restaurantId) {
      const optionToSelect = restaurantSelect.querySelector(`option[value="${restaurantId}"]`);
      if (optionToSelect) {
        optionToSelect.selected = true;
        console.log('Set selected restaurant:', restaurantId);
        // Fetch and display restaurant address
        fetchRestaurantAddress(restaurantId);
      } else {
        console.warn('Could not find restaurant option with value:', restaurantId);
      }
    } else if (restaurantSelect.value) {
      // If restaurant is already selected (e.g., from form data), fetch address
      fetchRestaurantAddress(restaurantSelect.value);
    }
  }
}

// =============================================================================
// RECEIPT OCR PROCESSING FUNCTIONALITY
// =============================================================================

/**
 * Apply OCR suggestion to form field
 */
function applyOCRSuggestion(field, value) {
  if (field === 'amount') {
    const amountInput = document.getElementById('amount');
    if (amountInput) {
      amountInput.value = value;
      amountInput.dispatchEvent(new Event('change', { bubbles: true }));
      showNotification('Amount updated from receipt', 'success');
    }
  } else if (field === 'date') {
    const dateInput = document.getElementById('date');
    if (dateInput) {
      dateInput.value = value;
      dateInput.dispatchEvent(new Event('change', { bubbles: true }));
      showNotification('Date updated from receipt', 'success');
    }
  } else if (field === 'restaurant') {
    // Try to find matching restaurant in dropdown
    const restaurantSelect = document.getElementById('restaurant_id');
    if (restaurantSelect) {
      // Search for restaurant by name (fuzzy match)
      for (const option of restaurantSelect.options) {
        if (option.text.toLowerCase().includes(value.toLowerCase()) ||
          value.toLowerCase().includes(option.text.toLowerCase())) {
          restaurantSelect.value = option.value;
          restaurantSelect.dispatchEvent(new Event('change', { bubbles: true }));
          showNotification('Restaurant updated from receipt', 'success');
          return;
        }
      }
      showNotification('Restaurant not found in your list. Please add it manually.', 'info');
    }
  } else if (field === 'time') {
    // Update time input field (type="time" expects HH:mm format)
    const timeInput = document.getElementById('time');
    if (timeInput) {
      // Parse the time value (e.g., "12:55 PM")
      const timeMatch = value.match(/(\d{1,2}):(\d{2})\s*(AM|PM)/i);
      if (timeMatch) {
        let hours = parseInt(timeMatch[1], 10);
        const minutes = parseInt(timeMatch[2], 10);
        const ampm = timeMatch[3].toUpperCase();

        // Convert to 24-hour format
        if (ampm === 'PM' && hours !== 12) {
          hours += 12;
        } else if (ampm === 'AM' && hours === 12) {
          hours = 0;
        }

        // Format as HH:mm for time input
        const hours24 = String(hours).padStart(2, '0');
        const mins = String(minutes).padStart(2, '0');
        timeInput.value = `${hours24}:${mins}`;
        timeInput.dispatchEvent(new Event('change', { bubbles: true }));
        showNotification('Time updated from receipt', 'success');
      }
    }
  } else if (field === 'restaurant_phone' || field === 'restaurant_website') {
    // Phone and website are restaurant fields, not expense fields
    // Show notification that these need to be updated on the restaurant record
    showNotification('Phone and website are restaurant fields. Please update them in the restaurant settings.', 'info');
  }
}

/**
 * Convert 24-hour time format to 12-hour format with AM/PM
 * @param {string} timeValue - Time in HH:mm format (24-hour)
 * @returns {string} Time in HH:MM AM/PM format or 'Not set'
 */
function formatTimeTo12Hour(timeValue) {
  if (!timeValue) {
    return 'Not set';
  }
  const [hours24, minutes] = timeValue.split(':');
  const hours = parseInt(hours24, 10);
  const mins = parseInt(minutes, 10);
  if (isNaN(hours) || isNaN(mins)) {
    return 'Not set';
  }
  // Convert to 12-hour format
  let hours12 = hours;
  const ampm = hours >= 12 ? 'PM' : 'AM';
  if (hours > 12) {
    hours12 = hours - 12;
  } else if (hours === 0) {
    hours12 = 12;
  }
  return `${hours12}:${String(mins).padStart(2, '0')} ${ampm}`;
}

/**
 * Compare two time strings with ±15 minute tolerance
 * @param {string} formTime - Form time in HH:MM AM/PM format
 * @param {string} ocrTime - OCR time in HH:MM AM/PM format
 * @returns {boolean} True if times match within tolerance
 */
function compareTimes(formTime, ocrTime) {
  if (formTime === 'Not set' || !ocrTime) {
    return false;
  }
  try {
    const formTimeMatch = formTime.match(/(\d{1,2}):(\d{2})\s*(AM|PM)/i);
    const ocrTimeMatch = ocrTime.match(/(\d{1,2}):(\d{2})\s*(AM|PM)/i);
    if (!formTimeMatch || !ocrTimeMatch) {
      return false;
    }
    let formHours = parseInt(formTimeMatch[1], 10);
    const formMinutes = parseInt(formTimeMatch[2], 10);
    const formAmpm = formTimeMatch[3].toUpperCase();
    let ocrHours = parseInt(ocrTimeMatch[1], 10);
    const ocrMinutes = parseInt(ocrTimeMatch[2], 10);
    const ocrAmpm = ocrTimeMatch[3].toUpperCase();

    // Convert to 24-hour format for comparison
    if (formAmpm === 'PM' && formHours !== 12) formHours += 12;
    if (formAmpm === 'AM' && formHours === 12) formHours = 0;
    if (ocrAmpm === 'PM' && ocrHours !== 12) ocrHours += 12;
    if (ocrAmpm === 'AM' && ocrHours === 12) ocrHours = 0;

    const formTotalMinutes = formHours * 60 + formMinutes;
    const ocrTotalMinutes = ocrHours * 60 + ocrMinutes;
    const timeDiff = Math.abs(formTotalMinutes - ocrTotalMinutes);
    return timeDiff <= 15; // ±15 minute tolerance
  } catch {
    return false;
  }
}

/**
 * Update address comparison in reconciliation table row
 * @param {HTMLElement} formValueCell - Cell containing form address value
 * @param {HTMLElement} row - Table row element
 * @param {string} address - Form address value
 * @param {string} ocrAddress - OCR extracted address value
 */
function updateAddressComparisonInRow(formValueCell, row, address, ocrAddress) {
  // Use semantic address comparison
  let addressMatch = false;
  let addressFormatDiffers = false;
  if (typeof window.AddressUtils !== 'undefined' && window.AddressUtils.compareAddressesSemantic) {
    const comparison = window.AddressUtils.compareAddressesSemantic(address, ocrAddress);
    addressMatch = comparison.isMatch;
    addressFormatDiffers = comparison.formatDiffers;
  } else {
    // Fallback: Simple comparison
    const formAddressLower = address.toLowerCase().replace(/[^\w\s]/g, '').replace(/\s+/g, ' ').trim();
    const ocrAddressLower = ocrAddress.toLowerCase().replace(/[^\w\s]/g, '').replace(/\s+/g, ' ').trim();
    addressMatch = formAddressLower && ocrAddressLower && (
      formAddressLower === ocrAddressLower ||
      formAddressLower.includes(ocrAddressLower) ||
      ocrAddressLower.includes(formAddressLower)
    );
  }
  const matchClass = addressMatch && !addressFormatDiffers ? 'text-success' : 'text-warning';
  formValueCell.className = matchClass;
  const ocrValueCell = row.querySelector('td:nth-child(3)');
  if (ocrValueCell) {
    ocrValueCell.className = matchClass;
  }
  const matchIcon = row.querySelector('td:first-child i');
  if (matchIcon) {
    matchIcon.className = addressMatch && !addressFormatDiffers
      ? 'fas fa-check-circle'
      : addressMatch && addressFormatDiffers
        ? 'fas fa-check-circle text-warning'
        : 'fas fa-exclamation-triangle';
  }
  const actionCell = row.querySelector('td:last-child');
  if (actionCell) {
    if (addressMatch && addressFormatDiffers) {
      actionCell.textContent = 'Match (format differs)';
    } else if (addressMatch) {
      actionCell.textContent = 'Match';
    }
  }
}

/**
 * Display reconciliation results
 * Optimized to prevent long tasks by using DocumentFragment and batching DOM operations
 */
function displayReconciliationResults(ocrData) {
  const panelDiv = document.getElementById('reconciliation-panel');
  const resultsDiv = document.getElementById('reconciliation-results');

  if (!panelDiv || !resultsDiv) return;

  // Cache DOM queries to avoid repeated lookups
  const amountInput = document.getElementById('amount');
  const dateInput = document.getElementById('date');
  const restaurantSelect = document.getElementById('restaurant_id');
  const timeInput = document.getElementById('time');

  // Get current form values (cached)
  const formAmount = amountInput?.value || '';
  const formDate = dateInput?.value || '';
  const formRestaurant = restaurantSelect?.selectedOptions[0]?.text || '';
  const formRestaurantId = restaurantSelect?.value;

  // Use DocumentFragment for efficient DOM manipulation
  const fragment = document.createDocumentFragment();
  const table = document.createElement('table');
  table.className = 'table table-sm table-bordered reconciliation-table';

  // Create table header
  const thead = document.createElement('thead');
  const headerRow = document.createElement('tr');
  ['Field', 'Form Value', 'Receipt Value', 'Action'].forEach((text) => {
    const th = document.createElement('th');
    th.textContent = text;
    headerRow.appendChild(th);
  });
  thead.appendChild(headerRow);
  table.appendChild(thead);

  const tbody = document.createElement('tbody');

  /**
   * Helper function to create a table row for reconciliation
   */
  function createReconciliationRow(fieldName, formValue, ocrValue, isMatch, ocrDataValue, fieldType, options = {}) {
    const row = document.createElement('tr');
    const matchClass = isMatch ? 'text-success' : 'text-warning';
    const matchIconClass = isMatch ? 'fas fa-check-circle' : 'fas fa-exclamation-triangle';
    const hideApplyButton = options.hideApplyButton || false;
    const matchPercentage = options.matchPercentage || null;

    // Field name cell
    const fieldCell = document.createElement('td');
    const strong = document.createElement('strong');
    strong.textContent = fieldName;
    const icon = document.createElement('i');
    icon.className = matchIconClass;
    fieldCell.appendChild(strong);
    fieldCell.appendChild(document.createTextNode(' '));
    fieldCell.appendChild(icon);
    row.appendChild(fieldCell);

    // Form value cell
    const formValueCell = document.createElement('td');
    formValueCell.className = matchClass;
    formValueCell.textContent = formValue;
    row.appendChild(formValueCell);

    // OCR value cell
    const ocrValueCell = document.createElement('td');
    ocrValueCell.className = matchClass;
    ocrValueCell.textContent = ocrValue;
    row.appendChild(ocrValueCell);

    // Action cell
    const actionCell = document.createElement('td');
    if (hideApplyButton) {
      // Show match percentage instead of apply button
      if (matchPercentage !== null) {
        actionCell.textContent = `Match (${matchPercentage}%)`;
      } else if (isMatch) {
        actionCell.textContent = 'Match';
      } else {
        actionCell.textContent = 'No match';
      }
    } else if (!isMatch && ocrDataValue) {
      const button = document.createElement('button');
      button.className = 'btn btn-sm btn-primary';
      button.textContent = 'Apply';
      button.setAttribute('data-field', fieldType);
      // Escape value to prevent XSS in data attribute
      button.setAttribute('data-value', escapeDataAttribute(String(ocrDataValue || '')));
      actionCell.appendChild(button);
    } else {
      actionCell.textContent = 'Match';
    }
    row.appendChild(actionCell);

    return row;
  }

  // Amount comparison
  if (ocrData.amount) {
    const formAmountNum = parseFloat(formAmount) || 0;
    const ocrAmountNum = parseFloat(ocrData.amount) || 0;
    const amountMatch = Math.abs(formAmountNum - ocrAmountNum) < 0.01; // ±1 cent tolerance
    const row = createReconciliationRow(
      'Amount',
      `$${formAmountNum.toFixed(2)}`,
      `$${ocrAmountNum.toFixed(2)}`,
      amountMatch,
      ocrData.amount,
      'amount',
    );
    tbody.appendChild(row);
  }

  // Date comparison with timezone awareness
  if (ocrData.date) {
    // Form date is in YYYY-MM-DD format (browser timezone context)
    const [formDateOnly] = formDate.split('T');

    // OCR date is an ISO datetime string (UTC)
    // Convert to browser timezone and extract date part
    let ocrDateInBrowserTz;
    let ocrDateOnly;
    try {
      // Parse the OCR date (assumed to be in UTC)
      const ocrDateUtc = new Date(ocrData.date);

      // Convert to browser's local timezone
      // Use Intl.DateTimeFormat to format in browser timezone
      // eslint-disable-next-line new-cap
      const dateTimeFormat = Intl.DateTimeFormat();
      const browserTimezone = dateTimeFormat.resolvedOptions().timeZone;

      const formatter = new Intl.DateTimeFormat('en-CA', {
        timeZone: browserTimezone,
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
      });

      // Format the UTC date in browser timezone to get YYYY-MM-DD
      const parts = formatter.formatToParts(ocrDateUtc);
      const year = parts.find((p) => p.type === 'year')?.value || '';
      const month = parts.find((p) => p.type === 'month')?.value || '';
      const day = parts.find((p) => p.type === 'day')?.value || '';
      ocrDateOnly = `${year}-${month}-${day}`;

      // Also format for display (with timezone context)
      ocrDateInBrowserTz = ocrDateOnly;
    } catch (error) {
      // Fallback: try simple date extraction if timezone conversion fails
      console.warn('Timezone conversion failed, using fallback:', error);
      const [fallbackDate] = ocrData.date.split('T');
      ocrDateOnly = fallbackDate;
      ocrDateInBrowserTz = ocrDateOnly;
    }

    // Compare dates (both should now be in YYYY-MM-DD format, browser timezone context)
    // Allow ±1 day difference for timezone edge cases
    const formDateObj = new Date(`${formDateOnly}T12:00:00`);
    const ocrDateObj = new Date(`${ocrDateOnly}T12:00:00`);
    const dateDiff = Math.abs(formDateObj - ocrDateObj);
    const dateMatch = formDateOnly === ocrDateOnly || dateDiff < 86400000; // ±1 day

    const row = createReconciliationRow(
      'Date',
      formDateOnly || 'Not set',
      ocrDateInBrowserTz,
      dateMatch,
      ocrDateOnly, // Use date-only format for applying
      'date',
    );
    tbody.appendChild(row);
  }

  // Time comparison
  if (ocrData.time) {
    // Extract time from form time input (type="time" format: HH:mm in 24-hour format)
    const formTime = timeInput && timeInput.value
      ? formatTimeTo12Hour(timeInput.value)
      : 'Not set';

    // Compare times with ±15 minute tolerance
    const timeMatch = compareTimes(formTime, ocrData.time);

    const row = createReconciliationRow(
      'Time',
      formTime,
      ocrData.time,
      timeMatch,
      ocrData.time,
      'time',
    );
    tbody.appendChild(row);
  }

  // Restaurant comparison (fuzzy match)
  if (ocrData.restaurant_name) {
    // Use backend similarity score if available, otherwise fall back to exact match check
    let restaurantMatch = false;
    let similarityScore = null;

    if (ocrData.reconciliation && ocrData.reconciliation.suggestions) {
      similarityScore = ocrData.reconciliation.suggestions.restaurant_similarity;
      if (similarityScore !== undefined) {
        // Use backend match status if available
        restaurantMatch = ocrData.reconciliation.matches?.restaurant === true;
      }
    }

    // Fallback to exact match check if no backend similarity available
    // Only match if names are exactly the same (case-insensitive)
    // Don't use substring check as it incorrectly matches "Cotton Patch Cafe" with "Cotton Patch Cafe - Wylie"
    if (similarityScore === null || similarityScore === undefined) {
      const formRestaurantLower = (formRestaurant || '').toLowerCase().trim();
      const ocrRestaurantLower = ocrData.restaurant_name.toLowerCase().trim();
      restaurantMatch = formRestaurantLower === ocrRestaurantLower;

      // If not exact match, calculate a simple similarity for display
      if (!restaurantMatch && formRestaurantLower && ocrRestaurantLower) {
        similarityScore = calculateSimpleSimilarity(formRestaurantLower, ocrRestaurantLower);
      }
    }

    // Create restaurant name row (no apply button, show match percentage)
    const restaurantFieldName = 'Restaurant';
    let matchPercentage = null;
    if (similarityScore !== null && similarityScore !== undefined) {
      matchPercentage = (similarityScore * 100).toFixed(0);
    } else if (restaurantMatch) {
      matchPercentage = '100';
    }

    const row = createReconciliationRow(
      restaurantFieldName,
      formRestaurant || 'Not set',
      ocrData.restaurant_name,
      restaurantMatch,
      ocrData.restaurant_name,
      'restaurant',
      {
        hideApplyButton: true,
        matchPercentage,
      },
    );
    tbody.appendChild(row);
  }

  // Restaurant address comparison
  if (ocrData.restaurant_address) {
    // Get restaurant address from API response data (restaurant_address_data)
    let formAddress = 'Not set';

    // First try: Get address from API response (restaurant_address_data from selected restaurant)
    if (ocrData.restaurant_address_data) {
      const restaurantAddr = ocrData.restaurant_address_data;
      if (restaurantAddr.full_address) {
        formAddress = restaurantAddr.full_address;
      } else {
        // Build from components
        const addressParts = [];
        if (restaurantAddr.address_line_1) addressParts.push(restaurantAddr.address_line_1);
        if (restaurantAddr.address_line_2) addressParts.push(restaurantAddr.address_line_2);
        if (restaurantAddr.city) addressParts.push(restaurantAddr.city);
        if (restaurantAddr.state) addressParts.push(restaurantAddr.state);
        if (restaurantAddr.postal_code) addressParts.push(restaurantAddr.postal_code);
        if (addressParts.length > 0) {
          formAddress = addressParts.join(', ');
        }
      }
    } else if (formRestaurantId) {
      // Fallback: Fetch restaurant address from API if not in OCR response
      // Note: This is async, so we'll show "Loading..." initially and update when it arrives
      formAddress = 'Loading...';
      // Defer async operation to avoid blocking
      requestAnimationFrame(() => {
        fetchRestaurantAddressForReconciliation(formRestaurantId).then((address) => {
          if (!address || address === 'Not set') {
            return;
          }
          // Update the reconciliation table with the fetched address
          const addressRow = tbody.querySelector('tr[data-field="restaurant_address"]');
          if (!addressRow) {
            return;
          }
          const formValueCell = addressRow.querySelector('td:nth-child(2)');
          if (!formValueCell) {
            return;
          }
          formValueCell.textContent = address;
          // Re-evaluate match status with the fetched address
          const ocrAddress = ocrData.restaurant_address;
          if (ocrAddress) {
            updateAddressComparisonInRow(formValueCell, addressRow, address, ocrAddress);
          }
        });
      });
    }

    // Check if address matches from reconciliation data
    let addressMatch = false;
    let addressFormatDiffers = false;
    let addressMatchStatus = 'Match';
    let matchClass = 'text-warning';
    let matchIconClass = 'fas fa-exclamation-triangle';

    if (ocrData.reconciliation && ocrData.reconciliation.matches) {
      addressMatch = ocrData.reconciliation.matches.restaurant_address === true;
      // Check if format differs (would be in warnings if available)
      if (addressMatch && ocrData.reconciliation.warnings) {
        const formatWarning = ocrData.reconciliation.warnings.find((w) =>
          w.includes('formats differ but match semantically'),
        );
        addressFormatDiffers = !!formatWarning;
      }
    } else {
      // Use semantic address comparison with USPS normalization
      if (typeof window.AddressUtils !== 'undefined' && window.AddressUtils.compareAddressesSemantic) {
        const comparison = window.AddressUtils.compareAddressesSemantic(formAddress, ocrData.restaurant_address);
        addressMatch = comparison.isMatch;
        addressFormatDiffers = comparison.formatDiffers;
      } else {
        // Fallback: Simple address comparison (normalize and compare)
        const formAddressLower = formAddress.toLowerCase().replace(/[^\w\s]/g, '').replace(/\s+/g, ' ').trim();
        const ocrAddressLower = ocrData.restaurant_address.toLowerCase().replace(/[^\w\s]/g, '').replace(/\s+/g, ' ').trim();
        addressMatch = formAddressLower && ocrAddressLower && (
          formAddressLower === ocrAddressLower ||
          formAddressLower.includes(ocrAddressLower) ||
          ocrAddressLower.includes(formAddressLower)
        );
      }
    }

    // Determine match status and styling
    if (addressMatch && addressFormatDiffers) {
      addressMatchStatus = 'Match (format differs)';
      matchClass = 'text-warning';
      matchIconClass = 'fas fa-check-circle text-warning';
    } else if (addressMatch) {
      addressMatchStatus = 'Match';
      matchClass = 'text-success';
      matchIconClass = 'fas fa-check-circle';
    } else {
      addressMatchStatus = 'Mismatch';
      matchClass = 'text-warning';
      matchIconClass = 'fas fa-exclamation-triangle';
    }

    // Create address row
    const addressRow = document.createElement('tr');
    addressRow.setAttribute('data-field', 'restaurant_address');
    const fieldCell = document.createElement('td');
    const strong = document.createElement('strong');
    strong.textContent = 'Restaurant Address';
    const icon = document.createElement('i');
    icon.className = matchIconClass;
    fieldCell.appendChild(strong);
    fieldCell.appendChild(document.createTextNode(' '));
    fieldCell.appendChild(icon);
    addressRow.appendChild(fieldCell);

    const formValueCell = document.createElement('td');
    formValueCell.className = matchClass;
    // Use textContent which is safe - it doesn't execute HTML/JS
    // textContent automatically escapes HTML entities, but we escape for extra safety
    // Note: formAddress comes from ocrData but is safely escaped and used with textContent
    const safeAddress = escapeHtml(formAddress);
    formValueCell.textContent = safeAddress;
    addressRow.appendChild(formValueCell);

    const ocrValueCell = document.createElement('td');
    ocrValueCell.className = matchClass;
    // textContent automatically escapes HTML, but escape for extra safety
    ocrValueCell.textContent = escapeHtml(ocrData.restaurant_address);
    addressRow.appendChild(ocrValueCell);

    const actionCell = document.createElement('td');
    if (!addressMatch) {
      const button = document.createElement('button');
      button.className = 'btn btn-sm btn-primary';
      button.textContent = 'Apply';
      button.setAttribute('data-field', 'restaurant_address');
      // Escape value to prevent XSS in data attribute
      button.setAttribute('data-value', escapeDataAttribute(String(ocrData.restaurant_address || '')));
      actionCell.appendChild(button);
    } else {
      actionCell.textContent = addressMatchStatus;
    }
    addressRow.appendChild(actionCell);

    tbody.appendChild(addressRow);
  }

  // Restaurant phone comparison (always show if restaurant is selected)
  if (formRestaurantId || ocrData.restaurant_phone) {
    // Get phone from API response data (restaurant_address_data)
    let formPhone = 'Not set';
    if (ocrData.restaurant_address_data && ocrData.restaurant_address_data.phone) {
      formPhone = ocrData.restaurant_address_data.phone;
    }

    const ocrPhone = ocrData.restaurant_phone || 'Not found on receipt';

    // Normalize phone numbers for comparison (remove spaces, dashes, parentheses)
    const normalizePhone = (phone) => {
      if (!phone || phone === 'Not set' || phone === 'Not found on receipt') return '';
      return phone.replace(/[\s\-()]/g, '').replace(/^\+?1/, '');
    };

    const formPhoneNormalized = normalizePhone(formPhone);
    const ocrPhoneNormalized = normalizePhone(ocrPhone);
    const phoneMatch = formPhoneNormalized && ocrPhoneNormalized && formPhoneNormalized === ocrPhoneNormalized;
    const hasBothValues = formPhoneNormalized && ocrPhoneNormalized;

    const matchClass = phoneMatch ? 'text-success' : (hasBothValues ? 'text-warning' : 'text-muted');
    const matchIconClass = phoneMatch ? 'fas fa-check-circle' : (hasBothValues ? 'fas fa-exclamation-triangle' : 'fas fa-info-circle');

    const row = document.createElement('tr');
    const fieldCell = document.createElement('td');
    const strong = document.createElement('strong');
    strong.textContent = 'Restaurant Phone';
    const icon = document.createElement('i');
    icon.className = matchIconClass;
    fieldCell.appendChild(strong);
    fieldCell.appendChild(document.createTextNode(' '));
    fieldCell.appendChild(icon);
    row.appendChild(fieldCell);

    const formValueCell = document.createElement('td');
    formValueCell.className = matchClass;
    formValueCell.textContent = formPhone;
    row.appendChild(formValueCell);

    const ocrValueCell = document.createElement('td');
    ocrValueCell.className = matchClass;
    ocrValueCell.textContent = ocrPhone;
    row.appendChild(ocrValueCell);

    const actionCell = document.createElement('td');
    if (ocrData.restaurant_phone && !phoneMatch) {
      const button = document.createElement('button');
      button.className = 'btn btn-sm btn-primary';
      button.textContent = 'Apply';
      button.setAttribute('data-field', 'restaurant_phone');
      // Escape value to prevent XSS in data attribute
      button.setAttribute('data-value', escapeDataAttribute(String(ocrData.restaurant_phone || '')));
      actionCell.appendChild(button);
    } else {
      actionCell.textContent = phoneMatch ? 'Match' : '-';
    }
    row.appendChild(actionCell);

    tbody.appendChild(row);
  }

  // Restaurant website comparison (always show if restaurant is selected)
  if (formRestaurantId || ocrData.restaurant_website) {
    // Get website from API response data (restaurant_address_data)
    let formWebsite = 'Not set';
    if (ocrData.restaurant_address_data && ocrData.restaurant_address_data.website) {
      formWebsite = ocrData.restaurant_address_data.website;
    }

    const ocrWebsite = ocrData.restaurant_website || 'Not found on receipt';

    // Normalize URLs for comparison (remove http://, https://, www., trailing slashes)
    const normalizeWebsite = (url) => {
      if (!url || url === 'Not set' || url === 'Not found on receipt') return '';
      return url.toLowerCase()
        .replace(/^https?:\/\//, '')
        .replace(/^www\./, '')
        .replace(/\/$/, '');
    };

    const formWebsiteNormalized = normalizeWebsite(formWebsite);
    const ocrWebsiteNormalized = normalizeWebsite(ocrWebsite);
    const websiteMatch = formWebsiteNormalized && ocrWebsiteNormalized && formWebsiteNormalized === ocrWebsiteNormalized;
    const hasBothValues = formWebsiteNormalized && ocrWebsiteNormalized;

    const matchClass = websiteMatch ? 'text-success' : (hasBothValues ? 'text-warning' : 'text-muted');
    const matchIconClass = websiteMatch ? 'fas fa-check-circle' : (hasBothValues ? 'fas fa-exclamation-triangle' : 'fas fa-info-circle');

    const row = document.createElement('tr');
    const fieldCell = document.createElement('td');
    const strong = document.createElement('strong');
    strong.textContent = 'Restaurant Website';
    const icon = document.createElement('i');
    icon.className = matchIconClass;
    fieldCell.appendChild(strong);
    fieldCell.appendChild(document.createTextNode(' '));
    fieldCell.appendChild(icon);
    row.appendChild(fieldCell);

    const formValueCell = document.createElement('td');
    formValueCell.className = matchClass;
    formValueCell.textContent = formWebsite;
    row.appendChild(formValueCell);

    const ocrValueCell = document.createElement('td');
    ocrValueCell.className = matchClass;
    ocrValueCell.textContent = ocrWebsite;
    row.appendChild(ocrValueCell);

    const actionCell = document.createElement('td');
    if (ocrData.restaurant_website && !websiteMatch) {
      const button = document.createElement('button');
      button.className = 'btn btn-sm btn-primary';
      button.textContent = 'Apply';
      button.setAttribute('data-field', 'restaurant_website');
      // Escape value to prevent XSS in data attribute
      button.setAttribute('data-value', escapeDataAttribute(String(ocrData.restaurant_website || '')));
      actionCell.appendChild(button);
    } else {
      actionCell.textContent = websiteMatch ? 'Match' : '-';
    }
    row.appendChild(actionCell);

    tbody.appendChild(row);
  }

  // Complete table structure
  table.appendChild(tbody);
  fragment.appendChild(table);

  // Use requestAnimationFrame to batch DOM updates and prevent blocking
  requestAnimationFrame(() => {
    resultsDiv.innerHTML = '';
    resultsDiv.appendChild(fragment);
    panelDiv.style.display = 'block';

    // Attach event listeners after DOM is updated (defer to avoid blocking)
    requestAnimationFrame(() => {
      const applyButtons = resultsDiv.querySelectorAll('button.btn-primary');
      applyButtons.forEach((button) => {
        const field = button.getAttribute('data-field');
        const value = button.getAttribute('data-value');
        if (field && value) {
          button.addEventListener('click', (e) => {
            e.preventDefault();
            applyOCRSuggestion(field, value);
          });
        }
      });
    });
  });
}

/**
 * View receipt in new tab
 */
function viewReceipt() {
  const receiptInput = document.getElementById('receipt_image');
  if (!receiptInput) return;

  // Clean up previous blob URL if exists
  if (window.currentReceiptBlobUrl) {
    URL.revokeObjectURL(window.currentReceiptBlobUrl);
    window.currentReceiptBlobUrl = null;
  }

  if (receiptInput.files && receiptInput.files.length > 0) {
    const [file] = receiptInput.files;
    try {
      // Create blob URL and open in new tab
      const blobUrl = URL.createObjectURL(file);
      window.currentReceiptBlobUrl = blobUrl;
      window.open(blobUrl, '_blank');
    } catch (_error) {
      showNotification('Failed to open receipt', 'error');
    }
  } else {
    // Check for existing receipt URL
    const existingReceiptUrl = receiptInput.getAttribute('data-existing-receipt');
    if (existingReceiptUrl) {
      window.open(existingReceiptUrl, '_blank');
    } else {
      showNotification('No receipt file available', 'warning');
    }
  }
}

/**
 * Process receipt with OCR to extract data
 */
async function processReceiptOCR() {
  const receiptInput = document.getElementById('receipt_image');
  const processBtn = document.getElementById('process-receipt-btn');
  const statusDiv = document.getElementById('ocr-processing-status');
  const statusText = document.getElementById('ocr-status-text');
  const panelDiv = document.getElementById('reconciliation-panel');

  if (!receiptInput) {
    showNotification('Receipt input not found', 'error');
    return;
  }

  let file;
  const hasNewFile = receiptInput.files && receiptInput.files.length > 0;

  if (hasNewFile) {
    // Existing behavior: use newly selected file
    [file] = receiptInput.files;
  } else {
    // New behavior: fetch existing receipt
    const existingReceiptUrl = receiptInput.getAttribute('data-existing-receipt');
    if (!existingReceiptUrl) {
      showNotification('Please select a receipt file first', 'warning');
      return;
    }

    // Fetch existing receipt and convert to File
    try {
      // Fetch from S3 presigned URL (presigned URLs don't require credentials, but including them is harmless)
      const response = await fetch(existingReceiptUrl, {
        credentials: 'include', // Include cookies (harmless for presigned URLs, but needed if CORS is involved)
      });

      if (!response.ok) {
        // Handle specific S3 error cases
        if (response.status === 403) {
          throw new Error('Access denied to receipt. The presigned URL may have expired.');
        } else if (response.status === 404) {
          throw new Error('Receipt file not found in storage.');
        } else {
          throw new Error(`Failed to fetch receipt: ${response.status} ${response.statusText}`);
        }
      }

      // Check if response is actually a file (not an error page)
      const contentType = response.headers.get('content-type');
      if (!contentType || (!contentType.startsWith('image/') && contentType !== 'application/pdf')) {
        // Might be an error page, try to get text
        const text = await response.text();
        if (text.includes('Error') || text.includes('AccessDenied') || text.includes('InvalidArgument')) {
          throw new Error('Failed to access receipt from storage. The URL may be invalid or expired.');
        }
      }

      const blob = await response.blob();

      // Validate blob size (should not be empty)
      if (blob.size === 0) {
        throw new Error('Received empty receipt file from storage.');
      }

      // Determine filename from URL or use default
      const urlParts = existingReceiptUrl.split('/');
      const filename = urlParts[urlParts.length - 1].split('?')[0] || 'receipt.pdf';
      file = new File([blob], filename, { type: blob.type || contentType || 'application/octet-stream' });
    } catch (error) {
      console.error('Error fetching existing receipt from S3:', error);
      const errorMessage = error.message || 'Failed to load existing receipt';
      showNotification(errorMessage, 'error');
      return;
    }
  }

  // Validate file size (5MB)
  const maxSize = 5 * 1024 * 1024;
  if (file.size > maxSize) {
    showNotification('File is too large. Maximum size is 5MB.', 'error');
    return;
  }

  // Show processing status
  if (statusDiv && statusText) {
    statusDiv.style.display = 'block';
    statusText.textContent = 'Processing receipt with OCR...';
    processBtn.disabled = true;
  }

  // Hide previous reconciliation results
  if (panelDiv) {
    panelDiv.style.display = 'none';
  }

  try {
    // Create form data
    const formData = new FormData();
    formData.append('receipt_file', file);

    // Add form values as hints for better matching (especially for bank statements)
    const amountInput = document.getElementById('amount');
    const dateInput = document.getElementById('date');
    const restaurantSelect = document.getElementById('restaurant_id');

    if (amountInput && amountInput.value) {
      formData.append('form_amount', amountInput.value);
    }
    if (dateInput && dateInput.value) {
      formData.append('form_date', dateInput.value);
    }
    if (restaurantSelect && restaurantSelect.selectedOptions[0]) {
      formData.append('form_restaurant_name', restaurantSelect.selectedOptions[0].text);
      if (restaurantSelect.value) {
        formData.append('form_restaurant_id', restaurantSelect.value);
      }
    }

    // Get CSRF token (check meta tag first, then form input)
    let csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
    if (!csrfToken) {
      const csrfInput = document.querySelector('input[name="csrf_token"]');
      csrfToken = csrfInput ? csrfInput.value : '';
    }

    if (!csrfToken) {
      showNotification('CSRF token not found', 'error');
      return;
    }

    // Send to OCR API
    const response = await fetch('/api/v1/receipts/ocr', {
      method: 'POST',
      headers: {
        'X-CSRFToken': csrfToken,
        'X-Requested-With': 'XMLHttpRequest', // Ensure API request detection
        Accept: 'application/json', // Ensure API request detection
      },
      credentials: 'include', // Include cookies for authentication (required for CORS)
      body: formData,
    });

    // Check for authentication errors
    if (response.status === 401 || response.status === 403) {
      showNotification('Authentication required. Please log in to use this feature.', 'error');
      return;
    }

    if (!response.ok) {
      // Try to get error message from response
      let errorMessage = `Failed to process receipt: ${response.status} ${response.statusText}`;
      try {
        const errorResult = await response.json();
        if (errorResult.message) {
          errorMessage = errorResult.message;
        } else if (errorResult.error) {
          errorMessage = errorResult.error;
        }

        // Provide helpful message for 503 (service unavailable)
        if (response.status === 503) {
          if (errorResult.message && errorResult.message.includes('OCR service not available')) {
            errorMessage = 'Receipt processing is not available. AWS Textract is not configured. Please contact support.';
          } else if (errorResult.message && errorResult.message.includes('OCR is disabled')) {
            errorMessage = 'Receipt processing is currently disabled.';
          } else {
            errorMessage = 'Receipt processing service is temporarily unavailable. Please try again later.';
          }
        }
      } catch (_e) {
        // Response is not JSON, use default message
        if (response.status === 503) {
          errorMessage = 'Receipt processing service is temporarily unavailable. Please try again later.';
        }
      }
      showNotification(errorMessage, 'error');
      return;
    }

    // Check if response is JSON
    const contentType = response.headers.get('content-type');
    if (!contentType || !contentType.includes('application/json')) {
      showNotification('Invalid response format from server', 'error');
      return;
    }

    const result = await response.json();

    if (result.status === 'success' && result.data) {
      // Display reconciliation results
      displayReconciliationResults(result.data);
      showNotification('Receipt processed successfully', 'success');
    } else {
      showNotification(result.message || 'Failed to process receipt', 'error');
    }
  } catch (error) {
    console.error('Error processing receipt:', error);
    showNotification(`Failed to process receipt: ${error.message || 'Unknown error'}`, 'error');
  } finally {
    // Reset processing status
    if (statusDiv && statusText) {
      statusDiv.style.display = 'none';
      statusText.textContent = '';
      processBtn.disabled = false;
    }
  }
}

/**
 * Process receipt with OCR when file is selected
 */
function setupReceiptOCR() {
  const receiptInput = document.getElementById('receipt_image');
  const processBtn = document.getElementById('process-receipt-btn');
  const viewBtn = document.getElementById('view-receipt-btn');

  if (receiptInput && processBtn && viewBtn) {
    // Function to check if buttons should be enabled
    const updateButtonState = () => {
      const hasFile = receiptInput.files && receiptInput.files.length > 0;
      const hasExistingReceipt = receiptInput.getAttribute('data-existing-receipt');

      // View button: only enable when new file is selected
      viewBtn.disabled = !hasFile;

      // Process button: enable when new file OR existing receipt is available
      processBtn.disabled = !(hasFile || hasExistingReceipt);
    };

    // Update button state when file is selected
    receiptInput.addEventListener('change', () => {
      updateButtonState();
    });

    // Initial state check - buttons start disabled unless file is selected
    updateButtonState();

    // Simple click handler - opens receipt in new tab
    viewBtn.removeAttribute('onclick');
    viewBtn.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();
      viewReceipt();
    });

    // Process receipt button click handler
    processBtn.removeAttribute('onclick');
    processBtn.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();
      processReceiptOCR();
    });
  }
}

/**
 * Apply all OCR suggestions
 */
function applyAllSuggestions() {
  const resultsDiv = document.getElementById('reconciliation-results');
  if (!resultsDiv) {
    return;
  }

  const applyButtons = resultsDiv.querySelectorAll('button.btn-primary');
  applyButtons.forEach((button) => {
    const onclick = button.getAttribute('onclick');
    if (onclick) {
      // Extract function call and execute it
      const match = onclick.match(/applyOCRSuggestion\('([^']+)',\s*'([^']+)'\)/);
      if (match) {
        applyOCRSuggestion(match[1], match[2]);
      }
    }
  });

  showNotification('All suggestions applied', 'success');
}

/**
 * Dismiss reconciliation panel
 */
function dismissReconciliation() {
  const panelDiv = document.getElementById('reconciliation-panel');
  if (panelDiv) {
    panelDiv.style.display = 'none';
  }
}

/**
 * Delete receipt (matches inline template function behavior)
 */
function deleteReceipt() {
  if (confirm('Are you sure you want to delete this receipt? This action cannot be undone.')) {
    const deleteReceiptInput = document.getElementById('delete_receipt');
    const receiptInput = document.getElementById('receipt_image');

    if (deleteReceiptInput) {
      deleteReceiptInput.value = 'true';
    }

    if (receiptInput) {
      receiptInput.value = '';
    }

    // Hide reconciliation panel if visible
    dismissReconciliation();

    // Hide the receipt actions
    const receiptActions = document.querySelector('.d-flex.gap-2');
    if (receiptActions) {
      receiptActions.style.display = 'none';
    }

    showNotification('Receipt marked for deletion', 'info');
  }
}

// Make OCR functions globally accessible for onclick handlers
window.processReceiptOCR = processReceiptOCR;
window.applyOCRSuggestion = applyOCRSuggestion;
window.applyAllSuggestions = applyAllSuggestions;
window.dismissReconciliation = dismissReconciliation;
window.deleteReceipt = deleteReceipt;
window.viewReceipt = viewReceipt;

// Initialize receipt OCR when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  setupReceiptOCR();
});

// Initialize the form when the DOM is fully loaded
document.addEventListener('DOMContentLoaded', initializeExpenseForm);
