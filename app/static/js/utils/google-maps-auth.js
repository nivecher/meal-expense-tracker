/**
 * Google Maps Authentication and Initialization
 *
 * This script handles the loading and initialization of the Google Maps JavaScript API.
 * It ensures the API is only loaded once and provides a way to run callbacks
 * when the API is ready to be used.
 */

import { logger } from './logger.js';

const GoogleMapsAuth = (function () {
  'use strict';

  const GOOGLE_MAPS_API_URL = 'https://maps.googleapis.com/maps/api/js';
  const GOOGLE_MAPS_LIBRARIES = ['places', 'geometry'];

  let googleMapsLoading = false;
  const googleMapsCallbacks = [];
  let googleMapsInitialized = false;

  /**
   * Execute all pending callbacks
   */
  function executeCallbacks () {
    while (googleMapsCallbacks.length > 0) {
      const callback = googleMapsCallbacks.shift();
      if (typeof callback === 'function') {
        try {
          callback();
        } catch (error) {
          logger.error('Error in Google Maps callback:', error);
        }
      }
    }
  }

  /**
   * Handle Google Maps API loading error
   * @private
   * @param {string} callbackName - The name of the global callback function
   */
  function handleGoogleMapsError (callbackName) {
    logger.error('Error loading Google Maps API');
    delete window[callbackName];
    googleMapsLoading = false;

    // Reject all callbacks
    while (googleMapsCallbacks.length > 0) {
      const cb = googleMapsCallbacks.shift();
      if (typeof cb === 'function') {
        try {
          cb(new Error('Failed to load Google Maps API'));
        } catch (e) {
          logger.error('Error in error callback:', e);
        }
      }
    }
  }

  /**
   * Create and configure the Google Maps script element
   * @private
   * @param {string} apiKey - Google Maps API key
   * @param {string} callbackName - Name of the global callback function
   * @returns {HTMLScriptElement} The configured script element
   */
  function createGoogleMapsScript (apiKey, callbackName) {
    const script = document.createElement('script');
    const libraries = GOOGLE_MAPS_LIBRARIES.join(',');

    // Set up the global callback
    window[callbackName] = function onGoogleMapsLoaded () {
      googleMapsInitialized = true;
      delete window[callbackName];
      logger.debug('Google Maps API loaded successfully');
      executeCallbacks();
    };

    // Set up error handling
    script.onerror = () => handleGoogleMapsError(callbackName);

    // Set the source URL with loading=async for better performance
    script.src = `${GOOGLE_MAPS_API_URL}?key=${encodeURIComponent(apiKey)}&libraries=${encodeURIComponent(libraries)}&callback=${callbackName}&loading=async`;
    script.async = true;
    script.defer = true;

    return script;
  }

  /**
   * Initialize Google Maps API with the provided API key
   * @param {string} apiKey - Google Maps API key
   * @param {Function} callback - Function to call when the API is loaded
   */
  function initGoogleMaps (apiKey, callback) {
    // Handle already initialized case
    if (googleMapsInitialized) {
      logger.warn('Google Maps API is already initialized');
      if (callback) callback();
      return;
    }

    // Validate API key
    if (!apiKey) {
      const error = new Error('Google Maps API key is required');
      logger.error(error.message);
      if (callback) callback(error);
      return;
    }

    // Handle case where Google Maps is already loaded but not marked as initialized
    if (window.google?.maps) {
      googleMapsInitialized = true;
      if (callback) callback();
      return;
    }

    // Handle case where Google Maps is already loading
    if (googleMapsLoading) {
      logger.debug('Google Maps API is already loading');
      if (callback) googleMapsCallbacks.push(callback);
      return;
    }

    // Add callback to the queue if provided
    if (callback) {
      googleMapsCallbacks.push(callback);
    }

    googleMapsLoading = true;
    const callbackName = `googleMapsApiLoaded${Date.now()}`;
    const script = createGoogleMapsScript(apiKey, callbackName);
    document.head.appendChild(script);
  }

  // Return public API
  return {
    init: initGoogleMaps,
    isInitialized () {
      return googleMapsInitialized || !!(window.google && window.google.maps);
    },
  };
})();

// Make it available globally for backward compatibility
window.GoogleMapsAuth = GoogleMapsAuth;

// Export the GoogleMapsAuth object
export { GoogleMapsAuth };
