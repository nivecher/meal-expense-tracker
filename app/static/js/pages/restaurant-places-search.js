/**
 * Restaurant Places Search
 *
 * Initializes the Google Places search component for finding restaurants
 */

// Import required modules
import RestaurantSearch from '../components/restaurant-search.js';
import { googlePlacesService } from '../services/google-places.js';
import GoogleMapsLoader from '../utils/google-maps-loader.js';

// Initialize the page when the DOM is fully loaded
document.addEventListener('DOMContentLoaded', async () => {
  // Get modal elements
  const successModal = document.getElementById('successModal');
  const errorModal = document.getElementById('errorModal');

  // Store the element that had focus before the modal opened
  let focusedElementBeforeModal = null;

  // Set up event listeners for modals
  if (successModal) {
    const modalInstance = new bootstrap.Modal(successModal);

    // When modal is about to be shown
    successModal.addEventListener('show.bs.modal', () => {
      // Store the current focused element
      focusedElementBeforeModal = document.activeElement;

      // Update ARIA attributes when modal is shown
      successModal.setAttribute('aria-hidden', 'false');
      successModal.setAttribute('aria-modal', 'true');

      // Remove the inert attribute to make modal content accessible
      successModal.removeAttribute('inert');
    });

    // When modal is fully hidden
    successModal.addEventListener('hidden.bs.modal', () => {
      // Reset ARIA attributes when modal is hidden
      successModal.setAttribute('aria-hidden', 'true');
      successModal.setAttribute('aria-modal', 'false');

      // Add inert attribute to prevent interaction when hidden
      successModal.setAttribute('inert', 'true');

      // Return focus to the element that had focus before the modal opened
      if (focusedElementBeforeModal && focusedElementBeforeModal.focus) {
        focusedElementBeforeModal.focus();
      }
    });
  }

  if (errorModal) {
    const modalInstance = new bootstrap.Modal(errorModal);

    // When modal is about to be shown
    errorModal.addEventListener('show.bs.modal', () => {
      // Store the current focused element
      focusedElementBeforeModal = document.activeElement;

      // Update ARIA attributes when modal is shown
      errorModal.setAttribute('aria-hidden', 'false');
      errorModal.setAttribute('aria-modal', 'true');

      // Remove the inert attribute to make modal content accessible
      errorModal.removeAttribute('inert');
    });

    // When modal is fully hidden
    errorModal.addEventListener('hidden.bs.modal', () => {
      // Reset ARIA attributes when modal is hidden
      errorModal.setAttribute('aria-hidden', 'true');
      errorModal.setAttribute('aria-modal', 'false');

      // Add inert attribute to prevent interaction when hidden
      errorModal.setAttribute('inert', 'true');

      // Return focus to the element that had focus before the modal opened
      if (focusedElementBeforeModal && focusedElementBeforeModal.focus) {
        focusedElementBeforeModal.focus();
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

          // Update the googlePlacesService with the API key
          googlePlacesService.apiKey = apiKey;

          const restaurantSearch = new RestaurantSearch({
            container: searchContainer,
            onSelect: handleRestaurantSelect,
            onError: handleSearchError,
          });

          // Make the search component available globally for debugging
          window.restaurantSearch = restaurantSearch;

          console.log('Restaurant search component initialized successfully');

          // Hide loading indicator if it was shown
          if (loadingIndicator) {
            loadingIndicator.classList.add('d-none');
          }
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
});

/**
 * Handle restaurant selection from the search results
 * @param {Object} restaurant - Selected restaurant data
 */
async function handleRestaurantSelect (restaurant) {
  try {
    // Extract address components
    const addressComponents = {
      street: '',
      city: '',
      state: '',
      postalCode: '',
      country: '',
    };

    if (restaurant.addressComponents) {
      restaurant.addressComponents.forEach((component) => {
        const { types } = component;
        if (types.includes('street_number') || types.includes('route')) {
          addressComponents.street = (`${addressComponents.street} ${component.long_name}`).trim();
        } else if (types.includes('locality')) {
          addressComponents.city = component.long_name;
        } else if (types.includes('administrative_area_level_1')) {
          addressComponents.state = component.short_name;
        } else if (types.includes('postal_code')) {
          addressComponents.postalCode = component.long_name;
        } else if (types.includes('country')) {
          addressComponents.country = component.long_name;
        }
      });
    }

    // Populate the hidden form
    document.getElementById('restaurant-name').value = restaurant.name || '';
    document.getElementById('restaurant-address').value = addressComponents.street || '';
    document.getElementById('restaurant-city').value = addressComponents.city || '';
    document.getElementById('restaurant-state').value = addressComponents.state || '';
    document.getElementById('restaurant-postal-code').value = addressComponents.postalCode || '';
    document.getElementById('restaurant-country').value = addressComponents.country || '';
    document.getElementById('restaurant-phone').value = restaurant.phone || '';
    document.getElementById('restaurant-website').value = restaurant.website || '';
    document.getElementById('restaurant-google-place-id').value = restaurant.id || '';
    document.getElementById('restaurant-latitude').value = restaurant.location?.lat || '';
    document.getElementById('restaurant-longitude').value = restaurant.location?.lng || '';

    // Prepare the restaurant data as JSON
    const restaurantData = {
      name: restaurant.name || '',
      type: 'restaurant',  // Default type since it's required
      address: addressComponents.street || '',
      city: addressComponents.city || '',
      state: addressComponents.state || '',
      postal_code: addressComponents.postalCode || '',
      country: addressComponents.country || '',
      phone: restaurant.phone || '',
      website: restaurant.website || '',
      google_place_id: restaurant.id || '',
      latitude: restaurant.location?.lat || '',
      longitude: restaurant.location?.lng || '',
    };

    // Get CSRF token from the meta tag
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content ||
                         document.querySelector('input[name="_csrf_token"]')?.value ||
                         document.querySelector('input[name="csrf_token"]')?.value;

    if (!csrfToken) {
      console.error('CSRF token not found');
      throw new Error('CSRF token is required');
    }

    // First check if the restaurant already exists
    const checkUrl = '/restaurants/check-restaurant-exists';
    console.log('Checking if restaurant exists:', restaurantData.google_place_id);

    const checkResponse = await fetch(checkUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Requested-With': 'XMLHttpRequest',
        'X-CSRFToken': csrfToken,
      },
      body: JSON.stringify({ google_place_id: restaurantData.google_place_id }),
      credentials: 'same-origin',
    });

    const checkResult = await checkResponse.json();

    if (checkResult.exists) {
      // Find the clicked restaurant card in the search results
      const restaurantCards = document.querySelectorAll('.restaurant-card');
      restaurantCards.forEach(card => {
        const cardPlaceId = card.getAttribute('data-place-id');
        if (cardPlaceId === restaurantData.google_place_id) {
          // Update the button to show "View" instead of "Add"
          const button = card.querySelector('.add-restaurant-btn');
          if (button) {
            button.innerHTML = '<i class="fas fa-eye me-1"></i> View Restaurant';
            button.classList.remove('btn-primary');
            button.classList.add('btn-outline-primary');
            button.onclick = (e) => {
              e.preventDefault();
              e.stopPropagation();
              window.location.href = `/restaurants/${checkResult.restaurant_id}`;
            };

            // Add a small info message
            const infoText = document.createElement('small');
            infoText.className = 'text-muted d-block mt-1';
            infoText.textContent = 'Already in your restaurants';
            button.parentNode.insertBefore(infoText, button.nextSibling);
          }
        }
      });

      // Show a toast notification
      const toastContainer = document.getElementById('toastContainer');
      if (toastContainer) {
        const toast = document.createElement('div');
        toast.className = 'toast align-items-center text-white bg-info border-0';
        toast.setAttribute('role', 'alert');
        toast.setAttribute('aria-live', 'assertive');
        toast.setAttribute('aria-atomic', 'true');
        toast.innerHTML = `
          <div class="d-flex">
            <div class="toast-body">
              <i class="fas fa-info-circle me-2"></i>
              "${checkResult.restaurant_name}" is already in your restaurants.
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
          </div>
        `;
        toastContainer.appendChild(toast);
        const bsToast = new bootstrap.Toast(toast);
        bsToast.show();

        // Remove the toast after it's hidden
        toast.addEventListener('hidden.bs.toast', () => {
          toast.remove();
        });
      }

      return;
    }

    // If we get here, the restaurant doesn't exist, so proceed with adding it
    const url = '/restaurants/add-from-google-places';
    console.log('Adding new restaurant:', restaurantData.name);

    // Send the request as JSON
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Requested-With': 'XMLHttpRequest',
        'X-CSRFToken': csrfToken,
      },
      body: JSON.stringify(restaurantData),
      credentials: 'same-origin',  // Include cookies for session/auth
    });

    // Check if the response is JSON before parsing
    const contentType = response.headers.get('content-type') || '';
    if (!contentType.includes('application/json')) {
      const text = await response.text();
      console.error('Expected JSON response, got:', {
        status: response.status,
        statusText: response.statusText,
        contentType,
        headers: Object.fromEntries(response.headers.entries()),
        body: text,
      });
      throw new Error(`Server returned ${response.status} ${response.statusText}. Expected JSON but got ${contentType}`);
    }

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.message || `HTTP error! status: ${response.status}`);
    }

    const result = await response.json();

    if (result.success) {
      // Show success modal
      const successMessage = document.getElementById('success-message');
      if (successMessage) {
        successMessage.textContent = `"${restaurant.name}" has been added to your restaurants.`;
      }

      const successModal = new bootstrap.Modal(document.getElementById('successModal'));
      successModal.show();

      // Update the URL to the new restaurant if needed
      if (result.redirect_url) {
        // Update the success modal's view button
        const viewButton = document.querySelector('#successModal .btn-outline-secondary');
        if (viewButton) {
          viewButton.href = result.redirect_url;
        }
      }
    } else {
      throw new Error(result.message || 'Failed to add restaurant');
    }
  } catch (error) {
    console.error('Error adding restaurant:', error);

    // Show error modal
    const errorMessage = document.getElementById('error-message');
    if (errorMessage) {
      errorMessage.textContent = error.message || 'An error occurred while adding the restaurant.';
    }

    const errorModal = new bootstrap.Modal(document.getElementById('errorModal'));
    errorModal.show();
  }
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

  const errorModal = new bootstrap.Modal(document.getElementById('errorModal'));
  errorModal.show();
}

// Add a utility function to handle CSRF tokens for AJAX requests
function getCSRFToken () {
  const meta = document.querySelector('meta[name="csrf-token"]');
  return meta ? meta.getAttribute('content') : '';
}

// Make the CSRF token available to all fetch requests
const csrfToken = getCSRFToken();
if (csrfToken) {
  // Add CSRF token to all fetch requests
  const originalFetch = window.fetch;
  window.fetch = function (resource, options = {}) {
    // Set up the headers
    options.headers = {
      ...options.headers,
      'X-CSRFToken': csrfToken,
      'X-Requested-With': 'XMLHttpRequest',
    };

    // Call the original fetch function
    return originalFetch(resource, options);
  };
}
