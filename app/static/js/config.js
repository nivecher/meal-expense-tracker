/**
 * Application Configuration
 * Centralized configuration for the application
 * Loads configuration from data attributes in the DOM
 */

// Default configuration
const defaultConfig = {
    // Base URL for static files
    staticBaseUrl: '',

    // Application settings
    app: {
        debug: false,
        env: 'production',
        version: '1.0.0'
    },

    // Google Maps configuration
    googleMaps: {
        apiKey: '',
        libraries: ['places']
    }
};

// Initialize configuration
const config = {
    ...defaultConfig,

    /**
     * Initialize the configuration from data attributes
     * @returns {Object} The configuration object
     */
    init() {
        try {
            // Find the config element
            const configEl = document.getElementById('app-config');
            if (configEl && configEl.dataset.appConfig) {
                // Parse the JSON configuration
                const userConfig = JSON.parse(configEl.dataset.appConfig);

                // Merge with defaults
                Object.assign(this, {
                    ...this,
                    ...userConfig,
                    app: {
                        ...defaultConfig.app,
                        ...(userConfig.app || {})
                    },
                    googleMaps: {
                        ...defaultConfig.googleMaps,
                        ...(userConfig.googleMaps || {})
                    }
                });
            }

            // Set Google Maps load promise
            window.googleMapsLoadPromise = null;

            return this;
        } catch (error) {
            console.error('Error initializing application configuration:', error);
            return this;
        }
    }
}.init();

// Export the configuration
export default config;
