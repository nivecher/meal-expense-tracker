/**
 * Browser Extension Error Handler
 *
 * Handles conflicts between browser extensions (autofill, password managers, etc.)
 * and custom form elements like Tagify. This prevents extension errors from
 * breaking the application functionality.
 *
 * @version 1.0.0
 * @author Meal Expense Tracker Team
 */

/**
 * Initialize comprehensive error handling for browser extension conflicts
 * This should be called early in the application lifecycle
 */
export function initExtensionErrorHandler() {
  // Override console.error to catch and suppress extension errors
  const originalConsoleError = console.error;
  console.error = function(...args) {
    const message = args.join(' ');

    // Suppress Bootstrap autofill overlay errors
    if (message.includes('tagName.toLowerCase is not a function') &&
        (message.includes('bootstrap-autofill-overlay') ||
         message.includes('autofill'))) {
      console.debug('Suppressed autofill extension error:', message);
      return;
    }

    // Suppress other common extension errors
    if (message.includes('extension://') ||
        message.includes('moz-extension://') ||
        message.includes('chrome-extension://') ||
        message.includes('safari-extension://')) {
      console.debug('Suppressed browser extension error:', message);
      return;
    }

    originalConsoleError.apply(console, args);
  };

  // Global error event handler
  window.addEventListener('error', (event) => {
    const isExtensionError = isExtensionRelatedError(event);
    if (isExtensionError) {
      console.debug('Suppressed extension error event:', event.error);
      event.preventDefault();
      return false;
    }
  });

  // Global unhandled promise rejection handler
  window.addEventListener('unhandledrejection', (event) => {
    const isExtensionRejection = isExtensionRelatedRejection(event);
    if (isExtensionRejection) {
      console.debug('Suppressed extension promise rejection:', event.reason);
      event.preventDefault();
      return false;
    }
  });
}

/**
 * Check if an error event is related to browser extensions
 * @param {ErrorEvent} event - The error event
 * @returns {boolean} - True if the error is extension-related
 */
function isExtensionRelatedError(event) {
  // Check filename for extension paths
  if (event.filename && (
    event.filename.includes('bootstrap-autofill-overlay.js') ||
    event.filename.includes('extension://') ||
    event.filename.includes('moz-extension://') ||
    event.filename.includes('chrome-extension://') ||
    event.filename.includes('safari-extension://')
  )) {
    return true;
  }

  // Check error message for specific patterns
  if (event.error && event.error.message) {
    const message = event.error.message;
    if (message.includes('tagName.toLowerCase is not a function') ||
        message.includes('autofill') ||
        message.includes('password manager')) {
      return true;
    }
  }

  return false;
}

/**
 * Check if a promise rejection is related to browser extensions
 * @param {PromiseRejectionEvent} event - The promise rejection event
 * @returns {boolean} - True if the rejection is extension-related
 */
function isExtensionRelatedRejection(event) {
  if (!event.reason) return false;

  // Check stack trace for extension paths
  if (event.reason.stack && (
    event.reason.stack.includes('bootstrap-autofill-overlay.js') ||
    event.reason.stack.includes('extension://') ||
    event.reason.stack.includes('moz-extension://') ||
    event.reason.stack.includes('chrome-extension://') ||
    event.reason.stack.includes('safari-extension://')
  )) {
    return true;
  }

  // Check error message for specific patterns
  if (event.reason.message) {
    const message = event.reason.message;
    if (message.includes('tagName.toLowerCase is not a function') ||
        message.includes('autofill') ||
        message.includes('password manager')) {
      return true;
    }
  }

  return false;
}

/**
 * Make an element "extension-safe" by adding defensive properties
 * This helps prevent browser extensions from interfering with custom elements
 * @param {HTMLElement} element - The element to make extension-safe
 */
export function makeElementExtensionSafe(element) {
  if (!element) return;

  // Add data attribute to identify as extension-safe
  element.setAttribute('data-extension-safe', 'true');

  // Ensure tagName property exists and is a string
  if (!element.tagName || typeof element.tagName !== 'string') {
    Object.defineProperty(element, 'tagName', {
      value: element.nodeName || 'DIV',
      writable: false,
      configurable: false
    });
  }

  // Add defensive properties for common extension checks
  if (!element.type) {
    element.type = 'text';
  }

  if (!element.name) {
    element.name = element.id || 'extension-safe-input';
  }
}

/**
 * Initialize extension-safe handling for Tagify elements
 * @param {HTMLElement} tagifyElement - The Tagify input element
 */
export function initTagifyExtensionSafety(tagifyElement) {
  if (!tagifyElement) return;

  // Make the base element extension-safe
  makeElementExtensionSafe(tagifyElement);

  // Add event listeners to handle extension interference
  tagifyElement.addEventListener('focus', () => {
    // Temporarily disable extension interference
    tagifyElement.setAttribute('data-extension-disabled', 'true');
  });

  tagifyElement.addEventListener('blur', () => {
    // Re-enable extension interference
    tagifyElement.removeAttribute('data-extension-disabled');
  });

  // Override any problematic methods that extensions might call
  const originalQuerySelector = tagifyElement.querySelector;
  if (originalQuerySelector) {
    tagifyElement.querySelector = function(selector) {
      try {
        return originalQuerySelector.call(this, selector);
      } catch (error) {
        if (error.message.includes('tagName.toLowerCase')) {
          console.debug('Suppressed querySelector error in Tagify element');
          return null;
        }
        throw error;
      }
    };
  }
}

// Auto-initialize when module is loaded
initExtensionErrorHandler();
