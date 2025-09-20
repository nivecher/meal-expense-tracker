/**
 * Console Warning Filter
 *
 * This utility helps filter out common CDN/library warnings
 * so you can focus on your application's actual issues.
 *
 * Usage: Include this script in development to filter noise
 */

(function() {
  'use strict';

  // Store original console methods
  const originalWarn = console.warn;
  const originalError = console.error;
  // const originalLog = console.log; // Unused for now

  // Common CDN/library warning patterns to filter
  const FILTERED_PATTERNS = [
    // Bootstrap warnings
    /Bootstrap.*deprecated/i,
    /Bootstrap.*warning/i,

    // jQuery warnings
    /jQuery.*deprecated/i,
    /jQuery.*warning/i,

    // Font Awesome warnings
    /Font Awesome.*deprecated/i,
    /Font Awesome.*warning/i,

    // Select2 warnings
    /Select2.*deprecated/i,
    /Select2.*warning/i,

    // Chart.js warnings
    /Chart\.js.*deprecated/i,
    /Chart\.js.*warning/i,

    // Generic CDN warnings
    /cdn\.jsdelivr\.net/i,
    /cdnjs\.cloudflare\.com/i,
    /code\.jquery\.com/i,

    // Browser compatibility warnings from external sources
    /webkit.*not supported/i,
    /text-size-adjust.*not supported/i,
    /color-adjust.*not supported/i,
  ];

  // Check if a message should be filtered
  function shouldFilter(message) {
    if (typeof message !== 'string') {
      return false;
    }

    return FILTERED_PATTERNS.some((pattern) => pattern.test(message));
  }

  // Filtered console.warn
  console.warn = function(...args) {
    const message = args[0];
    if (shouldFilter(message)) {
      // Log to a separate filtered warnings object for debugging
      if (!window.filteredWarnings) {
        window.filteredWarnings = [];
      }
      window.filteredWarnings.push({
        type: 'warn',
        message,
        timestamp: new Date().toISOString(),
        stack: new Error().stack,
      });
      return;
    }
    originalWarn.apply(console, args);
  };

  // Filtered console.error
  console.error = function(...args) {
    const message = args[0];
    if (shouldFilter(message)) {
      if (!window.filteredWarnings) {
        window.filteredWarnings = [];
      }
      window.filteredWarnings.push({
        type: 'error',
        message,
        timestamp: new Date().toISOString(),
        stack: new Error().stack,
      });
      return;
    }
    originalError.apply(console, args);
  };

  // Add utility functions to inspect filtered warnings
  window.getFilteredWarnings = function() {
    return window.filteredWarnings || [];
  };

  window.clearFilteredWarnings = function() {
    window.filteredWarnings = [];
  };

  window.showFilteredWarnings = function() {
    const warnings = window.getFilteredWarnings();
    console.group('🔍 Filtered Console Warnings');
    warnings.forEach((warning, index) => {
      console.log(`${index + 1}. [${warning.type.toUpperCase()}] ${warning.message}`);
    });
    console.groupEnd();
    return warnings.length;
  };

  // Log that the filter is active
  console.log('🔧 Console warning filter active. Use showFilteredWarnings() to see filtered messages.');

})();
