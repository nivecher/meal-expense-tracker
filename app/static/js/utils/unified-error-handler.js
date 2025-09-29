/**
 * Simple Error Handler
 *
 * Basic error handling that only logs critical errors.
 * No console overrides, no complex patterns, just simple error catching.
 */

(function() {
  'use strict';

  // Only log critical JavaScript errors (filter out extension errors)
  window.addEventListener('error', (event) => {
    const { error } = event;
    const message = event.message || 'Unknown error';

    // Filter out Chrome extension connection errors
    if (message.includes('Could not establish connection') ||
        message.includes('Receiving end does not exist') ||
        message.includes('runtime.lastError')) {
      // Suppress extension-related errors
      return;
    }

    // Only log actual JavaScript errors, not resource loading issues
    if (error instanceof Error) {
      // Also check error message for extension-related issues
      if (error.message && (
        error.message.includes('Could not establish connection') ||
          error.message.includes('Receiving end does not exist') ||
          error.message.includes('runtime.lastError'))) {
        // Suppress extension-related errors
        return;
      }

      console.error('JavaScript Error:', {
        message,
        stack: error.stack,
        filename: event.filename,
        line: event.lineno,
        column: event.colno,
      });
    }
  });

  // Log unhandled promise rejections (filter out extension errors)
  window.addEventListener('unhandledrejection', (event) => {
    const { reason } = event;

    // Filter out Chrome extension connection errors
    if (reason && typeof reason === 'object' && reason.message) {
      if (reason.message.includes('Could not establish connection') ||
          reason.message.includes('Receiving end does not exist') ||
          reason.message.includes('runtime.lastError')) {
        // Suppress extension-related errors
        return;
      }
    }

    // Filter out string-based extension errors
    if (typeof reason === 'string') {
      if (reason.includes('Could not establish connection') ||
          reason.includes('Receiving end does not exist') ||
          reason.includes('runtime.lastError')) {
        // Suppress extension-related errors
        return;
      }
    }

    console.error('Unhandled Promise Rejection:', event.reason);
  });

  // Development mode - log initialization
  if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
    console.debug('Simple Error Handler initialized');
  }

})();
