/**
 * Google Maps Utilities
 * Consolidated Google Maps API loading, maps service, and places functionality
 *
 * @module googleMaps
 * @version 2.0.0
 * @author Meal Expense Tracker Team
 */

import { logger } from './core-utils.js';

// ===== GOOGLE MAPS API LOADER =====

class GoogleMapsLoader {
  static isApiLoaded() {
    return !!(window.google && window.google.maps);
  }

  static async load(apiKey, libraries = ['places'], options = {}) {
    // If already loaded, return immediately
    if (this.isApiLoaded()) {
      logger.debug('Google Maps API already loaded');
      return Promise.resolve(window.google);
    }

    // If already loading, return existing promise
    if (window.googleMapsLoading) {
      logger.debug('Google Maps API already loading');
      return window.googleMapsLoading.promise;
    }

    // Create loading promise
    const loadingPromise = new Promise((resolve, reject) => {
      const callbackName = `gmapsCallback_${Date.now()}`;

      // Set up global callback
      window[callbackName] = () => {
        logger.debug('Google Maps API loaded successfully');
        delete window[callbackName];
        delete window.googleMapsLoading;

        if (!window.google || !window.google.maps) {
          const error = new Error('Google Maps API loaded but google.maps is not available');
          logger.error(error);
          reject(error);
          return;
        }

        resolve(window.google);
      };

      try {
        const effectiveApiKey = apiKey || window.GOOGLE_MAPS_API_KEY;
        if (!effectiveApiKey) {
          const error = new Error('Google Maps API key is required');
          logger.error(error);
          reject(error);
          return;
        }

        // Build URL parameters
        const params = new URLSearchParams({
          key: effectiveApiKey,
          callback: callbackName,
          loading: 'async',
          v: 'weekly',
        });

        if (libraries.length) {
          params.set('libraries', libraries.join(','));
        }

        if (options.mapId) {
          params.set('map_ids', options.mapId);
        }

        if (options.language) {
          params.set('language', options.language);
        }

        if (options.region) {
          params.set('region', options.region);
        }

        const url = `https://maps.googleapis.com/maps/api/js?${params.toString()}`;

        // Add script tag
        const script = document.createElement('script');
        script.src = url;
        script.async = true;
        script.defer = true;
        script.onerror = () => {
          const errorMsg = 'Failed to load Google Maps API';
          logger.error(errorMsg);
          delete window.googleMapsLoading;
          reject(new Error(errorMsg));
        };

        document.head.appendChild(script);
      } catch (error) {
        logger.error('Error loading Google Maps API:', error);
        reject(error);
        delete window[callbackName];
        delete window.googleMapsLoading;
      }
    });

    // Store loading state
    window.googleMapsLoading = { promise: loadingPromise };

    return loadingPromise;
  }

  static async loadWithRetry(apiKey, libraries = ['places'], maxRetries = 3, options = {}) {
    for (let attempt = 1; attempt <= maxRetries; attempt++) {
      try {
        logger.debug(`Loading Google Maps API (attempt ${attempt}/${maxRetries})`);
        return await this.load(apiKey, libraries, options);
      } catch (error) {
        if (attempt === maxRetries) {
          throw error;
        }
        logger.warn(`Google Maps API load failed, retrying... (${attempt}/${maxRetries})`);
        await new Promise((resolve) => {
          setTimeout(resolve, 1000 * attempt);
        });
      }
    }
  }

  // Compatibility methods for old google-maps-loader.js
  static async loadApiWithRetry(apiKey, callback, libraries = ['places'], maxRetries = 3) {
    try {
      const google = await this.loadWithRetry(apiKey, libraries, maxRetries);
      if (callback && typeof callback === 'function') {
        callback(google);
      }
      return google;
    } catch (error) {
      logger.error('Failed to load Google Maps API with retry:', error);
      throw error;
    }
  }

  static async loadApi(apiKey, callback, libraries = ['places']) {
    try {
      const google = await this.load(apiKey, libraries);
      if (callback && typeof callback === 'function') {
        callback(google);
      }
      return google;
    } catch (error) {
      logger.error('Failed to load Google Maps API:', error);
      throw error;
    }
  }

  // Alias for backward compatibility (isApiLoaded is already defined above)
}

// ===== GOOGLE MAPS SERVICE =====

class GoogleMapsService {
  constructor() {
    this.isInitialized = false;
    this.isLoading = false;
    this.loadPromise = null;
    this.defaultLibraries = ['places'];
    this.defaultOptions = {
      mapId: window.GOOGLE_MAPS_MAP_ID,
      loading: 'async',
    };

    // Rate limiting
    this.rateLimitKey = 'google_maps_service_rate_limit';
    this.rateLimitWindow = 60 * 60 * 1000; // 1 hour
    this.maxRequestsPerHour = 45;
  }

  canMakeRequest() {
    const now = Date.now();
    const rateLimitData = JSON.parse(localStorage.getItem(this.rateLimitKey) || '{"count": 0, "resetTime": 0}');

    if (now > rateLimitData.resetTime) {
      rateLimitData.count = 0;
      rateLimitData.resetTime = now + this.rateLimitWindow;
    }

    if (rateLimitData.count >= this.maxRequestsPerHour) {
      return false;
    }

    rateLimitData.count++;
    localStorage.setItem(this.rateLimitKey, JSON.stringify(rateLimitData));

    return true;
  }

  async initialize(libraries = this.defaultLibraries, options = this.defaultOptions) {
    if (this.isInitialized) {
      return true;
    }

    if (this.isLoading && this.loadPromise) {
      return this.loadPromise;
    }

    this.isLoading = true;
    this.loadPromise = this.loadGoogleMapsAPI(libraries, options);

    try {
      await this.loadPromise;
      this.isInitialized = true;
      this.isLoading = false;
      logger.info('Google Maps service initialized successfully');
      return true;
    } catch (error) {
      this.isLoading = false;
      this.loadPromise = null;
      logger.error('Failed to initialize Google Maps service:', error);
      throw error;
    }
  }

  async loadGoogleMapsAPI(libraries, options) {
    if (!this.canMakeRequest()) {
      throw new Error('Rate limit exceeded for Google Maps API requests');
    }

    const apiKey = window.GOOGLE_MAPS_API_KEY;
    if (!apiKey) {
      throw new Error('Google Maps API key not found');
    }

    try {
      await GoogleMapsLoader.loadWithRetry(apiKey, libraries, 3, options);
      logger.debug('Google Maps API loaded successfully');
    } catch (error) {
      logger.error('Failed to load Google Maps API:', error);
      throw new Error('Failed to load Google Maps. Please check your internet connection and try again.');
    }
  }

  isReady() {
    return this.isInitialized && GoogleMapsLoader.isApiLoaded();
  }

  async initializeForPlaces() {
    return this.initialize(['places'], this.defaultOptions);
  }

  async initializeForAdvancedMap() {
    return this.initialize(['places', 'marker'], {
      ...this.defaultOptions,
      mapId: window.GOOGLE_MAPS_MAP_ID,
    });
  }
}

// ===== GOOGLE PLACES SERVICE =====

class GooglePlacesService {
  constructor() {
    this.initialized = false;
    this.radius = 5000;
    this.maxResults = 20;
    this.useModernAPI = false;
    this.placesService = null;
    this.autocompleteService = null;
    this.mapReference = null; // Store map reference for auto-initialization
  }

  async init(map = null) {
    if (this.initialized) {
      return true;
    }

    try {
      if (!window.google || !window.google.maps || !window.google.maps.places) {
        throw new Error('Google Maps Places API not available');
      }

      // Store the map reference for future use
      if (map) {
        this.mapReference = map;
      }

      // Always initialize legacy services as fallback, check for modern APIs
      const mapToUse = map || this.mapReference || document.createElement('div');
      logger.debug('Initializing PlacesService with:', mapToUse === map ? 'provided map' : mapToUse === this.mapReference ? 'stored map' : 'fallback div');

      // Always create legacy services for backward compatibility and fallback
      try {
        this.placesService = new google.maps.places.PlacesService(mapToUse);
        this.autocompleteService = new google.maps.places.AutocompleteService();
        logger.debug('Legacy services created successfully:', {
          placesService: !!this.placesService,
          autocompleteService: !!this.autocompleteService
        });
      } catch (serviceError) {
        logger.error('Failed to create Places services:', serviceError);
        throw new Error(`Failed to create Places services: ${serviceError.message}`);
      }

      // Check if modern APIs are available for future use
      if (google.maps.places.Place && google.maps.places.AutocompleteSuggestion) {
        logger.debug('Modern Place class APIs detected, but using legacy APIs for now');
        this.useModernAPI = false; // Keep using legacy until modern implementation is complete
      } else {
        logger.debug('Using legacy PlacesService APIs');
        this.useModernAPI = false;
      }

      this.initialized = true;
      logger.debug('Google Places service initialized successfully. Final state:', {
        initialized: this.initialized,
        useModernAPI: this.useModernAPI,
        hasPlacesService: !!this.placesService,
        placesServiceType: this.placesService ? this.placesService.constructor.name : 'null'
      });
      return true;
    } catch (error) {
      logger.error('Failed to initialize Google Places service:', error);
      throw new Error('Failed to initialize map services. Please try again later.');
    }
  }

  async searchRestaurants(query, location = null) {
    if (!this.initialized) {
      await this.init();
    }

    try {
      if (this.useModernAPI) {
        return await this.searchUsingModernAPI(query, location);
      }
      return await this.searchUsingLegacyAPI(query, location);

    } catch (error) {
      logger.error('Restaurant search failed:', error);
      throw error;
    }
  }

  async searchUsingModernAPI(query, location) {
    // Modern API implementation would go here
    // For now, fall back to legacy API
    return this.searchUsingLegacyAPI(query, location);
  }

  async searchUsingLegacyAPI(query, location) {
    return new Promise((resolve, reject) => {
      if (!this.placesService) {
        reject(new Error('Places service not initialized'));
        return;
      }

      const request = {
        query: `${query} restaurant`,
        type: ['restaurant'],
        fields: [
          'place_id', 'name', 'formatted_address', 'geometry',
          'rating', 'user_ratings_total', 'price_level',
          'photos', 'business_status', 'types',
        ],
      };

      if (location && location.lat && location.lng) {
        request.location = new google.maps.LatLng(location.lat, location.lng);
        request.radius = this.radius;
      }

      this.placesService.textSearch(request, (results, status) => {
        if (status === google.maps.places.PlacesServiceStatus.OK) {
          const restaurants = results.slice(0, this.maxResults).map((place) => this.formatPlace(place));
          resolve({
            restaurants,
            status: 'success',
            total: restaurants.length,
          });
        } else {
          logger.error('Places search failed:', status);
          reject(new Error(`Search failed: ${status}`));
        }
      });
    });
  }

  formatPlace(place) {
    return {
      placeId: place.place_id,
      name: place.name || 'Unknown Restaurant',
      address: place.formatted_address || 'Address not available',
      location: place.geometry?.location ? {
        lat: place.geometry.location.lat(),
        lng: place.geometry.location.lng(),
      } : null,
      rating: place.rating || null,
      userRatingsTotal: place.user_ratings_total || 0,
      priceLevel: place.price_level || null,
      businessStatus: place.business_status || 'OPERATIONAL',
      types: place.types || [],
      photos: place.photos ? place.photos.slice(0, 3).map((photo) => ({
        url: photo.getUrl({ maxWidth: 400, maxHeight: 300 }),
        width: 400,
        height: 300,
      })) : [],
    };
  }

  async searchNearby(location, options = {}) {
    logger.debug('searchNearby called, initialized:', this.initialized, 'placesService:', !!this.placesService);

    if (!this.initialized) {
      logger.debug('Auto-initializing Places service...');
      await this.init();
    }

    return new Promise((resolve, reject) => {
      logger.debug('After init check - initialized:', this.initialized, 'useModernAPI:', this.useModernAPI, 'placesService:', !!this.placesService);

      // Always use legacy API for now since it's reliable and modern implementation is incomplete
      if (!this.placesService) {
        logger.error('Places service still not initialized after init attempt');
        reject(new Error('Places service not initialized'));
        return;
      }

      this.searchNearbyWithLegacyAPI(location, options, resolve, reject);
    });
  }

  /**
   * Search nearby using the modern Place API
   * @private
   */
  searchNearbyWithModernAPI(location, options, resolve, reject) {
    try {
      // Modern API implementation - placeholder for now
      logger.warn('Modern Place API not yet fully implemented, falling back to legacy API');
      this.searchNearbyWithLegacyAPI(location, options, resolve, reject);
    } catch (error) {
      logger.error('Modern API search failed:', error);
      reject(error);
    }
  }

  /**
   * Search nearby using the legacy PlacesService API
   * @private
   */
  searchNearbyWithLegacyAPI(location, options, resolve, reject) {
    const request = {
      location: new google.maps.LatLng(location.lat, location.lng),
      radius: options.radius || this.radius,
      types: ['restaurant'], // Changed from 'type' to 'types' for compatibility
    };

    logger.debug('Places API request (legacy):', request);

    if (options.keyword) {
      request.keyword = options.keyword;
    }

    try {
      this.placesService.nearbySearch(request, (results, status) => {
        try {
          logger.debug('Places API response:', { status, resultsCount: results?.length });

          if (status === google.maps.places.PlacesServiceStatus.OK) {
            const formattedResults = results.slice(0, options.maxResults || this.maxResults).map((place) => this.formatPlace(place));
            resolve({
              results: formattedResults,
              status: 'OK',
              error: null
            });
          } else {
            logger.error('Places nearby search failed:', status);
            resolve({
              results: [],
              status: status,
              error: `Search failed with status: ${status}`
            });
          }
        } catch (callbackError) {
          logger.error('Error in nearbySearch callback:', callbackError);
          reject(callbackError);
        }
      });
    } catch (apiError) {
      logger.error('Error calling nearbySearch API:', apiError);
      reject(apiError);
    }
  }

  createAutocomplete(inputElement, options = {}) {
    if (!inputElement) {
      throw new Error('Input element is required for autocomplete');
    }

    const autocompleteOptions = {
      types: ['restaurant', 'establishment'],
      fields: ['place_id', 'name', 'formatted_address', 'geometry'],
      ...options,
    };

    try {
      const autocomplete = new google.maps.places.Autocomplete(inputElement, autocompleteOptions);

      return {
        autocomplete,
        onPlaceChanged: (callback) => {
          autocomplete.addListener('place_changed', () => {
            const place = autocomplete.getPlace();
            if (place && place.place_id) {
              callback(this.formatPlace(place));
            }
          });
        },
      };
    } catch (error) {
      logger.error('Failed to create autocomplete:', error);
      throw new Error('Failed to initialize search. Please try again.');
    }
  }
}

// ===== UNIFIED GOOGLE MAPS MANAGER =====

class GoogleMapsManager {
  constructor() {
    this.mapsService = new GoogleMapsService();
    this.placesService = new GooglePlacesService();
    this.loader = GoogleMapsLoader;
  }

  // Service getters
  get maps() {
    return this.mapsService;
  }

  get places() {
    return this.placesService;
  }

  // Convenience methods
  async initialize(libraries = ['places'], options = {}) {
    await this.mapsService.initialize(libraries, options);
    await this.placesService.init();
    return this;
  }

  async initializeForRestaurants() {
    await this.mapsService.initializeForPlaces();
    await this.placesService.init();
    return this;
  }

  isReady() {
    return this.mapsService.isReady() && this.placesService.initialized;
  }

  // Direct access to common methods
  async searchRestaurants(query, location) {
    return this.placesService.searchRestaurants(query, location);
  }

  createAutocomplete(inputElement, options) {
    return this.placesService.createAutocomplete(inputElement, options);
  }
}

// ===== EXPORTS =====

// Create singleton instances
const googleMapsService = new GoogleMapsService();
const googlePlacesService = new GooglePlacesService();
const googleMapsManager = new GoogleMapsManager();

export {
  GoogleMapsLoader,
  GoogleMapsService,
  GooglePlacesService,
  GoogleMapsManager,
  googleMapsService,
  googlePlacesService,
  googleMapsManager,
};

// Default export for backward compatibility
export default googleMapsManager;
