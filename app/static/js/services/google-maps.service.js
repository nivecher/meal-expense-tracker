/**
 * Google Maps API service
 * Handles loading and initialization of Google Maps API
 */

// Handle Google Maps API authentication failures
const handleAuthFailure = () => {
    const errorMsg = 'Google Maps API authentication failed. Please check your API key and billing status.';
    console.error(errorMsg);

    // Dispatch custom event for error handling
    if (typeof document !== 'undefined') {
        document.dispatchEvent(new CustomEvent('googleMaps:error', {
            detail: { message: errorMsg }
        }));
    }
};

// Set up global auth failure handler
if (typeof window !== 'undefined') {
    window.gm_authFailure = handleAuthFailure;
}

/**
 * Google Maps Service
 * A simple service to load the Google Maps API
 */
class GoogleMapsService {
    static SCRIPT_ID = 'google-maps-script';

    constructor() {
        this.API_KEY = typeof window !== 'undefined' ? window.GOOGLE_MAPS_API_KEY || '' : '';
        this.loadPromise = null;
    }

    /**
     * Load Google Maps API if not already loaded
     * @returns {Promise<void>}
     */
    async load() {
        if (typeof window === 'undefined') {
            return Promise.reject(new Error('Google Maps can only be loaded in a browser environment'));
        }

        if (window.google?.maps) {
            return Promise.resolve();
        }

        if (this.loadPromise) {
            return this.loadPromise;
        }

        if (!this.API_KEY) {
            return Promise.reject(new Error('Google Maps API key is not configured'));
        }

        this.loadPromise = new Promise((resolve, reject) => {
            // Remove any existing script
            const existingScript = document.getElementById(GoogleMapsService.SCRIPT_ID);
            if (existingScript) {
                document.head.removeChild(existingScript);
            }

            const script = document.createElement('script');
            script.id = GoogleMapsService.SCRIPT_ID;
            script.src = `https://maps.googleapis.com/maps/api/js?key=${this.API_KEY}&libraries=places&callback=Function.prototype`;
            script.async = true;
            script.defer = true;

            script.onload = () => {
                if (!window.google?.maps) {
                    reject(new Error('Google Maps API failed to load'));
                    return;
                }
                resolve();
            };

            script.onerror = (error) => {
                console.error('Google Maps API script error:', error);
                reject(new Error('Failed to load Google Maps API'));
            };

            document.head.appendChild(script);
        });

        return this.loadPromise;
    }

    /**
     * Alias for load() for backward compatibility
     */
    ensureLoaded() {
        return this.load();
    }
}

// Create and export singleton instance
const googleMapsService = new GoogleMapsService();

export default googleMapsService;
