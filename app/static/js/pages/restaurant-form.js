/**
 * Restaurant Form Page Module
 * Handles form submission and initialization for restaurant addition/editing
 * Includes Google Places integration for address autocomplete
 *
 * @module restaurantForm
 */

import { logger } from '../utils/logger.js';
import GoogleMapsLoader from '../utils/google-maps-loader.js';
import { AddressAutocomplete } from '../components/address-autocomplete.js';

// Module state
const state = {
  isInitialized: false,
  googleMapsInitialized: false,
  googleMapsInitializing: false,
  googleMapsInitQueue: [],
  GOOGLE_MAPS_API_KEY: window.GOOGLE_MAPS_API_KEY || '',
  addressAutocomplete: null
};

// DOM Elements cache
const elements = {};

/**
 * Initialize the module
 * @public
 */
function init() {
  if (state.isInitialized) return;

  try {
    // Cache DOM elements
    cacheElements();

    // Set up event listeners
    setupEventListeners();

    // Get the API key from the window object
    state.GOOGLE_MAPS_API_KEY = window.GOOGLE_MAPS_API_KEY || '';

    if (!state.GOOGLE_MAPS_API_KEY) {
      console.warn('Google Maps API key not found. Google Places autocomplete will not be available.');
      const errorElement = document.getElementById('address-error');
      if (errorElement) {
        errorElement.textContent = 'Google Maps API key not configured. Some features may be limited.';
        errorElement.classList.remove('d-none');
      }
      return;
    }

    // Initialize Google Maps if the address input exists
    if (elements.addressInput) {
      ensureGoogleMapsInitialized()
        .then(initialized => {
          if (initialized) {
            initAddressAutocomplete();
          }
        })
        .catch(error => {
          console.error('Error initializing Google Maps:', error);
          const errorElement = document.getElementById('address-error');
          if (errorElement) {
            errorElement.textContent = 'Failed to initialize Google Maps. Please try refreshing the page.';
            errorElement.classList.remove('d-none');
          }
        });
    }

    state.isInitialized = true;
    logger.debug('Restaurant form initialized');
  } catch (error) {
    logger.error('Error initializing restaurant form:', error);
    throw error;
  }
}

/**
 * Cache DOM elements
 * @private
 */
function cacheElements() {
  // Instead of reassigning elements, update its properties
  const formElements = {
    form: document.getElementById('restaurantForm'),
    restaurantSearch: document.getElementById('restaurant-search'),
    searchRestaurantBtn: document.getElementById('search-restaurant-btn'),
    restaurantSuggestions: document.getElementById('restaurant-suggestions'),
    name: document.getElementById('name'),
    address: document.getElementById('address'),
    city: document.getElementById('city'),
    state: document.getElementById('state'),
    postalCode: document.getElementById('postal_code'),
    country: document.getElementById('country'),
    googlePlaceId: document.getElementById('google_place_id'),
    latitude: document.getElementById('latitude'),
    longitude: document.getElementById('longitude')
  };

  // Update the elements object
  Object.assign(elements, formElements);
}

/**
 * Set up event listeners
 * @private
 */
function setupEventListeners() {
  if (elements.form) {
    elements.form.addEventListener('submit', handleFormSubmit);
  }

  // Setup restaurant search
  if (elements.searchRestaurantBtn) {
    elements.searchRestaurantBtn.addEventListener('click', handleRestaurantSearch);
  }

  // Handle Enter key in restaurant search
  if (elements.restaurantSearch) {
    elements.restaurantSearch.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        handleRestaurantSearch();
      }
    });
  }

  // Clear Google Place ID on manual address edit
  if (elements.address) {
    elements.address.addEventListener('input', () => {
      if (elements.googlePlaceId) {
        elements.googlePlaceId.value = '';
      }
    });
  }
}

/**
 * Handle form submission
 * @param {Event} event - The form submission event
 */
function handleFormSubmit(event) {
  event.preventDefault();

  // Get form data
  const formData = new FormData(elements.form);
  const formAction = elements.form.getAttribute('action');
  const formMethod = elements.form.getAttribute('method') || 'POST';

  // Add loading state
  const submitButton = elements.form.querySelector('button[type="submit"]');
  const originalButtonText = submitButton.innerHTML;
  submitButton.disabled = true;
  submitButton.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>Saving...';

  // Submit form data
  fetch(formAction, {
    method: formMethod,
    body: formData,
    headers: {
      'X-Requested-With': 'XMLHttpRequest',
      'X-CSRFToken': getCSRFToken()
    }
  })
  .then(response => {
    if (!response.ok) {
      return response.json().then(err => {
        throw new Error(err.message || 'Failed to save restaurant');
      });
    }
    return response.json();
  })
  .then(data => {
    // Show success message
    showAlert('success', 'Restaurant saved successfully!');

    // If this was an add operation, redirect to edit page
    if (data.redirect_url) {
      window.location.href = data.redirect_url;
    }
  })
  .catch(error => {
    console.error('Error saving restaurant:', error);
    showAlert('danger', error.message || 'An error occurred while saving the restaurant');
  })
  .finally(() => {
    // Restore button state
    submitButton.disabled = false;
    submitButton.innerHTML = originalButtonText;
  });
}

/**
 * Show alert message
 * @param {string} type - Alert type (e.g., 'success', 'danger')
 * @param {string} message - Message to display
 */
function showAlert(type, message) {
  // Remove any existing alerts
  const existingAlert = document.querySelector('.alert-dismissible');
  if (existingAlert) {
    existingAlert.remove();
  }

  // Create alert element
  const alertDiv = document.createElement('div');
  alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
  alertDiv.role = 'alert';
  alertDiv.innerHTML = `
    ${message}
    <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
  `;

  // Insert alert at the top of the form
  const formHeader = elements.form.querySelector('.card-header');
  if (formHeader) {
    formHeader.insertAdjacentElement('afterend', alertDiv);
  } else {
    elements.form.prepend(alertDiv);
  }
}

/**
 * Get CSRF token from meta tag
 * @returns {string} CSRF token
 */
function getCSRFToken() {
  return document.querySelector('meta[name="csrf-token"]')?.content || '';
}

/**
 * Handle Google Places search
 * @private
 */
async function _handleGooglePlacesSearch() {
  try {
    showLoading(true);
    await ensureGoogleMapsInitialized();

    // This is just a placeholder implementation
    // Actual implementation would use the Google Places API
    const searchRequest = {
      query: 'search term',
      fields: ['name', 'formatted_address', 'geometry', 'place_id'],
    };

    const service = new google.maps.places.PlacesService(document.createElement('div'));
    service.textSearch(searchRequest, (results, status) => {
      if (status === google.maps.places.PlacesServiceStatus.OK) {
        displaySearchResults(results);
      } else {
        console.error('Error searching for places:', status);
      }
      showLoading(false);
    });
  } catch (error) {
    console.error('Error in Google Places search:', error);
    showLoading(false);
  }
}

/**
 * Display search results
 * @param {Array} _places - Array of place objects from Google Places API (unused in this implementation)
 */
function displaySearchResults(_places) {
  // Implementation would go here
  console.log('Displaying search results');
}

/**
 * Initialize the address autocomplete functionality
 * @private
 */
function initAddressAutocomplete() {
  if (!window.google || !window.google.maps || !window.google.maps.places) {
    console.warn('Google Maps Places API not available');
    return;
  }

  // Only initialize if we have the address input
  if (!elements.addressInput) {
    return;
  }

  // Create a new instance of AddressAutocomplete
  state.addressAutocomplete = new AddressAutocomplete({
    inputId: 'address',
    streetNumberId: 'street_number',
    streetNameId: 'route',
    cityId: 'city',
    stateId: 'state',
    postalCodeId: 'postal_code',
    countryId: 'country',
    placeId: 'google_place_id',
    latId: 'latitude',
    lngId: 'longitude'
  });

  // Initialize the autocomplete
  state.addressAutocomplete.init(google.maps.places.Autocomplete);
}

/**
 * Ensure Google Maps API is properly initialized
 * @returns {Promise<boolean>} Resolves with true when Google Maps is ready
 */
async function ensureGoogleMapsInitialized() {
  if (state.googleMapsInitialized) {
    return true;
  }

  if (state.googleMapsInitializing) {
    return new Promise((resolve) => {
      state.googleMapsInitQueue.push(resolve);
    });
  }

  state.googleMapsInitializing = true;

  try {
    if (!state.GOOGLE_MAPS_API_KEY) {
      console.warn('Google Maps API key not found. Google Places autocomplete will not be available.');
      return false;
    }

    // Load Google Maps API with Places library and Map ID
    await GoogleMapsLoader.loadApi(
      state.GOOGLE_MAPS_API_KEY,
      null,
      {
        libraries: ['places'],
        mapId: window.GOOGLE_MAPS_MAP_ID // Get Map ID from global config
      }
    );

    state.googleMapsInitialized = true;

    // Resolve all queued promises
    while (state.googleMapsInitQueue.length) {
      const resolve = state.googleMapsInitQueue.shift();
      resolve(true);
    }

    return true;
  } catch (error) {
    console.error('Failed to load Google Maps API:', error);
    logger.error('Failed to load Google Maps API', { error });

    // Reject all queued promises
    while (state.googleMapsInitQueue.length) {
      const resolve = state.googleMapsInitQueue.shift();
      resolve(false);
    }

    return false;
  } finally {
    state.googleMapsInitializing = false;
  }
}

/**
 * Show loading state
 * @param {boolean} _isLoading - Whether to show or hide loading indicator (unused in this implementation)
 */
function showLoading(_isLoading) {
  // Implementation would go here
  console.log('Loading state:', _isLoading);
}

/**
 * Handle restaurant search
 */
async function handleRestaurantSearch() {
  const query = elements.restaurantSearch.value.trim();
  if (!query) return;

  try {
    showLoading(true);
    await ensureGoogleMapsInitialized();

    if (!window.google || !window.google.maps || !window.google.maps.places) {
      throw new Error('Google Maps API not available');
    }

    const placesService = new google.maps.places.PlacesService(document.createElement('div'));

    const request = {
      query: query,
      fields: ['name', 'formatted_address', 'geometry', 'place_id', 'formatted_phone_number', 'website', 'opening_hours']
    };

    return new Promise((resolve, reject) => {
      placesService.textSearch(request, (results, status) => {
        if (status === google.maps.places.PlacesServiceStatus.OK) {
          displayRestaurantResults(results);
          resolve(results);
        } else {
          const error = new Error('Failed to find restaurants');
          showAlert('danger', 'No restaurants found. Please try a different search term.');
          reject(error);
        }
        showLoading(false);
      });
    });
  } catch (error) {
    console.error('Error searching for restaurants:', error);
    showAlert('danger', 'An error occurred while searching for restaurants.');
    showLoading(false);
  }
}

/**
 * Display restaurant search results
 * @param {Array} restaurants - Array of restaurant objects from Google Places API
 */
function displayRestaurantResults(restaurants) {
  if (!elements.restaurantSuggestions) return;

  if (!restaurants || restaurants.length === 0) {
    elements.restaurantSuggestions.innerHTML = '<div class="alert alert-warning">No restaurants found. Please try a different search term.</div>';
    return;
  }

  const resultsHtml = `
    <div class="list-group">
      ${restaurants.slice(0, 5).map(restaurant => `
        <button type="button"
                class="list-group-item list-group-item-action"
                data-place-id="${restaurant.place_id}"
                onclick="window.restaurantForm.selectRestaurant('${restaurant.place_id}')">
          <div class="d-flex w-100 justify-content-between">
            <h6 class="mb-1">${restaurant.name}</h6>
          </div>
          <p class="mb-1 text-muted">${restaurant.formatted_address || 'Address not available'}</p>
        </button>
      `).join('')}
    </div>
  `;

  elements.restaurantSuggestions.innerHTML = resultsHtml;
}

/**
 * Select a restaurant from search results
 * @param {string} placeId - Google Place ID of the selected restaurant
 */
window.restaurantForm = window.restaurantForm || {};
window.restaurantForm.selectRestaurant = async function(placeId) {
  try {
    showLoading(true);
    await ensureGoogleMapsInitialized();

    const placesService = new google.maps.places.PlacesService(document.createElement('div'));

    const request = {
      placeId: placeId,
      fields: [
        'name',
        'formatted_address',
        'formatted_phone_number',
        'website',
        'geometry',
        'address_components',
        'place_id'
      ]
    };

    return new Promise((resolve, reject) => {
      placesService.getDetails(request, (place, status) => {
        if (status === google.maps.places.PlacesServiceStatus.OK) {
          // Update form fields with place details
          if (elements.name) elements.name.value = place.name || '';
          if (elements.googlePlaceId) elements.googlePlaceId.value = place.place_id || '';

          // Update location fields if available
          if (place.geometry && place.geometry.location) {
            if (elements.latitude) elements.latitude.value = place.geometry.location.lat();
            if (elements.longitude) elements.longitude.value = place.geometry.location.lng();
          }

          // Parse address components
          let streetNumber = '';
          let route = '';

          if (place.address_components) {
            place.address_components.forEach(component => {
              const types = component.types;
              if (types.includes('street_number')) {
                streetNumber = component.long_name;
              } else if (types.includes('route')) {
                route = component.long_name;
              } else if (types.includes('locality') && elements.city) {
                elements.city.value = component.long_name;
              } else if (types.includes('administrative_area_level_1') && elements.state) {
                elements.state.value = component.short_name;
              } else if (types.includes('postal_code') && elements.postalCode) {
                elements.postalCode.value = component.long_name;
              } else if (types.includes('country') && elements.country) {
                elements.country.value = component.long_name;
              }
            });
          }

          // Build the street address from components if available, otherwise use formatted_address
          const streetAddress = [streetNumber, route].filter(Boolean).join(' ').trim();
          if (elements.address) {
            elements.address.value = streetAddress || place.formatted_address || '';
          }

          // Set phone number if available
          if (place.formatted_phone_number && elements.phone) {
            elements.phone.value = place.formatted_phone_number;
          }

          // Set website if available
          if (place.website && elements.website) {
            elements.website.value = place.website;
          }

          showAlert('success', 'Restaurant details have been filled in. Please review and submit the form.');
          resolve(place);
        } else {
          const error = new Error('Failed to get restaurant details');
          showAlert('danger', 'Failed to load restaurant details. Please try again.');
          reject(error);
        }
        showLoading(false);
      });
    });
  } catch (error) {
    console.error('Error getting restaurant details:', error);
    showAlert('danger', 'An error occurred while loading restaurant details.');
    showLoading(false);
  }
};

// Public API
const publicApi = {
  init,
  initRestaurantForm: init, // Alias for backward compatibility
  showLoading,
  selectRestaurant: window.restaurantForm?.selectRestaurant
};

// For backward compatibility
window.restaurantForm = window.restaurantForm || {};
Object.assign(window.restaurantForm, publicApi);

// Auto-initialize when loaded as a module
if (import.meta.url === document.currentScript?.src) {
  document.addEventListener('DOMContentLoaded', () => {
    init();
  });
}

// Export the public API
export const initializeRestaurantForm = init;
export { publicApi };
export default publicApi;
