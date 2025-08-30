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
import { show_success_message, show_error_message } from '../utils/ui-feedback.js';

// Initialize the page when the DOM is fully loaded
document.addEventListener('DOMContentLoaded', async () => {
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
  const searchContainer = document.getElementById('google-places-search');
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

  // Ultra-aggressive fix: Use MutationObserver to watch for aria-hidden changes
  const setupAriaHiddenWatcher = (modal, modalName) => {
    if (!modal) return;

    const observer = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        if (mutation.type === 'attributes' && mutation.attributeName === 'aria-hidden') {
          const isHidden = modal.getAttribute('aria-hidden') === 'true';
          const hasFocusedChild = modal.contains(document.activeElement);

          console.log(`${modalName}: aria-hidden changed to ${isHidden}, has focused child: ${hasFocusedChild}`);

          if (isHidden && hasFocusedChild) {
            // Remove focus immediately when aria-hidden is being set to true
            document.activeElement.blur();
            console.log(`${modalName}: Emergency focus removal due to aria-hidden conflict`);
          } else if (!isHidden && modal.style.display !== 'none') {
            // Set focus when aria-hidden is removed and modal is visible
            setTimeout(() => {
              const targetBtn = modal.querySelector('#continue-searching-btn, #error-close-btn');
              if (targetBtn && document.activeElement !== targetBtn) {
                // Remove tabindex to make it focusable, then focus
                targetBtn.removeAttribute('tabindex');
                targetBtn.focus();
                console.log(`${modalName}: Focus set after aria-hidden removed (via MutationObserver)`);
              }
            }, 50);
          }
        }
      });
    });

    observer.observe(modal, {
      attributes: true,
      attributeFilter: ['aria-hidden']
    });

    console.log(`${modalName}: MutationObserver setup for aria-hidden monitoring`);
    return observer;
  };

  // Set up watcher for error modal (success modal removed)
  setupAriaHiddenWatcher(errorModal, 'Error Modal');
});

/**
 * Handle "Add Restaurant" button click from search results
 * @param {Object} restaurant - Selected restaurant data from Google Places
 */
async function handleAddRestaurantClick(restaurant) {
  try {
    const google_place_id = extract_place_id(restaurant);
    const duplicate_check = await check_for_existing_restaurant(google_place_id);

    if (duplicate_check.exists) {
      showExistingRestaurantModal(duplicate_check, restaurant);
      return;
    }

    await process_new_restaurant_addition(restaurant, google_place_id);
  } catch (error) {
    console.error('Error handling add restaurant click:', error);
    handleSearchError(`Error adding restaurant: ${error.message}`);
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
    google_place_id: google_place_id,
    // Note: coordinates, rating, price_level would be looked up dynamically from Google Places API
  };
}

/**
 * Show modal for existing restaurant with options
 * @param {Object} existsData - Data about existing restaurant
 * @param {Object} restaurant - Original restaurant data from Google Places
 */
function showExistingRestaurantModal(existsData, restaurant) {
  const modalHtml = `
    <div class="modal fade" id="existingRestaurantModal" tabindex="-1">
      <div class="modal-dialog">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">
              <i class="fas fa-exclamation-triangle text-warning me-2"></i>
              Restaurant Already Exists
            </h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
          </div>
          <div class="modal-body">
            <p>The restaurant "<strong>${existsData.restaurant_name}</strong>" already exists in your collection.</p>
            <p>What would you like to do?</p>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
            <a href="/restaurants/${existsData.restaurant_id}" class="btn btn-primary">
              <i class="fas fa-eye me-1"></i>View Restaurant
            </a>
            <a href="/restaurants/${existsData.restaurant_id}/edit" class="btn btn-outline-primary">
              <i class="fas fa-edit me-1"></i>Update Restaurant
            </a>
          </div>
        </div>
      </div>
    </div>
  `;

  // Remove any existing modal
  const existingModal = document.getElementById('existingRestaurantModal');
  if (existingModal) {
    existingModal.remove();
  }

  // Add modal to body
  document.body.insertAdjacentHTML('beforeend', modalHtml);

  // Show modal
  const modalElement = document.getElementById('existingRestaurantModal');
  const modal = new bootstrap.Modal(modalElement);

  // Add proper focus management
  modalElement.addEventListener('shown.bs.modal', () => {
    const viewBtn = modalElement.querySelector('.btn-primary');
    if (viewBtn) {
      viewBtn.focus();
    }
  });

  modal.show();

  // Clean up modal after hiding
  modalElement.addEventListener('hidden.bs.modal', () => {
    modalElement.remove();
  });
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
      show_duplicate_restaurant_warning(duplicate_check);
      return;
    }

    await submit_restaurant_data(restaurant_data);

  } catch (error) {
    console.error('Error handling restaurant selection:', error);
    show_error_message('Failed to add restaurant. Please try again.');
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

function mapPlaceTypesToForm(types, primaryType) {
  const result = { type: '', cuisine: '' };

  if (!types || !Array.isArray(types)) {
    console.log('No types array provided for place type mapping');
    return result;
  }

  console.log('Mapping place types:', types, 'Primary type:', primaryType);

  // Map type based on Google Places types
  if (types.includes('bar') || types.includes('night_club')) {
    result.type = 'bar';
  } else if (types.includes('cafe') || types.includes('coffee_shop')) {
    result.type = 'cafe';
  } else if (types.includes('bakery')) {
    result.type = 'bakery';
  } else if (types.includes('meal_takeaway') || types.includes('meal_delivery')) {
    result.type = 'fast_food';
  } else if (types.includes('restaurant') || types.includes('food') || types.includes('establishment')) {
    result.type = 'restaurant';
  }

  // Map cuisine based on more specific types
  if (types.includes('chinese_restaurant')) {
    result.cuisine = 'chinese';
  } else if (types.includes('italian_restaurant')) {
    result.cuisine = 'italian';
  } else if (types.includes('japanese_restaurant')) {
    result.cuisine = 'japanese';
  } else if (types.includes('mexican_restaurant')) {
    result.cuisine = 'mexican';
  } else if (types.includes('indian_restaurant')) {
    result.cuisine = 'indian';
  } else if (types.includes('thai_restaurant')) {
    result.cuisine = 'thai';
  } else if (types.includes('french_restaurant')) {
    result.cuisine = 'french';
  } else if (types.includes('american_restaurant')) {
    result.cuisine = 'american';
  } else if (types.includes('pizza_restaurant')) {
    result.cuisine = 'pizza';
  } else if (types.includes('seafood_restaurant')) {
    result.cuisine = 'seafood';
  } else if (types.includes('steak_house')) {
    result.cuisine = 'steakhouse';
  } else if (types.includes('sushi_restaurant')) {
    result.cuisine = 'sushi';
  }

  // Use primaryType as fallback if available
  if (!result.type && primaryType) {
    if (primaryType.includes('restaurant')) {
      result.type = 'restaurant';
    } else if (primaryType.includes('cafe')) {
      result.type = 'cafe';
    } else if (primaryType.includes('bar')) {
      result.type = 'bar';
    }
  }

  console.log('Mapped to type:', result.type, 'cuisine:', result.cuisine);
  return result;
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
    name: name,
    type: typeAndCuisine.type || 'restaurant',  // Use mapped type or default
    cuisine: typeAndCuisine.cuisine || '',      // Use mapped cuisine
    address: address_components.street || restaurant.formatted_address || '',
    city: address_components.city || '',
    state: address_components.state || '',
    postal_code: address_components.postalCode || '',
    country: address_components.country || '',
    phone: phone,
    website: website,
    google_place_id: google_place_id,
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
function handleSearchError (message) {
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
  restaurant_cards.forEach(card => {
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

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  const result = await response.json();

  if (result.success) {
    // Show success toast with message from server
    show_success_message(result.message || 'Restaurant added successfully!');

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

// UI feedback functions are imported from utils/ui-feedback.js

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
