/**
 * Restaurant Places Search
 *
 * Initializes the Google Places search component for finding restaurants
 */

// Import required modules
import RestaurantSearch from '../components/restaurant-search.js';
import { googlePlacesService } from '../services/google-places.js';
import { GoogleMapsLoader } from '../utils/google-maps.js';
import { initializeModalAccessibility } from '../utils/modal-accessibility.js';
import { getCSRFToken } from '../utils/csrf-token.js';
import { showSuccessToast, showErrorToast } from '../utils/notifications.js';
import { mapPlaceTypesToRestaurant } from '../utils/cuisine-formatter.js';

// Initialize the page when the DOM is fully loaded
document.addEventListener('DOMContentLoaded', async() => {
  // Get modal elements (success modal removed - using toasts instead)
  const errorModal = document.getElementById('errorModal');

  if (errorModal) {
    initializeModalAccessibility(errorModal);
    // Add robust focus management
    errorModal.addEventListener('shown.bs.modal', () => {
      setTimeout(() => {
        const closeBtn = errorModal.querySelector('#error-close-btn');
        if (closeBtn) {
          // Remove tabindex to make it focusable, then focus
          closeBtn.removeAttribute('tabindex');
          closeBtn.focus();
          console.log('Restaurant Places Search: Focused close button after error modal shown');
        }
      }, 50);
    });

    // Ensure tabindex is reset when modal is hidden
    errorModal.addEventListener('hidden.bs.modal', () => {
      const closeBtn = errorModal.querySelector('#error-close-btn');
      if (closeBtn) {
        closeBtn.setAttribute('tabindex', '-1');
        console.log('Restaurant Places Search: Reset close button tabindex after modal hidden');
      }
    });

    // Ensure focus is removed before modal is hidden
    errorModal.addEventListener('hide.bs.modal', () => {
      const focusedElement = document.activeElement;
      if (focusedElement && errorModal.contains(focusedElement)) {
        focusedElement.blur();
        console.log('Restaurant Places Search: Removed focus before error modal hide');
      }
    });
  }

  // Check if we're on the places search page
  const searchContainer = document.getElementById('find-places-search');
  if (!searchContainer) return;

  try {
    // Get API key from app config
    const appConfig = JSON.parse(document.getElementById('app-config').dataset.appConfig);
    const apiKey = appConfig?.googleMaps?.apiKey;

    if (!apiKey) {
      throw new Error('Google Maps API key is not configured in the application settings.');
    }

    console.log('Initializing Google Maps API...');

    // Get the loading indicator element
    const loadingIndicator = document.getElementById('loading-indicator');

    // Initialize Google Maps API with retry and error handling
    try {
      await GoogleMapsLoader.loadApiWithRetry(
        apiKey,
        () => {
          console.log('Google Maps API loaded, initializing search component...');

          // Ensure the Google Maps API is fully loaded
          if (!window.google || !window.google.maps || !window.google.maps.places) {
            throw new Error('Google Maps API is not fully loaded');
          }

          // Add a delay to ensure all Google Maps services are fully initialized
          setTimeout(() => {
            try {
              // Update the googlePlacesService with the API key
              googlePlacesService.apiKey = apiKey;

              const restaurantSearch = new RestaurantSearch({
                container: searchContainer,
                onSelect: handleRestaurantSelect,
                onError: handleSearchError,
                onAddRestaurant: handleAddRestaurantClick,
              });

              // Make the search component available globally for debugging
              window.restaurantSearch = restaurantSearch;

              console.log('Restaurant search component initialized successfully');

              // Hide loading indicator if it was shown
              if (loadingIndicator) {
                loadingIndicator.classList.add('d-none');
              }
            } catch (initError) {
              console.error('Error during search component initialization:', initError);
              handleSearchError(`Failed to initialize search component: ${initError.message}`);
            }
          }, 500); // 500ms delay to ensure Google Maps services are ready
        },
        ['places', 'geocoding'], // Required libraries
        3, // maxRetries
        1000, // retryDelay
      );
    } catch (error) {
      console.error('Error initializing Google Maps API:', error);
      handleSearchError(`Failed to load Google Maps: ${error.message}`);
      return;
    }
  } catch (error) {
    console.error('Error initializing Google Maps:', error);
    handleSearchError(`Failed to initialize Google Maps: ${error.message}`);
  }

  // Set up the retry button in the error modal
  const retryButton = document.getElementById('retry-button');
  if (retryButton) {
    retryButton.addEventListener('click', () => {
      window.location.reload();
    });
  }

  // Global modal focus management as a backup for any programmatically shown modals
  document.addEventListener('shown.bs.modal', (event) => {
    const modal = event.target;
    const modalId = modal.id;

    console.log('Restaurant Places Search: Global modal shown event for:', modalId);

    // Success modal removed - using toasts for feedback instead

    // Handle error modal
    if (modalId === 'errorModal') {
      setTimeout(() => {
        const closeBtn = modal.querySelector('#error-close-btn');
        if (closeBtn && document.activeElement !== closeBtn) {
          closeBtn.focus();
          console.log('Restaurant Places Search: Global handler focused close button');
        }
      }, 100);
    }
  });

  // Global modal hide management to prevent aria-hidden conflicts
  document.addEventListener('hide.bs.modal', (event) => {
    const modal = event.target;
    const focusedElement = document.activeElement;

    if (focusedElement && modal.contains(focusedElement)) {
      focusedElement.blur();
      console.log('Restaurant Places Search: Global handler removed focus before modal hide');
    }
  });

  // Setup aria-hidden watcher with proper error handling
  const setupAriaHiddenWatcher = (modal, modalName) => {
    // Safety: Validate inputs
    if (!modal || !modalName) {
      console.warn(`setupAriaHiddenWatcher: Invalid parameters - modal: ${!!modal}, modalName: ${modalName}`);
      return null;
    }

    try {
      const observer = new MutationObserver((mutations) => {
        mutations.forEach((mutation) => {
          if (mutation.type === 'attributes' && mutation.attributeName === 'aria-hidden') {
            try {
              const isHidden = modal.getAttribute('aria-hidden') === 'true';
              const hasFocusedChild = modal.contains(document.activeElement);

              console.log(`${modalName}: aria-hidden changed to ${isHidden}, has focused child: ${hasFocusedChild}`);

              if (isHidden && hasFocusedChild) {
                // Safety: Check if activeElement exists before blurring
                if (document.activeElement && typeof document.activeElement.blur === 'function') {
                  document.activeElement.blur();
                  console.log(`${modalName}: Emergency focus removal due to aria-hidden conflict`);
                }
              } else if (!isHidden && modal.style.display !== 'none') {
                // Set focus when aria-hidden is removed and modal is visible
                setTimeout(() => {
                  const targetBtn = modal.querySelector('#continue-searching-btn, #error-close-btn');
                  if (targetBtn && document.activeElement !== targetBtn) {
                    // Safety: Ensure element can receive focus
                    targetBtn.removeAttribute('tabindex');
                    if (typeof targetBtn.focus === 'function') {
                      targetBtn.focus();
                      console.log(`${modalName}: Focus set after aria-hidden removed (via MutationObserver)`);
                    }
                  }
                }, 50);
              }
            } catch (error) {
              console.error(`${modalName}: Error in aria-hidden mutation handler:`, error);
            }
          }
        });
      });

      observer.observe(modal, {
        attributes: true,
        attributeFilter: ['aria-hidden'],
      });

      console.log(`${modalName}: MutationObserver setup for aria-hidden monitoring`);
      return observer;

    } catch (error) {
      console.error(`${modalName}: Failed to setup MutationObserver:`, error);
      return null;
    }
  };

  // Set up watcher for error modal with safety check
  if (errorModal) {
    setupAriaHiddenWatcher(errorModal, 'Error Modal');
  } else {
    console.warn('Restaurant Places Search: Error modal not found, skipping aria-hidden watcher setup');
  }
});

/**
 * Handle "Add Restaurant" button click from search results
 * @param {Object} restaurant - Selected restaurant data from Google Places
 */
async function handleAddRestaurantClick(restaurant) {
  // Safety: Validate restaurant data
  if (!restaurant || typeof restaurant !== 'object') {
    console.error('Invalid restaurant data provided to handleAddRestaurantClick');
    showErrorToast('Invalid restaurant data. Please try selecting a different restaurant.');
    return;
  }

  try {
    const google_place_id = extract_place_id(restaurant);

    // Check for existing restaurant before attempting to add
    const duplicate_check = await check_for_existing_restaurant(google_place_id);

    if (duplicate_check.exists) {
      showExistingRestaurantModal(duplicate_check, restaurant);
      return;
    }

    await process_new_restaurant_addition(restaurant, google_place_id);
  } catch (error) {
    console.error('Error handling add restaurant click:', error);

    // Enhanced error handling - check if it's a conflict that wasn't caught by pre-check
    if (error.message && error.message.includes('already exists')) {
      showErrorToast('This restaurant already exists in your list. Please check your existing restaurants.');
    } else if (error.message && error.message.includes('Restaurant conflict handled')) {
      // Error was already handled by showConflictDialog, no need to show additional error
      return;
    } else {
      // Generic error handling
      const userFriendlyMessage = error.message.includes('HTTP error')
        ? 'Unable to connect to server. Please check your connection and try again.'
        : `Error adding restaurant: ${error.message}`;

      handleSearchError(userFriendlyMessage);
    }
  }
}

function extract_place_id(restaurant) {
  // Handle different Google Places API formats
  const google_place_id = restaurant.placeId || restaurant.place_id || restaurant.id || '';
  console.log('Extracted place ID:', google_place_id, 'from restaurant object:', restaurant);
  return google_place_id;
}

async function check_for_existing_restaurant(google_place_id) {
  const check_url = '/restaurants/check-restaurant-exists';
  const response = await fetch(check_url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Requested-With': 'XMLHttpRequest',
      'X-CSRFToken': getCSRFToken(),
    },
    body: JSON.stringify({ google_place_id }),
    credentials: 'same-origin',
  });

  return await response.json();
}

async function process_new_restaurant_addition(restaurant, google_place_id) {
  console.log('Restaurant does not exist, adding new restaurant...');

  const address_components = extract_restaurant_address_components(restaurant);
  const restaurant_data = build_restaurant_submission_data(restaurant, address_components, google_place_id);

  console.log('Submitting restaurant data:', restaurant_data);
  await submit_restaurant_data(restaurant_data);
}

function extract_restaurant_address_components(restaurant) {
  const components_array = restaurant.address_components || restaurant.addressComponents || [];
  console.log('Address components found:', components_array?.length || 0, 'components');
  return extract_address_components(components_array);
}

function build_restaurant_submission_data(restaurant, address_components, google_place_id) {
  return {
    name: restaurant.name || restaurant.displayName?.text || '',
    type: 'restaurant',
    address: address_components.street || restaurant.formatted_address || '',
    city: address_components.city || '',
    state: address_components.state || '',
    postal_code: address_components.postalCode || '',
    country: address_components.country || '',
    phone: restaurant.formatted_phone_number || restaurant.nationalPhoneNumber || '',
    website: restaurant.website || restaurant.websiteURI || '',
    google_place_id,
    // Note: coordinates, rating, price_level would be looked up dynamically from Google Places API
  };
}

/**
 * Show modal for existing restaurant with options
 * @param {Object} existsData - Data about existing restaurant
 * @param {Object} restaurant - Original restaurant data from Google Places
 */
function showExistingRestaurantModal(existsData, restaurant) {
  // Convert legacy existsData to new conflict dialog format for consistency
  const errorData = {
    error: {
      code: 'DUPLICATE_GOOGLE_PLACE_ID',
      existing_restaurant: {
        id: existsData.restaurant_id,
        name: existsData.restaurant_name,
        full_name: existsData.restaurant_name,
        city: existsData.restaurant_city || null
      }
    }
  };

  // Use the enhanced conflict dialog
  showConflictDialog(errorData, restaurant);
}

/**
 * Handle restaurant selection from the search results (legacy function)
 * @param {Object} restaurant - Selected restaurant data
 */
async function handleRestaurantSelect(restaurant) {
  try {
    // Handle different property name formats from different Google Places API responses
    const addressComponentsArray = restaurant.address_components || restaurant.addressComponents || [];
    console.log('handleRestaurantSelect - Restaurant object properties:', Object.keys(restaurant));
    console.log('handleRestaurantSelect - Address components found:', addressComponentsArray?.length || 0, 'components');
    const address_components = extract_address_components(addressComponentsArray);
    const restaurant_data = build_restaurant_data(restaurant, address_components);

    populate_hidden_form(restaurant, address_components);

    const duplicate_check = await check_for_duplicate_restaurant(restaurant_data);
    if (duplicate_check.exists) {
      // Use the new conflict dialog for consistency
      const errorData = {
        error: {
          code: 'DUPLICATE_RESTAURANT',
          existing_restaurant: {
            id: duplicate_check.restaurant_id,
            name: duplicate_check.restaurant_name,
            full_name: duplicate_check.restaurant_name
          }
        }
      };
      showConflictDialog(errorData, restaurant_data);
      return;
    }

    await submit_restaurant_data(restaurant_data);

  } catch (error) {
    console.error('Error handling restaurant selection:', error);
    showErrorToast('Failed to add restaurant. Please try again.');
  }
}

function extract_address_components(address_components_array) {
  const address_components = {
    street: '',
    city: '',
    state: '',
    postalCode: '',
    country: '',
  };

  if (!address_components_array || !Array.isArray(address_components_array)) {
    console.warn('No valid address components array provided. Received:', typeof address_components_array, address_components_array);
    return address_components;
  }

  if (address_components_array.length === 0) {
    console.warn('Address components array is empty. This restaurant may not have detailed location data.');
    return address_components;
  }

  let streetNumber = '';
  let route = '';

  address_components_array.forEach((component) => {
    // Handle both old and new Google Places API formats
    const types = component.types || [];
    const longText = component.long_name || component.longText || '';
    const shortText = component.short_name || component.shortText || '';

    console.log('Processing address component:', longText, 'Types:', types);

    if (types.includes('street_number')) {
      streetNumber = longText;
    } else if (types.includes('route')) {
      route = longText;
    } else if (types.includes('locality') || types.includes('sublocality_level_1')) {
      address_components.city = longText;
    } else if (types.includes('administrative_area_level_1')) {
      address_components.state = shortText || longText;
    } else if (types.includes('postal_code') || types.includes('postal_code_prefix')) {
      address_components.postalCode = longText;
    } else if (types.includes('country')) {
      address_components.country = longText;
    }
  });

  // Build street address from components
  address_components.street = [streetNumber, route].filter(Boolean).join(' ');

  console.log('Extracted address components:', address_components);
  return address_components;
}

function populate_hidden_form(restaurant, address_components) {
  // Handle different Google Places API formats for place ID
  const google_place_id = restaurant.placeId || restaurant.place_id || restaurant.id || '';

  // Handle website field with fallback to different property names
  const website = restaurant.websiteURI || restaurant.website || restaurant.url || '';

  // Handle phone number with fallback to different property names
  const phone = restaurant.nationalPhoneNumber || restaurant.formatted_phone_number || restaurant.phone || '';

  // Handle name with fallback to different property names
  const name = restaurant.displayName?.text || restaurant.name || '';

  const field_mappings = {
    'restaurant-name': name,
    'restaurant-address': address_components.street || restaurant.formatted_address || '',
    'restaurant-city': address_components.city || '',
    'restaurant-state': address_components.state || '',
    'restaurant-postal-code': address_components.postalCode || '',
    'restaurant-country': address_components.country || '',
    'restaurant-phone': phone,
    'restaurant-website': website,
    'restaurant-google-place-id': google_place_id,
    // Note: coordinates would be looked up dynamically from Google Places API
  };

  console.log('Populating hidden form with mappings:', field_mappings);

  Object.entries(field_mappings).forEach(([field_id, value]) => {
    const element = document.getElementById(field_id);
    if (element) {
      element.value = value;
      console.log(`Set ${field_id} = ${value}`);
    } else {
      console.warn(`Form field ${field_id} not found`);
    }
  });
}

// Use centralized cuisine formatting utility
function mapPlaceTypesToForm(types, primaryType) {
  return mapPlaceTypesToRestaurant(types, primaryType);
}

// Conversion functions removed - using Google Places native format directly

function build_restaurant_data(restaurant, address_components) {
  // Handle different Google Places API formats for place ID
  const google_place_id = restaurant.placeId || restaurant.place_id || restaurant.id || '';

  // Handle website field with fallback to different property names
  const website = restaurant.websiteURI || restaurant.website || restaurant.url || '';

  // Handle phone number with fallback to different property names
  const phone = restaurant.nationalPhoneNumber || restaurant.formatted_phone_number || restaurant.phone || '';

  // Handle name with fallback to different property names
  const name = restaurant.displayName?.text || restaurant.name || '';

  // Map Google Places types to restaurant type and cuisine (same logic as autocomplete)
  const typeAndCuisine = mapPlaceTypesToForm(restaurant.types, restaurant.primaryType);

  // Note: We no longer store Google's rating/price_level/coordinates in our database
  // These would be looked up dynamically when needed for display

  return {
    name,
    type: typeAndCuisine.type || 'restaurant',  // Use mapped type or default
    cuisine: typeAndCuisine.cuisine || '',      // Use mapped cuisine
    address: address_components.street || restaurant.formatted_address || '',
    city: address_components.city || '',
    state: address_components.state || '',
    postal_code: address_components.postalCode || '',
    country: address_components.country || '',
    phone,
    website,
    google_place_id,
    // Note: rating would be user's personal rating, not Google's
    // Google's rating, coordinates, price_level would be looked up dynamically
  };
}

// CSRF token function removed - using imported getCSRFToken instead

async function check_for_duplicate_restaurant(restaurant_data) {
  const csrf_token = getCSRFToken();
  const check_url = '/restaurants/check-restaurant-exists';

  console.log('Checking if restaurant exists:', restaurant_data.google_place_id);

  const response = await fetch(check_url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Requested-With': 'XMLHttpRequest',
      'X-CSRFToken': csrf_token,
    },
    body: JSON.stringify({ google_place_id: restaurant_data.google_place_id }),
    credentials: 'same-origin',
  });

  return await response.json();
}

/**
 * Handle search errors
 * @param {string} message - Error message
 */
function handleSearchError(message) {
  console.error('Search error:', message);

  // Show error modal
  const errorMessage = document.getElementById('error-message');
  if (errorMessage) {
    errorMessage.textContent = message || 'An error occurred while searching for restaurants.';
  }

  const errorModalElement = document.getElementById('errorModal');
  const errorModal = new bootstrap.Modal(errorModalElement);
  errorModal.show();
}

// CSRF token handling is imported from utils/csrf-token.js

// Additional helper functions for restaurant selection
function show_duplicate_restaurant_warning(check_result) {
  update_restaurant_card_to_view_mode(check_result);
  show_duplicate_toast_notification(check_result);
}

function update_restaurant_card_to_view_mode(check_result) {
  const restaurant_cards = document.querySelectorAll('.restaurant-card');
  restaurant_cards.forEach((card) => {
    const card_place_id = card.getAttribute('data-place-id');
    if (card_place_id === check_result.google_place_id) {
      const button = card.querySelector('.add-restaurant-btn');
      if (button) {
        button.innerHTML = '<i class="fas fa-eye me-1"></i> View Restaurant';
        button.classList.remove('btn-primary');
        button.classList.add('btn-outline-primary');

        // Replace onclick with data attributes for event delegation
        button.dataset.action = 'view-restaurant';
        button.dataset.restaurantId = check_result.restaurant_id;
        button.removeAttribute('onclick');

        // Add info message
        const info_text = document.createElement('small');
        info_text.className = 'text-muted d-block mt-1';
        info_text.textContent = 'Already in your restaurants';
        button.parentNode.insertBefore(info_text, button.nextSibling);
      }
    }
  });
}

function show_duplicate_toast_notification(check_result) {
  const toast_container = document.getElementById('toastContainer');
  if (!toast_container) return;

  const toast = document.createElement('div');
  toast.className = 'toast align-items-center text-white bg-info border-0';
  toast.setAttribute('role', 'alert');
  toast.setAttribute('aria-live', 'assertive');
  toast.setAttribute('aria-atomic', 'true');
  toast.innerHTML = `
    <div class="d-flex">
      <div class="toast-body">
        <i class="fas fa-info-circle me-2"></i>
        "${check_result.restaurant_name}" is already in your restaurants.
      </div>
      <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
    </div>
  `;

  toast_container.appendChild(toast);
  const bs_toast = new bootstrap.Toast(toast);
  bs_toast.show();

  // Remove the toast after it's hidden
  toast.addEventListener('hidden.bs.toast', () => {
    toast.remove();
  });
}

async function submit_restaurant_data(restaurant_data) {
  const csrf_token = getCSRFToken();

  const response = await fetch('/restaurants/add-from-google-places', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Requested-With': 'XMLHttpRequest',
      'X-CSRFToken': csrf_token,
    },
    body: JSON.stringify(restaurant_data),
    credentials: 'same-origin',
  });

  // Handle non-200 responses with proper error handling
  if (!response.ok) {
    if (response.status === 409) {
      // Handle conflict (duplicate restaurant) with enhanced dialog
      try {
        const errorData = await response.json();
        showConflictDialog(errorData, restaurant_data);
        return; // Don't throw, let dialog handle the interaction
      } catch (parseError) {
        console.error('Failed to parse conflict response:', parseError);
        throw new Error('Restaurant already exists. Please check your existing restaurants.');
      }
    }
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  const result = await response.json();

  if (result.success) {
    // Show success toast with message from server
    showSuccessToast(result.message || 'Restaurant added successfully!');

    // Delay redirect slightly to allow toast to show
    setTimeout(() => {
      if (result.redirect_url) {
        window.location.href = result.redirect_url;
      } else {
        window.location.reload();
      }
    }, 1500); // Show toast for 1.5 seconds before redirect
  } else {
    throw new Error(result.message || 'Failed to add restaurant');
  }
}

/**
 * Show conflict dialog when restaurant already exists
 * @param {Object} errorData - Error response data with conflict details
 * @param {Object} originalData - Original restaurant data being submitted
 */
function showConflictDialog(errorData, originalData) {
  // Safety: Validate inputs
  if (!errorData || !errorData.error) {
    console.error('Invalid error data provided to showConflictDialog');
    showErrorToast('Restaurant conflict detected, but details are unavailable.');
    return;
  }

  const { error } = errorData;
  const existingRestaurant = error.existing_restaurant;

  // Safety: Ensure existing restaurant data is available
  if (!existingRestaurant) {
    console.error('Missing existing restaurant data in conflict response');
    showErrorToast('Restaurant already exists. Please check your restaurant list.');
    return;
  }

  const modalId = 'restaurantConflictModal';
  const isGooglePlaceConflict = error.code === 'DUPLICATE_GOOGLE_PLACE_ID';

  // Build warning message based on conflict type
  const conflictMessage = isGooglePlaceConflict
    ? `The restaurant "${existingRestaurant.name}" from this Google Places location already exists in your list.`
    : `A restaurant named "${existingRestaurant.name}" already exists in your list.`;

  const modalHtml = `
    <div class="modal fade" id="${modalId}" tabindex="-1" aria-labelledby="${modalId}Label" aria-hidden="true">
      <div class="modal-dialog modal-dialog-centered">
        <div class="modal-content">
          <div class="modal-header bg-warning text-dark">
            <h5 class="modal-title" id="${modalId}Label">
              <i class="fas fa-exclamation-triangle me-2"></i>
              Restaurant Already Exists
            </h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
          </div>
          <div class="modal-body">
            <div class="alert alert-warning d-flex align-items-start" role="alert">
              <div class="flex-grow-1">
                <strong>Conflict Detected</strong><br>
                ${conflictMessage}
                ${isGooglePlaceConflict ? '<br><small class="text-muted">This location is already tracked in your restaurants.</small>' : ''}
              </div>
            </div>

            <div class="card border-primary">
              <div class="card-header bg-light">
                <h6 class="card-title mb-0">
                  <i class="fas fa-utensils me-2"></i>
                  Existing Restaurant
                </h6>
              </div>
              <div class="card-body">
                <div class="d-flex justify-content-between align-items-start">
                  <div>
                    <strong>${existingRestaurant.full_name || existingRestaurant.name}</strong>
                    ${existingRestaurant.city ? `<br><small class="text-muted">${existingRestaurant.city}</small>` : ''}
                  </div>
                </div>
              </div>
            </div>

            <div class="mt-3">
              <p class="mb-2"><strong>What would you like to do?</strong></p>
              <ul class="text-muted small mb-0">
                <li>View the existing restaurant details</li>
                <li>Update the existing restaurant with new information</li>
                <li>Cancel and search for a different restaurant</li>
              </ul>
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">
              Cancel
            </button>
            <button type="button" class="btn btn-primary" id="viewExistingBtn" data-restaurant-id="${existingRestaurant.id}">
              <i class="fas fa-eye me-1"></i>View Restaurant
            </button>
            <button type="button" class="btn btn-secondary" id="updateExistingBtn" data-restaurant-id="${existingRestaurant.id}">
              <i class="fas fa-edit me-1"></i>Update Restaurant
            </button>
          </div>
        </div>
      </div>
    </div>
  `;

  // Remove any existing conflict modal
  const existingModal = document.getElementById(modalId);
  if (existingModal) {
    existingModal.remove();
  }

  // Add modal to DOM
  document.body.insertAdjacentHTML('beforeend', modalHtml);

  const modalElement = document.getElementById(modalId);
  const modal = new bootstrap.Modal(modalElement);

  // Set up event handlers for action buttons
  setupConflictModalHandlers(modalElement, existingRestaurant.id, originalData);

  // Show modal with proper focus management
  modal.show();

  // Focus management
  modalElement.addEventListener('shown.bs.modal', () => {
    const viewBtn = modalElement.querySelector('#viewExistingBtn');
    if (viewBtn) {
      viewBtn.focus();
    }
  });

  // Clean up modal after hiding
  modalElement.addEventListener('hidden.bs.modal', () => {
    modalElement.remove();
  });
}

/**
 * Set up event handlers for conflict modal action buttons
 * @param {HTMLElement} modalElement - The modal DOM element
 * @param {number} restaurantId - ID of the existing restaurant
 * @param {Object} googlePlacesData - Google Places data for the restaurant
 */
function setupConflictModalHandlers(modalElement, restaurantId, googlePlacesData = null) {
  // Safety: Validate inputs
  if (!modalElement || !restaurantId) {
    console.error('Invalid parameters for conflict modal handlers');
    return;
  }

  const viewBtn = modalElement.querySelector('#viewExistingBtn');
  const updateBtn = modalElement.querySelector('#updateExistingBtn');

  if (viewBtn) {
    viewBtn.addEventListener('click', () => {
      window.location.href = `/restaurants/${restaurantId}`;
    });
  }

  if (updateBtn) {
    updateBtn.addEventListener('click', () => {
      // Store Google Places data for the edit form and redirect
      storeGooglePlacesDataForEdit(googlePlacesData, restaurantId);
    });
  }
}

/**
 * Store Google Places data in session storage and redirect to edit form
 * @param {Object} googlePlacesData - Google Places data for the restaurant
 * @param {number} restaurantId - ID of the restaurant to edit
 */
function storeGooglePlacesDataForEdit(googlePlacesData, restaurantId) {
  // Safety: Validate inputs
  if (!restaurantId) {
    console.error('Restaurant ID required for edit redirect');
    return;
  }

  try {
    // Store Google Places data in session storage for the edit form to use
    if (googlePlacesData && typeof googlePlacesData === 'object') {
      const dataToStore = {
        timestamp: Date.now(),
        restaurantId: restaurantId,
        googlePlacesData: googlePlacesData
      };

      sessionStorage.setItem('restaurantEditGooglePlacesData', JSON.stringify(dataToStore));
      console.log('Stored Google Places data for restaurant edit:', dataToStore);
    }

    // Redirect to edit form
    window.location.href = `/restaurants/${restaurantId}/edit`;
  } catch (error) {
    console.error('Error storing Google Places data:', error);
    // Fallback: redirect without data
    window.location.href = `/restaurants/${restaurantId}/edit`;
  }
}

// UI feedback functions are imported from utils/notifications.js

// Set up event delegation for view restaurant buttons
document.addEventListener('click', (event) => {
  const button = event.target.closest('[data-action="view-restaurant"]');
  if (button) {
    event.preventDefault();
    event.stopPropagation();
    const restaurant_id = button.dataset.restaurantId;
    if (restaurant_id) {
      window.location.href = `/restaurants/${restaurant_id}`;
    }
  }
});

/**
 * Standard init function for the restaurant places search page
 */
function init() {
  // This module uses DOMContentLoaded listener above for initialization
  // But this function is available for explicit initialization if needed
  console.log('Restaurant places search module initialized');
}

// Export for testing and explicit initialization
export { init };
