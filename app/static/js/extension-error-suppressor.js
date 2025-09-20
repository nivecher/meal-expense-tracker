/**
 * Browser Extension Error Suppressor
 *
 * This script aggressively suppresses errors from browser extensions,
 * particularly password managers and autofill extensions that cause
 * "element.tagName.toLowerCase is not a function" errors.
 */

(function() {
  'use strict';

  // Store original methods
  const originalError = console.error;
  const originalWarn = console.warn;
  const originalLog = console.log;

  // Error patterns to suppress
  const SUPPRESS_PATTERNS = [
    'bootstrap-autofill-overlay',
    'element.tagName.toLowerCase is not a function',
    'elementIsInstanceOf',
    'elementIsFormElement',
    'nodeIsFormElement',
    'CollectAutofillContentService',
    'DomQueryService',
    'queryAutofillFormAndFieldElements',
  ];

  // Check if message should be suppressed
  function shouldSuppress(message) {
    if (!message || typeof message !== 'string') {
      return false;
    }
    return SUPPRESS_PATTERNS.some((pattern) =>
      message.toLowerCase().includes(pattern.toLowerCase()),
    );
  }

  // Override console methods
  console.error = function(...args) {
    const message = args.join(' ');
    if (shouldSuppress(message)) {
      return; // Completely suppress
    }
    originalError.apply(console, args);
  };

  console.warn = function(...args) {
    const message = args.join(' ');
    if (shouldSuppress(message)) {
      return; // Completely suppress
    }
    originalWarn.apply(console, args);
  };

  console.log = function(...args) {
    const message = args.join(' ');
    if (shouldSuppress(message)) {
      return; // Completely suppress
    }
    originalLog.apply(console, args);
  };

  // Global error handler
  window.addEventListener('error', (event) => {
    if (shouldSuppress(event.message) ||
        (event.filename && shouldSuppress(event.filename))) {
      event.preventDefault();
      event.stopPropagation();
      event.stopImmediatePropagation();
      return false;
    }
  }, true); // Use capture phase

  // Unhandled promise rejection handler
  window.addEventListener('unhandledrejection', (event) => {
    if (event.reason && (
      shouldSuppress(event.reason.message) ||
        (event.reason.stack && shouldSuppress(event.reason.stack))
    )) {
      event.preventDefault();
      event.stopPropagation();
      event.stopImmediatePropagation();
      return false;
    }
  }, true); // Use capture phase

  // Override problematic DOM methods that extensions might use
  if (typeof document !== 'undefined') {
    const originalQuerySelector = document.querySelector;
    const originalQuerySelectorAll = document.querySelectorAll;

    document.querySelector = function(selector) {
      try {
        return originalQuerySelector.call(this, selector);
      } catch {
        if (shouldSuppress(error.message) ||
            (error.stack && shouldSuppress(error.stack))) {
          return null;
        }
        throw error;
      }
    };

    document.querySelectorAll = function(selector) {
      try {
        return originalQuerySelectorAll.call(this, selector);
      } catch {
        if (shouldSuppress(error.message) ||
            (error.stack && shouldSuppress(error.stack))) {
          return [];
        }
        throw error;
      }
    };
  }

  // Override NodeList methods that extensions might use
  if (typeof NodeList !== 'undefined' && NodeList.prototype) {
    const originalForEach = NodeList.prototype.forEach;
    NodeList.prototype.forEach = function(callback, thisArg) {
      try {
        return originalForEach.call(this, callback, thisArg);
      } catch {
        if (shouldSuppress(error.message) ||
            (error.stack && shouldSuppress(error.stack))) {
          return;
        }
        throw error;
      }
    };
  }

  console.debug('Extension error suppressor loaded successfully');
})();
