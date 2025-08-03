/**
 * Restaurant Search Initialization
 *
 * This module initializes the restaurant search functionality, including
 * Google Places Autocomplete for location-based searches.
 */

// Import GoogleMapsLoader for async loading of Google Maps API
import GoogleMapsLoader from '../utils/google-maps-loader.js';

// Track initialization status
let isInitialized = false;
const initCallbacks = [];

/**
 * Initialize the restaurant search functionality
 */
async function initRestaurantSearch () {
  // Check if already initialized
  if (isInitialized) return;

  try {
    // Get DOM elements
    const searchForm = document.getElementById('restaurantSearchForm');
    const searchInput = document.getElementById('restaurantSearch');
    const locationInput = document.getElementById('locationSearch');

    if (!searchForm || !searchInput) return;

    // Initialize Google Places Autocomplete for restaurant search
    initRestaurantAutocomplete();

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
    searchForm.addEventListener('submit', handleSearchSubmit);

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

/**
 * Initialize Google Places Autocomplete for restaurant name search
 */
function initRestaurantAutocomplete () {
  const searchInput = document.getElementById('restaurantSearchInput');
  const suggestionsContainer = document.getElementById('searchSuggestions');

  if (!searchInput || !suggestionsContainer) return;

  let autocompleteService;
  let placesService;

  // Initialize services when Google Maps is ready
  function initServices () {
    if (!window.google || !window.google.maps || !window.google.maps.places) {
      console.error('Google Maps Places library not loaded');
      return;
    }

    autocompleteService = new google.maps.places.AutocompleteService();
    placesService = new google.maps.places.PlacesService(document.createElement('div'));

    // Add event listeners
    searchInput.addEventListener('input', debounce(handleSearchInput, 300));
    searchInput.addEventListener('focus', handleSearchFocus);
    document.addEventListener('click', handleDocumentClick);
  }

  // Handle search input with debounce
  function handleSearchInput () {
    const query = searchInput.value.trim();
    if (query.length < 2) {
      suggestionsContainer.style.display = 'none';
      return;
    }

    const request = {
      input: query,
      types: ['restaurant', 'food', 'cafe', 'bar'],
      componentRestrictions: { country: 'us' }, // Adjust country code as needed
    };

    autocompleteService.getPlacePredictions(request, (predictions, status) => {
      if (status !== google.maps.places.PlacesServiceStatus.OK || !predictions) {
        suggestionsContainer.style.display = 'none';
        return;
      }

      // Display suggestions
      showSuggestions(predictions);
    });
  }

  // Show suggestions in dropdown
  function showSuggestions (predictions) {
    if (!predictions || predictions.length === 0) {
      suggestionsContainer.style.display = 'none';
      return;
    }

    suggestionsContainer.innerHTML = predictions
      .map((prediction) => `
                <a class="dropdown-item" href="#" data-place-id="${prediction.place_id}">
                    <div class="d-flex align-items-center">
                        <i class="fas fa-utensils me-2 text-muted"></i>
                        <div>
                            <div class="fw-bold">${prediction.structured_formatting.main_text}</div>
                            <small class="text-muted">${prediction.structured_formatting.secondary_text || ''}</small>
                        </div>
                    </div>
                </a>
            `)
      .join('');

    suggestionsContainer.style.display = 'block';

    // Add click handlers for suggestions
    document.querySelectorAll('#searchSuggestions .dropdown-item').forEach((item) => {
      item.addEventListener('click', (e) => {
        e.preventDefault();
        const { placeId } = e.currentTarget.dataset;
        selectPlace(placeId);
      });
    });
  }

  // Handle place selection
  function selectPlace (placeId) {
    const request = {
      placeId,
      fields: ['name', 'formatted_address', 'geometry', 'website', 'formatted_phone_number'],
    };

    placesService.getDetails(request, (place, status) => {
      if (status === google.maps.places.PlacesServiceStatus.OK) {
        // Update the search input with the selected place
        searchInput.value = place.name;
        suggestionsContainer.style.display = 'none';

        // You can also fill in other form fields if needed
        const locationInput = document.getElementById('locationSearch');
        if (locationInput) {
          locationInput.value = place.formatted_address || '';
        }

        // Submit the form or trigger search
        searchInput.form.submit();
      }
    });
  }

  // Handle search input focus
  function handleSearchFocus () {
    if (searchInput.value.trim().length > 1) {
      handleSearchInput();
    }
  }

  // Handle clicks outside the search box
  function handleDocumentClick (e) {
    if (!searchInput.contains(e.target) && !suggestionsContainer.contains(e.target)) {
      suggestionsContainer.style.display = 'none';
    }
  }

  // Debounce function to limit API calls
  function debounce (func, wait) {
    let timeout;
    return function executedFunction (...args) {
      const later = () => {
        clearTimeout(timeout);
        func(...args);
      };
      clearTimeout(timeout);
      timeout = setTimeout(later, wait);
    };
  }

  // Initialize Google Maps if not already loaded
  if (window.google && window.google.maps && window.google.maps.places) {
    initServices();
  } else {
    // Wait for Google Maps to be ready
    window.initGoogleMapsCallback = function () {
      initServices();
    };
  }
}

/**
 * Initialize Google Places Autocomplete for location input
 * @param {HTMLElement} inputElement - The input element to attach autocomplete to
 */
function initPlacesAutocomplete (inputElement) {
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
function performSearch (query, location) {
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

function handleSearchSubmit (e) {
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

// Export the init function
export { initRestaurantSearch };

// Initialize when the DOM is fully loaded
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    initRestaurantSearch().catch((error) => {
      console.error('Error initializing restaurant search:', error);
    });
  });
} else {
  // DOM already loaded, initialize immediately
  initRestaurantSearch().catch((error) => {
    console.error('Error initializing restaurant search:', error);
  });
}
