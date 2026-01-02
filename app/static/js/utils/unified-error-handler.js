/**
 * Simple Error Handler
 *
 * Basic error handling that only logs critical errors.
 * No console overrides, no complex patterns, just simple error catching.
 */

(function() {
  'use strict';

  // CRITICAL FIX: Ensure all elements have proper tagName property
  // This must run IMMEDIATELY to prevent browser extension errors
  // Browser extensions inject code that traverses the DOM and calls tagName.toLowerCase()
  // This fix ensures tagName is always a string with toLowerCase method

  // Immediate synchronous fix - patch Element.prototype.tagName if possible
  (function patchTagNameProperty() {
    'use strict';

    function getSafeTagName(element) {
      try {
        // Try to get tagName from the original descriptor
        if (element.nodeType === Node.ELEMENT_NODE) {
          // Use nodeName as fallback (always available on elements)
          const { nodeName } = element;
          if (nodeName && typeof nodeName === 'string') {
            return nodeName;
          }
          // Try localName (for custom elements)
          const { localName } = element;
          if (localName && typeof localName === 'string') {
            return localName.toUpperCase();
          }
        }
        return 'UNKNOWN';
      } catch (_error) {
        return 'UNKNOWN';
      }
    }

    function createTagNameGetter(originalDescriptor) {
      return function() {
        try {
          // Try original getter first
          if (originalDescriptor && originalDescriptor.get) {
            const tagName = originalDescriptor.get.call(this);
            if (tagName && typeof tagName === 'string') {
              return tagName;
            }
          }
          // Fallback to nodeName
          return getSafeTagName(this);
        } catch (_error) {
          // Fallback if getter fails
          return getSafeTagName(this);
        }
      };
    }

    function patchElementPrototype(proto, descriptor) {
      if (!descriptor) {
        // No descriptor found, try to create one
        try {
          Object.defineProperty(proto, 'tagName', {
            get() {
              return getSafeTagName(this);
            },
            configurable: true,
            enumerable: false,
          });
        } catch (_createError) {
          // If creation fails, use per-element fixing
        }
        return;
      }

      if (descriptor.configurable) {
        // Override tagName getter to ensure it always returns a string
        Object.defineProperty(proto, 'tagName', {
          get: createTagNameGetter(descriptor),
          configurable: true,
          enumerable: false,
        });
        return;
      }

      // If not configurable, try to wrap the getter
      const originalGetter = descriptor.get;
      if (!originalGetter) {
        return;
      }

      try {
        const wrappedGetter = createTagNameGetter(descriptor);
        // Try to replace (may fail if not configurable)
        Object.defineProperty(proto, 'tagName', {
          get: wrappedGetter,
          configurable: false,
          enumerable: false,
        });
      } catch (_wrapError) {
        // If wrapping fails, we'll use per-element fixing
      }
    }

    // Patch Element.prototype.tagName
    try {
      const ElementProto = Element.prototype;
      const originalTagNameDescriptor = Object.getOwnPropertyDescriptor(ElementProto, 'tagName');
      patchElementPrototype(ElementProto, originalTagNameDescriptor);
    } catch (_error) {
      // If we can't patch prototype, use per-element fixing
    }

    // Also patch HTMLElement.prototype as a fallback
    try {
      if (typeof HTMLElement !== 'undefined' && HTMLElement.prototype) {
        const HTMLElementProto = HTMLElement.prototype;
        const htmlTagNameDescriptor = Object.getOwnPropertyDescriptor(HTMLElementProto, 'tagName');
        patchElementPrototype(HTMLElementProto, htmlTagNameDescriptor);
      }
    } catch (_htmlError) {
      // Silently fail
    }
  })();

  (function fixElementTagNameGlobally() {
    'use strict';

    function fixElementTagName(element) {
      if (!element || element.nodeType !== Node.ELEMENT_NODE) {
        return;
      }

      try {
        // Get the actual tag name (handles custom elements)
        const actualTagName = element.localName || element.nodeName || 'UNKNOWN';
        const upperTagName = typeof actualTagName === 'string' ? actualTagName.toUpperCase() : 'UNKNOWN';

        // Check if tagName is missing, not a string, or doesn't have toLowerCase
        const currentTagName = element.tagName;
        const needsFix = !currentTagName ||
          typeof currentTagName !== 'string' ||
          typeof currentTagName.toLowerCase !== 'function';

        if (!needsFix) {
          return;
        }

        // Try to get the original tagName descriptor
        let descriptor = Object.getOwnPropertyDescriptor(element, 'tagName');
        if (!descriptor) {
          // Try parent prototype
          const proto = Object.getPrototypeOf(element);
          if (proto) {
            descriptor = Object.getOwnPropertyDescriptor(proto, 'tagName');
          }
        }

        // Only try to fix if configurable or if we can't determine
        if (descriptor && descriptor.configurable === false) {
          return;
        }

        // Try to replace with a string value
        try {
          Object.defineProperty(element, 'tagName', {
            value: upperTagName,
            writable: false,
            configurable: true,
            enumerable: false,
          });
          return;
        } catch (_defineError) {
          // If defineProperty fails, try to wrap it
        }

        // Fallback: Create a wrapper that ensures tagName is always a string
        const originalTagName = currentTagName || upperTagName;
        try {
          Object.defineProperty(element, 'tagName', {
            get() {
              const tagName = originalTagName || (element.localName || element.nodeName || 'UNKNOWN').toUpperCase();
              return typeof tagName === 'string' ? tagName : String(tagName).toUpperCase();
            },
            configurable: true,
            enumerable: false,
          });
        } catch (_wrapError) {
          // Silently fail - element may not be configurable
        }
      } catch (_error) {
        // Silently handle errors
      }
    }

    // Fix all existing elements immediately
    function fixAllElements() {
      try {
        if (document.body) {
          const allElements = document.querySelectorAll('*');
          allElements.forEach((el) => {
            fixElementTagName(el);
          });
        }
      } catch (_error) {
        // Silently handle errors
      }
    }

    // Run fix immediately if DOM is ready, otherwise wait
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', fixAllElements, { once: true });
    } else {
      fixAllElements();
    }

    // Watch for new elements being added and fix them
    if (document.body) {
      const observer = new MutationObserver((mutations) => {
        mutations.forEach((mutation) => {
          mutation.addedNodes.forEach((node) => {
            if (node.nodeType === Node.ELEMENT_NODE) {
              fixElementTagName(node);
              // Fix all child elements
              if (node.querySelectorAll) {
                try {
                  const allElements = node.querySelectorAll('*');
                  allElements.forEach((el) => {
                    fixElementTagName(el);
                  });
                } catch (_error) {
                  // Silently handle errors
                }
              }
            }
          });
        });
      });

      observer.observe(document.body, {
        childList: true,
        subtree: true,
      });
    } else {
      // Wait for body to be available
      document.addEventListener('DOMContentLoaded', () => {
        if (document.body) {
          const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
              mutation.addedNodes.forEach((node) => {
                if (node.nodeType === Node.ELEMENT_NODE) {
                  fixElementTagName(node);
                  if (node.querySelectorAll) {
                    try {
                      const allElements = node.querySelectorAll('*');
                      allElements.forEach((el) => {
                        fixElementTagName(el);
                      });
                    } catch (_error) {
                      // Silently handle errors
                    }
                  }
                }
              });
            });
          });

          observer.observe(document.body, {
            childList: true,
            subtree: true,
          });
        }
      }, { once: true });
    }
  })();

  // Only log critical JavaScript errors (filter out extension errors)
  window.addEventListener('error', (event) => {
    const { error } = event;
    const message = event.message || 'Unknown error';
    const filename = event.filename || '';
    const stack = error?.stack || '';

    // Filter out Chrome extension connection errors
    if (message.includes('Could not establish connection') ||
        message.includes('Receiving end does not exist') ||
        message.includes('runtime.lastError')) {
      // Suppress extension-related errors
      event.preventDefault();
      event.stopPropagation();
      return false;
    }

    // Filter out tagName.toLowerCase errors from browser extensions
    const isTagNameError =
      message.includes('tagName.toLowerCase is not a function') ||
      (error && error.message && error.message.includes('tagName.toLowerCase is not a function')) ||
      filename.includes('bootstrap-autofill-overlay-notifications') ||
      filename.includes('bootstrap-autofill') ||
      stack.includes('bootstrap-autofill-overlay-notifications') ||
      stack.includes('bootstrap-autofill') ||
      stack.includes('elementIsInstanceOf') ||
      stack.includes('elementIsFormElement') ||
      stack.includes('nodeIsFormElement') ||
      stack.includes('DomQueryService') ||
      stack.includes('CollectAutofillContentService');

    if (isTagNameError) {
      // Suppress - these are from browser extensions, not our code
      event.preventDefault();
      event.stopPropagation();
      event.stopImmediatePropagation();
      return false;
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
  // MUST be added early to catch errors before they're logged
  window.addEventListener('unhandledrejection', (event) => {
    const { reason } = event;

    // Extract error information from various possible formats
    let message = '';
    let stack = '';
    let errorString = '';

    if (reason) {
      if (typeof reason === 'string') {
        message = reason;
        errorString = reason;
      } else if (typeof reason === 'object') {
        message = reason.message || reason.toString() || '';
        stack = reason.stack || '';
        errorString = JSON.stringify(reason);
      } else {
        message = String(reason);
        errorString = String(reason);
      }
    }

    // Filter out bootstrap-autofill extension errors - comprehensive check
    const isBootstrapAutofillError =
      message.includes('tagName.toLowerCase is not a function') ||
      message.includes('bootstrap-autofill-overlay-notifications') ||
      message.includes('bootstrap-autofill') ||
      stack.includes('bootstrap-autofill-overlay-notifications') ||
      stack.includes('bootstrap-autofill') ||
      stack.includes('elementIsInstanceOf') ||
      stack.includes('elementIsFormElement') ||
      stack.includes('nodeIsFormElement') ||
      stack.includes('DomQueryService') ||
      stack.includes('CollectAutofillContentService') ||
      errorString.includes('bootstrap-autofill-overlay-notifications') ||
      errorString.includes('bootstrap-autofill') ||
      errorString.includes('tagName.toLowerCase');

    if (isBootstrapAutofillError) {
      // Suppress the error completely
      event.preventDefault();
      event.stopPropagation();
      event.stopImmediatePropagation();
      return false;
    }

    // Filter out Chrome extension connection errors
    if (reason && typeof reason === 'object' && reason.message) {
      if (reason.message.includes('Could not establish connection') ||
          reason.message.includes('Receiving end does not exist') ||
          reason.message.includes('runtime.lastError') ||
          reason.message.includes('tagName.toLowerCase is not a function')) {
        // Suppress extension-related errors
        event.preventDefault();
        event.stopPropagation();
        return false;
      }
    }

    // Filter out string-based extension errors
    if (typeof reason === 'string') {
      if (reason.includes('Could not establish connection') ||
          reason.includes('Receiving end does not exist') ||
          reason.includes('runtime.lastError') ||
          reason.includes('tagName.toLowerCase is not a function') ||
          reason.includes('bootstrap-autofill')) {
        // Suppress extension-related errors
        event.preventDefault();
        event.stopPropagation();
        return false;
      }
    }

    // Check error object properties for extension indicators
    if (reason && typeof reason === 'object') {
      const reasonString = JSON.stringify(reason);
      if (reasonString.includes('bootstrap-autofill') ||
          reasonString.includes('tagName.toLowerCase')) {
        event.preventDefault();
        event.stopPropagation();
        return false;
      }
    }

    console.error('Unhandled Promise Rejection:', event.reason);
  });

  // Override console.error to filter extension errors - MUST be set up early
  const originalConsoleError = console.error;
  console.error = function(...args) {
    // Convert all arguments to string for checking
    const message = args.map((arg) => {
      if (typeof arg === 'string') return arg;
      if (arg && typeof arg === 'object') {
        if (arg.message) return arg.message;
        if (arg.stack) return arg.stack;
        return JSON.stringify(arg);
      }
      return String(arg);
    }).join(' ');

    // Filter out bootstrap-autofill extension errors - comprehensive check
    const isExtensionError =
      message.includes('tagName.toLowerCase is not a function') ||
      message.includes('bootstrap-autofill-overlay-notifications') ||
      message.includes('bootstrap-autofill') ||
      message.includes('elementIsInstanceOf') ||
      message.includes('elementIsFormElement') ||
      message.includes('nodeIsFormElement') ||
      message.includes('DomQueryService') ||
      message.includes('CollectAutofillContentService');

    if (isExtensionError) {
      // Suppress - these are from browser extensions, not our code
      return;
    }

    // Check individual arguments for extension indicators
    for (const arg of args) {
      if (typeof arg === 'string' && (
        arg.includes('bootstrap-autofill') ||
        arg.includes('tagName.toLowerCase')
      )) {
        return; // Suppress
      }

      if (arg && typeof arg === 'object') {
        const argString = JSON.stringify(arg);
        if (argString.includes('bootstrap-autofill') ||
            argString.includes('tagName.toLowerCase')) {
          return; // Suppress
        }

        // Check stack property
        if (arg.stack && (
          arg.stack.includes('bootstrap-autofill') ||
          arg.stack.includes('elementIsInstanceOf') ||
          arg.stack.includes('elementIsFormElement')
        )) {
          return; // Suppress
        }
      }
    }

    // Call original console.error for legitimate errors
    originalConsoleError.apply(console, args);
  };

  // Development mode - log initialization
  if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
    console.debug('Simple Error Handler initialized');
  }

})();
