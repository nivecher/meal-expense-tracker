/**
 * RestaurantMap - Interactive map for displaying and searching restaurants
 * Handles map initialization, geolocation, search, and user interactions
 *
 * @class RestaurantMap
 * @property {Object} config - Configuration options
 * @property {string} config.mapContainerId - ID of the map container element
 * @property {string} [config.statusContainerId] - ID of the status container element
 * @property {string} [config.searchInputId] - ID of the search input element
 * @property {string} [config.searchButtonId] - ID of the search button element
 * @property {string} [config.radiusSliderId] - ID of the radius slider element
 * @property {string} [config.radiusValueId] - ID of the radius value display element
 * @property {string} [config.zoomInButtonId] - ID of the zoom in button
 * @property {string} [config.zoomOutButtonId] - ID of the zoom out button
 * @property {string} [config.locateMeButtonId] - ID of the locate me button
 * @property {number} [config.initialLat=40.7128] - Initial latitude
 * @property {number} [config.initialLng=-74.0060] - Initial longitude
 * @property {number} [config.initialZoom=12] - Initial zoom level
 * @property {string} [config.initialQuery=''] - Initial search query
 * @property {number} [config.defaultRadius=1000] - Default search radius in meters
 * @property {number} [config.maxRadius=50000] - Maximum search radius in meters
 */
class RestaurantMap {
    /**
     * Create a new RestaurantMap instance
     * @param {Object} options - Configuration options
     */
    constructor(options = {}) {
        // Prevent multiple instances
        if (window.restaurantMapInstance) {
            console.warn('RestaurantMap instance already exists');
            return window.restaurantMapInstance;
        }
        window.restaurantMapInstance = this;

        // Default configuration
        this.config = {
            mapContainerId: 'map',
            statusContainerId: 'map-status-container',
            searchInputId: 'search-keyword',
            searchButtonId: 'search-button',
            radiusSliderId: 'radius-slider',
            radiusValueId: 'radius-value',
            zoomInButtonId: 'zoom-in',
            zoomOutButtonId: 'zoom-out',
            locateMeButtonId: 'locate-me',
            initialLat: 40.7128,
            initialLng: -74.0060,
            initialZoom: 12,
            initialQuery: '',
            defaultRadius: 1000, // meters
            maxRadius: 50000, // 50km
            ...options
        };

        // DOM elements
        this.elements = {};

        // Map state
        this.map = null;
        this.userLocationMarker = null;
        this.markers = [];
        this.userPosition = null;
        this.searchCircle = null;
        this.markerCluster = null;
        this.locationWatchId = null;
        this.currentRequest = null;
        this.lastSearchTime = 0;
        this.searchDebounceTimer = null;
        this.isLoading = false;
        this.currentPage = 1;
        this.hasMoreResults = true;
        this.initialized = false;

        // Cache configuration
        this.cacheConfig = {
            maxSize: 50, // Maximum number of cached searches
            ttl: 30 * 60 * 1000, // 30 minutes in milliseconds
            currentSize: 0
        };
        this.resultsCache = new Map();
        this.cacheTimestamps = new Map();

        // Bind methods
        this._bindMethods();

        // Initialize when DOM is ready
        this._initWhenReady();
    }

    /**
     * Bind class methods to instance
     * @private
     */
    _bindMethods() {
        const methods = [
            'init',
            'initMap',
            'setupEventListeners',
            'handleSearch',
            'searchNearbyRestaurants',
            'displaySearchResults',
            'clearMarkers',
            'updateStatus',
            'cleanup',
            'requestLocation',
            'handleGeolocationSuccess',
            'handleGeolocationError',
            'executeSearch',
            'handleSearchError',
            'updateMapCenter',
            'addRestaurantMarker',
            'showRestaurantDetails',
            'updateStatus',
            'cleanupCache',
            '_cacheElements',
            '_initWhenReady'
        ];

        methods.forEach(method => {
            if (typeof this[method] === 'function') {
                this[method] = this[method].bind(this);
            }
        });
    }

    /**
     * Initialize when DOM is ready
     * @private
     */
    _initWhenReady() {
        if (document.readyState === 'complete' || document.readyState === 'interactive') {
            this.init();
        } else {
            document.addEventListener('DOMContentLoaded', this.init);
        }
    }

    /**
     * Cache DOM elements
     * @private
     */
    _cacheElements() {
        this.elements = {
            mapContainer: document.getElementById(this.config.mapContainerId),
            statusContainer: this.config.statusContainerId ?
                document.getElementById(this.config.statusContainerId) : null,
            searchInput: this.config.searchInputId ?
                document.getElementById(this.config.searchInputId) : null,
            searchButton: this.config.searchButtonId ?
                document.getElementById(this.config.searchButtonId) : null,
            radiusSlider: this.config.radiusSliderId ?
                document.getElementById(this.config.radiusSliderId) : null,
            radiusValue: this.config.radiusValueId ?
                document.getElementById(this.config.radiusValueId) : null,
            zoomInButton: this.config.zoomInButtonId ?
                document.getElementById(this.config.zoomInButtonId) : null,
            zoomOutButton: this.config.zoomOutButtonId ?
                document.getElementById(this.config.zoomOutButtonId) : null,
            locateMeButton: this.config.locateMeButtonId ?
                document.getElementById(this.config.locateMeButtonId) : null
        };
    }

    /**
     * Initialize the map and set up event listeners
     * @returns {boolean} True if initialization was successful, false otherwise
     */
    init() {
        try {
            // Prevent multiple initializations
            if (this.initialized) {
                console.warn('RestaurantMap.init() already called');
                return false;
            }

            // Cache DOM elements
            this.cacheElements();

            // Initialize map
            if (!this.initMap()) {
                throw new Error('Failed to initialize map');
            }

            // Set up event listeners
            this.setupEventListeners();

            // Request user location
            this.requestLocation();

            // Mark as initialized
            this.initialized = true;
            console.log('RestaurantMap initialized successfully');
            return true;

        } catch (error) {
            console.error('Error initializing RestaurantMap:', error);
            this.updateStatus('Error initializing map. Please refresh the page and try again.', 'error');
            return false;
        }
    }

    /**
     * Cache DOM elements for better performance
     */
    cacheElements() {
        this.elements = {
            resultsElement: document.getElementById('search-results'),
            radiusSlider: document.getElementById('radius-slider'),
            radiusValue: document.getElementById('radius-value'),
            searchKeywordInput: document.getElementById('search-keyword'),
            searchButton: document.getElementById('search-button'),
            zoomInBtn: document.getElementById('zoomIn'),
            zoomOutBtn: document.getElementById('zoomOut'),
            resultsCount: document.getElementById('results-count'),
            mapContainer: document.getElementById('map')
        };

        // Get CSRF token for authenticated requests
        this.csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || '';

        // Constants
        this.constants = {
            DEFAULT_ZOOM: 15,
            MIN_ZOOM: 2,
            MAX_ZOOM: 19,
            DEFAULT_RADIUS: 5000, // 5km in meters
            MAX_RADIUS: 20000,    // 20km in meters
            SEARCH_DEBOUNCE: 500,  // ms
            API_RATE_LIMIT: 1000,  // ms between API calls
            CACHE_TTL: 15 * 60 * 1000 // 15 minutes
        };

        // Unit system based on locale
        this.unitSystem = this.getUnitSystem();
    }

    /**
     * Initialize the Leaflet map
     * @returns {boolean} True if map was initialized successfully, false otherwise
     */
    initMap() {
        try {
            if (!this.elements.mapContainer) {
                throw new Error('Map container element not found');
            }

            // Check if map is already initialized in this instance
            if (this.map) {
                console.warn('Map already initialized in this instance');
                return true;
            }

            // Check if Leaflet map is already initialized on this container
            if (this.elements.mapContainer._leaflet_id) {
                console.warn('Map container already has a Leaflet instance');
                // Try to reuse the existing map instance if possible
                try {
                    this.map = L.map('map', { preferCanvas: true });
                    return true;
                } catch (e) {
                    console.error('Failed to reuse existing map instance:', e);
                    return false;
                }
            }

            this.updateStatus('Initializing map...', 'info');

            // Ensure map container has dimensions
            const mapContainer = this.elements.mapContainer;
            if (mapContainer.offsetWidth === 0 || mapContainer.offsetHeight === 0) {
                console.warn('Map container has no dimensions, setting default size');
                mapContainer.style.height = '600px';
                mapContainer.style.width = '100%';
            }

            try {
                this.map = L.map('map', {
                    center: [20, 0],
                    zoom: this.constants.DEFAULT_ZOOM,
                    zoomControl: false,
                    preferCanvas: true,
                    fadeAnimation: true,
                    zoomAnimation: true,
                    minZoom: this.constants.MIN_ZOOM,
                    maxZoom: this.constants.MAX_ZOOM,
                    tap: !L.Browser.mobile
                });

                // Add tile layer with error handling
                L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
                    maxZoom: this.constants.MAX_ZOOM,
                    minZoom: this.constants.MIN_ZOOM,
                    detectRetina: true
                }).addTo(this.map);

                // Initialize marker cluster group
                this.initMarkerCluster();

                // Add zoom controls
                L.control.zoom({
                    position: 'topright'
                }).addTo(this.map);

                // Add scale control
                L.control.scale({
                    imperial: this.unitSystem.name === 'miles',
                    metric: this.unitSystem.name === 'km',
                    maxWidth: 200,
                    updateWhenIdle: true
                }).addTo(this.map);

                // Force a resize/redraw of the map
                setTimeout(() => {
                    this.map.invalidateSize({ animate: false });
                }, 100);

                console.log('Map initialized successfully');
                return true;

            } catch (mapError) {
                console.error('Error initializing map:', mapError);
                this.updateStatus(`Failed to initialize map: ${mapError.message}`, 'error');
                return false;
            }
        } catch (error) {
            console.error('Unexpected error in map initialization:', error);
            this.updateStatus('Failed to initialize map. Please check the console for details.', 'danger');
            return false;
        }
    }

    /**
     * Initialize marker cluster group for better performance with many markers
     */
    initMarkerCluster() {
        if (this.markerCluster) {
            this.map.removeLayer(this.markerCluster);
        }

        this.markerCluster = L.markerClusterGroup({
            maxClusterRadius: 40,
            spiderfyOnMaxZoom: true,
            showCoverageOnHover: false,
            zoomToBoundsOnClick: true,
            disableClusteringAtZoom: 18,
            chunkedLoading: true,
            chunkInterval: 100,
            chunkDelay: 50,
            iconCreateFunction: this.createClusterIcon
        });

        this.map.addLayer(this.markerCluster);
    }

    /**
     * Create a custom cluster icon
     */
    createClusterIcon(cluster) {
        const count = cluster.getChildCount();
        let size = 'small';

        if (count > 50) size = 'large';
        else if (count > 10) size = 'medium';

        return L.divIcon({
            html: `<div><span>${count}</span></div>`,
            className: `marker-cluster marker-cluster-${size}`,
            iconSize: L.point(40, 40)
        });
    }

    /**
     * Update status message
     * @param {string} message - Status message
     * @param {string} type - Message type (info, success, warning, danger)
     */
    updateStatus(message, type = 'info') {
        const statusContainer = document.getElementById('map-status-container');
        if (!statusContainer) return;

        const alertClass = `alert-${type}`;
        statusContainer.innerHTML = `
            <div class="alert ${alertClass} alert-dismissible fade show" role="alert">
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            </div>`;
    }

    /**
     * Debounce function to limit rapid-fire function calls
     */
    debounce(func, wait, immediate = false) {
        let timeout;
        return function(...args) {
            const context = this;
            const later = () => {
                timeout = null;
                if (!immediate) func.apply(context, args);
            };
            const callNow = immediate && !timeout;
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
            if (callNow) func.apply(context, args);
        };
    }

    /**
     * Get the unit system based on user's locale
     * @returns {Object} Unit system configuration
     */
    getUnitSystem() {
        const lang = (navigator.language || 'en-US').toLowerCase();
        if (lang.startsWith('en')) {
            return { name: 'miles', multiplier: 0.000621371, radius_unit: 'mi' };
        }
        return { name: 'km', multiplier: 0.001, radius_unit: 'km' };
    }

    /**
     * Request the user's current location
     */
    requestLocation() {
        if (!navigator.geolocation) {
            this.updateStatus('Geolocation is not supported by your browser', 'warning');
            return;
        }

        this.updateStatus('Requesting your location...', 'info');

        navigator.geolocation.getCurrentPosition(
            (pos) => this.handleGeolocationSuccess(pos),
            (err) => this.handleGeolocationError(err),
            {
                enableHighAccuracy: true,
                timeout: 10000,
                maximumAge: 60000
            }
        );
    }

    /**
     * Handle successful geolocation
     * @param {GeolocationPosition} position - The geolocation position
     */
    handleGeolocationSuccess(position) {
        this.userPosition = {
            lat: position.coords.latitude,
            lng: position.coords.longitude,
            accuracy: position.coords.accuracy,
            timestamp: position.timestamp
        };

        this.updateStatus('Location found! Searching for nearby restaurants...', 'success');
        this.updateUserLocationMarker();
        this.adjustSearchRadius(position.coords.accuracy);
        this.setupLocationWatch();
        this.handleSearch();
    }

    /**
     * Handle geolocation error
     * @param {GeolocationPositionError} error - The geolocation error
     */
    handleGeolocationError(error) {
        let message = 'Error getting your location: ';

        switch(error.code) {
            case error.PERMISSION_DENIED:
                message += 'Please enable location services to find nearby restaurants.';
                break;
            case error.POSITION_UNAVAILABLE:
                message += 'Location information is unavailable.';
                break;
            case error.TIMEOUT:
                message += 'The request to get your location timed out.';
                break;
            default:
                message += 'An unknown error occurred.';
        }

        console.error('Geolocation error:', error);
        this.updateStatus(message, 'warning');
        this.fallbackToIPLocation();
    }

    /**
     * Fallback to IP-based geolocation if GPS fails
     */
    fallbackToIPLocation() {
        this.updateStatus('Falling back to approximate location...', 'info');

        fetch('https://ipapi.co/json/')
            .then(response => response.json())
            .then(data => {
                if (data.latitude && data.longitude) {
                    this.userPosition = {
                        lat: parseFloat(data.latitude),
                        lng: parseFloat(data.longitude),
                        accuracy: 10000, // Approximate accuracy in meters
                        isApproximate: true
                    };

                    this.updateStatus('Using approximate location. Enable GPS for better accuracy.', 'warning');
                    this.updateUserLocationMarker();
                    this.handleSearch();
                } else {
                    throw new Error('Could not determine location');
                }
            })
            .catch(error => {
                console.error('IP geolocation failed:', error);
                this.updateStatus(
                    'Could not determine your location. Please try enabling location services.',
                    'danger'
                );
            });
    }

    /**
     * Update the user location marker on the map
     */
    updateUserLocationMarker() {
        if (!this.userPosition || !this.map) return;

        const { lat, lng, accuracy, isApproximate } = this.userPosition;
        const iconClass = isApproximate ? 'approximate-location-marker' : 'user-location-marker';

        // Update or create user location marker
        if (this.userLocationMarker) {
            this.userLocationMarker.setLatLng([lat, lng]);
        } else {
            this.userLocationMarker = L.marker([lat, lng], {
                icon: L.divIcon({
                    className: iconClass,
                    iconSize: [24, 24],
                    iconAnchor: [12, 24],
                    html: isApproximate ? '<div class="approximate-marker">📍</div>' : '<div class="pulse-marker"></div>',
                    popupAnchor: [0, -24]
                }),
                zIndexOffset: 1000,
                title: isApproximate ? 'Approximate Location' : 'Your Location'
            }).addTo(this.map);

            // Add popup with accessibility attributes
            this.userLocationMarker.bindPopup(isApproximate ? 'Approximate Location' : 'Your Location', {
                className: 'location-popup',
                closeButton: false,
                autoClose: false,
                closeOnClick: false
            });

            // Center map on user location
            this.map.setView([lat, lng], this.constants.DEFAULT_ZOOM);
        }

        // Add/update accuracy circle if available
        if (accuracy) {
            if (this.accuracyCircle) {
                this.accuracyCircle.setLatLng([lat, lng]).setRadius(accuracy);
            } else {
                this.accuracyCircle = L.circle([lat, lng], {
                    radius: accuracy,
                    fillColor: isApproximate ? '#ff9800' : '#30a5ff',
                    fillOpacity: 0.2,
                    stroke: false,
                    interactive: false
                }).addTo(this.map);
            }
        }

        // Show popup if this is the first time or if location is approximate
        if (isApproximate || !this.hasShownLocationPopup) {
            this.userLocationMarker.openPopup();
            this.hasShownLocationPopup = true;
        }
    }

    /**
     * Set up continuous location watching
     */
    setupLocationWatch() {
        if (this.locationWatchId || !('geolocation' in navigator)) return;

        this.locationWatchId = navigator.geolocation.watchPosition(
            (position) => {
                this.userPosition = {
                    lat: position.coords.latitude,
                    lng: position.coords.longitude,
                    accuracy: position.coords.accuracy,
                    timestamp: position.timestamp,
                    isApproximate: false
                };
                this.updateUserLocationMarker();

                // If we were using approximate location before, do a new search
                if (this.userPosition.isApproximate) {
                    this.handleSearch();
                }
            },
            (error) => {
                console.warn('Error watching position:', error);
                // Don't show error if we're already using approximate location
                if (!this.userPosition?.isApproximate) {
                    this.handleGeolocationError(error);
                }
            },
            {
                enableHighAccuracy: true,
                maximumAge: 30000, // 30 seconds
                timeout: 10000 // 10 seconds
            }
        );
    }

    /**
     * Adjust search radius based on location accuracy
     * @param {number} accuracy - Location accuracy in meters
     */
    adjustSearchRadius(accuracy) {
        if (!accuracy || !this.elements.radiusSlider) return;

        const accuracyKm = accuracy / 1000; // Convert to km
        const suggestedRadius = Math.max(0.5, Math.ceil(accuracyKm * 2) * 1000); // At least 500m, or 2x accuracy
        const maxRadius = this.constants.MAX_RADIUS;

        this.elements.radiusSlider.value = Math.min(suggestedRadius, maxRadius);
        this.elements.radiusValue.textContent =
            `${this.elements.radiusSlider.value} ${this.unitSystem.radius_unit}`;
    }

    /**
     * Handle search with debouncing, rate limiting, and caching
     */
    handleSearch() {
        // Don't start a new search if one is already in progress
        if (this.isLoading) {
            console.log('Search already in progress');
            return;
        }

        // Clear any pending searches
        if (this.searchDebounceTimer) {
            clearTimeout(this.searchDebounceTimer);
        }

        // Get current search parameters
        const params = this.getCurrentSearchParams();
        const cacheKey = this.generateCacheKey(params);

        // Check cache first
        const cachedResults = this.getCachedResults(cacheKey);
        if (cachedResults) {
            console.log('Using cached results for key:', cacheKey);
            this.displaySearchResults(cachedResults, this.userPosition);
            this.updateStatus(`Showing ${cachedResults.length} restaurants (cached)`, 'info');
            return;
        }

        // Rate limit API calls
        const now = Date.now();
        const timeSinceLastSearch = now - this.lastSearchTime;
        const minTimeBetweenSearches = this.constants.API_RATE_LIMIT;

        const executeSearch = () => {
            this.searchDebounceTimer = null;
            this.searchNearbyRestaurants();
        };

        if (timeSinceLastSearch < minTimeBetweenSearches) {
            // If we've searched recently, schedule the next one
            this.searchDebounceTimer = setTimeout(executeSearch, minTimeBetweenSearches - timeSinceLastSearch);
        } else {
            // Otherwise, search immediately
            executeSearch();
        }
    }

    /**
     * Get current search parameters from UI
     * @returns {Object} Search parameters
     */
    getCurrentSearchParams() {
        if (!this.userPosition) {
            return null;
        }

        // Get radius from slider or use default, ensure it's a number
        let radius = this.elements.radiusSlider ?
            parseInt(this.elements.radiusSlider.value, 10) :
            this.constants.DEFAULT_RADIUS;

        // Ensure radius is within valid range (1-50000 meters)
        // If radius is in kilometers (common for UI), convert to meters
        const isLikelyInKm = radius < 100; // Assume values < 100 are in km
        if (isLikelyInKm) {
            radius = radius * 1000; // Convert km to meters
        }

        // Clamp the radius between 100m and 50km (100-50000m)
        radius = Math.max(100, Math.min(radius, 50000));

        const keyword = this.elements.searchKeywordInput ?
            this.elements.searchKeywordInput.value.trim() : '';

        console.log('Search params:', {
            lat: this.userPosition.lat,
            lng: this.userPosition.lng,
            radius: radius,
            keyword: keyword
        });

        return {
            lat: this.userPosition.lat,
            lng: this.userPosition.lng,
            radius: Math.round(radius), // Ensure integer value
            keyword: keyword
        };
    }

    /**
     * Search for restaurants near the user's location
     */
    async searchNearbyRestaurants() {
        if (!this.userPosition) {
            this.updateStatus('Could not search for restaurants without your location.', 'warning');
            return;
        }

        // Cancel any in-progress request
        if (this.currentRequest) {
            this.currentRequest.abort();
            this.currentRequest = null;
        }

        // Show loading state
        this.updateStatus('Searching for restaurants...', 'info');
        this.isLoading = true;

        // Get search parameters
        const params = this.getCurrentSearchParams();
        if (!params) {
            this.isLoading = false;
            return;
        }

        try {
            const { lat, lng, radius, keyword } = params;

            // Update search area on map
            this.updateSearchArea(
                [lat, lng],
                Math.min(radius, this.constants.MAX_RADIUS)
            );

            // Build query parameters
            const queryParams = new URLSearchParams({
                lat: lat,
                lng: lng,
                radius: Math.min(radius, this.constants.MAX_RADIUS)
            });

            if (keyword) {
                queryParams.append('keyword', keyword);
            }

            // Add cache buster for GET requests
            queryParams.append('_', Date.now());

            // Generate cache key
            const cacheKey = this.generateCacheKey(params);

            // Check cache first (skip cache for keyword searches or if disabled)
            const useCache = !keyword && this.cacheConfig.enabled !== false;
            if (useCache) {
                const cachedResults = this.getCachedResults(cacheKey);
                if (cachedResults) {
                    this.displaySearchResults(cachedResults, this.userPosition);
                    this.updateStatus(
                        `Found ${cachedResults.length} restaurants (cached)`,
                        'info'
                    );
                    this.isLoading = false;
                    return;
                }
            }

            // Show loading skeleton
            this.showLoadingSkeleton();

            // Make API request with timeout
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 15000); // 15 second timeout

            this.currentRequest = controller;
            this.lastSearchTime = Date.now();

            // Log the request (without sensitive data)
            const safeParams = new URLSearchParams(queryParams);
            safeParams.delete('key');
            console.log(`API Request: /restaurants/api/places/search?${safeParams.toString()}`);

            const response = await fetch(`/restaurants/api/places/search?${queryParams.toString()}`, {
                method: 'GET',
                headers: {
                    'Accept': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRF-TOKEN': this.csrfToken,
                    'Cache-Control': 'no-cache',
                    'Pragma': 'no-cache'
                },
                signal: controller.signal,
                cache: 'no-store'
            });

            clearTimeout(timeoutId);

            const contentType = response.headers.get('content-type');
            let data;

            try {
                data = contentType?.includes('application/json')
                    ? await response.json()
                    : { error: 'Invalid response format' };
            } catch (e) {
                console.error('Error parsing JSON response:', e);
                throw new Error('Failed to parse server response');
            }

            if (!response.ok) {
                const errorMsg = data?.error || `HTTP error! status: ${response.status}`;
                const error = new Error(errorMsg);
                error.status = response.status;
                error.details = data?.details;
                throw error;
            }

            if (data.error) {
                const error = new Error(data.error);
                error.details = data.details;
                throw error;
            }

            const results = data.results || [];

            // Cache the results if this wasn't a keyword search
            if (!keyword) {
                this.cacheResults(results, cacheKey);
            }

            // Display results
            this.displaySearchResults(results, this.userPosition);
            const resultCount = results.length;

            if (resultCount === 0) {
                this.updateStatus(
                    'No restaurants found. Try adjusting your search area or criteria.',
                    'info'
                );
            } else {
                this.updateStatus(
                    `Found ${resultCount} ${resultCount === 1 ? 'restaurant' : 'restaurants'}`,
                    'success'
                );
            }

        } catch (error) {
            if (error.name === 'AbortError') {
                console.log('Search was aborted');
                return;
            }

            console.error('Error searching for restaurants:', error);
            this.handleSearchError(error);

        } finally {
            this.currentRequest = null;
            this.isLoading = false;
        }
    }

    /**
     * Handle search errors and display appropriate messages
     * @param {Error} error - The error that occurred
     */
    handleSearchError(error) {
        console.error('Search error:', error);

        let errorMessage = 'An error occurred while searching for restaurants.';
        let errorType = 'danger';
        let showRetry = true;
        let details = '';

        // Handle different types of errors
        if (error.name === 'AbortError') {
            // User navigated away or request was cancelled
            return;
        } else if (error.message.includes('NetworkError') || error.message.includes('Failed to fetch')) {
            errorMessage = 'Network error. Please check your internet connection.';
            errorType = 'warning';
        } else if (error.message.includes('timeout') || error.message.includes('abort')) {
            errorMessage = 'The request took too long. Please try again.';
            errorType = 'warning';
        } else if (error.status === 403) {
            errorMessage = 'Access denied. Please log in again.';
            errorType = 'warning';
            showRetry = false;
        } else if (error.status === 429) {
            errorMessage = 'Too many requests. Please wait before trying again.';
            errorType = 'warning';
        } else if (error.status >= 500) {
            errorMessage = 'Server error. Our team has been notified.';
            errorType = 'danger';
        } else if (error.message.includes('ZERO_RESULTS')) {
            errorMessage = 'No restaurants found in this area. Try adjusting your search radius.';
            errorType = 'info';
            showRetry = false;
        } else if (error.message.includes('OVER_QUERY_LIMIT')) {
            errorMessage = 'Search quota exceeded. Please try again later.';
            errorType = 'warning';
        } else if (error.message.includes('REQUEST_DENIED') || error.message.includes('API key')) {
            errorMessage = 'Search service is currently unavailable. Please try again later.';
            errorType = 'danger';
            showRetry = false;
        } else if (error.message.includes('INVALID_REQUEST')) {
            errorMessage = 'Invalid search request. Please try different parameters.';
            errorType = 'warning';
        } else if (error.message.includes('UNKNOWN_ERROR')) {
            errorMessage = 'Temporary service issue. Please try again in a moment.';
            errorType = 'warning';
        }

        // Add details if available
        if (error.details) {
            details = `<div class="mt-2 small text-muted">${error.details}</div>`;
        }

        // Update status and show error in UI
        this.updateStatus(errorMessage, errorType);

        // Show error in results container
        if (this.elements.resultsElement) {
            this.elements.resultsElement.innerHTML = `
                <div class="alert alert-${errorType} mb-3">
                    <div class="d-flex align-items-center">
                        <i class="fas ${errorType === 'danger' ? 'fa-exclamation-circle' : 'fa-info-circle'} me-2"></i>
                        <span>${errorMessage}</span>
                    </div>
                    ${details}
                    ${showRetry ? `
                    <div class="mt-2">
                        <button class="btn btn-sm btn-${errorType === 'danger' ? 'outline-' : ''}${errorType}"
                                onclick="window.restaurantMap.handleSearch()">
                            <i class="fas fa-sync-alt me-1"></i> Try Again
                        </button>
                    </div>` : ''}
                </div>`;
        }

        // Clear loading state
        this.isLoading = false;
    }

    /**
     * Update the search area circle on the map
     * @param {Array} latlng - Array of [lat, lng] coordinates
     * @param {number} radius - Radius in meters
     */
    updateSearchArea(latlng, radius) {
        if (!this.map) return;

        // Remove existing search area circle if it exists
        if (this.searchAreaCircle) {
            this.map.removeLayer(this.searchAreaCircle);
        }

        // Create or update the search area circle
        this.searchAreaCircle = L.circle(latlng, {
            radius: radius,
            color: '#4285F4',
            weight: 2,
            fillColor: '#4285F4',
            fillOpacity: 0.1,
            interactive: false
        }).addTo(this.map);

        // If this is the first time, fit the map to show the search area
        if (!this.hasInitialFit) {
            this.map.fitBounds(this.searchAreaCircle.getBounds(), {
                padding: [50, 50],
                maxZoom: 14
            });
            this.hasInitialFit = true;
        }
    }

    /**
     * Display loading skeleton in the results container
     */
    showLoadingSkeleton() {
        if (!this.elements.resultsElement) return;

        // Create skeleton items
        const skeletonItems = Array(5).fill(`
            <div class="result-item skeleton-loading">
                <div class="skeleton-image"></div>
                <div class="skeleton-content">
                    <div class="skeleton-line w-75"></div>
                    <div class="skeleton-line w-50"></div>
                    <div class="skeleton-line w-25"></div>
                </div>
            </div>`).join('');

        this.elements.resultsElement.innerHTML = `
            <div class="skeleton-container">
                ${skeletonItems}
            </div>`;
    }

    /**
     * Display search results in the sidebar and on the map
     * @param {Array} results - Array of restaurant objects
     * @param {Object} userPosition - User's current position {lat, lng}
     */
    displaySearchResults(results, userPosition) {
        if (!results || !Array.isArray(results)) {
            console.error('Invalid results format:', results);
            return;
        }

        // Clear previous results and markers
        this.clearMarkers();

        // Sort by distance if we have user position
        const sortedResults = [...results];
        if (userPosition) {
            sortedResults.sort((a, b) => {
                const distA = this.calculateDistance(
                    userPosition.lat,
                    userPosition.lng,
                    a.geometry?.location?.lat || 0,
                    a.geometry?.location?.lng || 0
                );
                const distB = this.calculateDistance(
                    userPosition.lat,
                    userPosition.lng,
                    b.geometry?.location?.lat || 0,
                    b.geometry?.location?.lng || 0
                );
                return distA - distB;
            });
        }

        // Update results count
        if (this.elements.resultsCount) {
            this.elements.resultsCount.textContent = `${sortedResults.length} ${sortedResults.length === 1 ? 'result' : 'results'}`;
        }

        // Generate HTML for results
        const resultsHTML = this.generateResultsHTML(sortedResults, userPosition);

        // Update the DOM
        if (this.elements.resultsElement) {
            this.elements.resultsElement.innerHTML = resultsHTML;

            // Add event listeners to result items
            this.setupResultItemListeners();

            // Scroll to top of results
            this.elements.resultsElement.scrollTop = 0;
        }

        // Add markers to the map
        this.addMarkers(sortedResults, userPosition);

        // If we have markers, fit the map to show all of them
        if (this.markers.length > 0) {
            const group = new L.featureGroup(this.markers);
            this.map.fitBounds(group.getBounds().pad(0.1), {
                maxZoom: 14
            });
        }
    }

    /**
     * Generate HTML for the search results
     * @param {Array} results - Array of restaurant objects
     * @param {Object} userPosition - User's current position {lat, lng}
     * @returns {string} HTML string
     */
    generateResultsHTML(results, userPosition) {
        if (!results || results.length === 0) {
            return `
                <div class="text-center py-5">
                    <i class="fas fa-utensils fa-3x mb-3 text-muted"></i>
                    <p class="text-muted">No restaurants found. Try adjusting your search criteria.</p>
                </div>`;
        }

        return results.map((place, index) => {
            const placeId = place.place_id || `place-${index}`;
            const name = place.name || 'Unnamed Restaurant';
            const address = place.vicinity || place.formatted_address || 'Address not available';
            const rating = place.rating !== undefined ? place.rating : 'N/A';
            const priceLevel = place.price_level !== undefined ? '\u0024'.repeat(place.price_level) : 'N/A';
            const isOpen = place.opening_hours?.open_now;
            const photo = place.photos?.[0]?.photo_reference;
            const photoUrl = photo ? `/api/places/photo?photo_reference=${photo}&maxwidth=400` : '';

            // Calculate distance if we have user position
            let distance = '';
            if (userPosition && place.geometry?.location) {
                const dist = this.calculateDistance(
                    userPosition.lat,
                    userPosition.lng,
                    place.geometry.location.lat,
                    place.geometry.location.lng
                );
                distance = `• ${this.formatDistance(dist)}`;
            }

            // Generate rating stars
            const ratingStars = this.generateRatingStars(rating);

            return `
                <div class="result-item" data-place-id="${placeId}" role="button" tabindex="0">
                    <div class="result-image" style="background-image: url('${photoUrl}')">
                        ${!photo && '<i class="fas fa-utensils"></i>'}
                    </div>
                    <div class="result-content">
                        <h3 class="result-title">${this.escapeHtml(name)}</h3>
                        <div class="result-meta">
                            <span class="rating">${ratingStars} ${rating !== 'N/A' ? rating : ''}</span>
                            ${distance ? `<span class="distance">${distance}</span>` : ''}
                        </div>
                        <p class="result-address">${this.escapeHtml(address)}</p>
                        <div class="result-footer">
                            <span class="price-level">${priceLevel}</span>
                            <span class="status ${isOpen ? 'open' : 'closed'}">
                                ${isOpen ? 'Open Now' : 'Closed'}
                            </span>
                        </div>
                    </div>
                    <button class="btn btn-sm btn-outline-primary add-button"
                            data-place-id="${placeId}"
                            aria-label="Add ${this.escapeHtml(name)} to your list">
                        <i class="fas fa-plus"></i> Add
                    </button>
                </div>`;
        }).join('');
    }

    /**
     * Generate HTML for rating stars
     * @param {number|string} rating - The rating value (0-5)
     * @returns {string} HTML string with star icons
     */
    generateRatingStars(rating) {
        if (rating === 'N/A' || rating === undefined) return '';

        const fullStars = Math.floor(rating);
        const hasHalfStar = rating % 1 >= 0.5;
        const emptyStars = 5 - fullStars - (hasHalfStar ? 1 : 0);

        let stars = '';

        // Full stars
        stars += '<span class="stars">';
        stars += '<i class="fas fa-star"></i>'.repeat(fullStars);

        // Half star
        if (hasHalfStar) {
            stars += '<i class="fas fa-star-half-alt"></i>';
        }

        // Empty stars
        stars += '<i class="far fa-star"></i>'.repeat(emptyStars);
        stars += '</span>';

        return stars;
    }

    /**
     * Add markers to the map for each restaurant
     * @param {Array} results - Array of restaurant objects
     * @param {Object} userPosition - User's current position {lat, lng}
     */
    addMarkers(results, userPosition) {
        if (!this.map || !results || !Array.isArray(results)) return;

        results.forEach((place, index) => {
            if (!place.geometry?.location) return;

            const placeId = place.place_id || `place-${index}`;
            const position = place.geometry.location;
            const name = place.name || 'Unnamed Restaurant';
            const rating = place.rating !== undefined ? place.rating : null;
            const isOpen = place.opening_hours?.open_now;

            // Calculate distance if we have user position
            let distance = '';
            if (userPosition) {
                const dist = this.calculateDistance(
                    userPosition.lat,
                    userPosition.lng,
                    position.lat,
                    position.lng
                );
                distance = `${this.formatDistance(dist)} away`;
            }

            // Create popup content
            const popupContent = `
                <div class="map-popup">
                    <h5 class="popup-title">${this.escapeHtml(name)}</h5>
                    ${rating !== null ? `
                        <div class="popup-rating">
                            ${this.generateRatingStars(rating)}
                            <span class="ms-1">${rating}</span>
                        </div>` : ''
                    }
                    ${distance ? `<div class="popup-distance"><i class="fas fa-walking me-1"></i>${distance}</div>` : ''}
                    <div class="popup-status ${isOpen ? 'open' : 'closed'}">
                        ${isOpen ? 'Open Now' : 'Closed'}
                    </div>
                    <div class="popup-actions mt-2">
                        <button class="btn btn-sm btn-primary w-100 add-to-list"
                                data-place-id="${placeId}">
                            <i class="fas fa-plus me-1"></i> Add to List
                        </button>
                    </div>
                </div>`;

            // Create marker
            const marker = L.marker([position.lat, position.lng], {
                title: name,
                alt: name,
                riseOnHover: true,
                icon: L.divIcon({
                    className: 'restaurant-marker',
                    html: '<i class="fas fa-utensils"></i>',
                    iconSize: [32, 32],
                    iconAnchor: [16, 32],
                    popupAnchor: [0, -32]
                })
            });

            // Bind popup
            marker.bindPopup(popupContent, {
                maxWidth: 240,
                minWidth: 200,
                className: 'restaurant-popup',
                closeButton: false,
                autoClose: false,
                closeOnClick: false
            });

            // Store reference to marker with place ID
            marker.placeId = placeId;

            // Add to markers array and cluster group
            this.markers.push(marker);
            this.markerCluster.addLayer(marker);

            // Add to markers map for quick lookup
            this.markersMap[placeId] = marker;

            // Add click event to open popup when clicking on result item
            const resultItem = document.querySelector(`.result-item[data-place-id="${placeId}"]`);
            if (resultItem) {
                resultItem.addEventListener('click', () => {
                    this.highlightMarker(placeId);
                });
            }
        });
    }

    /**
     * Clear all markers from the map
     */
    clearMarkers() {
        if (this.markerCluster) {
            this.markerCluster.clearLayers();
        }

        this.markers = [];
        this.markersMap = {};

        // Clear any highlighted markers
        if (this.highlightedMarker) {
            const icon = this.highlightedMarker.getIcon();
            if (icon.options.className.includes('highlighted')) {
                icon.options.className = icon.options.className.replace(' highlighted', '');
                this.highlightedMarker.setIcon(icon);
            }
            this.highlightedMarker = null;
        }
    }

    /**
     * Highlight a specific marker by place ID
     * @param {string} placeId - The place ID to highlight
     */
    highlightMarker(placeId) {
        // Remove highlight from previously highlighted marker
        if (this.highlightedMarker) {
            const prevIcon = this.highlightedMarker.getIcon();
            if (prevIcon.options.className.includes('highlighted')) {
                prevIcon.options.className = prevIcon.options.className.replace(' highlighted', '');
                this.highlightedMarker.setIcon(prevIcon);
            }
        }

        // Find and highlight the new marker
        const marker = this.markersMap[placeId];
        if (marker) {
            const icon = marker.getIcon();
            icon.options.className += ' highlighted';
            marker.setIcon(icon);

            // Open popup and pan to marker
            marker.openPopup();
            this.map.panTo(marker.getLatLng(), {
                animate: true,
                duration: 0.5,
                easeLinearity: 0.25,
                noMoveStart: true
            });

            // Highlight the corresponding result item
            this.highlightResultItem(placeId);

            this.highlightedMarker = marker;
        }
    }

    /**
     * Highlight a result item in the sidebar
     * @param {string} placeId - The place ID to highlight
     */
    highlightResultItem(placeId) {
        // Remove highlight from all result items
        document.querySelectorAll('.result-item').forEach(item => {
            item.classList.remove('active');
        });

        // Add highlight to the selected item
        const resultItem = document.querySelector(`.result-item[data-place-id="${placeId}"]`);
        if (resultItem) {
            resultItem.classList.add('active');

            // Scroll into view if not fully visible
            const container = this.elements.resultsElement;
            const itemRect = resultItem.getBoundingClientRect();
            const containerRect = container.getBoundingClientRect();

            if (itemRect.bottom > containerRect.bottom || itemRect.top < containerRect.top) {
                resultItem.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            }
        }
    }

    /**
     * Set up event listeners for result items
     */
    setupResultItemListeners() {
        if (!this.elements.resultsElement) return;

        // Handle click on result item
        this.elements.resultsElement.addEventListener('click', (e) => {
            const resultItem = e.target.closest('.result-item');
            const addButton = e.target.closest('.add-button');

            if (resultItem && !addButton) {
                const placeId = resultItem.dataset.placeId;
                if (placeId) {
                    this.highlightMarker(placeId);
                }
            }
        });

        // Handle keyboard navigation on result items
        this.elements.resultsElement.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                const resultItem = e.target.closest('.result-item');
                if (resultItem) {
                    resultItem.click();
                }
            }
        });

        // Handle add to list button clicks
        this.elements.resultsElement.addEventListener('click', (e) => {
            const addButton = e.target.closest('.add-button');
            if (addButton) {
                e.stopPropagation();
                const placeId = addButton.dataset.placeId;
                if (placeId) {
                    this.handleAddToList(placeId);
                }
            }
        });
    }

    /**
     * Handle adding a restaurant to the user's list
     * @param {string} placeId - The place ID to add
     */
    handleAddToList(placeId) {
        if (!placeId) return;

        console.log(`Adding place ${placeId} to list`);
        // TODO: Implement actual add to list functionality
        // This would typically make an API call to your backend

        // Show success message
        this.updateStatus('Restaurant added to your list!', 'success');

        // Update UI to show it's been added
        const addButton = document.querySelector(`.add-button[data-place-id="${placeId}"]`);
        if (addButton) {
            addButton.disabled = true;
            addButton.innerHTML = '<i class="fas fa-check"></i> Added';
            addButton.classList.remove('btn-outline-primary');
            addButton.classList.add('btn-success');
        }
    }

    /**
     * Calculate distance between two points in meters
     * @param {number} lat1 - Start latitude
     * @param {number} lon1 - Start longitude
     * @param {number} lat2 - End latitude
     * @param {number} lon2 - End longitude
     * @returns {number} Distance in meters
     */
    calculateDistance(lat1, lon1, lat2, lon2) {
        const R = 6371e3; // Earth radius in meters
        const φ1 = lat1 * Math.PI / 180;
        const φ2 = lat2 * Math.PI / 180;
        const Δφ = (lat2 - lat1) * Math.PI / 180;
        const Δλ = (lon2 - lon1) * Math.PI / 180;

        const a = Math.sin(Δφ/2) * Math.sin(Δφ/2) +
                  Math.cos(φ1) * Math.cos(φ2) *
                  Math.sin(Δλ/2) * Math.sin(Δλ/2);
        const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));

        return R * c;
    }

    /**
     * Escape HTML to prevent XSS
     * @param {string} str - String to escape
     * @returns {string} Escaped string
     */
    escapeHtml(str) {
        if (!str) return '';
        return str.toString()
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    /**
     * Generate a cache key based on search parameters
     * @param {Object} params - Search parameters
     * @returns {string} Cache key
     */
    generateCacheKey(params) {
        if (!params) return 'default';

        // Create a stable string representation of the parameters
        const keyParts = [
            params.lat ? Math.round(params.lat * 10000) / 10000 : '0',
            params.lng ? Math.round(params.lng * 10000) / 10000 : '0',
            params.radius || '0',
            params.keyword || '',
            params.page || '1'
        ];

        return keyParts.join('|');
    }

    /**
     * Get cached results if they exist and are fresh
     * @param {string} cacheKey - The cache key
     * @returns {Array|null} Cached results or null if not found or expired
     */
    getCachedResults(cacheKey) {
        if (!this.resultsCache.has(cacheKey)) {
            return null;
        }

        const timestamp = this.cacheTimestamps.get(cacheKey);
        const now = Date.now();

        // Check if cache entry is expired
        if (now - timestamp > this.cacheConfig.ttl) {
            this.resultsCache.delete(cacheKey);
            this.cacheTimestamps.delete(cacheKey);
            this.cacheConfig.currentSize--;
            return null;
        }

        return JSON.parse(JSON.stringify(this.resultsCache.get(cacheKey))); // Return a deep copy
    }

    /**
     * Cache the search results
     * @param {string} cacheKey - The cache key
     * @param {Array} results - The results to cache
     */
    cacheResults(cacheKey, results) {
        // Clean up old cache if we've reached max size
        if (this.cacheConfig.currentSize >= this.cacheConfig.maxSize) {
            this.cleanupCache(true); // Force cleanup
        }

        // Store the results with current timestamp
        this.resultsCache.set(cacheKey, JSON.parse(JSON.stringify(results))); // Store a deep copy
        this.cacheTimestamps.set(cacheKey, Date.now());
        this.cacheConfig.currentSize++;
    }

    /**
     * Clean up expired cache entries
     * @param {boolean} force - If true, remove oldest entries even if not expired
     */
    cleanupCache(force = false) {
        const now = Date.now();
        const entriesToRemove = [];

        // Find expired entries
        for (const [key, timestamp] of this.cacheTimestamps.entries()) {
            if (force || (now - timestamp > this.cacheConfig.ttl)) {
                entriesToRemove.push(key);
            }
        }

        // Remove entries
        entriesToRemove.forEach(key => {
            this.resultsCache.delete(key);
            this.cacheTimestamps.delete(key);
            this.cacheConfig.currentSize--;
        });

        // If still over limit after removing expired, remove oldest entries
        if (this.cacheConfig.currentSize > this.cacheConfig.maxSize) {
            const sortedByTimestamp = Array.from(this.cacheTimestamps.entries())
                .sort((a, b) => a[1] - b[1])
                .slice(0, this.cacheConfig.currentSize - this.cacheConfig.maxSize);

            sortedByTimestamp.forEach(([key]) => {
                this.resultsCache.delete(key);
                this.cacheTimestamps.delete(key);
                this.cacheConfig.currentSize--;
            });
        }
    }

    /**
     * Set up all event listeners
     */
    setupEventListeners() {
        // Search button click
        if (this.elements.searchButton) {
            this.elements.searchButton.addEventListener('click', () => {
                this.handleSearch();
            });
        }

        // Search input keyup with debounce
        if (this.elements.searchKeywordInput) {
            const debouncedSearch = this.debounce(() => {
                this.handleSearch();
            }, this.constants.SEARCH_DEBOUNCE);

            this.elements.searchKeywordInput.addEventListener('keyup', (e) => {
                if (e.key === 'Enter') {
                    this.handleSearch();
                } else {
                    debouncedSearch();
                }
            });
        }

        // Radius slider change
        if (this.elements.radiusSlider) {
            this.elements.radiusSlider.addEventListener('input', (e) => {
                if (this.elements.radiusValue) {
                    this.elements.radiusValue.textContent =
                        `${e.target.value} ${this.unitSystem.radius_unit}`;
                }
            });

            // Update search when user stops sliding
            this.elements.radiusSlider.addEventListener('change', () => {
                this.handleSearch();
            });
        }

        // Map move/zoom events with debounce
        if (this.map) {
            const debouncedMoveEnd = this.debounce(() => {
                if (this.userPosition && this.searchAreaCircle) {
                    const center = this.map.getCenter();
                    const radius = this.searchAreaCircle.getRadius();
                    this.updateSearchArea([center.lat, center.lng], radius);
                }
            }, 500);

            this.map.on('moveend', debouncedMoveEnd);
            this.map.on('zoomend', debouncedMoveEnd);
        }

        // Window resize handler
        window.addEventListener('resize', this.debounce(() => {
            if (this.map) {
                this.map.invalidateSize();
            }
        }, 250));

        // Handle popup events for add to list buttons inside popups
        this.map.on('popupopen', (e) => {
            const popup = e.popup;
            const popupElement = popup.getElement();

            // Add click handler for add to list button in popup
            const addButton = popupElement?.querySelector('.add-to-list');
            if (addButton) {
                addButton.addEventListener('click', (e) => {
                    e.stopPropagation();
                    const placeId = addButton.dataset.placeId;
                    if (placeId) {
                        this.handleAddToList(placeId);
                    }
                });
            }
        });
    }

    /**
     * Clean up event listeners and map resources
     */
    cleanup() {
        // Stop watching position
        if (this.locationWatchId && navigator.geolocation) {
            navigator.geolocation.clearWatch(this.locationWatchId);
            this.locationWatchId = null;
        }

        // Cancel any pending requests
        if (this.currentRequest) {
            this.currentRequest.abort();
            this.currentRequest = null;
        }

        // Clear any timeouts
        if (this.searchDebounceTimer) {
            clearTimeout(this.searchDebounceTimer);
            this.searchDebounceTimer = null;
        }

        // Remove map
        if (this.map) {
            this.map.off();
            this.map.remove();
            this.map = null;
        }

        // Clear references to DOM elements
        this.elements = {};

        // Clear markers
        this.clearMarkers();

        // Clear other properties
        this.userPosition = null;
        this.markers = [];
        this.markersMap = {};
        this.highlightedMarker = null;
        this.searchAreaCircle = null;
        this.accuracyCircle = null;
        this.userLocationMarker = null;
        this.markerCluster = null;
        this.hasInitialFit = false;
        this.isLoading = false;
        this.lastSearchTime = 0;
    }

    /**
     * Initialize the restaurant map
     */
    init() {
        try {
            // Cache DOM elements
            this.cacheElements();

            // Initialize the map
            this.initMap();

            // Set up event listeners
            this.setupEventListeners();

            // Request user's location
            this.requestLocation();

            // Add cleanup on page unload
            window.addEventListener('beforeunload', () => this.cleanup());

            console.log('RestaurantMap initialized successfully');

        } catch (error) {
            console.error('Error initializing RestaurantMap:', error);
            this.updateStatus('Failed to initialize the map. Please refresh the page.', 'danger');
        }
    }
}

// Initialize the restaurant map
function initRestaurantMap() {
    try {
        // Only initialize if not already initialized and the map container exists
        const mapContainer = document.getElementById('map');
        if (!mapContainer) {
            console.error('Map container not found');
            return;
        }

        if (window.restaurantMap) {
            console.warn('RestaurantMap already initialized');
            return;
        }

        // Set minimum dimensions for the map container if not set
        if (!mapContainer.style.minHeight) {
            mapContainer.style.minHeight = '500px';
        }
        if (!mapContainer.style.minWidth) {
            mapContainer.style.minWidth = '100%';
        }

        // Initialize the map
        window.restaurantMap = new RestaurantMap();
        window.restaurantMap.init();

        // Handle window resize
        const handleResize = () => {
            if (window.restaurantMap && window.restaurantMap.map) {
                window.restaurantMap.map.invalidateSize();
            }
        };
        window.addEventListener('resize', handleResize);

        // Clean up event listener on unload
        window.addEventListener('beforeunload', () => {
            window.removeEventListener('resize', handleResize);
            if (window.restaurantMap) {
                window.restaurantMap.cleanup();
                window.restaurantMap = null;
            }
        });

    } catch (error) {
        console.error('Failed to initialize RestaurantMap:', error);
        const statusContainer = document.getElementById('map-status-container');
        if (statusContainer) {
            statusContainer.innerHTML = `
                <div class="alert alert-danger alert-dismissible fade show" role="alert">
                    Failed to initialize map: ${error.message}
                    <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                </div>`;
        }
    }
}

// Export the RestaurantMap class as default
export default RestaurantMap;

// Initialize when the Google Maps API is ready
if (window.google && window.google.maps) {
    initRestaurantMap();
} else {
    // Fallback in case the callback doesn't work
    window.initGoogleMaps = initRestaurantMap;
}
