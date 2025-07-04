/**
 * Restaurant Search Page
 * Handles the restaurant search functionality and map initialization
 */

// Import dependencies
import googleMapsService from '../services/google-maps.service.js';
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
        // Create the alert div
        const alertDiv = document.createElement('div');
        alertDiv.className = 'alert alert-success alert-dismissible fade show';
        alertDiv.setAttribute('role', 'alert');

        // Create the message span and set textContent for safety
        const messageSpan = document.createElement('span');
        messageSpan.textContent = message;
        alertDiv.appendChild(messageSpan);

        // Create the close button using innerHTML (static, not user input)
        const closeBtn = document.createElement('button');
        closeBtn.type = 'button';
        closeBtn.className = 'btn-close';
        closeBtn.setAttribute('data-bs-dismiss', 'alert');
        closeBtn.setAttribute('aria-label', 'Close');
        alertDiv.appendChild(closeBtn);

        // Clear and append
        container.innerHTML = '';
        container.appendChild(alertDiv);
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
    if (!window.google?.maps) {
        console.warn('Google Maps not available when trying to clear markers');
        return;
    }

    markers.forEach(marker => {
        try {
            // Remove marker from the map
            if (marker.setMap) {
                marker.setMap(null);
            }

            // Remove all listeners from the marker
            if (marker.addListener) {
                google.maps.event.clearInstanceListeners(marker);
            }
        } catch (error) {
            console.error('Error removing marker:', error);
        }
    });

    markers = [];

    // Also clear the user location marker if it exists
    if (userLocationMarker) {
        try {
            if (userLocationMarker.setMap) {
                userLocationMarker.setMap(null);
            }
            google.maps.event.clearInstanceListeners(userLocationMarker);
            userLocationMarker = null;
        } catch (error) {
            console.error('Error removing user location marker:', error);
        }
    }
};

/**
 * Add a standard Google Maps Marker to the map
 * @param {Object} options - Marker options
 * @param {Object} options.position - Marker position { lat, lng }
 * @param {string} options.title - Marker title
 * @param {Object} [options.icon] - Custom icon
 * @param {string} [options.content] - Info window content
 * @returns {google.maps.Marker} - The created marker
 */
const addMarker = ({ position, title, icon, content }) => {
    if (!window.google?.maps?.marker?.AdvancedMarkerElement) {
        console.error('Google Maps AdvancedMarkerElement is not available');
        return null;
    }

    const { maps } = window.google;
    const positionObj = new maps.LatLng(position.lat, position.lng);

    try {
        // Create a standard Marker
        const marker = new maps.marker.AdvancedMarkerElement({
            map,
            position: positionObj,
            title,
            content: (() => {
                if (icon) {
                    const img = document.createElement('img');
                    img.src = icon.url;
                    img.style.width = '32px';
                    img.style.height = '32px';
                    return img;
                }
                return undefined;
            })()
        });

        // Handle info window if content is provided
        if (content) {
            const infoWindow = new maps.InfoWindow({
                content,
                disableAutoPan: true
            });

            marker.addEventListener('gmp-click', () => {
                // Close any open info windows
                if (currentInfoWindow) {
                    currentInfoWindow.close();
                }
                // Open new info window at marker position
                infoWindow.open({
                    anchor: marker,
                    map,
                    shouldFocus: false
                });
                currentInfoWindow = infoWindow;
            });
        }


        markers.push(marker);
        return marker;
    } catch (error) {
        console.error('Error creating marker:', error);
        return null;
    }
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
        let errorMessage = 'An error occurred while searching for restaurants. Please try again.';

        if (error.code === error.PERMISSION_DENIED) {
            errorMessage = 'Location access was denied. Please enable location services and try again.';
        } else if (error.code === error.POSITION_UNAVAILABLE) {
            errorMessage = 'Location information is unavailable.';
        } else if (error.code === error.TIMEOUT) {
            errorMessage = 'The request to get your location timed out.';
        } else if (error.message) {
            errorMessage = error.message;
        }

        showError(errorMessage);
    }
};

/**
 * Initialize the map
 * @returns {Promise<google.maps.Map>} The initialized map
 */
const initMap = async () => {
    if (!mapContainer) {
        throw new Error('Map container not found');
    }

    // Add loading state
    mapContainer.innerHTML = `
        <div class="d-flex flex-column align-items-center justify-content-center h-100 bg-light">
            <div class="spinner-border text-primary mb-3" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
            <p class="text-muted">Loading map...</p>
        </div>
    `;

    try {
        // Load Google Maps API
        await googleMapsService.load().catch(error => {
            console.error('Failed to load Google Maps API:', error);
            throw new Error('Failed to load Google Maps. Please try again later.');
        });

        if (!window.google?.maps) {
            throw new Error('Google Maps API failed to initialize');
        }

        const { maps } = window.google;

        // Clear any existing map instance
        if (map) {
            map.unbindAll();
            map = null;
        }

        // Create map centered on default location
        map = new maps.Map(mapContainer, {
            center: DEFAULT_LOCATION,
            zoom: DEFAULT_ZOOM,
            mapId: 'fd6f9096c4c4db22913a0cae',
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
                userLocationMarker = new maps.marker.AdvancedMarkerElement({
                    map: map,
                    position: userLocation,
                    title: 'Your Location',
                    content: (() => {
                        const img = document.createElement('img');
                        img.src = 'https://maps.google.com/mapfiles/ms/icons/blue-dot.png';
                        img.style.width = '32px';
                        img.style.height = '32px';
                        return img;
                    })()
                });

            } catch (error) {
                console.warn('Error getting user location:', error);
                // Continue with default location if geolocation fails
            }
        }


        // Initialize Places Service
        placesService = new maps.places.PlacesService(map);

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
        const alertDiv = document.createElement('div');
        alertDiv.className = 'alert alert-danger m-3';

        const strong = document.createElement('strong');
        strong.textContent = 'Error loading map: ';

        const msg = document.createElement('span');
        msg.textContent = error.message || 'Please try again later.';

        alertDiv.appendChild(strong);
        alertDiv.appendChild(msg);

        mapContainer.innerHTML = '';
        mapContainer.appendChild(alertDiv);

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
 * Initialize the restaurant search page
 */
export async function init() {
    // Get DOM elements
    mapContainer = document.getElementById('map');
    searchForm = document.getElementById('restaurant-search-form');
    searchInput = document.getElementById('restaurant-search-input');
    searchButton = document.getElementById('restaurant-search-btn');
    currentLocationBtn = document.getElementById('current-location-btn');

    if (!mapContainer || !searchForm || !searchInput || !searchButton) {
        console.warn('Required DOM elements not found for restaurant search initialization.');
        return;
    }

    // Initialize the map
    await initMap();

    // Initialize the search form (if needed)
    if (typeof initSearchForm === 'function') {
        initSearchForm({
            searchForm,
            searchInput,
            searchButton,
            map,
            searchRestaurants,
            showError,
            setLoading
        });
    }

    // Optionally, add event listeners for current location button, etc.
    if (currentLocationBtn) {
        currentLocationBtn.addEventListener('click', async () => {
            if (navigator.geolocation) {
                setLoading(true);
                navigator.geolocation.getCurrentPosition(async (position) => {
                    const userLocation = {
                        lat: position.coords.latitude,
                        lng: position.coords.longitude
                    };
                    map.setCenter(userLocation);
                    setLoading(false);
                }, (error) => {
                    showError('Unable to get your current location.');
                    setLoading(false);
                });
            } else {
                showError('Geolocation is not supported by your browser.');
            }
        });
    }
}
