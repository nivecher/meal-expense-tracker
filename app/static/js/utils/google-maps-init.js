/**
 * Google Maps API Key Initialization
 *
 * This module handles the initialization of the Google Maps API key
 * and related debug functionality.
 */

/**
 * Initialize Google Maps API key and debug mode
 * @param {string} apiKey - The Google Maps API key
 * @param {boolean} debug - Whether to enable debug mode
 */
function initGoogleMaps(apiKey, debug = false) {
    window.GOOGLE_MAPS_API_KEY = apiKey || '';
    window.GOOGLE_MAPS_DEBUG = debug;

    if (debug) {
        console.log('Google Maps API Key initialized');
    }
}

// Export for testing
export { initGoogleMaps };

// Auto-initialize if script is loaded directly
if (typeof window !== 'undefined') {
    // Get configuration from data attributes on the script tag
    const script = document.currentScript;
    if (script) {
        const apiKey = script.getAttribute('data-api-key') || '';
        const debug = script.getAttribute('data-debug') === 'true';
        initGoogleMaps(apiKey, debug);
    }
}
