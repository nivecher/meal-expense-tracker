/**
 * Enhanced error handling for restaurant operations
 * Handles specific error cases like duplicate Google Place ID
 */

import { showErrorToast, showWarningToast, showInfoToast } from './notifications.js';
import { getLogger } from './logger.js';

const logger = getLogger('RestaurantErrorHandler');

/**
 * Handle restaurant-related errors with specific error type handling
 * @param {Error|Object} error - The error object or response
 * @param {Object} context - Additional context for error handling
 */
export function handleRestaurantError(error, context = {}) {
  logger.debug('Handling restaurant error:', error, context);

  // If it's a fetch response error, try to parse the error details
  if (error && typeof error === 'object' && error.error) {
    return handleStructuredError(error, context);
  }

  // If it's a simple error message
  if (typeof error === 'string') {
    return handleGenericError(error, context);
  }

  // If it's an Error object with a message
  if (error instanceof Error) {
    return handleGenericError(error.message, context);
  }

  // Default fallback
  return handleGenericError('An unexpected error occurred', context);
}

/**
 * Handle structured error responses from the API
 * @param {Object} errorResponse - Structured error response
 * @param {Object} context - Additional context
 */
function handleStructuredError(errorResponse, context) {
  const { error } = errorResponse;

  switch (error.code) {
    case 'DUPLICATE_GOOGLE_PLACE_ID':
      return handleDuplicateGooglePlaceIdError(error, context);

    case 'DUPLICATE_RESTAURANT':
      return handleDuplicateRestaurantError(error, context);

    case 'VALIDATION_ERROR':
      return handleValidationError(error, context);

    default:
      return handleGenericError(error.message || 'Unknown error occurred', context);
  }
}

/**
 * Handle duplicate Google Place ID error with user-friendly options
 * @param {Object} error - The duplicate Google Place ID error
 * @param {Object} context - Additional context
 */
function handleDuplicateGooglePlaceIdError(error, context) {
  logger.info('Handling duplicate Google Place ID error:', error);

  const { existing_restaurant, google_place_id } = error;

  // Create and show a modal with options
  showDuplicateRestaurantModal({
    title: 'Restaurant Already Exists',
    message: `You already have "${existing_restaurant.full_name}" in your restaurants.`,
    details: `This restaurant has the same Google Place ID (${google_place_id.slice(0, 20)}...).`,
    existing_restaurant,
    actions: [
      {
        label: 'View Existing Restaurant',
        class: 'btn-primary',
        action: () => {
          window.location.href = `/restaurants/${existing_restaurant.id}`;
        },
      },
      {
        label: 'Add Expense to This Restaurant',
        class: 'btn-success',
        action: () => {
          window.location.href = `/expenses/add?restaurant_id=${existing_restaurant.id}`;
        },
      },
      {
        label: 'Cancel',
        class: 'btn-secondary',
        action: () => {
          // Just close the modal
        },
      },
    ],
  });

  return true; // Indicate error was handled
}

/**
 * Handle duplicate restaurant (name/city) error
 * @param {Object} error - The duplicate restaurant error
 * @param {Object} context - Additional context
 */
function handleDuplicateRestaurantError(error, context) {
  logger.info('Handling duplicate restaurant error:', error);

  const { existing_restaurant, name, city } = error;

  showDuplicateRestaurantModal({
    title: 'Similar Restaurant Found',
    message: `You already have a restaurant named "${name}"${city ? ` in ${city}` : ''}.`,
    details: 'This might be the same restaurant you\'re trying to add.',
    existing_restaurant,
    actions: [
      {
        label: 'View Existing Restaurant',
        class: 'btn-primary',
        action: () => {
          window.location.href = `/restaurants/${existing_restaurant.id}`;
        },
      },
      {
        label: 'Add Anyway',
        class: 'btn-warning',
        action: () => {
          // Allow user to proceed with creation
          showWarningToast('You can modify the restaurant name or location to make it unique.');
        },
      },
      {
        label: 'Cancel',
        class: 'btn-secondary',
        action: () => {
          // Just close the modal
        },
      },
    ],
  });

  return true;
}

/**
 * Handle validation errors
 * @param {Object} error - The validation error
 * @param {Object} context - Additional context
 */
function handleValidationError(error, context) {
  logger.warn('Handling validation error:', error);

  const message = error.message || 'Please check your input and try again.';

  if (error.field) {
    // Highlight the specific field if possible
    const fieldElement = document.querySelector(`[name="${error.field}"], #${error.field}`);
    if (fieldElement) {
      fieldElement.classList.add('is-invalid');
      fieldElement.focus();

      // Remove invalid class after a delay
      setTimeout(() => {
        fieldElement.classList.remove('is-invalid');
      }, 5000);
    }
  }

  showErrorToast(message, 5000);
  return true;
}

/**
 * Handle generic errors
 * @param {string} message - Error message
 * @param {Object} context - Additional context
 */
function handleGenericError(message, context) {
  logger.error('Handling generic error:', message, context);

  // Extract meaningful error from common error patterns
  let userMessage = message;

  if (message.includes('Google Place ID')) {
    userMessage = 'This restaurant already exists in your list. Please choose a different restaurant or search for the existing one.';
  } else if (message.includes('already exists')) {
    userMessage = 'A similar restaurant already exists. Please check your existing restaurants or modify the details.';
  } else if (message.includes('Failed to save')) {
    userMessage = 'Unable to save the restaurant. Please check your connection and try again.';
  } else if (message.includes('Failed to add')) {
    userMessage = 'Unable to add the restaurant. Please check your connection and try again.';
  }

  showErrorToast(userMessage, 5000);
  return false; // Indicate generic handling
}

/**
 * Show a modal for duplicate restaurant conflicts
 * @param {Object} options - Modal configuration
 */
function showDuplicateRestaurantModal(options) {
  const {
    title,
    message,
    details,
    existing_restaurant,
    actions = [],
  } = options;

  // Create modal HTML
  const modalId = 'duplicateRestaurantModal';
  const modalHtml = `
    <div class="modal fade" id="${modalId}" tabindex="-1" aria-labelledby="${modalId}Label" aria-hidden="true">
      <div class="modal-dialog modal-dialog-centered">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title" id="${modalId}Label">
              <i class="fas fa-exclamation-triangle text-warning me-2"></i>
              ${title}
            </h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
          </div>
          <div class="modal-body">
            <div class="alert alert-warning" role="alert">
              <strong>${message}</strong>
              ${details ? `<br><small class="text-muted">${details}</small>` : ''}
            </div>

            ${existing_restaurant ? `
              <div class="card mt-3">
                <div class="card-body">
                  <h6 class="card-title">
                    <i class="fas fa-utensils me-2"></i>
                    ${existing_restaurant.full_name}
                  </h6>
                  <div class="d-flex gap-2 mt-2">
                    <a href="/restaurants/${existing_restaurant.id}" class="btn btn-sm btn-outline-primary">
                      <i class="fas fa-eye me-1"></i>
                      View Details
                    </a>
                    <a href="/expenses/add?restaurant_id=${existing_restaurant.id}" class="btn btn-sm btn-outline-success">
                      <i class="fas fa-plus me-1"></i>
                      Add Expense
                    </a>
                  </div>
                </div>
              </div>
            ` : ''}
          </div>
          <div class="modal-footer">
            ${actions.map((action) => `
              <button type="button" class="btn ${action.class}" data-action="${action.label}">
                ${action.label}
              </button>
            `).join('')}
          </div>
        </div>
      </div>
    </div>
  `;

  // Remove existing modal if any
  const existingModal = document.getElementById(modalId);
  if (existingModal) {
    existingModal.remove();
  }

  // Add modal to DOM
  document.body.insertAdjacentHTML('beforeend', modalHtml);

  const modalElement = document.getElementById(modalId);

  // Add event listeners for action buttons
  actions.forEach((action) => {
    const button = modalElement.querySelector(`[data-action="${action.label}"]`);
    if (button && action.action) {
      button.addEventListener('click', () => {
        action.action();
        // Close modal after action (unless it's a navigation action)
        if (!action.label.includes('View') && !action.label.includes('Add Expense')) {
          const bsModal = bootstrap.Modal.getInstance(modalElement);
          if (bsModal) bsModal.hide();
        }
      });
    }
  });

  // Show modal
  const bsModal = new bootstrap.Modal(modalElement);
  bsModal.show();

  // Clean up modal after hiding
  modalElement.addEventListener('hidden.bs.modal', () => {
    modalElement.remove();
  });
}

/**
 * Parse error response from fetch
 * @param {Response} response - Fetch response
 * @returns {Promise<Object>} Parsed error object
 */
export async function parseErrorResponse(response) {
  try {
    const errorData = await response.json();
    return {
      status: response.status,
      error: errorData.error || { message: errorData.message || 'Unknown error' },
      message: errorData.message,
    };
  } catch (parseError) {
    logger.warn('Failed to parse error response:', parseError);
    return {
      status: response.status,
      error: { message: `HTTP ${response.status}: ${response.statusText}` },
      message: `HTTP ${response.status}: ${response.statusText}`,
    };
  }
}

/**
 * Enhanced fetch wrapper with restaurant error handling
 * @param {string} url - Request URL
 * @param {Object} options - Fetch options
 * @returns {Promise<Object>} Response data
 */
export async function fetchWithRestaurantErrorHandling(url, options = {}) {
  try {
    const response = await fetch(url, options);

    if (!response.ok) {
      const errorData = await parseErrorResponse(response);

      // Handle specific HTTP status codes
      if (response.status === 409) {
        // Conflict - likely duplicate restaurant
        handleRestaurantError(errorData);
        throw new Error('Restaurant conflict handled');
      }

      throw new Error(errorData.message || `HTTP ${response.status}`);
    }

    return response.json();
  } catch (error) {
    if (error.message !== 'Restaurant conflict handled') {
      handleRestaurantError(error);
    }
    throw error;
  }
}

// Export for global access
if (typeof window !== 'undefined') {
  window.RestaurantErrorHandler = {
    handleRestaurantError,
    parseErrorResponse,
    fetchWithRestaurantErrorHandling,
  };
}
