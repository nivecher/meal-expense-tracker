/**
 * Configuration Utility
 * Reads configuration from HTML data attributes
 * Follows HTML-JS separation rules
 */

// Cache for configuration values
const config_cache = {};

/**
 * Get Google Maps configuration from HTML data attributes
 * @returns {Object} Configuration object with apiKey and mapId
 */
export function getGoogleMapsConfig() {
  if (config_cache.googleMaps) {
    return config_cache.googleMaps;
  }

  const config_element = document.getElementById('google-maps-global-config');
  if (!config_element) {
    console.warn('Google Maps config element not found');
    return { apiKey: '', mapId: '' };
  }

  const config = {
    apiKey: config_element.dataset.apiKey || '',
    mapId: config_element.dataset.mapId || '',
  };

  // Cache the configuration
  config_cache.googleMaps = config;

  // Log for debugging (following the original behavior)
  console.log('Google Maps API Key:', config.apiKey ? 'Key loaded' : 'No API key found');
  if (config.mapId) {
    console.log('Google Maps Map ID loaded');
  }

  return config;
}

/**
 * Get CSRF token from meta tag
 * @returns {string} CSRF token
 */
export function getCSRFToken() {
  if (config_cache.csrfToken) {
    return config_cache.csrfToken;
  }

  const meta_tag = document.querySelector('meta[name="csrf-token"]');
  const token = meta_tag ? meta_tag.getAttribute('content') : '';

  config_cache.csrfToken = token;
  return token;
}

/**
 * Get application configuration
 * @returns {Object} Configuration object
 */
export function getAppConfig() {
  return {
    googleMaps: getGoogleMapsConfig(),
    csrfToken: getCSRFToken(),
  };
}

// For backward compatibility, set global variables if needed
// This allows existing code to continue working
function setGlobalCompatibility() {
  const google_config = getGoogleMapsConfig();

  // Only set if not already defined
  if (typeof window.GOOGLE_MAPS_API_KEY === 'undefined') {
    window.GOOGLE_MAPS_API_KEY = google_config.apiKey;
  }

  if (typeof window.GOOGLE_MAPS_MAP_ID === 'undefined') {
    window.GOOGLE_MAPS_MAP_ID = google_config.mapId;
  }
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', setGlobalCompatibility);
} else {
  setGlobalCompatibility();
}
