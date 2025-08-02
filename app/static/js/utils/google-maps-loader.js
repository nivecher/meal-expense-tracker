import { logger } from './logger.js';

/**
 * Google Maps API Loader Utility
 * Handles asynchronous loading of Google Maps JavaScript API
 */
class GoogleMapsLoader {
  static isApiLoaded () {
    return window.google && window.google.maps;
  }

  static loadApi (apiKey, callback, libraries = ['places', 'geocoding']) {
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

    // Create loading state first
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

        if (typeof callback === 'function') {
          callback(window.google);
        }
        resolve(window.google);
      };

      // Store the loading state in window
      window.googleMapsLoading = loadingState;

      // Create the script element
      const script = document.createElement('script');
      const librariesParam = libraries.length > 0 ? `&libraries=${libraries.join(',')}` : '';

      script.src = `https://maps.googleapis.com/maps/api/js?key=${apiKey}${librariesParam}&callback=${callbackName}&v=weekly`;
      script.async = true;
      script.defer = true;
      script.fetchpriority = 'high';
      script.crossOrigin = 'anonymous';

      // Error handling
      const handleScriptError = (error) => {
        logger.error('Failed to load Google Maps API', error);
        delete window[callbackName];
        delete window.googleMapsLoading;
        reject(new Error('Failed to load Google Maps API'));
      };

      script.onerror = handleScriptError;
      script.onabort = handleScriptError;

      // Add to document
      logger.debug('Loading Google Maps API...');
      document.head.appendChild(script);
    });

    return loadingState.promise;
  }
}

export default GoogleMapsLoader;
