/**
 * Enhanced error handling for restaurant operations
 * Handles specific error cases like duplicate Google Place ID
 */

import { showErrorToast, showWarningToast, showInfoToast } from './notifications.js';
import { getLogger } from './logger.js';

const logger = getLogger('RestaurantErrorHandler');

// Error handler functions - defined first
function showDuplicateRestaurantModal(existingRestaurant, googlePlaceId = null) {
  // Create modal HTML
  const modalHtml = `
    <div class="modal fade" id="duplicateRestaurantModal" tabindex="-1" aria-labelledby="duplicateRestaurantModalLabel" aria-hidden="true">
      <div class="modal-dialog">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title" id="duplicateRestaurantModalLabel">Restaurant Already Exists</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
          </div>
          <div class="modal-body">
            <div class="alert alert-warning" role="alert">
              <i class="fas fa-exclamation-triangle me-2"></i>
              A restaurant with this information already exists in our database.
            </div>

            <div class="card">
              <div class="card-header">
                <h6 class="mb-0">Existing Restaurant Details</h6>
              </div>
              <div class="card-body">
                <p><strong>Name:</strong> ${existingRestaurant.name}</p>
                <p><strong>Address:</strong> ${existingRestaurant.address || 'Not provided'}</p>
                ${existingRestaurant.phone ? `<p><strong>Phone:</strong> ${existingRestaurant.phone}</p>` : ''}
                ${existingRestaurant.website ? `<p><strong>Website:</strong> <a href="${existingRestaurant.website}" target="_blank">${existingRestaurant.website}</a></p>` : ''}
                ${googlePlaceId ? `<p><strong>Google Place ID:</strong> ${googlePlaceId}</p>` : ''}
              </div>
            </div>

            <div class="mt-3">
              <p class="text-muted small">
                If this is the same restaurant, you can use the existing entry.
                If it's different, please modify the information to make it unique.
              </p>
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
            <button type="button" class="btn btn-primary" onclick="window.location.href='/restaurants/${existingRestaurant.id}'">
              View Existing Restaurant
            </button>
          </div>
        </div>
      </div>
    </div>
  `;

  // Remove existing modal if present
  const existingModal = document.getElementById('duplicateRestaurantModal');
  if (existingModal) {
    existingModal.remove();
  }

  // Add modal to page
  document.body.insertAdjacentHTML('beforeend', modalHtml);

  // Show modal
  const modal = new bootstrap.Modal(document.getElementById('duplicateRestaurantModal'));
  modal.show();

  // Clean up modal when hidden
  document.getElementById('duplicateRestaurantModal').addEventListener('hidden.bs.modal', () => {
    document.getElementById('duplicateRestaurantModal').remove();
  });
}

function handleGenericError(message, context) {
  logger.error('Generic restaurant error:', message, context);
  showErrorToast(message);
}

function handleDuplicateGooglePlaceIdError(error, context) {
  const { existing_restaurant, google_place_id } = error.details || {};

  logger.warn('Duplicate Google Place ID detected:', { existing_restaurant, google_place_id });

  // Show modal with existing restaurant details
  showDuplicateRestaurantModal(existing_restaurant, google_place_id);
}

function handleDuplicateRestaurantError(error, context) {
  const { existing_restaurant } = error.details || {};

  logger.warn('Duplicate restaurant detected:', { existing_restaurant });

  // Show modal with existing restaurant details
  showDuplicateRestaurantModal(existing_restaurant);
}

function handleValidationError(error, context) {
  const { field_errors } = error.details || {};

  logger.warn('Restaurant validation error:', { field_errors });

  if (field_errors && Object.keys(field_errors).length > 0) {
    const errorMessages = Object.values(field_errors).flat();
    showErrorToast(`Validation failed: ${errorMessages.join(', ')}`);
  } else {
    showErrorToast('Please check your input and try again.');
  }
}

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
      return handleGenericError(error.message || 'An error occurred', context);
  }
}

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
 * Handle network errors specifically
 * @param {Error} error - Network error
 * @param {Object} context - Additional context
 */
export function handleNetworkError(error, context = {}) {
  logger.error('Network error:', error, context);

  if (!navigator.onLine) {
    showErrorToast('No internet connection. Please check your network and try again.');
  } else if (error.name === 'TypeError' && error.message.includes('fetch')) {
    showErrorToast('Unable to connect to the server. Please try again later.');
  } else {
    showErrorToast('A network error occurred. Please try again.');
  }
}

/**
 * Handle timeout errors
 * @param {Error} error - Timeout error
 * @param {Object} context - Additional context
 */
export function handleTimeoutError(error, context = {}) {
  logger.error('Timeout error:', error, context);
  showWarningToast('The request timed out. Please try again.');
}

/**
 * Handle server errors (5xx)
 * @param {Object} response - Server response
 * @param {Object} context - Additional context
 */
export function handleServerError(response, context = {}) {
  logger.error('Server error:', response, context);

  const status = response.status || 500;
  const message = response.statusText || 'Internal Server Error';

  showErrorToast(`Server error (${status}): ${message}. Please try again later.`);
}

/**
 * Handle client errors (4xx)
 * @param {Object} response - Client error response
 * @param {Object} context - Additional context
 */
export function handleClientError(response, context = {}) {
  logger.warn('Client error:', response, context);

  const status = response.status || 400;
  const message = response.statusText || 'Bad Request';

  showWarningToast(`Request error (${status}): ${message}. Please check your input.`);
}
