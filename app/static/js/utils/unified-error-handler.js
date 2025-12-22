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
  try {
    const ElementProto = Element.prototype;
    const originalTagNameDescriptor = Object.getOwnPropertyDescriptor(ElementProto, 'tagName');

    if (originalTagNameDescriptor && originalTagNameDescriptor.configurable) {
      // Override tagName getter to ensure it always returns a string
      Object.defineProperty(ElementProto, 'tagName', {
        get() {
          try {
            const tagName = originalTagNameDescriptor.get ? originalTagNameDescriptor.get.call(this) : this.nodeName;
            if (typeof tagName === 'string') {
              return tagName;
            }
            // Fallback: use nodeName or localName
            return (this.localName || this.nodeName || 'UNKNOWN').toUpperCase();
          } catch (_error) {
            // Fallback if getter fails
            return (this.localName || this.nodeName || 'UNKNOWN').toUpperCase();
          }
        },
        configurable: true,
        enumerable: false,
      });
    }
  } catch (_error) {
    // If we can't patch prototype, use per-element fixing
  }

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

    // Filter out Chrome extension connection errors
    if (message.includes('Could not establish connection') ||
        message.includes('Receiving end does not exist') ||
        message.includes('runtime.lastError')) {
      // Suppress extension-related errors
      return;
    }

    // Filter out tagName.toLowerCase errors (we're fixing these)
    if (message.includes('tagName.toLowerCase is not a function') ||
        (error && error.message && error.message.includes('tagName.toLowerCase is not a function'))) {
      // Suppress - we're fixing this globally
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
          reason.message.includes('runtime.lastError') ||
          reason.message.includes('tagName.toLowerCase is not a function')) {
        // Suppress extension-related errors
        return;
      }
    }

    // Filter out string-based extension errors
    if (typeof reason === 'string') {
      if (reason.includes('Could not establish connection') ||
          reason.includes('Receiving end does not exist') ||
          reason.includes('runtime.lastError') ||
          reason.includes('tagName.toLowerCase is not a function')) {
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
