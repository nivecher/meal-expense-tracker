/**
 * Simplified Error Handler
 *
 * Only handles essential error suppression for browser extensions
 * and prevents critical errors from freezing the page.
 */

(function() {
  'use strict';

  // Suppress browser extension errors that can freeze the page
  window.addEventListener('error', (event) => {
    const { error, message } = event;
    const errorMessage = message || (error && error.message) || '';

    // Suppress known browser extension errors
    if (errorMessage.includes('tagName.toLowerCase is not a function') ||
        errorMessage.includes('bootstrap-autofill') ||
        errorMessage.includes('Could not establish connection') ||
        errorMessage.includes('Receiving end does not exist')) {
      event.preventDefault();
      event.stopPropagation();
      return false;
    }
  }, true);

  // Suppress unhandled promise rejections from extensions
  window.addEventListener('unhandledrejection', (event) => {
    const { reason } = event;
    const message = (reason && reason.message) || String(reason || '');

    if (message.includes('tagName.toLowerCase is not a function') ||
        message.includes('bootstrap-autofill') ||
        message.includes('Could not establish connection') ||
        message.includes('Receiving end does not exist')) {
      event.preventDefault();
      return false;
    }
  });

  // Simple console.error filter - only suppress extension errors
  const originalConsoleError = console.error;
  console.error = function(...args) {
    const message = args.map((arg) => {
      if (typeof arg === 'string') return arg;
      if (arg && typeof arg === 'object' && arg.message) return arg.message;
      return String(arg);
    }).join(' ');

    // Only suppress extension-related errors
    if (message.includes('tagName.toLowerCase is not a function') ||
        message.includes('bootstrap-autofill')) {
      return; // Suppress
    }

    // Call original for all other errors
    originalConsoleError.apply(console, args);
  };

})();
