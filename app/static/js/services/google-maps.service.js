/**
 * Google Maps API service
 * Handles loading and initialization of Google Maps API
 */

// Handle Google Maps API authentication failures
const handleAuthFailure = () => {
    const errorMsg = 'Google Maps API authentication failed. Please check your API key and billing status.';
    console.error(errorMsg);

    // Dispatch custom event for error handling
    document.dispatchEvent(new CustomEvent('googleMaps:error', {
        detail: { message: errorMsg }
    }));
};

// Set up global auth failure handler
if (typeof window !== 'undefined') {
    window.gm_authFailure = handleAuthFailure;
}

/**
 * Google Maps Service
 * Singleton service to handle Google Maps API loading and initialization
 */
class GoogleMapsService {
    static instance = null;

    constructor() {
        if (GoogleMapsService.instance) {
            return GoogleMapsService.instance;
        }

        this.isLoaded = false;
        this.isLoading = false;
        this.callbacks = [];
        this.loadPromise = null;

        GoogleMapsService.instance = this;
    }

    /**
     * Execute all registered callbacks
     * @private
     */
    executeCallbacks() {
        while (this.callbacks.length) {
            const callback = this.callbacks.pop();
            if (typeof callback === 'function') {
                callback();
            }
        }
    }

    /**
     * Load Google Maps API
     * @param {string} apiKey - Google Maps API key
     * @returns {Promise<void>}
     */
    async load(apiKey) {
        if (this.loadPromise) {
            return this.loadPromise;
        }

        if (this.isLoaded) {
            return Promise.resolve();
        }

        if (this.isLoading) {
            return new Promise((resolve) => {
                this.callbacks.push(resolve);
            });
        }

        this.isLoading = true;

        // If no API key provided, try to get it from config
        if (!apiKey) {
            try {
                const config = await import('../config.js');
                apiKey = config.default.googleMaps?.apiKey;

                if (!apiKey) {
                    throw new Error('Google Maps API key is not configured');
                }
            } catch (error) {
                this.isLoading = false;
                return Promise.reject(error);
            }
        }

        this.loadPromise = new Promise((resolve, reject) => {
            const script = document.createElement('script');
            script.src = `https://maps.googleapis.com/maps/api/js?key=${apiKey}&libraries=places&callback=Function.prototype`;
            script.async = true;
            script.defer = true;
            script.onload = () => {
                this.isLoaded = true;
                this.isLoading = false;
                this.executeCallbacks();
                resolve();
            };
            script.onerror = (error) => {
                this.isLoading = false;
                this.loadPromise = null;
                const errorDetail = 'Failed to load Google Maps API. Please check your API key and network connection.';
                console.error(errorDetail, error);
                // Dispatch error event
                document.dispatchEvent(new CustomEvent('googleMaps:error', {
                    detail: { message: errorDetail, error }
                }));

                reject(new Error(errorDetail));
            };

            // Add script to document
            document.head.appendChild(script);
            console.log('GoogleMapsService: Script element added to document');
        });

        return this.loadPromise;
    }

}

// Create and export singleton instance
const googleMapsService = new GoogleMapsService();

export { googleMapsService as default };

// Export a function to load Google Maps API with the provided key
export const loadGoogleMapsAPI = async () => {
    // Import the config to get the API key
    const config = await import('../config.js');
    const apiKey = config.default.googleMaps?.apiKey;

    if (!apiKey) {
        const error = new Error('Google Maps API key is not configured');
        console.error(error);
        throw error;
    }

    // The actual loading is handled by the GoogleMapsService class
    return googleMapsService.load(apiKey);
};

// Also make it available globally for legacy code
if (typeof window !== 'undefined') {
    window.GoogleMapsService = googleMapsService;
}
