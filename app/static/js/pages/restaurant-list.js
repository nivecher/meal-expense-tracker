document.addEventListener('DOMContentLoaded', function () {
    'use strict';

    // Check if map container exists
    const mapContainer = document.getElementById('map');
    if (!mapContainer) {
        console.log('Map container not found, skipping map initialization');
        return;
    }

    console.log('Map container found, initializing map...');

    // Map state variables
    let map, userLocationMarker, markers = [];
    let userPosition = null;
    let searchCircle = null;
    let markerCluster = null;
    let locationWatchId = null;
    let currentRequest = null;

    // DOM elements
    const radiusSlider = document.getElementById('radius-slider');
    const radiusValue = document.getElementById('radius-value');
    const searchKeywordInput = document.getElementById('search-keyword');
    const searchButton = document.getElementById('search-button');
    const zoomInBtn = document.getElementById('zoomIn');
    const zoomOutBtn = document.getElementById('zoomOut');
    const resultsContainer = document.getElementById('search-results');
    const resultsCount = document.getElementById('results-count');

    // Get CSRF token for authenticated requests
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || '';

    // Constants
    const DEFAULT_ZOOM = 15;
    const MIN_ZOOM = 2;
    const MAX_ZOOM = 19;
    const DEFAULT_RADIUS = 5000; // 5km in meters
    const MAX_RADIUS = 20000;    // 20km in meters

    // Unit system based on locale
    const unitSystem = getUnitSystem();

    // Initialize marker cluster group
    function initMarkerCluster() {
        if (markerCluster) {
            map.removeLayer(markerCluster);
        }
        markerCluster = L.markerClusterGroup({
            maxClusterRadius: 40,
            spiderfyOnMaxZoom: true,
            showCoverageOnHover: false,
            zoomToBoundsOnClick: true
        });
        map.addLayer(markerCluster);
    }

    function updateStatus(message, type = 'info') {
        const statusContainer = document.getElementById('map-status-container');
        if (!statusContainer) return;
        const alertClass = type === 'danger' ? 'alert-danger' : (type === 'success' ? 'alert-success' : 'alert-info');
        statusContainer.innerHTML = `<div class="alert ${alertClass} alert-dismissible fade show" role="alert">${message}<button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button></div>`;
    }

    function getUnitSystem() {
        const lang = (navigator.language || 'en-US').toLowerCase();
        if (lang.startsWith('en')) {
            console.log(`[Debug] Detected English ('${lang}'). Using miles.`);
            return { name: 'miles', multiplier: 0.000621371, radius_unit: 'mi' };
        }
        console.log(`[Debug] Non-English language ('${lang}'). Using kilometers.`);
        return { name: 'km', multiplier: 0.001, radius_unit: 'km' };
    }

    // Initialize the map
    function initMap() {
        updateStatus('Initializing map...', 'info');

        try {
            // Initialize map with better defaults
            map = L.map('map', {
                center: [20, 0],
                zoom: 2,
                zoomControl: false, // We'll add a custom one
                preferCanvas: true, // Better performance for many markers
                fadeAnimation: true,
                zoomAnimation: true,
                minZoom: MIN_ZOOM,
                maxZoom: MAX_ZOOM
            });

            // Add tile layer with loading state
            // Store tileLayer in a variable
            tileLayer = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
                maxZoom: MAX_ZOOM,
                minZoom: MIN_ZOOM
            }).addTo(map);

            // Initialize marker cluster group
            initMarkerCluster();

            // Add zoom controls
            L.control.zoom({
                position: 'topright'
            }).addTo(map);

            // Add scale control
            L.control.scale({
                imperial: unitSystem.name === 'miles',
                metric: unitSystem.name === 'km',
                maxWidth: 200,
                position: 'bottomright'
            }).addTo(map);

            // Add locate control
            const locateControl = L.control.locate({
                position: 'topleft',
                drawCircle: true,
                showPopup: false,
                locateOptions: {
                    maxZoom: DEFAULT_ZOOM,
                    enableHighAccuracy: true,
                    timeout: 10000,
                    maximumAge: 0
                },
                strings: {
                    title: 'Show my location',
                    popup: 'You are within {distance} {unit} from this point',
                    outsideMapBoundsMsg: 'You seem located outside the map bounds',
                },
                onLocationError: function(err) {
                    updateStatus(`Location error: ${err.message}`, 'danger');
                    console.error('Location error:', err);
                },
                onLocationOutsideMapBounds: function() {
                    updateStatus('Your location is outside the map bounds', 'warning');
                }
            }).addTo(map);

            // Start locating
            locateControl.start();

            // Set up event listeners
            setupEventListeners();

            // Try to get user's location
            if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition(
                    geolocationSuccess,
                    geolocationError,
                    {
                        enableHighAccuracy: true,
                        timeout: 10000,
                        maximumAge: 0
                    }
                );
            } else {
                updateStatus('Geolocation is not supported by your browser.', 'warning');
            }

        } catch (error) {
            console.error('Error initializing map:', error);
            updateStatus('Failed to initialize map. Please refresh the page to try again.', 'danger');
        }

        // Add loading control
        tileLayer.on('loading', () => {
            updateStatus('Loading map data...', 'info');
        });
        tileLayer.on('load', () => {
            updateStatus('Map loaded', 'success');
        });

        // Add custom zoom controls
        L.control.zoom({
            position: 'topright'
        }).addTo(map);

        // Initialize marker cluster group
        markerCluster = L.markerClusterGroup({
            maxClusterRadius: 40,
            spiderfyOnMaxZoom: true,
            showCoverageOnHover: true,
            zoomToBoundsOnClick: true
        });
        map.addLayer(markerCluster);

        // Add geolocation control
        const geolocateControl = L.control.locate({
            position: 'topright',
            strings: {
                title: 'Show me where I am',
                popup: 'You are within {distance} {unit} from this point',
                outsideMapBoundsMsg: 'You seem located outside the boundaries of the map.'
            },
            locateOptions: {
                maxZoom: 16,
                enableHighAccuracy: true
            }
        }).addTo(map);

        // Try to get user's location with a timeout
        if (navigator.geolocation) {
            updateStatus('Detecting your location...', 'info');
            navigator.geolocation.getCurrentPosition(
                geolocationSuccess,
                geolocationError,
                { timeout: 10000, maximumAge: 60000, enableHighAccuracy: true }
            );
        } else {
            updateStatus('Geolocation is not supported by your browser.', 'warning');
        }

        // Show map container
        document.getElementById('map-loading').style.display = 'none';
        const mapContainer = document.getElementById('map-container');
        if (mapContainer) {
            mapContainer.style.display = 'block';
            // Trigger resize to ensure proper rendering
            setTimeout(() => map.invalidateSize(), 100);
        }
    }

    // Set up event listeners
    function setupEventListeners() {
        // Search button click
        if (searchButton) {
            searchButton.addEventListener('click', searchNearbyRestaurants);
        }

        // Radius slider change
        if (radiusSlider) {
            radiusSlider.addEventListener('input', function() {
                radiusValue.textContent = this.value;
                if (userPosition) {
                    const radius = parseInt(this.value) * 1000; // Convert to meters
                    updateSearchArea(userPosition, radius);
                    // Debounce the search to avoid too many API calls
                    debounce(searchNearbyRestaurants, 500)();
                }
            });
        }

        // Search input enter key
        if (searchKeywordInput) {
            searchKeywordInput.addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    searchNearbyRestaurants();
                }
            });
        }

        // Zoom controls
        if (zoomInBtn) {
            zoomInBtn.addEventListener('click', function() {
                map.zoomIn();
            });
        }

        if (zoomOutBtn) {
            zoomOutBtn.addEventListener('click', function() {
                map.zoomOut();
            });
        }
    }

    // Handle successful geolocation
    function geolocationSuccess(position) {
        console.log('Geolocation success:', position);

        // Update user position
        userPosition = {
            lat: position.coords.latitude,
            lng: position.coords.longitude,
            accuracy: position.coords.accuracy || 100 // Default to 100m if accuracy not available
        };

        // Hide loading state and show map
        const mapLoading = document.getElementById('map-loading');
        const mapContainer = document.getElementById('map-container');
        if (mapLoading && mapContainer) {
            mapLoading.style.display = 'none';
            mapContainer.style.display = 'block';
        }

        // Update UI to show we have a location
        updateStatus('Location found! Searching for nearby restaurants...', 'success');

        // Center map on user's location with smooth animation
        map.flyTo([userPosition.lat, userPosition.lng], DEFAULT_ZOOM, {
            duration: 1,
            easeLinearity: 0.25
        });

        // Add or update user location marker with pulse effect
        if (!userLocationMarker) {
            const pulseIcon = L.divIcon({
                className: 'user-location-marker',
                html: '<div class="pulse-marker"></div>',
                iconSize: [20, 20],
                iconAnchor: [10, 10],
                popupAnchor: [0, -10]
            });

            userLocationMarker = L.marker([userPosition.lat, userPosition.lng], {
                icon: pulseIcon,
                zIndexOffset: 1000,
                interactive: false
            }).addTo(map);

            // Add accuracy circle if accuracy is available
            if (userPosition.accuracy) {
                L.circle([userPosition.lat, userPosition.lng], {
                    radius: userPosition.accuracy,
                    color: '#0d6efd',
                    fillColor: '#0d6efd',
                    fillOpacity: 0.1,
                    weight: 1,
                    className: 'accuracy-circle',
                    interactive: false
                }).addTo(map);
            }
        } else {
            userLocationMarker.setLatLng([userPosition.lat, userPosition.lng]);
        }

        // Update search area visualization
        const radius = radiusSlider ? parseInt(radiusSlider.value) * 1000 : DEFAULT_RADIUS;
        updateSearchArea(userPosition, radius);

        // Search for nearby restaurants
        searchNearbyRestaurants();
    }

    function geolocationError(error) {
        console.error('Geolocation error:', error);
        updateStatus(`Error detecting location: ${error.message}. You can still search manually.`, 'danger');
    }

    // Debounce function to limit API calls
    function debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    // Update search when slider changes (debounced)
    radiusSlider.addEventListener('input', debounce(searchNearbyRestaurants, 300));
    searchKeywordInput.addEventListener('input', debounce(searchNearbyRestaurants, 500));

    // Search for restaurants near the user's location
    async function searchNearbyRestaurants() {
        if (!userPosition) {
            updateStatus('Could not search for restaurants without your location.', 'warning');
            return;
        }

        const radiusInKm = parseInt(radiusSlider.value);
        const radiusInMeters = Math.min(radiusInKm * 1000, MAX_RADIUS);
        const keyword = searchKeywordInput.value.trim();
        const resultsElement = document.getElementById('search-results');

        // Cancel any pending request
        if (currentRequest) {
            currentRequest.abort();
        }

        // Update search area visualization
        updateSearchArea(userPosition, radiusInMeters);

        // Show loading state
        updateStatus('Searching for nearby restaurants...', 'info');

        if (resultsElement) {
            resultsElement.innerHTML = `
                <div class="search-loading">
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                    <p class="mt-2">Searching restaurants within ${radiusInKm} km...</p>
                </div>`;
        }

        // Create new AbortController for this request
        const controller = new AbortController();
        const signal = controller.signal;
        currentRequest = controller;

        try {
            // Build query parameters
            const params = new URLSearchParams({
                lat: userPosition.lat,
                lng: userPosition.lng,
                radius: radiusInMeters
            });

            if (keyword) {
                params.append('keyword', encodeURIComponent(keyword));
            }

            const response = await fetch(`/api/places/search?${params.toString()}`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken,
                    'X-Requested-With': 'XMLHttpRequest'
                },
                signal: signal
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            displaySearchResults(data.results || [], userPosition);

            const resultCount = data.results ? data.results.length : 0;
            updateStatus(`Found ${resultCount} restaurant${resultCount !== 1 ? 's' : ''}`, 'success');

            // Update results count
            if (resultsCount) {
                resultsCount.textContent = resultCount;
            }

        } catch (error) {
            if (error.name === 'AbortError') {
                console.log('Request was aborted');
                return;
            }

            console.error('Error searching for restaurants:', error);
            updateStatus(`Error: ${error.message}`, 'danger');

            // Show error in results container
            if (resultsElement) {
                resultsElement.innerHTML = `
                    <div class="alert alert-danger m-3">
                        <i class="fas fa-exclamation-triangle me-2"></i>
                        Failed to load restaurants. ${error.message || 'Please try again.'}
                    </div>`;
            }
        } finally {
            currentRequest = null;
            if (map) {
                map.fire('load');
            }
        }
    }

    function updateSearchArea(center, radius) {
        // Remove previous search area if exists
        if (searchCircle) {
            map.removeLayer(searchCircle);
        }

        // Add new search area circle
        searchCircle = L.circle([center.lat, center.lng], {
            radius: radius,
            color: '#3388ff',
            weight: 2,
            fillColor: '#3388ff',
            fillOpacity: 0.1
        }).addTo(map);

        // If this is the first search, fit the map to show the search area
        if (!markers.length) {
            map.fitBounds(searchCircle.getBounds());
        }
    }

    // Display search results in the sidebar and on the map
    function displaySearchResults(results, userPosition) {
        const resultsElement = document.getElementById('search-results');
        if (!resultsElement) {
            console.error('Search results container not found');
            return;
        }

        // Clear previous markers and results
        clearMarkers();

        // Handle no results case
        if (!Array.isArray(results) || results.length === 0) {
            resultsElement.innerHTML = `
                <div class="alert alert-info m-3">
                    <i class="fas fa-info-circle me-2"></i>
                    No restaurants found. Try adjusting your search criteria or expanding the search radius.
                </div>`;
            return;
        }

        // Process and validate results
        const validResults = results.filter(restaurant =>
            restaurant &&
            restaurant.geometry?.location &&
            restaurant.geometry.location.lat &&
            restaurant.geometry.location.lng
        );

        if (validResults.length === 0) {
            resultsElement.innerHTML = `
                <div class="alert alert-warning m-3">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    No valid restaurant locations found in the results.
                </div>`;
            return;
        }

        // Calculate distances if user position is available
        if (userPosition) {
            validResults.forEach(restaurant => {
                const { lat, lng } = restaurant.geometry.location;
                restaurant.distance = calculateDistance(
                    userPosition.lat,
                    userPosition.lng,
                    lat,
                    lng
                );
            });

            // Sort by distance
            validResults.sort((a, b) => (a.distance || Infinity) - (b.distance || Infinity));
        }

        // Generate HTML for results list
        const resultsHTML = generateResultsHTML(validResults);
        resultsElement.innerHTML = resultsHTML;

        // Create markers and set up interactions
        createMarkers(validResults);

        // Set up event listeners
        setupResultItemInteractions();

        // Fit map to show all markers
        if (markers.length > 0) {
            const group = L.featureGroup(markers);
            map.fitBounds(group.getBounds().pad(0.1));
        }

        // Ensure search circle is still visible if it exists
        if (searchCircle) {
            map.fitBounds(searchCircle.getBounds().pad(0.1));
        }

        // Helper function to generate results HTML
        function generateResultsHTML(restaurants) {
            const searchSummary = `
                <div class="search-summary mb-2 text-muted">
                    Found ${restaurants.length} ${restaurants.length === 1 ? 'restaurant' : 'restaurants'}
                </div>`;

            const resultsList = restaurants.map((restaurant, index) => {
                const { name, geometry, vicinity, formatted_address, opening_hours, rating,
                        user_ratings_total, price_level, place_id } = restaurant;
                const { lat, lng } = geometry.location;

                // Format distance
                const distance = restaurant.distance ?
                    (restaurant.distance < 1000 ?
                        `${Math.round(restaurant.distance)}m` :
                        `${(restaurant.distance / 1000).toFixed(1)}km`) :
                    '';

                // Format rating
                const ratingStars = rating ?
                    `★${rating.toFixed(1)}${user_ratings_total ? ` (${user_ratings_total})` : ''}` :
                    'Not rated';

                // Format price level
                const priceIndicator = price_level ?
                    '• ' + '💲'.repeat(Math.min(price_level, 4)) : '';

                // Format open/closed status
                const isOpenNow = opening_hours?.open_now !== undefined
                    ? (opening_hours.open_now
                        ? '<span class="badge bg-success">Open Now</span>'
                        : '<span class="badge bg-danger">Closed</span>')
                    : '';

                return `
                    <div class="list-group-item list-group-item-action restaurant-item"
                         data-place-id="${place_id || index}"
                         data-lat="${lat}"
                         data-lng="${lng}">
                        <div class="d-flex w-100 justify-content-between align-items-start">
                            <h6 class="mb-1">
                                <i class="fas fa-utensils me-2"></i>
                                ${name || 'Unnamed Restaurant'}
                            </h6>
                            <div class="d-flex align-items-center">
                                ${isOpenNow}
                                ${distance ? `<small class="ms-2">${distance}</small>` : ''}
                            </div>
                        </div>
                        <p class="mb-1 text-muted small">
                            <i class="fas fa-map-marker-alt me-1"></i>
                            ${vicinity || formatted_address || 'Address not available'}
                        </p>
                        <div class="d-flex justify-content-between align-items-center">
                            <small class="text-warning">
                                <i class="fas fa-star"></i> ${ratingStars} ${priceIndicator}
                            </small>
                            <button class="btn btn-sm btn-outline-primary add-restaurant"
                                    data-place-id="${place_id || index}">
                                <i class="fas fa-plus"></i> Add
                            </button>
                        </div>
                    </div>`;
            }).join('');

            return `
                ${searchSummary}
                <div class="search-results-list" style="max-height: 70vh; overflow-y: auto;">
                    <div class="list-group list-group-flush">
                        ${resultsList}
                    </div>
                </div>`;
        }

        // Helper function to create markers and set up hover effects
        function createMarkers(restaurants) {
            const newMarkers = [];

            restaurants.forEach(restaurant => {
                if (!restaurant.geometry?.location) return;

                const { lat, lng } = restaurant.geometry.location;
                const marker = L.marker([lat, lng], {
                    title: restaurant.name,
                    alt: restaurant.name || 'Restaurant',
                    riseOnHover: true,
                    customId: restaurant.place_id || `restaurant-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
                });

                // Create popup content
                const distance = restaurant.distance ?
                    (restaurant.distance < 1000 ?
                        `${Math.round(restaurant.distance)}m` :
                        `${(restaurant.distance / 1000).toFixed(1)}km`) :
                    '';

                const popupContent = createPopupContent(restaurant, distance);
                marker.bindPopup(popupContent, {
                    maxWidth: 300,
                    minWidth: 200,
                    className: 'restaurant-popup'
                });

                // Add marker to the map and store reference
                marker.addTo(map);
                newMarkers.push(marker);

                // Set up hover effects
                const item = document.querySelector(`.restaurant-item[data-place-id="${restaurant.place_id}"]`);
                if (item) {
                    // Highlight list item on marker hover
                    marker.on('mouseover', () => {
                        item.classList.add('bg-light');
                        item.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                    });

                    marker.on('mouseout', () => {
                        item.classList.remove('bg-light');
                    });

                    // Highlight marker on list item hover
                    item.addEventListener('mouseenter', () => {
                        marker.openPopup();
                    });

                    item.addEventListener('mouseleave', () => {
                        marker.closePopup();
                    });
                }
            });

            // Clear existing markers and add new ones to cluster
            if (markerCluster) {
                markerCluster.clearLayers();
                markerCluster.addLayers(newMarkers);
            }

            // Update markers array
            markers = newMarkers;
        }

        // Helper function to set up result item interactions
        function setupResultItemInteractions() {
            // Handle clicks on result items
            document.querySelectorAll('.restaurant-item').forEach(item => {
                item.addEventListener('click', function(e) {
                    // Don't trigger if clicking on the add button
                    if (e.target.closest('.add-restaurant')) {
                        return;
                    }

                    const lat = parseFloat(this.dataset.lat);
                    const lng = parseFloat(this.dataset.lng);
                    const placeId = this.dataset.placeId;

                    if (isNaN(lat) || isNaN(lng)) {
                        console.error('Invalid coordinates for restaurant item');
                        return;
                    }

                    // Find and open the corresponding marker's popup
                    const marker = markers.find(m =>
                        m.options.customId === placeId ||
                        (m.getLatLng().lat === lat && m.getLatLng().lng === lng)
                    );

                    if (marker) {
                        // Center map on marker with offset to account for sidebar
                        map.setView(marker.getLatLng(), map.getZoom(), {
                            animate: true,
                            duration: 0.5
                        });

                        // Open popup
                        marker.openPopup();

                        // Highlight the selected result
                        document.querySelectorAll('.restaurant-item').forEach(el => {
                            el.classList.remove('active');
                        });
                        this.classList.add('active');
                    }
                });
            });

            // Handle clicks on add restaurant buttons
            document.querySelectorAll('.add-restaurant').forEach(button => {
                // Remove any existing listeners to prevent duplicates
                const newButton = button.cloneNode(true);
                button.parentNode.replaceChild(newButton, button);

                newButton.addEventListener('click', function(e) {
                    e.stopPropagation();
                    const placeId = this.dataset.placeId;
                    if (placeId) {
                        addRestaurant(placeId);
                    }
                });
            });
        }
    }

    function createPopupContent(restaurant) {
        let content = `<div class="restaurant-popup"><h6 class="mb-1">${restaurant.name || 'Unnamed Restaurant'}</h6>`;
        if (restaurant.rating) content += `<div class="d-flex align-items-center mb-1"><div class="text-warning me-1">${'★'.repeat(Math.floor(restaurant.rating))}${'☆'.repeat(5 - Math.floor(restaurant.rating))}</div><small class="text-muted ms-1">${restaurant.rating.toFixed(1)}</small></div>`;
        if (restaurant.vicinity || restaurant.formatted_address) content += `<p class="mb-1 small"><i class="fas fa-map-marker-alt me-1"></i>${restaurant.vicinity || restaurant.formatted_address}</p>`;
        if (restaurant.types) content += `<div class="mb-2">${restaurant.types.slice(0, 3).map(type => `<span class="badge bg-light text-dark me-1 mb-1">${type.replace(/_/g, ' ')}</span>`).join('')}</div>`;
        content += `<div class="d-flex justify-content-between align-items-center"><button class="btn btn-sm btn-outline-primary" data-place-id="${restaurant.place_id || ''}"><i class="fas fa-plus me-1"></i> Add</button><div class="btn-group">${restaurant.website ? `<a href="${restaurant.website}" target="_blank" rel="noopener noreferrer" class="btn btn-sm btn-outline-secondary"><i class="fas fa-external-link-alt"></i></a>` : ''}<button class="btn btn-sm btn-outline-secondary" data-lat="${restaurant.geometry.lat}" data-lng="${restaurant.geometry.lng}" title="Copy coordinates"><i class="fas fa-copy"></i></button></div></div></div>`;
        return content;
    }

    function clearMarkers() {
        if (markerCluster) {
            markerCluster.clearLayers();
        }
        markers = [];
    }

    function calculateDistance(lat1, lon1, lat2, lon2) {
        const R = 6371; // Radius of the Earth in kilometers
        const dLat = (lat2 - lat1) * Math.PI / 180;
        const dLon = (lon2 - lon1) * Math.PI / 180;
        const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) + Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) * Math.sin(dLon / 2) * Math.sin(dLon / 2);
        const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
        const distanceInKm = R * c;

        // Check user's locale to determine units
        const userLocale = navigator.language || 'en-US';
        if (userLocale.startsWith('en-US') || userLocale.startsWith('en-GB')) {
            const distanceInMiles = distanceInKm * 0.621371;
            return { distance: distanceInMiles.toFixed(2), unit: 'mi' };
        }
        return { distance: distanceInKm.toFixed(2), unit: 'km' };
    }

    async function addRestaurant(placeId) {
        if (!placeId) {
            updateStatus('Error: Missing place ID', 'danger');
            return;
        }

        updateStatus('Adding restaurant to your list...', 'info');

        try {
            const response = await fetch('/restaurants/api/add', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken,
                    'Accept': 'application/json'
                },
                body: JSON.stringify({ place_id: placeId })
            });

            const data = await response.json();

            if (response.ok && data.success) {
                updateStatus('Restaurant added successfully!', 'success');
            } else {
                throw new Error(data.error || 'Failed to add restaurant');
            }
        } catch (error) {
            console.error('Error adding restaurant:', error);
            updateStatus(error.message || 'Failed to add restaurant. Please try again.', 'danger');
        }
    }

    initMap();

    document.body.addEventListener('click', function(e) {
        if (e.target.closest('[data-place-id]')) {
            addRestaurant(e.target.closest('[data-place-id]').dataset.placeId);
        }
        if (e.target.closest('[data-lat][data-lng]')) {
            const btn = e.target.closest('[data-lat][data-lng]');
            if(btn.title === 'Copy coordinates'){
                 copyCoordinates(btn.dataset.lat, btn.dataset.lng);
            }
        }
    });

    document.body.addEventListener('mouseover', function(e) {
        if (e.target.closest('.list-group-item-action[data-lat]')) {
            centerMapOnRestaurant(e.target.closest('.list-group-item-action[data-lat]'));
        }
    });
});
