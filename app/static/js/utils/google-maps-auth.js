/**
 * Google Maps Authentication and Initialization
 *
 * This script handles the loading and initialization of the Google Maps JavaScript API.
 * It ensures the API is only loaded once and provides a way to run callbacks
 * when the API is ready to be used.
 */

// Create a global namespace for our Google Maps utilities
window.GoogleMapsAuth = (function() {
    'use strict';

    const GOOGLE_MAPS_API_URL = 'https://maps.googleapis.com/maps/api/js';
    const GOOGLE_MAPS_LIBRARIES = ['places', 'geometry'];

    let googleMapsLoading = false;
    let googleMapsCallbacks = [];
    let googleMapsInitialized = false;

    /**
     * Execute all pending callbacks
     */
    function executeCallbacks() {
        while (googleMapsCallbacks.length > 0) {
            const callback = googleMapsCallbacks.shift();
            if (typeof callback === 'function') {
                try {
                    callback();
                } catch (error) {
                    console.error('Error in Google Maps callback:', error);
                }
            }
        }
    }

    /**
     * Initialize Google Maps API with the provided API key
     * @param {string} apiKey - Google Maps API key
     * @param {Function} callback - Function to call when the API is loaded
     */
    function initGoogleMaps(apiKey, callback) {
        if (!apiKey) {
            console.error('Google Maps API key is required');
            if (callback) {
                callback(new Error('Google Maps API key is not configured'));
            }
            return;
        }

        if (window.google && window.google.maps) {
            // Google Maps already loaded
            if (callback) callback();
            return;
        }

        if (callback) {
            googleMapsCallbacks.push(callback);
        }

        if (googleMapsLoading) {
            // Already loading, just add to callbacks
            return;
        }

        googleMapsLoading = true;

        // Create script element
        const script = document.createElement('script');
        const libraries = GOOGLE_MAPS_LIBRARIES.join(',');
        const callbackName = 'googleMapsApiLoaded' + Date.now();

        // Set up the callback
        window[callbackName] = function() {
            googleMapsInitialized = true;
            delete window[callbackName];
            console.log('Google Maps API loaded successfully');
            executeCallbacks();
        };

        // Set up error handling
        script.onerror = function() {
            console.error('Error loading Google Maps API');
            delete window[callbackName];
            googleMapsLoading = false;

            // Reject all callbacks
            while (googleMapsCallbacks.length > 0) {
                const cb = googleMapsCallbacks.shift();
                if (typeof cb === 'function') {
                    try {
                        cb(new Error('Failed to load Google Maps API'));
                    } catch (e) {
                        console.error('Error in error callback:', e);
                    }
                }
            }
        };

        // Set the source URL with loading=async for better performance
        script.src = `${GOOGLE_MAPS_API_URL}?key=${encodeURIComponent(apiKey)}&libraries=${encodeURIComponent(libraries)}&callback=${callbackName}&loading=async`;
        script.async = true;
        script.defer = true;

        // Add to document
        document.head.appendChild(script);
    }

    // Return public API
    return {
        init: initGoogleMaps
    };
})();

// The GoogleMapsAuth object is now available globally
