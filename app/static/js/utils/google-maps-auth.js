/**
 * Google Maps Authentication and Initialization
 *
 * @deprecated Use google-maps-loader.js instead
 * This file is kept for backward compatibility but will be removed in a future version.
 */

import { logger } from './logger.js';
import GoogleMapsLoader from './google-maps-loader.js';

const GoogleMapsAuth = (function () {
  'use strict';

  const GOOGLE_MAPS_LIBRARIES = ['places', 'geometry'];
  let googleMapsInitialized = false;

  /**
   * Initialize Google Maps API with the provided API key
   * @param {string} apiKey - Google Maps API key
   * @param {Function} callback - Function to call when the API is loaded
   */
  async function initGoogleMaps (apiKey, callback) {
    if (!apiKey) {
      logger.error('Google Maps API key is required');
      return;
    }

    try {
      // Use the new GoogleMapsLoader utility
      await GoogleMapsLoader.loadApiWithRetry(
        apiKey,
        (google) => {
          googleMapsInitialized = true;
          if (typeof callback === 'function') {
            callback(google);
          }
        },
        GOOGLE_MAPS_LIBRARIES,
        3,  // max retries
        1000, // retry delay in ms
      );
    } catch (error) {
      logger.error('Failed to load Google Maps API:', error);
      throw error;
    }
  }

  /**
   * Check if Google Maps API is initialized
   * @returns {boolean} True if Google Maps API is initialized
   */
  function isInitialized () {
    return googleMapsInitialized || GoogleMapsLoader.isApiLoaded();
  }

  // Return public API
  return {
    init: initGoogleMaps,
    isInitialized,
  };
})();

// Make it available globally for backward compatibility
window.GoogleMapsAuth = GoogleMapsAuth;

// Export as both named and default for backward compatibility
export { GoogleMapsAuth };
export default GoogleMapsAuth;
