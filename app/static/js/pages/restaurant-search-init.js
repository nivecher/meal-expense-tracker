/**
 * Restaurant Search Initialization
 *
 * This module initializes the restaurant search functionality, including
 * Google Places Autocomplete for location-based searches.
 */

// Import GoogleMapsLoader for async loading of Google Maps API
import { GoogleMapsLoader } from '../utils/google-maps.js';

// Track initialization status
let isInitialized = false;
const initCallbacks = [];

/**
 * Initialize the restaurant search functionality
 */
async function initRestaurantSearch() {
  // Check if already initialized
  if (isInitialized) return;

  try {
    // Get DOM elements for main search page
    const searchForm = document.getElementById('restaurantSearchForm');
    const searchInput = document.getElementById('restaurantSearch');
    const locationInput = document.getElementById('locationSearch');

    // Also check for restaurant form search field
    const restaurantFormSearchInput = document.getElementById('restaurant-search');

    // Initialize autocomplete for main search page if elements exist
    if (searchForm && searchInput) {
      initRestaurantAutocomplete();
    }

    // Initialize autocomplete for restaurant form search field if it exists
    if (restaurantFormSearchInput) {
      initRestaurantFormAutocomplete();
    }

    // Initialize Google Places Autocomplete if location input exists
    if (locationInput) {
      try {
        // Get API key from config
        const configElement = document.getElementById('app-config');
        if (!configElement) {
          throw new Error('App config element not found');
        }

        const config = JSON.parse(configElement.dataset.appConfig);
        const apiKey = (config.googleMaps && config.googleMaps.apiKey) || window.GOOGLE_MAPS_API_KEY;

        if (!apiKey) {
          throw new Error('Google Maps API key not found in config');
        }

        // Load Google Maps API with retry logic
        await GoogleMapsLoader.loadApiWithRetry(
          apiKey,
          () => {
            if (window.google && window.google.maps && window.google.maps.places) {
              initPlacesAutocomplete(locationInput);
            } else {
              throw new Error('Google Maps API loaded but required components not available');
            }
          },
          ['places', 'geocoding'], // Required libraries
          3, // maxRetries
          1000, // retryDelay
        );
      } catch (error) {
        console.error('Error initializing Google Maps:', error);
        // Show error to user if needed
        const errorElement = document.createElement('div');
        errorElement.className = 'alert alert-warning mt-3';
        errorElement.textContent = 'Failed to load location services. Please refresh the page to try again.';
        searchForm.appendChild(errorElement);
      }
    }

    // Handle form submission
    if (searchForm) {
      searchForm.addEventListener('submit', handleSearchSubmit);
    }

    isInitialized = true;

    // Execute any queued callbacks
    while (initCallbacks.length) {
      const callback = initCallbacks.shift();
      if (typeof callback === 'function') {
        try {
          callback();
        } catch (error) {
          console.error('Error in initialization callback:', error);
        }
      }
    }
  } catch (error) {
    console.error('Error initializing restaurant search:', error);
  }
}

// Utility function for debouncing
function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

function cacheAutocompleteElements() {
  return {
    searchInput: document.getElementById('restaurant-search'),
    suggestionsContainer: document.getElementById('restaurant-suggestions'),
  };
}

function setupGoogleMapsServices() {
  if (!window.google || !window.google.maps || !window.google.maps.places) {
    console.error('Google Maps Places library not loaded');

    // Try to wait for Google Maps to load
    setTimeout(() => {
      if (window.google && window.google.maps && window.google.maps.places) {
        console.log('Google Maps loaded after delay, retrying restaurant form autocomplete...');
        initRestaurantFormAutocomplete();
      }
    }, 1000);

    return null;
  }

  console.log('Google Maps services are available');
  return {
    autocompleteService: new google.maps.places.AutocompleteService(),
    placesService: new google.maps.places.PlacesService(document.createElement('div')),
  };
}

function createAutocompleteRequest(query) {
  return {
    input: query,
    types: ['restaurant', 'food', 'cafe', 'bar'],
    componentRestrictions: { country: 'us' }, // Adjust country code as needed
  };
}

function createSuggestionHtml(prediction) {
  return `
    <a class="dropdown-item" href="#" data-place-id="${prediction.place_id}">
      <div class="d-flex align-items-center">
        <i class="fas fa-utensils me-2 text-muted"></i>
        <div>
          <div class="fw-bold">${prediction.structured_formatting.main_text}</div>
          <small class="text-muted">${prediction.structured_formatting.secondary_text || ''}</small>
        </div>
      </div>
    </a>
  `;
}

function renderSuggestionList(predictions, container) {
  container.innerHTML = predictions
    .map((prediction) => createSuggestionHtml(prediction))
    .join('');
}

function createPlaceDetailsRequest(placeId) {
  return {
    placeId,
    fields: [
      'place_id',
      'name',
      'formatted_address',
      'geometry',
      'website',
      'formatted_phone_number',
      'address_components',
      'business_status',
      'types',
    ],
  };
}

function populateRestaurantFormFields(place) {
  console.log('Populating restaurant form with place data:', place);

  // Basic information
  const nameField = document.getElementById('name');
  if (nameField) {
    nameField.value = place.name || '';
  }

  // Address information
  const addressField = document.getElementById('address');
  if (addressField) {
    addressField.value = place.formatted_address || '';
  }

  // Phone number
  const phoneField = document.getElementById('phone');
  if (phoneField && place.formatted_phone_number) {
    phoneField.value = place.formatted_phone_number;
  }

  // Website
  const websiteField = document.getElementById('website');
  if (websiteField && place.website) {
    websiteField.value = place.website;
  }

  // Google Place ID
  const placeIdField = document.getElementById('google_place_id');
  if (placeIdField && place.place_id) {
    placeIdField.value = place.place_id;
  }

  // Note: coordinates would be looked up dynamically from Google Places API

  console.log('✅ Restaurant form fields populated successfully');
}

function submitSearchForm(elements) {
  const { searchInput } = elements;

  // Check if we're in restaurant form context
  const restaurantForm = document.getElementById('restaurantForm');
  if (restaurantForm) {
    // Don't submit the form, just populated the fields
    console.log('Restaurant selected for form population');
    return;
  }

  // Regular search form submission
  if (searchInput.form) {
    searchInput.form.submit();
  }
}

function populateSearchFormWithPlace(place, elements) {
  const { searchInput, suggestionsContainer } = elements;

  // Update the search input with the selected place
  searchInput.value = place.name;
  suggestionsContainer.style.display = 'none';

  // Check if we're in restaurant form context and populate those fields
  const restaurantForm = document.getElementById('restaurantForm');
  if (restaurantForm) {
    populateRestaurantFormFields(place);
    return;
  }

  // Fill in location field if available (for search page)
  const locationInput = document.getElementById('locationSearch');
  if (locationInput) {
    locationInput.value = place.formatted_address || '';
  }
}

function handlePlaceSelection(placeId, elements, services) {
  const { placesService } = services;
  const request = createPlaceDetailsRequest(placeId);

  placesService.getDetails(request, (place, status) => {
    if (status === google.maps.places.PlacesServiceStatus.OK) {
      populateSearchFormWithPlace(place, elements);
      submitSearchForm(elements);
    }
  });
}

function setupSuggestionClickHandlers(elements, services) {
  document.querySelectorAll('#restaurant-suggestions .dropdown-item').forEach((item) => {
    item.addEventListener('click', (e) => {
      e.preventDefault();
      const { placeId } = e.currentTarget.dataset;
      handlePlaceSelection(placeId, elements, services);
    });
  });
}

function showAutocompleteSuggestions(predictions, elements, services) {
  const { suggestionsContainer } = elements;

  if (!predictions || predictions.length === 0) {
    suggestionsContainer.style.display = 'none';
    return;
  }

  renderSuggestionList(predictions, suggestionsContainer);
  setupSuggestionClickHandlers(elements, services);
  suggestionsContainer.style.display = 'block';
}

function handleSearchInput(elements, services) {
  const { searchInput, suggestionsContainer } = elements;
  const { autocompleteService } = services;

  const query = searchInput.value.trim();
  if (query.length < 2) {
    suggestionsContainer.style.display = 'none';
    return;
  }

  const request = createAutocompleteRequest(query);

  autocompleteService.getPlacePredictions(request, (predictions, status) => {
    if (status !== google.maps.places.PlacesServiceStatus.OK || !predictions) {
      suggestionsContainer.style.display = 'none';
      return;
    }

    showAutocompleteSuggestions(predictions, elements, services);
  });
}

function handleSearchFocus(elements) {
  const { searchInput } = elements;
  if (searchInput.value.trim().length > 1) {
    // Trigger a new search to show existing suggestions
    const services = setupGoogleMapsServices();
    if (services) {
      handleSearchInput(elements, services);
    }
  }
}

function handleDocumentClick(event, elements) {
  const { searchInput, suggestionsContainer } = elements;
  if (!searchInput.contains(event.target) && !suggestionsContainer.contains(event.target)) {
    suggestionsContainer.style.display = 'none';
  }
}

function setupAutocompleteEventListeners(elements, services) {
  const { searchInput } = elements;

  searchInput.addEventListener('input', debounce(() => {
    handleSearchInput(elements, services);
  }, 300));

  searchInput.addEventListener('focus', () => {
    handleSearchFocus(elements);
  });

  document.addEventListener('click', (event) => {
    handleDocumentClick(event, elements);
  });
}

/**
 * Initialize Google Places Autocomplete for restaurant name search
 */
function initRestaurantAutocomplete() {
  const elements = cacheAutocompleteElements();
  if (!elements.searchInput || !elements.suggestionsContainer) return;

  const services = setupGoogleMapsServices();
  if (!services) return;

  setupAutocompleteEventListeners(elements, services);
}

function initRestaurantFormAutocomplete() {
  console.log('Initializing restaurant form autocomplete...');

  const elements = cacheAutocompleteElements();
  if (!elements.searchInput || !elements.suggestionsContainer) {
    console.log('Restaurant form search elements not found');
    return;
  }

  const services = setupGoogleMapsServices();
  if (!services) {
    console.error('Google Maps services not available for restaurant form');
    return;
  }

  console.log('Setting up restaurant form autocomplete event listeners...');
  setupAutocompleteEventListeners(elements, services);
  console.log('✅ Restaurant form autocomplete initialized successfully');
}

function handleSearchSubmit(e) {
  e.preventDefault();
  const query = document.getElementById('restaurantSearch').value.trim();
  const location = document.getElementById('locationSearch') ? document.getElementById('locationSearch').value.trim() : '';

  if (!query && !location) {
    // Show validation error
    return;
  }

  // Trigger search
  performSearch(query, location);
}

/**
 * Initialize Google Places Autocomplete for location input
 * @param {HTMLElement} inputElement - The input element to attach autocomplete to
 */
function initPlacesAutocomplete(inputElement) {
  if (!window.google || !window.google.maps || !window.google.maps.places) {
    console.warn('Google Maps Places API not available');
    return;
  }

  const autocomplete = new google.maps.places.Autocomplete(inputElement, {
    types: ['(cities)'],
    componentRestrictions: { country: 'us' }, // Adjust based on your target market
  });

  // Clear the input when the user selects a place
  autocomplete.addListener('place_changed', () => {
    const place = autocomplete.getPlace();
    if (!place || !place.formatted_address) {
      inputElement.value = '';
    }
  });
}

/**
 * Perform a restaurant search
 * @param {string} query - The search query (restaurant name, cuisine, etc.)
 * @param {string} location - The location to search in
 */
function performSearch(query, location) {
  // This function would typically make an API call to your backend
  // For now, we'll just log the search parameters
  console.log('Searching for:', { query, location });

  // Example of what the API call might look like:
  /*
    fetch('/api/v1/restaurants/search', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('input[name="csrf_token"]')?.value || ''
        },
        body: JSON.stringify({ query, location })
    })
    .then(response => response.json())
    .then(data => {
        // Handle search results
        console.log('Search results:', data);
    })
    .catch(error => {
        console.error('Error performing search:', error);
    });
    */
}

// Make initRestaurantFormAutocomplete available globally for Google Maps callback
window.initRestaurantFormAutocomplete = initRestaurantFormAutocomplete;

// Export the init function
export { initRestaurantSearch, initRestaurantFormAutocomplete };

// Only initialize if we're on a page that needs restaurant search
function shouldInitialize() {
  // Check if we're on the restaurant form page (has restaurant-search field)
  const restaurantSearchField = document.getElementById('restaurant-search');

  // Check if we're on the restaurant search page (has restaurantSearchForm)
  const restaurantSearchForm = document.getElementById('restaurantSearchForm');

  return restaurantSearchField || restaurantSearchForm;
}

// Initialize when the DOM is fully loaded, but only if needed
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    if (shouldInitialize()) {
      initRestaurantSearch().catch((error) => {
        console.error('Error initializing restaurant search:', error);
      });
    }
  });
} else {
  // DOM already loaded, check if we should initialize
  if (shouldInitialize()) {
    initRestaurantSearch().catch((error) => {
      console.error('Error initializing restaurant search:', error);
    });
  }
}
