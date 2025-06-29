/**
 * MapLoader - Utility for loading and initializing map-related scripts
 */

// Will be imported when needed
let GoogleMapsService = null;

class MapLoader {
    /**
     * Initialize the map loader with configuration
     * @param {Object} config - Configuration object
     * @param {string} config.apiKey - Google Maps API key
     * @param {Function} [config.onLoad] - Callback when map is loaded
     * @param {Function} [config.onError] - Callback for errors
     */
    constructor({ apiKey, onLoad, onError }) {
        if (!apiKey) {
            throw new Error('Google Maps API key is required');
        }

        this.apiKey = apiKey;
        this.onLoad = onLoad || (() => {});
        this.onError = onError || (() => {});
        this.isLoaded = false;

        // Initialize Google Maps Service if not already available
        if (!window.GoogleMapsService) {
            console.warn('GoogleMapsService not found. Make sure google-maps.service.js is loaded before MapLoader');
        }
    }

    /**
     * Load required map scripts
     * @returns {Promise<void>}
     */
    async load() {
        if (this.isLoaded) {
            this.onLoad();
            return Promise.resolve();
        }

        try {
            // Load Leaflet first
            await this.loadLeaflet();

            // Then load Google Maps using the service
            try {
                // Dynamically import GoogleMapsService when needed
                if (!GoogleMapsService) {
                    const module = await import('../services/google-maps.service.js');
                    GoogleMapsService = module.default;
                }
                await GoogleMapsService.load(this.apiKey);
            } catch (error) {
                console.error('Failed to load Google Maps:', error);
                throw new Error('Failed to load Google Maps. Please check your API key and network connection.');
            }

            this.isLoaded = true;
            this.onLoad();
        } catch (error) {
            console.error('Failed to load map scripts:', error);
            this.onError(error);
            throw error;
        }
    }

    /**
     * Load Leaflet.js and its dependencies
     * @private
     * @returns {Promise<void>}
     */
    loadLeaflet() {
        return new Promise((resolve, reject) => {
            if (window.L) {
                return resolve();
            }

            // Load Leaflet CSS
            const leafletCss = document.createElement('link');
            leafletCss.rel = 'stylesheet';
            leafletCss.href = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css';
            leafletCss.integrity = 'sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=';
            leafletCss.crossOrigin = '';
            document.head.appendChild(leafletCss);

            // Load Leaflet JS
            const leafletJs = document.createElement('script');
            leafletJs.src = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js';
            leafletJs.integrity = 'sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=';
            leafletJs.crossOrigin = '';
            leafletJs.onload = () => {
                // Load MarkerCluster
                this.loadMarkerCluster().then(resolve).catch(reject);
            };
            leafletJs.onerror = reject;
            document.head.appendChild(leafletJs);
        });
    }

    /**
     * Load Leaflet MarkerCluster
     * @private
     */
    loadMarkerCluster() {
        return new Promise((resolve, reject) => {
            if (window.L.markerClusterGroup) {
                return resolve();
            }

            // Load MarkerCluster CSS
            const clusterCss = document.createElement('link');
            clusterCss.rel = 'stylesheet';
            clusterCss.href = 'https://unpkg.com/leaflet.markercluster@1.4.1/dist/MarkerCluster.css';
            document.head.appendChild(clusterCss);

            const clusterDefaultCss = document.createElement('link');
            clusterDefaultCss.rel = 'stylesheet';
            clusterDefaultCss.href = 'https://unpkg.com/leaflet.markercluster@1.4.1/dist/MarkerCluster.Default.css';
            document.head.appendChild(clusterDefaultCss);

            // Load MarkerCluster JS
            const clusterJs = document.createElement('script');
            clusterJs.src = 'https://unpkg.com/leaflet.markercluster@1.4.1/dist/leaflet.markercluster.js';
            clusterJs.onload = resolve;
            clusterJs.onerror = reject;
            document.head.appendChild(clusterJs);
        });
    }

    /**
     * Load Google Maps API using the GoogleMapsService
     * @private
     * @returns {Promise<void>}
     */
    loadGoogleMaps() {
        if (!window.GoogleMapsService) {
            const error = new Error('GoogleMapsService is not available');
            console.error(error);
            return Promise.reject(error);
        }

        return window.GoogleMapsService.load(this.apiKey)
            .then(() => {
                console.log('Google Maps API loaded successfully via GoogleMapsService');
            })
            .catch(error => {
                console.error('Failed to load Google Maps API:', error);
                throw error;
            });
    }
}

// Export as ES module
export default MapLoader;
