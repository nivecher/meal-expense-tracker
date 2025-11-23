/**
 * Location Utilities
 *
 * Provides utilities for managing location data including clearing location cookies,
 * localStorage, and resetting location permissions.
 */

/**
 * Get a cookie value by name
 * @param {string} name - Cookie name
 * @returns {string|null} Cookie value or null if not found
 */
function getCookie(name) {
  const nameEQ = `${name}=`;
  const cookies = document.cookie.split(';');

  for (let i = 0; i < cookies.length; i++) {
    let cookie = cookies[i];
    while (cookie.charAt(0) === ' ') {
      cookie = cookie.substring(1, cookie.length);
    }
    if (cookie.indexOf(nameEQ) === 0) {
      return cookie.substring(nameEQ.length, cookie.length);
    }
  }
  return null;
}

/**
 * Delete a cookie by name
 * @param {string} name - Cookie name to delete
 * @param {string} path - Cookie path (default: '/')
 * @param {string} domain - Cookie domain (optional)
 */
function deleteCookie(name, path = '/', domain = '') {
  const domainStr = domain ? `;domain=${domain}` : '';
  document.cookie = `${name}=;expires=Thu, 01 Jan 1970 00:00:00 GMT;path=${path}${domainStr}`;
}

/**
 * Reset location-related components to their initial state
 */
function resetLocationComponents() {
  // Reset restaurant autocomplete location
  const autocompleteElements = document.querySelectorAll('[data-restaurant-autocomplete]');
  autocompleteElements.forEach((element) => {
    if (element.restaurantAutocomplete && element.restaurantAutocomplete.userLocation) {
      element.restaurantAutocomplete.userLocation = null;
      element.restaurantAutocomplete.locationError = null;
      console.log('Reset restaurant autocomplete location');
    }
  });

  // Reset map components
  const mapElements = document.querySelectorAll('[data-map-search]');
  mapElements.forEach((element) => {
    if (element.mapSearch && element.mapSearch.currentLocation) {
      element.mapSearch.currentLocation = null;
      element.mapSearch.currentLocationMarker = null;
      console.log('Reset map search location');
    }
  });

  // Trigger location permission reset (user will need to allow again)
  if ('permissions' in navigator) {
    navigator.permissions.query({ name: 'geolocation' }).then((permission) => {
      console.log('Current geolocation permission:', permission.state);
    }).catch((error) => {
      console.log('Cannot query geolocation permission:', error);
    });
  }
}

/**
 * Show notification that location data was cleared
 * @param {Array} clearedItems - List of cleared items
 */
function showLocationClearNotification(clearedItems) {
  // Try to use existing toast/notification system
  if (typeof showToast === 'function') {
    showToast('Location data cleared successfully', 'success');
  } else if (typeof window.showNotification === 'function') {
    window.showNotification('Location data cleared successfully', 'success');
  } else {
    // Fallback to simple alert or console
    console.log('Location data cleared:', clearedItems);

    // Create a simple notification element
    const notification = document.createElement('div');
    notification.className = 'alert alert-success alert-dismissible fade show';
    notification.style.cssText = `
      position: fixed;
      top: 20px;
      right: 20px;
      z-index: 9999;
      max-width: 300px;
    `;
    notification.innerHTML = `
      <strong>Location Cleared!</strong>
      Cleared ${clearedItems.length} location data items.
      <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;

    document.body.appendChild(notification);

    // Auto-remove after 5 seconds
    setTimeout(() => {
      if (notification.parentNode) {
        notification.parentNode.removeChild(notification);
      }
    }, 5000);
  }
}

/**
 * Clear all location-related data from the browser
 * @param {Object} options - Configuration options
 * @param {boolean} options.clearCookies - Clear location cookies (default: true)
 * @param {boolean} options.clearLocalStorage - Clear location localStorage (default: true)
 * @param {boolean} options.showNotification - Show success notification (default: true)
 */
function clearLocationData(options = {}) {
  const config = {
    clearCookies: true,
    clearLocalStorage: true,
    showNotification: true,
    ...options,
  };

  const clearedItems = [];

  try {
    // Clear location-related cookies
    if (config.clearCookies) {
      const locationCookies = [
        'userLocation',
        'lastKnownLocation',
        'locationPermission',
        'mapCenter',
        'mapZoom',
        'searchLocation',
        'preferredLocation',
      ];

      locationCookies.forEach((cookieName) => {
        if (getCookie(cookieName)) {
          deleteCookie(cookieName);
          clearedItems.push(`Cookie: ${cookieName}`);
        }
      });
    }

    // Clear location-related localStorage
    if (config.clearLocalStorage) {
      const locationKeys = [
        'userLocation',
        'lastKnownLocation',
        'locationPermission',
        'mapState',
        'searchHistory',
        'locationPreferences',
      ];

      locationKeys.forEach((key) => {
        if (localStorage.getItem(key)) {
          localStorage.removeItem(key);
          clearedItems.push(`LocalStorage: ${key}`);
        }
      });
    }

    // Clear sessionStorage location data
    const sessionKeys = [
      'currentLocation',
      'tempLocation',
      'searchLocation',
    ];

    sessionKeys.forEach((key) => {
      if (sessionStorage.getItem(key)) {
        sessionStorage.removeItem(key);
        clearedItems.push(`SessionStorage: ${key}`);
      }
    });

    // Reset any location-related components
    resetLocationComponents();

    // Show notification if requested
    if (config.showNotification && clearedItems.length > 0) {
      showLocationClearNotification(clearedItems);
    }

    console.log('Location data cleared:', clearedItems);
    return {
      success: true,
      clearedItems,
      message: `Cleared ${clearedItems.length} location data items`,
    };

  } catch (error) {
    console.error('Error clearing location data:', error);
    return {
      success: false,
      error: error.message,
      clearedItems,
    };
  }
}

/**
 * Clear location data and reload the page
 * Useful for completely resetting location state
 */
function clearLocationAndReload() {
  const result = clearLocationData({ showNotification: false });

  if (result.success) {
    // Show a brief message before reload
    if (typeof showToast === 'function') {
      showToast('Location cleared. Reloading page...', 'info');
    }

    // Reload after a short delay
    setTimeout(() => {
      window.location.reload();
    }, 1000);
  } else {
    console.error('Failed to clear location data:', result.error);
    if (typeof showToast === 'function') {
      showToast('Failed to clear location data', 'error');
    }
  }
}

/**
 * Check if any location data exists
 * @returns {Object} Information about existing location data
 */
function checkLocationData() {
  const locationCookies = [
    'userLocation',
    'lastKnownLocation',
    'locationPermission',
    'mapCenter',
    'mapZoom',
    'searchLocation',
    'preferredLocation',
  ];

  const locationLocalStorage = [
    'userLocation',
    'lastKnownLocation',
    'locationPermission',
    'mapState',
    'searchHistory',
    'locationPreferences',
  ];

  const existingCookies = locationCookies.filter((name) => getCookie(name));
  const existingLocalStorage = locationLocalStorage.filter((key) => localStorage.getItem(key));
  const existingSessionStorage = ['currentLocation', 'tempLocation', 'searchLocation']
    .filter((key) => sessionStorage.getItem(key));

  return {
    cookies: existingCookies,
    localStorage: existingLocalStorage,
    sessionStorage: existingSessionStorage,
    hasLocationData: existingCookies.length > 0 ||
                     existingLocalStorage.length > 0 ||
                     existingSessionStorage.length > 0,
  };
}

// Export functions for use in other modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    clearLocationData,
    getCookie,
    deleteCookie,
    resetLocationComponents,
    clearLocationAndReload,
    checkLocationData,
  };
}

// Make functions available globally
window.LocationUtils = {
  clearLocationData,
  getCookie,
  deleteCookie,
  resetLocationComponents,
  clearLocationAndReload,
  checkLocationData,
};

// Add console commands for developer convenience
if (typeof window !== 'undefined' && window.console) {
  console.log('🗺️ Location Utils loaded. Available commands:');
  console.log('  LocationUtils.clearLocationData() - Clear all location data');
  console.log('  LocationUtils.checkLocationData() - Check what location data exists');
  console.log('  LocationUtils.clearLocationAndReload() - Clear location data and reload page');
}
