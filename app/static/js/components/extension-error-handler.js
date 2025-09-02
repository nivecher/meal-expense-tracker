/**
 * Extension Error Handler
 * Handles browser extension conflicts with custom elements like Tagify
 */

class ExtensionErrorHandler {
    constructor() {
        this.isInitialized = false;
    }

    /**
     * Initialize the extension error handler
     */
    init() {
        if (this.isInitialized) return;

        this.setupGlobalErrorHandlers();
        this.setupElementProtection();
        this.isInitialized = true;
    }

    /**
     * Setup global error handlers to suppress extension errors
     */
    setupGlobalErrorHandlers() {
        // Handle uncaught errors
        window.addEventListener('error', (event) => {
            if (this.isExtensionError(event.error)) {
                console.warn('Suppressed extension error:', event.error.message);
                event.preventDefault();
                return false;
            }
        });

        // Handle unhandled promise rejections
        window.addEventListener('unhandledrejection', (event) => {
            if (this.isExtensionError(event.reason)) {
                console.warn('Suppressed extension promise rejection:', event.reason.message);
                event.preventDefault();
                return false;
            }
        });
    }

    /**
     * Check if an error is from a browser extension
     */
    isExtensionError(error) {
        if (!error || !error.message) return false;

        const extensionErrorPatterns = [
            'tagName.toLowerCase is not a function',
            'bootstrap-autofill-overlay',
            'elementIsInstanceOf',
            'elementIsFormElement',
            'nodeIsFormElement',
            'CollectAutofillContentService',
            'DomQueryService'
        ];

        return extensionErrorPatterns.some(pattern =>
            error.message.includes(pattern) ||
            error.stack?.includes(pattern)
        );
    }

    /**
     * Setup element protection for custom elements
     */
    setupElementProtection() {
        // Protect Tagify elements
        this.protectTagifyElements();

        // Monitor for new Tagify elements
        this.observeTagifyElements();
    }

    /**
     * Protect existing Tagify elements
     */
    protectTagifyElements() {
        const tagifyElements = document.querySelectorAll('tag, .tagify, .tagify__tag');
        tagifyElements.forEach(element => {
            this.makeElementExtensionSafe(element);
        });
    }

    /**
     * Observe for new Tagify elements and protect them
     */
    observeTagifyElements() {
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                mutation.addedNodes.forEach((node) => {
                    if (node.nodeType === Node.ELEMENT_NODE) {
                        // Check if it's a Tagify element
                        if (node.tagName === 'TAG' ||
                            node.classList?.contains('tagify') ||
                            node.classList?.contains('tagify__tag')) {
                            this.makeElementExtensionSafe(node);
                        }

                        // Check children for Tagify elements
                        const tagifyChildren = node.querySelectorAll?.('tag, .tagify, .tagify__tag');
                        tagifyChildren?.forEach(child => {
                            this.makeElementExtensionSafe(child);
                        });
                    }
                });
            });
        });

        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
    }

    /**
     * Make an element safe from extension interference
     */
    makeElementExtensionSafe(element) {
        if (!element || !element.tagName) return;

        // Add extension-safe attributes
        element.setAttribute('data-extension-safe', 'true');
        element.setAttribute('data-autofill-safe', 'true');

        // Ensure tagName property exists and is a function
        if (!element.tagName || typeof element.tagName.toLowerCase !== 'function') {
            const originalTagName = element.tagName || element.nodeName || 'UNKNOWN';

            Object.defineProperty(element, 'tagName', {
                get: function() {
                    return originalTagName;
                },
                configurable: true
            });

            // Add toLowerCase method if missing
            if (typeof element.tagName.toLowerCase !== 'function') {
                element.tagName.toLowerCase = function() {
                    return originalTagName.toLowerCase();
                };
            }
        }

        // Add other properties that extensions might expect
        if (!element.nodeName) {
            element.nodeName = element.tagName;
        }

        if (!element.nodeType) {
            element.nodeType = Node.ELEMENT_NODE;
        }
    }
}

// Global utility function for other components to use
window.makeElementExtensionSafe = function(element) {
    if (window.extensionErrorHandler) {
        window.extensionErrorHandler.makeElementExtensionSafe(element);
    }
};

// Initialize the extension error handler
window.extensionErrorHandler = new ExtensionErrorHandler();

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.extensionErrorHandler.init();
    });
} else {
    window.extensionErrorHandler.init();
}

// Export for module usage
export default ExtensionErrorHandler;
