/**
 * Simple Console Filter
 *
 * Reduces console noise in production by filtering common library warnings.
 * Enable debug mode with ?debug=true or localStorage.setItem('debug-mode', 'true')
 */

(function() {
  'use strict';

  // Enable debug mode via URL parameter or localStorage
  const DEBUG_MODE = window.location.search.includes('debug=true') ||
                     localStorage.getItem('debug-mode') === 'true';

  // If debug mode is on, don't filter anything
  if (DEBUG_MODE) {
    console.log('🐛 Debug mode enabled - all console messages visible');
    return;
  }

  // Store original console methods
  const originalLog = console.log;
  const originalWarn = console.warn;
  const originalError = console.error;

  // Simple patterns to filter out
  const FILTERED_PATTERNS = [
    // Library warnings
    /Bootstrap.*deprecated/i,
    /jQuery.*deprecated/i,
    /Font Awesome.*deprecated/i,
    /Select2.*deprecated/i,
    /Chart\.js.*deprecated/i,

    // CDN warnings
    /cdn\.jsdelivr\.net/i,
    /cdnjs\.cloudflare\.com/i,

    // Browser compatibility warnings
    /webkit.*not supported/i,
    /text-size-adjust.*not supported/i,
    /color-adjust.*not supported/i,

    // Application debug logs
    /RestaurantAutocomplete.*called/i,
    /RestaurantAutocomplete.*init/i,
    /Setting up event listeners/i,
    /Input event triggered/i,
    /handleInput called/i,
    /Got suggestions/i,
    /Response data/i,
    /Populating form/i,
    /Document ready state/i,
    /Application initialized successfully/i,
  ];

  function shouldFilter(message) {
    return typeof message === 'string' &&
           FILTERED_PATTERNS.some((pattern) => pattern.test(message));
  }

  // Filter console.log (most common noise source)
  console.log = function(...args) {
    if (shouldFilter(args[0])) {
      return; // Silent filter
    }
    originalLog.apply(console, args);
  };

  // Keep console.warn and console.error unfiltered for important issues
  // Only filter obvious library warnings
  console.warn = function(...args) {
    if (shouldFilter(args[0])) {
      return;
    }
    originalWarn.apply(console, args);
  };

  console.error = function(...args) {
    if (shouldFilter(args[0])) {
      return;
    }
    originalError.apply(console, args);
  };

  // Simple debug toggle
  window.toggleDebug = function() {
    const newMode = !DEBUG_MODE;
    localStorage.setItem('debug-mode', newMode.toString());
    console.log('🔄 Debug mode toggled. Refresh page to apply changes.');
  };

})();
