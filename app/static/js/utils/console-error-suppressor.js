/**
 * Console Error Suppressor
 *
 * Suppresses known browser extension and framework errors that clutter the console
 * without affecting application functionality. This runs immediately to prevent
 * errors from appearing in the console.
 */
(function() {
  'use strict';

  // IMMEDIATELY override console methods before ANY other script runs
  const originalError = console.error;
  const originalWarn = console.warn;
  const originalLog = console.log;

  console.error = function(...args) {
    const msg = args.join(' ');
    if (msg && typeof msg === 'string' && (msg.includes('bootstrap-autofill-overlay') ||
            msg.includes('tagName.toLowerCase') ||
            msg.includes('elementIsInstanceOf'))) {
      return; // SILENT SUPPRESSION
    }
    originalError.apply(console, args);
  };

  console.warn = function(...args) {
    const msg = args.join(' ');
    if (msg && typeof msg === 'string' && (msg.includes('bootstrap-autofill-overlay') ||
            msg.includes('tagName.toLowerCase') ||
            msg.includes('elementIsInstanceOf'))) {
      return; // SILENT SUPPRESSION
    }
    originalWarn.apply(console, args);
  };

  console.log = function(...args) {
    const msg = args.join(' ');
    if (msg && typeof msg === 'string' && (msg.includes('bootstrap-autofill-overlay') ||
            msg.includes('tagName.toLowerCase') ||
            msg.includes('elementIsInstanceOf'))) {
      return; // SILENT SUPPRESSION
    }
    originalLog.apply(console, args);
  };

  // IMMEDIATE error suppression
  window.addEventListener('error', (e) => {
    if (e.message && (e.message.includes('tagName.toLowerCase') ||
            e.message.includes('bootstrap-autofill-overlay'))) {
      e.preventDefault();
      e.stopPropagation();
      return false;
    }
  }, true);

  // IMMEDIATE promise rejection suppression
  window.addEventListener('unhandledrejection', (e) => {
    if (e.reason && e.reason.message &&
            (e.reason.message.includes('tagName.toLowerCase') ||
             e.reason.message.includes('bootstrap-autofill-overlay'))) {
      e.preventDefault();
      e.stopPropagation();
      return false;
    }
  }, true);

})();
