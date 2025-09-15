/**
 * Configuration Utility
 * Reads configuration from HTML data attributes
 * Follows HTML-JS separation rules
 */

// Cache for configuration values
const config_cache = {};

/**
 * Get Google Maps configuration from global variable
 * @returns {Object} Configuration object with apiKey
 */
export function getGoogleMapsConfig() {
  if (config_cache.googleMaps) {
    return config_cache.googleMaps;
  }

  const config = {
    apiKey: window.GOOGLE_MAPS_API_KEY || '',
  };

  // Cache the configuration
  config_cache.googleMaps = config;

  return config;
}

/**
 * Get CSRF token from meta tag
 * @returns {string} CSRF token
 */
export function getCSRFToken() {
  // Try meta tag first (preferred method)
  const meta_tag = document.querySelector('meta[name="csrf-token"]');
  if (meta_tag && meta_tag.getAttribute('content')) {
    return meta_tag.getAttribute('content');
  }

  // Fallback to form input
  const csrf_input = document.querySelector('input[name="csrf_token"]');
  if (csrf_input && csrf_input.value) {
    return csrf_input.value;
  }

  console.warn('CSRF token not found in DOM');
  return '';
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
