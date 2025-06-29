/**
 * Restaurant Search Page
 * Handles the restaurant search functionality and map initialization
 */

// Import dependencies
import { loadGoogleMapsAPI } from '../services/google-maps.service.js';
import { initSearchForm } from './search-init.js';

// Constants
const DEFAULT_LOCATION = { lat: 40.7128, lng: -74.0060 }; // New York
const DEFAULT_ZOOM = 12;

// DOM Elements
let mapContainer;
let searchForm;
let searchInput;
let searchButton;
let currentLocationBtn;

// Google Maps instances
let map;
let placesService;
let markers = [];
let userLocationMarker = null;
let currentInfoWindow = null;

/**
 * Show error message
 * @param {string} message - Error message to display
 * @param {string} [containerId='search-status'] - Container ID for the message
 */
const showError = (message, containerId = 'search-status') => {
    const container = document.getElementById(containerId);
    if (container) {
        container.innerHTML = `
            <div class="alert alert-danger alert-dismissible fade show" role="alert">
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            </div>`;
    }
    console.error('Error:', message);
};

/**
 * Show success message
 * @param {string} message - Success message to display
 * @param {string} [containerId='search-status'] - Container ID for the message
 */
const showSuccess = (message, containerId = 'search-status') => {
    const container = document.getElementById(containerId);
    if (container) {
        container.innerHTML = `
            <div class="alert alert-success alert-dismissible fade show" role="alert">
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            </div>`;
    }
    console.log('Success:', message);
};

/**
 * Show loading state
 * @param {boolean} isLoading - Whether to show or hide loading state
 */
const setLoading = (isLoading) => {
    if (!searchButton) return;

    if (isLoading) {
        searchButton.disabled = true;
        searchButton.innerHTML = `
            <span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
            Searching...
        `;
    } else {
        searchButton.disabled = false;
        searchButton.innerHTML = 'Search';
    }
};

/**
 * Clear all markers from the map
 */
const clearMarkers = () => {
    markers.forEach(marker => marker.setMap(null));
    markers = [];
};

/**
 * Add a marker to the map
 * @param {Object} options - Marker options
 * @param {Object} options.position - Marker position { lat, lng }
 * @param {string} options.title - Marker title
 * @param {Object} [options.icon] - Custom icon
 * @param {string} [options.content] - Info window content
 * @returns {google.maps.Marker} - The created marker
 */
const addMarker = ({ position, title, icon, content }) => {
    const marker = new google.maps.Marker({
        position,
        map,
        title,
        icon,
        animation: google.maps.Animation.DROP
    });

    if (content) {
        const infoWindow = new google.maps.InfoWindow({ content });

        marker.addListener('click', () => {
            // Close any open info windows
            if (currentInfoWindow) {
                currentInfoWindow.close();
            }

            // Open new info window
            infoWindow.open(map, marker);
            currentInfoWindow = infoWindow;
        });
    }

    markers.push(marker);
    return marker;
};

/**
 * Search for restaurants using Google Places API
 * @param {string} query - Search query
 */
const searchRestaurants = async (query) => {
    if (!query || !query.trim()) {
        showError('Please enter a search term');
        return;
    }

    try {
        setLoading(true);
        clearMarkers();

        // Check if Google Maps is loaded
        if (!window.google || !window.google.maps || !window.google.maps.places) {
            throw new Error('Google Maps API is not properly loaded');
        }

        // Get current map center or use default location if map is not initialized
        let location = null;
        if (map) {
            location = map.getCenter();
        } else {
            // Default to New York if map is not initialized
            location = new google.maps.LatLng(40.7128, -74.0060);
            console.warn('Map not initialized, using default location');
        }

        // Create a new request object for the Places API text search
        const request = {
            query: query,
            fields: ['name', 'geometry', 'formatted_address', 'place_id', 'photos', 'rating', 'user_ratings_total', 'types'],
            location: location,
            radius: 10000 // 10km radius
        };

        // Use the Places API text search
        const placesService = new google.maps.places.PlacesService(map);

        // Perform the search
        const results = await new Promise((resolve, reject) => {
            placesService.textSearch(request, (results, status) => {
                if (status === google.maps.places.PlacesServiceStatus.OK) {
                    resolve(results || []);
                } else if (status === google.maps.places.PlacesServiceStatus.ZERO_RESULTS) {
                    resolve([]); // Return empty array for no results
                } else {
                    reject(new Error(`Places service error: ${status}`));
                }
            });
        });

        // Process results
        if (results && results.length > 0) {
            // Clear previous markers
            clearMarkers();

            // Create a bounds object to fit all markers
            const bounds = new google.maps.LatLngBounds();

            // Add a marker for each result
            results.forEach(place => {
                if (place.geometry && place.geometry.location) {
                    const position = {
                        lat: place.geometry.location.lat(),
                        lng: place.geometry.location.lng()
                    };

                    // Extend bounds to include this position
                    bounds.extend(position);

                    // Sanitize place data to prevent XSS
                    const name = place.name || 'Unnamed Restaurant';
                    const address = place.formatted_address || 'Address not available';
                    const rating = place.rating ? place.rating.toFixed(1) : 'N/A';
                    const reviewCount = place.user_ratings_total || 0;

                    // Create info window content
                    const content = `
                        <div class="map-info-window">
                            <h6>${name.replace(/</g, '&lt;').replace(/>/g, '&gt;')}</h6>
                            <p class="mb-1">${address.replace(/</g, '&lt;').replace(/>/g, '&gt;')}</p>
                            <p class="mb-1">Rating: ${rating} (${reviewCount} reviews)</p>
                            <button class="btn btn-primary btn-sm mt-2" data-place-id="${place.place_id}">
                                Add to My Restaurants
                            </button>
                        </div>
                    `;

                    // Add marker
                    addMarker({
                        position,
                        title: name,
                        content: content,
                        placeId: place.place_id
                    });
                }
            });

            // Fit map to bounds with padding
            map.fitBounds(bounds, { top: 50, right: 50, bottom: 50, left: 50 });

            // Show success message
            showSuccess(`Found ${results.length} restaurants matching "${query}"`);

            // Dispatch custom event
            document.dispatchEvent(new CustomEvent('search:complete', {
                detail: {
                    query,
                    resultCount: results.length,
                    bounds: bounds.toJSON()
                }
            }));

        } else {
            showError('No restaurants found matching your search');

            // Dispatch custom event for no results
            document.dispatchEvent(new CustomEvent('search:no-results', {
                detail: { query }
            }));
        }

    } catch (error) {
        console.error('Search error:', error);
        const errorMessage = error.message || 'An error occurred while searching for restaurants. Please try again.';
                    errorMessage = 'Location information is unavailable.';
                    break;
                case error.TIMEOUT:
                    errorMessage = 'The request to get your location timed out.';
                    break;
            }

            showError(errorMessage);
        },
        {
            enableHighAccuracy: true,
            timeout: 10000,
            maximumAge: 0
        }
    );
};

/**
 * Initialize the map
 * @returns {Promise<google.maps.Map>} The initialized map instance
 */
const initMap = async () => {
    if (!mapContainer) {
        throw new Error('Map container not found');
    }

    try {
        // Add loading state
        mapContainer.innerHTML = `
            <div class="d-flex flex-column align-items-center justify-content-center h-100 bg-light">
                <div class="spinner-border text-primary mb-3" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <p class="text-muted">Loading map...</p>
            </div>
        `;

        // Load configuration
        const config = await import('../config.js').then(m => m.default);

        if (!config.googleMaps?.apiKey) {
            throw new Error('Google Maps API key is not configured');
        }

        // Load Google Maps API with the configured API key
        await loadGoogleMapsAPI(config.googleMaps.apiKey);

        if (!window.google || !window.google.maps) {
            throw new Error('Google Maps API failed to load');
        }

        // Create map centered on default location
        map = new google.maps.Map(mapContainer, {
            center: DEFAULT_LOCATION,
            zoom: DEFAULT_ZOOM,
            mapTypeControl: false,
            streetViewControl: false,
            fullscreenControl: true,
            zoomControl: true,
            gestureHandling: 'auto',
            styles: [
                {
                    featureType: 'poi',
                    elementType: 'labels',
                    stylers: [{ visibility: 'off' }]
                }
            ]
        });

        // Try to get user's current location
        if (navigator.geolocation) {
            try {
                const position = await new Promise((resolve, reject) => {
                    navigator.geolocation.getCurrentPosition(resolve, reject, {
                        enableHighAccuracy: true,
                        timeout: 10000,
                        maximumAge: 0
                    });
                });

                const userLocation = {
                    lat: position.coords.latitude,
                    lng: position.coords.longitude
                };

                // Center map on user's location
                map.setCenter(userLocation);

                // Add a marker for user's location
                userLocationMarker = new google.maps.Marker({
                    position: userLocation,
                    map: map,
                    title: 'Your Location',
                    icon: {
                        url: 'http://maps.google.com/mapfiles/ms/icons/blue-dot.png',
                        scaledSize: new google.maps.Size(32, 32)
                    }
                });

            } catch (error) {
                console.warn('Error getting user location:', error);
                // Continue with default location if geolocation fails
            }
        }

        // Initialize Places Service
        placesService = new google.maps.places.PlacesService(map);

        // Add click listener to close info windows when clicking on the map
        map.addListener('click', () => {
            if (currentInfoWindow) {
                currentInfoWindow.close();
                currentInfoWindow = null;
            }
        });

        console.log('Map initialized successfully');

        // Set a flag to indicate map is ready
        window.mapInitialized = true;

        // Dispatch custom event when map is ready
        document.dispatchEvent(new CustomEvent('map:ready', {
            detail: { map }
        }));

        return map;

    } catch (error) {
        console.error('Error initializing map:', error);

        // Show error message to user
        mapContainer.innerHTML = `
            <div class="alert alert-danger m-3">
                <strong>Error loading map:</strong> ${error.message || 'Please try again later.'}
            </div>
        `;

        // Dispatch custom event for error handling
        document.dispatchEvent(new CustomEvent('map:error', {
            detail: {
                message: 'Failed to initialize Google Maps',
                error: error.message
            }
        }));

        throw error;
    }
}

/**
 * Initialize event listeners
 */
const initEventListeners = () => {
    if (searchForm) {
        searchForm.addEventListener('submit', handleSearch);
    }

    if (currentLocationBtn) {
        currentLocationBtn.addEventListener('click', handleCurrentLocation);
    }
};

/**
 * Clean up event listeners
 */
const cleanupEventListeners = () => {
    if (searchForm) {
        searchForm.removeEventListener('submit', handleSearch);
    }

    if (currentLocationBtn) {
        currentLocationBtn.removeEventListener('click', handleCurrentLocation);
    }
};
 * Initialize the restaurant search page
 */
export async function init() {
    console.log('Initializing restaurant search...');

    try {
        // Initialize search form with URL parameters
        initSearchForm();

        // Get DOM elements
        mapContainer = document.getElementById('map');
        searchForm = document.getElementById('restaurant-search-form');
        searchInput = document.getElementById('search-query');
        searchButton = document.getElementById('search-button');
        currentLocationBtn = document.getElementById('current-location-btn');

        // Check if we're on a page that needs the map
        if (!mapContainer) {
            console.log('No map container found, skipping map initialization');
            return;
        }

        // Load configuration
        const config = await import('../config.js').then(m => m.default);

        // Check if Google Maps API key is configured
        if (!config.googleMaps?.apiKey) {
            throw new Error('Google Maps API key is not configured');
        }

        // Initialize map
        await initMap();

        // Initialize event listeners
        initEventListeners();

        // If there's a search query in the URL, perform the search
        const urlParams = new URLSearchParams(window.location.search);
        const searchQuery = urlParams.get('q');
        if (searchQuery && searchQuery.trim() !== '') {
            await searchRestaurants(searchQuery);
        }

        // Show success message if redirected from another page with success message
        const successMessage = document.getElementById('success-message');
        if (successMessage && successMessage.textContent.trim() !== '') {
            showSuccess(successMessage.textContent);
        }

        // Show error message if redirected from another page with error message
        const errorMessage = document.getElementById('error-message');
        if (errorMessage && errorMessage.textContent.trim() !== '') {
            showError(errorMessage.textContent);
        }

    } catch (error) {
        console.error('Initialization error:', error);
        const errorMessage = error.message || 'Failed to initialize the page. Please try again later.';
        showError(errorMessage);

        // Dispatch custom event for error handling
        document.dispatchEvent(new CustomEvent('app:error', {
            detail: {
                message: 'Failed to initialize restaurant search',
                error: error.message
            }
        }));
    }
}

/**
 * Clean up resources when the page is unloaded
 */
const cleanup = () => {
    cleanupEventListeners();
    clearMarkers();

    if (userLocationMarker) {
        userLocationMarker.setMap(null);
        userLocationMarker = null;
    }

    if (currentInfoWindow) {
        currentInfoWindow.close();
        currentInfoWindow = null;
    }

    map = null;
    placesService = null;
};

// Initialize when the DOM is fully loaded
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    // DOMContentLoaded has already fired
    init();
}

// Clean up event listeners when the page is unloaded
window.addEventListener('unload', cleanup);

// Export for testing
export const __test__ = {
    init,
    cleanup,
    searchRestaurants,
    handleSearch,
    handleCurrentLocation,
    showError,
    showSuccess
};
