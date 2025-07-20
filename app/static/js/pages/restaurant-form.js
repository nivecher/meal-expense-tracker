/**
 * Restaurant Form Page Module
 * Handles form submission and initialization for restaurant addition/editing
 * Includes Google Places integration for finding and populating restaurant details
 *
 * @module restaurantForm
 */

/** @typedef {import('@types/google.maps').AutocompleteService} AutocompleteService */
/** @typedef {import('@types/google.maps').PlacesService} PlacesService */

/**
 * Main restaurant form module
 * @namespace restaurantForm
 */
const restaurantForm = (() => {
  // Module state
  const state = {
    isInitialized: false,
    placesService: null,
    autocompleteService: null,
    map: null,
    marker: null,
    googleMapsInitialized: false,
    googleMapsInitializing: false,
    googleMapsInitQueue: [],
    GOOGLE_MAPS_API_KEY: document.currentScript?.dataset?.googleMapsApiKey || ''
  };

  // DOM Selectors
  const SELECTORS = {
    MAP_CONTAINER: 'map',
    SEARCH_INPUT: 'googlePlacesSearchInput',
    SEARCH_BUTTON: 'googlePlacesSearchButton',
    SEARCH_RESULTS: 'googlePlacesSearchResults',
    MODAL: 'googlePlacesModal',
    USE_SELECTED_BTN: 'useSelectedPlace',
    LOADING_INDICATOR: 'googlePlacesLoading',
    ERROR_DISPLAY: 'googlePlacesError'
  };

  // DOM Elements cache
  const elements = {};

  /**
   * Initialize the module
   * @public
   */
  function init() {
    if (state.isInitialized) {
      return;
    }

    try {
      cacheElements();
      setupEventListeners();
      state.isInitialized = true;
      console.log('Restaurant form initialized');
    } catch (error) {
      console.error('Error initializing restaurant form:', error);
      throw error;
    }
  }

  /**
   * Cache DOM elements
   * @private
   */
  function cacheElements() {
    elements.mapContainer = document.getElementById(SELECTORS.MAP_CONTAINER);
    elements.searchInput = document.getElementById(SELECTORS.SEARCH_INPUT);
    elements.searchButton = document.getElementById(SELECTORS.SEARCH_BUTTON);
    elements.searchResults = document.getElementById(SELECTORS.SEARCH_RESULTS);
    elements.modal = document.getElementById(SELECTORS.MODAL);
    elements.useSelectedBtn = document.getElementById(SELECTORS.USE_SELECTED_BTN);
    elements.loadingIndicator = document.getElementById(SELECTORS.LOADING_INDICATOR);
    elements.errorDisplay = document.getElementById(SELECTORS.ERROR_DISPLAY);
  }

  /**
   * Set up event listeners
   * @private
   */
  function setupEventListeners() {
    // Search form submission
    const searchForm = document.querySelector('form[data-role="search-form"]');
    if (searchForm) {
      searchForm.addEventListener('submit', handleSearch);
    }

    // Google Places search button
    if (elements.searchButton) {
      elements.searchButton.addEventListener('click', handleGooglePlacesSearch);
    }

    // Use selected place button
    if (elements.useSelectedBtn) {
      elements.useSelectedBtn.addEventListener('click', handleUseSelectedPlace);
    }
  }

  /**
   * Handle search form submission
   * @param {Event} event - The form submission event
   */
  function handleSearch(event) {
    event.preventDefault();
    // Handle search form submission
    console.log('Search form submitted');
  }

  /**
   * Handle Google Places search
   */
  async function handleGooglePlacesSearch() {
    try {
      if (!elements.searchInput || !elements.searchInput.value.trim()) {
        showErrorInModal('Please enter a search term');
        return;
      }

      showLoading(true);
      await ensureGoogleMapsInitialized();

      const request = {
        query: elements.searchInput.value.trim(),
        fields: ['name', 'formatted_address', 'geometry', 'place_id']
      };

      const service = new google.maps.places.PlacesService(document.createElement('div'));
      service.textSearch(request, (results, status) => {
        if (status === google.maps.places.PlacesServiceStatus.OK) {
          displaySearchResults(results);
        } else {
          showErrorInModal('Error searching for places: ' + status);
        }
        showLoading(false);
      });
    } catch (error) {
      console.error('Error in Google Places search:', error);
      showErrorInModal('Error performing search');
      showLoading(false);
    }
  }

  /**
   * Display search results in the modal
   * @param {Array} places - Array of place objects from Google Places API
   */
  function displaySearchResults(places) {
    if (!elements.searchResults) return;

    elements.searchResults.innerHTML = '';

    if (!places || places.length === 0) {
      elements.searchResults.innerHTML = '<div class="alert alert-info">No results found</div>';
      return;
    }

    const resultsList = document.createElement('div');
    resultsList.className = 'list-group';

    places.forEach((place, index) => {
      const resultItem = document.createElement('button');
      resultItem.type = 'button';
      resultItem.className = 'list-group-item list-group-item-action';
      resultItem.dataset.placeId = place.place_id;
      resultItem.dataset.index = index;

      resultItem.innerHTML = `
        <div class="d-flex w-100 justify-content-between">
          <h5 class="mb-1">${place.name}</h5>
        </div>
        <p class="mb-1">${place.formatted_address || 'Address not available'}</p>
      `;

      resultItem.addEventListener('click', () => {
        // Highlight selected item
        document.querySelectorAll('.list-group-item').forEach(item => {
          item.classList.remove('active');
        });
        resultItem.classList.add('active');
        state.selectedPlace = place;
      });

      resultsList.appendChild(resultItem);
    });

    elements.searchResults.appendChild(resultsList);
  }

  /**
   * Handle using the selected place
   */
  function handleUseSelectedPlace() {
    if (!state.selectedPlace) {
      showErrorInModal('Please select a place from the list');
      return;
    }

    // Update form fields with selected place data
    updateFormWithPlaceData(state.selectedPlace);

    // Close the modal
    const modal = bootstrap.Modal.getInstance(elements.modal);
    if (modal) {
      modal.hide();
    }
  }

  /**
   * Update form with place data
   * @param {Object} place - Google Place object
   */
  function updateFormWithPlaceData(place) {
    // Update name field
    const nameInput = document.querySelector('input[name="name"]');
    if (nameInput) {
      nameInput.value = place.name || '';
    }

    // Update address fields
    const addressInput = document.querySelector('input[name="address"]');
    if (addressInput) {
      addressInput.value = place.formatted_address || '';
    }

    // You can add more field updates here based on your form structure
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

    return new Promise((resolve, reject) => {
      if (typeof google === 'undefined' || !google.maps || !google.maps.places) {
        const error = new Error('Google Maps API not loaded');
        console.error(error);
        reject(error);
        return;
      }

      try {
        state.autocompleteService = new google.maps.places.AutocompleteService();
        state.placesService = new google.maps.places.PlacesService(document.createElement('div'));
        state.googleMapsInitialized = true;

        // Process any queued callbacks
        state.googleMapsInitQueue.forEach(callback => callback(true));
        state.googleMapsInitQueue = [];

        resolve(true);
      } catch (error) {
        console.error('Error initializing Google Maps services:', error);
        state.googleMapsInitializing = false;

        // Process any queued callbacks with error
        state.googleMapsInitQueue.forEach(callback => callback(false, error));
        state.googleMapsInitQueue = [];

        reject(error);
      }
    });
  }

  /**
   * Show loading state
   * @param {boolean} isLoading - Whether to show or hide loading indicator
   */
  function showLoading(isLoading) {
    if (!elements.loadingIndicator) return;

    if (isLoading) {
      elements.loadingIndicator.classList.remove('d-none');
    } else {
      elements.loadingIndicator.classList.add('d-none');
    }
  }

  /**
   * Show error message in the modal
   * @param {string} message - The error message to display
   */
  function showErrorInModal(message) {
    if (!elements.errorDisplay) {
      console.error('Error display element not found');
      return;
    }

    const errorMessage = elements.errorDisplay.querySelector('.error-message');
    if (errorMessage) {
      errorMessage.textContent = message;
      elements.errorDisplay.classList.remove('d-none');

      // Auto-hide error after 5 seconds
      setTimeout(() => {
        elements.errorDisplay.classList.add('d-none');
      }, 5000);
    }
  }

  // Public API
  const publicApi = {
    init,
    initRestaurantForm: init, // Alias for backward compatibility
    handleSearch,
    handleGooglePlacesSearch,
    handleUseSelectedPlace,
    ensureGoogleMapsInitialized,

    // Expose the map for debugging purposes
    get map() {
      return state.map;
    },

    // Expose the places service for debugging purposes
    get placesService() {
      return state.placesService;
    },

    // Expose the autocomplete service for debugging purposes
    get autocompleteService() {
      return state.autocompleteService;
    }
  };

  // Initialize when DOM is loaded
  document.addEventListener('DOMContentLoaded', () => {
    try {
      // Initialize the restaurant form
      publicApi.init();

      // Initialize Google Places search button if it exists
      const findButton = document.getElementById('findWithGooglePlaces');
      if (findButton) {
        findButton.addEventListener('click', (e) => {
          e.preventDefault();
          const modalElement = document.getElementById('googlePlacesModal');
          if (modalElement && window.bootstrap) {
            const modal = new bootstrap.Modal(modalElement, {
              backdrop: 'static',
              keyboard: false
            });
            modal.show();
          }
        });
      }

      // Initialize address autocomplete if available
      if (window.restaurantAddressAutocomplete) {
        window.restaurantAddressAutocomplete.init();
      }
    } catch (error) {
      console.error('Error initializing restaurant form:', error);
    }
  });

  // Make the public API available globally
  window.restaurantForm = publicApi;

  return publicApi;
})();
