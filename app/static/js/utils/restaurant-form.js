/**
 * Restaurant Form Utilities
 * Consolidated form management, Google Places integration, geolocation, and address processing
 *
 * @module restaurantForm
 * @version 2.0.0
 * @author Meal Expense Tracker Team
 */

import { logger, debounce } from './core-utils.js';
import { showFormLoading, hideFormLoading, showErrorToast, showSuccessToast } from './ui-utils.js';
import { post } from './api-utils.js';
import { googleMapsManager } from './google-maps.js';

// ===== CONSTANTS =====

const DEFAULT_LOCATION = {
  lat: 40.7128,
  lng: -74.0060,
};

const ADDRESS_COMPONENT_TYPES = {
  STREET_NUMBER: 'street_number',
  ROUTE: 'route',
  LOCALITY: 'locality',
  ADMIN_AREA_LEVEL_1: 'administrative_area_level_1',
  POSTAL_CODE: 'postal_code',
  COUNTRY: 'country',
};

const GEOLOCATION_OPTIONS = {
  enableHighAccuracy: true,
  timeout: 10000,
  maximumAge: 300000,
};

// ===== FORM MANAGER =====

class RestaurantFormManager {
  constructor() {
    this.elements = {};
    this.state = {
      isInitialized: false,
      isSubmitting: false,
      autocomplete: null,
      userLocation: { ...DEFAULT_LOCATION },
    };
  }

  // Cache DOM elements
  cacheElements() {
    this.elements = {
      searchInput: document.getElementById('restaurant-search'),
      restaurantForm: document.getElementById('restaurant-form'),
      loadingIndicator: document.getElementById('loading-indicator'),
      addressInput: document.getElementById('address'),
      nameInput: document.getElementById('name'),
      cityInput: document.getElementById('city'),
      stateInput: document.getElementById('state'),
      zipInput: document.getElementById('zip'),
      latInput: document.getElementById('lat'),
      lngInput: document.getElementById('lng'),
    };

    logger.debug('DOM elements cached:', Object.keys(this.elements));
  }

  // Get cached element
  getElement(key) {
    return this.elements[key] || null;
  }

  // Set up event listeners
  setupEventListeners() {
    const { restaurantForm, searchInput } = this.elements;

    if (restaurantForm) {
      restaurantForm.addEventListener('submit', this.handleFormSubmit.bind(this));
      logger.debug('Form submit event listener attached');
    }

    if (searchInput) {
      const debouncedSearch = debounce(this.handleSearchInput.bind(this), 300);
      searchInput.addEventListener('input', debouncedSearch);
      logger.debug('Search input event listener attached');
    }
  }

  // Handle form submission
  async handleFormSubmit(event) {
    event.preventDefault();

    if (this.state.isSubmitting) {
      logger.warn('Form submission already in progress');
      return;
    }

    this.state.isSubmitting = true;
    const form = event.target;

    try {
      showFormLoading(form, 'Saving restaurant...');

      const formData = new FormData(form);
      const data = Object.fromEntries(formData.entries());

      // Validate required fields
      if (!data.name || !data.address) {
        throw new Error('Restaurant name and address are required');
      }

      const response = await post(form.action, data);

      if (response.success) {
        showSuccessToast('Restaurant saved successfully!');

        // Redirect if URL provided
        if (response.redirect_url) {
          window.location.href = response.redirect_url;
        } else {
          form.reset();
        }
      } else {
        throw new Error(response.message || 'Failed to save restaurant');
      }
    } catch (error) {
      logger.error('Form submission error:', error);
      showErrorToast(error.message || 'Failed to save restaurant');
    } finally {
      hideFormLoading(form);
      this.state.isSubmitting = false;
    }
  }

  // Handle search input
  handleSearchInput(event) {
    const query = event.target.value.trim();
    logger.debug('Search input:', query);

    if (query.length >= 3) {
      this.searchRestaurants(query);
    }
  }

  // Search restaurants
  async searchRestaurants(query) {
    try {
      await this.ensureGoogleMapsReady();

      const results = await googleMapsManager.searchRestaurants(query, this.state.userLocation);
      this.displaySearchResults(results);
    } catch (error) {
      logger.error('Restaurant search failed:', error);
      showErrorToast('Search failed. Please try again.');
    }
  }

  // Display search results
  displaySearchResults(results) {
    // Implementation for displaying search results
    logger.debug('Search results:', results);
  }

  // Show loading state
  showLoading(message = 'Loading...') {
    const { loadingIndicator } = this.elements;
    if (loadingIndicator) {
      loadingIndicator.textContent = message;
      loadingIndicator.style.display = 'block';
    }
  }

  // Hide loading state
  hideLoading() {
    const { loadingIndicator } = this.elements;
    if (loadingIndicator) {
      loadingIndicator.style.display = 'none';
    }
  }

  // Show error
  showError(message) {
    showErrorToast(message);
  }

  // Ensure Google Maps is ready
  async ensureGoogleMapsReady() {
    if (!googleMapsManager.isReady()) {
      await googleMapsManager.initializeForRestaurants();
    }
  }
}

// ===== GEOLOCATION MANAGER =====

class GeolocationManager {
  constructor() {
    this.userLocation = { ...DEFAULT_LOCATION };
    this.isLocationCached = false;
  }

  async getCurrentLocation() {
    if (this.isLocationCached) {
      return this.userLocation;
    }

    try {
      if (!navigator.geolocation) {
        logger.warn('Geolocation not supported, using default location');
        return this.userLocation;
      }

      const position = await this.getPosition();
      this.userLocation = {
        lat: position.coords.latitude,
        lng: position.coords.longitude,
      };
      this.isLocationCached = true;

      logger.info('User location obtained:', this.userLocation);
      return this.userLocation;
    } catch (error) {
      logger.warn('Geolocation failed, using default location:', error);
      return this.userLocation;
    }
  }

  getPosition() {
    return new Promise((resolve, reject) => {
      navigator.geolocation.getCurrentPosition(resolve, reject, GEOLOCATION_OPTIONS);
    });
  }

  getDefaultLocation() {
    return { ...DEFAULT_LOCATION };
  }

  clearLocationCache() {
    this.isLocationCached = false;
    this.userLocation = { ...DEFAULT_LOCATION };
  }
}

// ===== ADDRESS PROCESSOR =====

class AddressProcessor {
  extractComponent(addressComponents, type) {
    if (!Array.isArray(addressComponents)) {
      logger.warn('Invalid address components provided');
      return '';
    }

    const component = addressComponents.find((comp) =>
      comp.types && comp.types.includes(type),
    );

    if (component) {
      return component.long_name || component.short_name || '';
    }

    logger.debug(`Address component '${type}' not found`);
    return '';
  }

  getAddressFromPlace(place) {
    if (!place || !place.address_components) {
      logger.warn('Invalid place object or missing address components');
      return null;
    }

    const { address_components: components } = place;

    return {
      streetNumber: this.extractComponent(components, ADDRESS_COMPONENT_TYPES.STREET_NUMBER),
      route: this.extractComponent(components, ADDRESS_COMPONENT_TYPES.ROUTE),
      city: this.extractComponent(components, ADDRESS_COMPONENT_TYPES.LOCALITY),
      state: this.extractComponent(components, ADDRESS_COMPONENT_TYPES.ADMIN_AREA_LEVEL_1),
      zipCode: this.extractComponent(components, ADDRESS_COMPONENT_TYPES.POSTAL_CODE),
      country: this.extractComponent(components, ADDRESS_COMPONENT_TYPES.COUNTRY),
    };
  }

  populateAddressFields(place, formManager) {
    const addressInfo = this.getAddressFromPlace(place);
    if (!addressInfo) return;

    const { elements } = formManager;

    // Populate form fields
    if (elements.nameInput && place.name) {
      elements.nameInput.value = place.name;
    }

    if (elements.addressInput) {
      const fullAddress = [addressInfo.streetNumber, addressInfo.route]
        .filter(Boolean)
        .join(' ');
      elements.addressInput.value = fullAddress || place.formatted_address || '';
    }

    if (elements.cityInput) {
      elements.cityInput.value = addressInfo.city;
    }

    if (elements.stateInput) {
      elements.stateInput.value = addressInfo.state;
    }

    if (elements.zipInput) {
      elements.zipInput.value = addressInfo.zipCode;
    }

    // Populate coordinates if available
    if (place.geometry && place.geometry.location) {
      const { location } = place.geometry;
      const lat = typeof location.lat === 'function' ? location.lat() : location.lat;
      const lng = typeof location.lng === 'function' ? location.lng() : location.lng;

      if (elements.latInput) {
        elements.latInput.value = lat;
      }

      if (elements.lngInput) {
        elements.lngInput.value = lng;
      }
    }

    logger.debug('Address fields populated from place:', addressInfo);
  }
}

// ===== GOOGLE PLACES MANAGER =====

class GooglePlacesManager {
  constructor(formManager, addressProcessor) {
    this.formManager = formManager;
    this.addressProcessor = addressProcessor;
    this.state = {
      isInitialized: false,
      autocomplete: null,
    };
  }

  async initGooglePlacesSearch() {
    if (this.state.isInitialized) {
      logger.debug('Google Places search already initialized');
      return;
    }

    try {
      await googleMapsManager.initializeForRestaurants();
      await this.initAutocomplete();

      this.state.isInitialized = true;
      logger.info('Google Places search initialized successfully');
    } catch (error) {
      logger.error('Failed to initialize Google Places search:', error);
      throw error;
    }
  }

  async initAutocomplete() {
    const searchInput = this.formManager.getElement('searchInput');
    if (!searchInput) {
      logger.warn('Restaurant search input not found');
      return;
    }

    try {
      const autocompleteOptions = {
        types: ['restaurant', 'establishment'],
        fields: [
          'place_id', 'name', 'formatted_address', 'geometry',
          'address_components', 'rating', 'user_ratings_total',
        ],
      };

      const { autocomplete, onPlaceChanged } = googleMapsManager.createAutocomplete(
        searchInput,
        autocompleteOptions,
      );

      this.state.autocomplete = autocomplete;

      // Handle place selection
      onPlaceChanged((place) => {
        logger.debug('Place selected:', place);
        this.addressProcessor.populateAddressFields(place, this.formManager);
      });

      logger.debug('Autocomplete initialized for search input');
    } catch (error) {
      logger.error('Failed to initialize autocomplete:', error);
      throw error;
    }
  }

  isInitialized() {
    return this.state.isInitialized;
  }
}

// ===== MAIN RESTAURANT FORM CLASS =====

class RestaurantForm {
  constructor() {
    this.formManager = new RestaurantFormManager();
    this.geolocationManager = new GeolocationManager();
    this.addressProcessor = new AddressProcessor();
    this.placesManager = new GooglePlacesManager(this.formManager, this.addressProcessor);
  }

  async init() {
    if (this.formManager.state.isInitialized) {
      logger.debug('Restaurant form already initialized');
      return;
    }

    try {
      logger.info('Initializing restaurant form...');

      // Cache DOM elements
      this.formManager.cacheElements();

      // Set up event listeners
      this.formManager.setupEventListeners();

      // Initialize geolocation
      await this.initializeGeolocation();

      // Initialize Google Places search
      await this.initializeGooglePlaces();

      this.formManager.state.isInitialized = true;
      logger.info('Restaurant form initialized successfully');
    } catch (error) {
      logger.error('Failed to initialize restaurant form:', error);
      throw error;
    }
  }

  async initializeGeolocation() {
    try {
      const location = await this.geolocationManager.getCurrentLocation();
      this.formManager.state.userLocation = location;
      logger.debug('Geolocation initialized:', location);
    } catch (error) {
      logger.warn('Geolocation initialization failed:', error);
    }
  }

  async initializeGooglePlaces() {
    try {
      await this.placesManager.initGooglePlacesSearch();
      logger.debug('Google Places initialized');
    } catch (error) {
      logger.warn('Google Places initialization failed:', error);
    }
  }

  // Public API methods
  showLoading(message) {
    this.formManager.showLoading(message);
  }

  hideLoading() {
    this.formManager.hideLoading();
  }

  showError(message) {
    this.formManager.showError(message);
  }

  getElement(key) {
    return this.formManager.getElement(key);
  }

  isInitialized() {
    return this.formManager.state.isInitialized;
  }
}

// ===== EXPORTS =====

// Create singleton instance
const restaurantForm = new RestaurantForm();

export {
  RestaurantForm,
  RestaurantFormManager,
  GeolocationManager,
  AddressProcessor,
  GooglePlacesManager,
  restaurantForm,
  DEFAULT_LOCATION,
  ADDRESS_COMPONENT_TYPES,
};

// Default export
export default restaurantForm;
