import { logger } from './logger.js';

/**
 * Google Maps API Loader Utility
 * Handles asynchronous loading of Google Maps JavaScript API
 */
class GoogleMapsLoader {
  /**
   * Check if Google Maps API is already loaded
   * @returns {boolean} True if Google Maps API is loaded
   */
  static isApiLoaded() {
    return !!(window.google && window.google.maps);
  }

  /**
   * Load Google Maps API
   * @param {string} apiKey - Google Maps API key
   * @param {Function} [callback] - Callback function to execute when API is loaded
   * @param {string[]|Object} [librariesOrOptions=['places', 'geocoding']] - Libraries to load or options object
   * @param {string} [options.mapId] - Optional Map ID for advanced features
   * @returns {Promise<Object>} Promise that resolves with the google.maps object
   */
  static loadApi(apiKey, callback, librariesOrOptions = ['places', 'geocoding']) {
    // If already loaded, just call the callback
    if (this.isApiLoaded()) {
      logger.debug('Google Maps API already loaded');
      if (typeof callback === 'function') {
        callback(window.google);
      }
      return Promise.resolve(window.google);
    }

    // If already loading, just add to the callback queue
    if (window.googleMapsLoading) {
      logger.debug('Google Maps API already loading, adding to queue');
      return window.googleMapsLoading.promise.then(() => {
        if (typeof callback === 'function') callback(window.google);
        return window.google;
      });
    }

    // Create loading state
    const loadingState = {};

    // Create promise and store it in loadingState
    loadingState.promise = new Promise((resolve, reject) => {
      const callbackName = `gmapsCallback_${Date.now()}`;

      // Set up the global callback
      window[callbackName] = () => {
        logger.debug('Google Maps API loaded successfully');
        delete window[callbackName];
        delete window.googleMapsLoading;

        // Ensure google.maps is available
        if (!window.google || !window.google.maps) {
          const error = new Error('Google Maps API loaded but google.maps is not available');
          logger.error(error);
          reject(error);
          return;
        }

        // Resolve with the google object
        resolve(window.google);
        if (typeof callback === 'function') callback(window.google);
      };

      try {
        // Parse options
        const options = {
          libraries: Array.isArray(librariesOrOptions) ? librariesOrOptions : (librariesOrOptions.libraries || ['places', 'geocoding']),
          mapId: librariesOrOptions.mapId,
          language: librariesOrOptions.language,
          region: librariesOrOptions.region
        };

        // Build the URL with parameters
        const baseUrl = 'https://maps.googleapis.com/maps/api/js';
        const params = new URLSearchParams({
          key: apiKey,
          libraries: [...new Set([...options.libraries, 'marker'])].join(','), // Ensure marker library is included
          callback: callbackName,
          v: 'weekly',
          loading: 'async'
        });

        // Add optional parameters if provided
        if (options.mapId) params.append('map_ids', options.mapId);
        if (options.language) params.append('language', options.language);
        if (options.region) params.append('region', options.region);

        // Create a script element
        const script = document.createElement('script');
        script.async = true;
        script.defer = true;
        script.src = `${baseUrl}?${params.toString()}`;

        script.onerror = () => {
          const error = new Error('Failed to load Google Maps API');
          logger.error(error);
          reject(error);
          delete window[callbackName];
          delete window.googleMapsLoading;
        };

        // Add to document
        document.head.appendChild(script);
      } catch (error) {
        logger.error('Error loading Google Maps API:', error);
        reject(error);
        delete window[callbackName];
        delete window.googleMapsLoading;
      }
    });

    // Store loading state
    window.googleMapsLoading = loadingState;

    return loadingState.promise;
  }

  /**
   * Load Google Maps API with retry logic
   * @param {string} apiKey - Google Maps API key
   * @param {Function} [callback] - Callback function to execute when API is loaded
   * @param {string[]} [libraries=['places', 'geocoding']] - Libraries to load
   * @param {number} [maxRetries=2] - Maximum number of retry attempts
   * @param {number} [retryDelay=1000] - Delay between retries in milliseconds
   * @returns {Promise<Object>} Promise that resolves with the google.maps object
   */
  static loadApiWithRetry(apiKey, callback, libraries = ['places', 'geocoding'], maxRetries = 2, retryDelay = 1000) {
    return new Promise((resolve, reject) => {
      const attempt = (attemptsLeft) => {
        this.loadApi(apiKey, callback, libraries)
          .then(resolve)
          .catch((error) => {
            if (attemptsLeft <= 0) {
              logger.error('Max retries reached, giving up on loading Google Maps API');
              reject(error);
              return;
            }

            logger.warn(`Google Maps API load failed, retrying... (${maxRetries - attemptsLeft + 1}/${maxRetries})`);
            setTimeout(() => attempt(attemptsLeft - 1), retryDelay);
          });
      };

      attempt(maxRetries);
    });
  }

  /**
   * Load Google Maps API with options
   * @param {Object} options - Configuration options
   * @param {string} options.key - Google Maps API key
   * @param {string[]} [options.libraries=['places']] - Libraries to load
   * @param {string} [options.language='en'] - Language code
   * @param {string} [options.region='US'] - Region code
   * @returns {Promise<boolean>} Resolves with true when loaded
   */
  static async load({ key, libraries = ['places'], language = 'en', region = 'US' }) {
    try {
      await this.loadApi(key, null, libraries);

      // Set language and region if provided
      if (language && window.google?.maps) {
        const maps = await window.google.maps.importLibrary('maps');
        if (maps?.settings) {
          maps.settings.language = language;
        }
      }

      if (region && window.google?.maps) {
        const maps = await window.google.maps.importLibrary('maps');
        if (maps?.settings) {
          maps.settings.region = region;
        }
      }

      return true;
    } catch (error) {
      console.error('Failed to load Google Maps API:', error);
      throw error;
    }
  }
}

export default GoogleMapsLoader;
