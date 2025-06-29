/**
 * Restaurant Form Handling
 * Handles Google Maps integration, form validation, and other interactive elements
 * for the restaurant add/edit form.
 */

// Global application state
const appState = {
    autocomplete: null,
    placeSearch: null,
    placesService: null,
    map: null,
    marker: null,
    geocoder: null,
    searchBox: null,
    placeChangedListener: null,
    isLoading: false,
    retryCount: 0,
    MAX_RETRIES: 3
};

// Validation rules and messages
const VALIDATION_RULES = {
    // Restaurant Information
    name: {
        required: true,
        minLength: 2,
        maxLength: 100,
        pattern: /^[\w\s\-',.&]+$/,
        messages: {
            required: 'Restaurant name is required',
            minLength: 'Name must be at least 2 characters',
            maxLength: 'Name cannot exceed 100 characters',
            pattern: 'Name contains invalid characters (only letters, numbers, spaces, and -\',.& are allowed)'
        }
    },

    // Contact Information
    phone: {
        pattern: /^[\d\s\-().+]+$/,
        maxLength: 20,
        messages: {
            pattern: 'Please enter a valid phone number',
            maxLength: 'Phone number is too long (max 20 characters)'
        }
    },
    website: {
        pattern: /^(https?:\/\/)?([\w-]+\.)+[\w-]+(\/[\w- .\/?%&=]*)?$/,
        maxLength: 255,
        messages: {
            pattern: 'Please enter a valid website URL (e.g., https://example.com)',
            maxLength: 'Website URL is too long (max 255 characters)'
        }
    },
    email: {
        pattern: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
        maxLength: 100,
        messages: {
            pattern: 'Please enter a valid email address (e.g., name@example.com)',
            maxLength: 'Email is too long (max 100 characters)'
        }
    },

    // Address Fields
    street_address: {
        maxLength: 255,
        messages: {
            maxLength: 'Street address is too long (max 255 characters)'
        }
    },
    city: {
        maxLength: 100,
        pattern: /^[\w\s\-']+$/,
        messages: {
            maxLength: 'City name is too long (max 100 characters)',
            pattern: 'City name contains invalid characters'
        }
    },
    state: {
        maxLength: 50,
        pattern: /^[A-Za-z\s\-']+$/,
        messages: {
            maxLength: 'State name is too long (max 50 characters)',
            pattern: 'State name contains invalid characters'
        }
    },
    postal_code: {
        pattern: /^[\w\s\-]+$/,
        maxLength: 20,
        messages: {
            pattern: 'Please enter a valid postal code',
            maxLength: 'Postal code is too long (max 20 characters)'
        }
    },
    country: {
        maxLength: 100,
        pattern: /^[A-Za-z\s\-']+$/,
        messages: {
            maxLength: 'Country name is too long (max 100 characters)',
            pattern: 'Country name contains invalid characters'
        }
    },

    // Additional Information
    price_range: {
        validate: (value) => {
            if (!value) return true; // Optional field
            const price = parseInt(value, 10);
            return !isNaN(price) && price >= 1 && price <= 4;
        },
        messages: {
            validate: 'Please select a valid price range (1-4)'
        }
    },
    cuisine_types: {
        validate: (value) => {
            if (!value) return true; // Optional field
            return value.length <= 5; // Max 5 cuisine types
        },
        messages: {
            validate: 'You can select up to 5 cuisine types'
        }
    },
    opening_hours: {
        validate: (value) => {
            if (!value) return true; // Optional field
            // Basic validation for opening hours format (HH:MM - HH:MM)
            return /^([01]?[0-9]|2[0-3]):[0-5][0-9]\s*-\s*([01]?[0-9]|2[0-3]):[0-5][0-9]$/.test(value);
        },
        messages: {
            validate: 'Please enter valid opening hours (e.g., 09:00 - 22:00)'
        }
    },
    description: {
        maxLength: 1000,
        messages: {
            maxLength: 'Description is too long (max 1000 characters)'
        }
    },
    tags: {
        validate: (value) => {
            if (!value) return true; // Optional field
            const tags = value.split(',').map(tag => tag.trim()).filter(tag => tag);
            return tags.length <= 10; // Max 10 tags
        },
        messages: {
            validate: 'You can add up to 10 tags',
            maxLength: 'Each tag should be at most 50 characters',
            pattern: 'Tags can only contain letters, numbers, and hyphens'
        }
    }
};

// UI Elements cache
const ui = {
    // UI Elements
    loadingIndicator: null,
    errorContainer: null,
    formOverlay: null,

    // Initialize UI components
    init() {
        this.loadingIndicator = document.getElementById('loading-indicator');
        this.errorContainer = document.getElementById('error-container');
        this.formOverlay = document.getElementById('form-overlay');
        return this;
    },

    // Show loading indicator
    showLoading(message = 'Loading...') {
        if (this.loadingIndicator) {
            const textEl = this.loadingIndicator.querySelector('span') || this.loadingIndicator;
            textEl.textContent = message;
            this.loadingIndicator.classList.remove('d-none');
        }
    },

    // Hide loading indicator
    hideLoading() {
        if (this.loadingIndicator) {
            this.loadingIndicator.classList.add('d-none');
        }
    },

    // Show form overlay with loading state
    showFormLoading(show = true, message = 'Saving changes...') {
        if (!this.formOverlay) return;

        if (show) {
            const messageEl = this.formOverlay.querySelector('p');
            if (messageEl) {
                messageEl.textContent = message;
            }
            this.formOverlay.classList.remove('d-none');
        } else {
            this.formOverlay.classList.add('d-none');
        }
    },

    // Show error message
    showError(message, isFatal = false) {
        console.error(message);
        if (!this.errorContainer) return;

        // Create error ID for later reference
        const errorId = `error-${Date.now()}`;

        // Create error element
        const errorEl = document.createElement('div');
        errorEl.id = errorId;
        errorEl.className = `alert alert-${isFatal ? 'danger' : 'warning'} alert-dismissible fade show mb-2`;
        errorEl.role = 'alert';
        errorEl.innerHTML = `
            <i class="fas ${isFatal ? 'fa-exclamation-circle' : 'fa-exclamation-triangle'} me-2"></i>
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;

        // Add to the top of the container
        if (this.errorContainer.firstChild) {
            this.errorContainer.insertBefore(errorEl, this.errorContainer.firstChild);
        } else {
            this.errorContainer.appendChild(errorEl);
        }

        // Auto-dismiss non-fatal errors after 5 seconds
        if (!isFatal) {
            setTimeout(() => {
                const el = document.getElementById(errorId);
                if (el) {
                    el.classList.remove('show');
                    setTimeout(() => el.remove(), 150);
                }
            }, 5000);
        }

        return errorId;
    },

    // Clear all error messages
    clearErrors() {
        if (this.errorContainer) {
            this.errorContainer.innerHTML = '';
        }
    },

    // Disable form elements
    disableForm(form, disable = true) {
        if (!form) return;

        const elements = form.elements;
        for (let i = 0; i < elements.length; i++) {
            elements[i].disabled = disable;
        }
    },

    // Show success message
    showSuccess(message) {
        return this.showError(message, false);
    }
}.init();

/**
 * Initialize Google Maps services
 * @returns {Promise<void>}
 */
async function initGoogleMaps() {
    if (appState.isLoading) {
        console.log('Google Maps initialization already in progress');
        return;
    }

    ui.clearErrors();
    ui.showLoading('Initializing map...');
    appState.isLoading = true;

    try {
        // Ensure Google Maps is available
        if (typeof google === 'undefined' || !google.maps) {
            throw new Error('Google Maps API is not available');
        }

        // Load the Places library if not already loaded
        if (!google.maps.places) {
            await withRetry(() => google.maps.importLibrary('places'), {
                maxRetries: 3,
                delay: 1000,
                description: 'Loading Google Places library'
            });
        }

        // Initialize services with error handling
        try {
            appState.autocomplete = new google.maps.places.AutocompleteService();
            const mapElement = document.getElementById('map') || document.createElement('div');

            appState.placeSearch = new google.maps.places.PlacesService(mapElement);

            // Create a dummy map for PlacesService if needed
            if (!appState.map) {
                const mapContainer = document.createElement('div');
                mapContainer.style.display = 'none';
                document.body.appendChild(mapContainer);

                appState.map = new google.maps.Map(mapContainer, {
                    center: { lat: 0, lng: 0 },
                    zoom: 2
                });

                appState.placesService = new google.maps.places.PlacesService(appState.map);
            }
        } catch (error) {
            throw new Error(`Failed to initialize Google Maps services: ${error.message}`);
        }

        // Initialize search functionality if not already initialized
        if (!appState.searchInitialized) {
            initSearch();
            appState.searchInitialized = true;
        }

        appState.retryCount = 0; // Reset retry counter on success
        return Promise.resolve();
    } catch (error) {
        appState.retryCount++;
        const errorMsg = `Error initializing Google Maps (attempt ${appState.retryCount}/${appState.MAX_RETRIES}): ${error.message}`;

        if (appState.retryCount < appState.MAX_RETRIES) {
            console.warn(errorMsg + ' Retrying...');
            return new Promise(resolve => {
                setTimeout(() => resolve(initGoogleMaps()), 1000 * appState.retryCount);
            });
        }

        ui.showError('Failed to load Google Maps. Please check your connection and refresh the page.', true);
        return Promise.reject(new Error(errorMsg));
    } finally {
        appState.isLoading = false;
        ui.hideLoading();
    }
}

// Fill address fields from Google Places result
function fillAddressFields(place) {
    // Helper function to get address component
    function getAddressComponent(addressComponents, type) {
        const component = addressComponents.find(comp => comp.types.includes(type));
        return component ? component.long_name : '';
    }

    // Get address components
    const addressComponents = place.address_components || [];

    // Fill in the address fields
    document.getElementById('name').value = place.name || '';
    document.getElementById('address').value = place.formatted_address || '';

    // Extract address components
    const streetNumber = getAddressComponent(addressComponents, 'street_number');
    const route = getAddressComponent(addressComponents, 'route');
    const city = getAddressComponent(addressComponents, 'locality');
    const state = getAddressComponent(addressComponents, 'administrative_area_level_1');
    const zipCode = getAddressComponent(addressComponents, 'postal_code');
    const country = getAddressComponent(addressComponents, 'country');

    // Fill street address (combine street number and route)
    const streetAddress = [streetNumber, route].filter(Boolean).join(' ');
    if (streetAddress) {
        document.getElementById('street_address').value = streetAddress;
    }

    // Fill other fields
    if (city) document.getElementById('city').value = city;
    if (state) document.getElementById('state').value = state;
    if (zipCode) document.getElementById('zip_code').value = zipCode;
    if (country) document.getElementById('country').value = country;

    // Fill latitude and longitude if available
    if (place.geometry?.location) {
        document.getElementById('latitude').value = place.geometry.location.lat();
        document.getElementById('longitude').value = place.geometry.location.lng();
    }

    // Fill place_id if available
    if (place.place_id) {
        document.getElementById('google_place_id').value = place.place_id;
    }

    // Fill additional fields if available
    if (place.formatted_phone_number) {
        document.getElementById('phone').value = place.formatted_phone_number;
    }

    // Fill website if available
    if (place.website) {
        document.getElementById('website').value = place.website;
    }

    // Fill price level if available
    if (place.price_level !== undefined) {
        const priceLevels = {
            0: 'inexpensive',
            1: 'inexpensive',
            2: 'moderate',
            3: 'expensive',
            4: 'very_expensive'
        };
        const priceLevelSelect = document.getElementById('price_range');
        if (priceLevelSelect) {
            priceLevelSelect.value = priceLevels[place.price_level] || '';
        }
    }

    // Fill types/categories if available
    if (place.types && place.types.length > 0) {
        // Map Google Place types to our cuisine types
        const typeMapping = {
            'restaurant': 'restaurant',
            'cafe': 'cafe',
            'bakery': 'bakery',
            'bar': 'bar',
            'meal_takeaway': 'takeout',
            'meal_delivery': 'delivery'
        };

        const typeSelect = document.getElementById('type');
        if (typeSelect) {
            for (const type of place.types) {
                if (typeMapping[type]) {
                    typeSelect.value = typeMapping[type];
                    break;
                }
            }
        }
    }

    // Trigger change events to update any dependent fields
    ['city', 'state', 'zip_code', 'country'].forEach(field => {
        const el = document.getElementById(field);
        if (el) el.dispatchEvent(new Event('change'));
    });
}

// Initialize search functionality
function initSearch() {
    const searchInput = document.getElementById('restaurant_search');
    const searchResults = document.getElementById('search_results');

    if (!searchInput || !searchResults) return;

    let debounceTimer;

    // Debounce search input
    searchInput.addEventListener('input', () => {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => {
            const query = searchInput.value.trim();
            if (query.length >= 2) {
                searchPlaces(query);
            } else {
                searchResults.style.display = 'none';
            }
        }, 300);
    });

    // Handle search button click
    const searchButton = document.getElementById('searchButton');
    if (searchButton) {
        searchButton.addEventListener('click', () => {
            const query = searchInput.value.trim();
            if (query.length >= 2) {
                searchPlaces(query);
            }
        });
    }

    // Hide results when clicking outside
    document.addEventListener('click', (e) => {
        if (!searchResults.contains(e.target) && e.target !== searchInput) {
            searchResults.style.display = 'none';
        }
    });
}

// Search for places using Google Places API
function searchPlaces(query) {
    const searchResults = document.getElementById('search_results');
    if (!searchResults) return;

    searchResults.innerHTML = '';

    if (!appState.autocomplete) {
        console.error('Autocomplete service not initialized');
        return;
    }

    const placeType = document.getElementById('placeType')?.value || 'establishment';

    appState.autocomplete.getPlacePredictions(
        {
            input: query,
            componentRestrictions: { country: 'us' },
            types: [placeType]
        },
        (predictions, status) => {
            if (status !== google.maps.places.PlacesServiceStatus.OK || !predictions) {
                searchResults.style.display = 'none';
                return;
            }

            const resultsList = document.createElement('div');
            resultsList.className = 'list-group';

            predictions.slice(0, 5).forEach(prediction => {
                const resultItem = document.createElement('button');
                resultItem.type = 'button';
                resultItem.className = 'list-group-item list-group-item-action text-start';
                resultItem.innerHTML = `
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <h6 class="mb-1">${prediction.structured_formatting.main_text}</h6>
                            <small class="text-muted">${prediction.structured_formatting.secondary_text || ''}</small>
                        </div>
                        <i class="fas fa-chevron-right ms-2"></i>
                    </div>
                `;

                resultItem.addEventListener('click', () => {
                    selectPlace(prediction.place_id);
                });

                resultsList.appendChild(resultItem);
            });

            searchResults.innerHTML = '';
            searchResults.appendChild(resultsList);
            searchResults.style.display = 'block';
        }
    );
}

// Handle place selection
function selectPlace(placeId) {
    if (!appState.placesService) {
        console.error('Places service not initialized');
        return;
    }

    appState.placesService.getDetails(
        {
            placeId: placeId,
            fields: [
                'name', 'formatted_address', 'geometry', 'place_id',
                'address_components', 'formatted_phone_number', 'website',
                'opening_hours', 'price_level', 'rating', 'user_ratings_total',
                'photos', 'reviews', 'types'
            ]
        },
        (place, status) => {
            if (status === google.maps.places.PlacesServiceStatus.OK) {
                fillAddressFields(place);
                const searchResults = document.getElementById('search_results');
                if (searchResults) {
                    searchResults.style.display = 'none';
                }
            }
        }
    );
}

// Show alert message
function showAlert(message, type = 'info') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.role = 'alert';
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;

    const container = document.querySelector('.container');
    if (container) {
        container.insertBefore(alertDiv, container.firstChild);

        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            const alert = bootstrap.Alert.getOrCreateInstance(alertDiv);
            if (alert) {
                alert.close();
            } else {
                alertDiv.remove();
            }
        }, 5000);
    }
}

// Format cuisine options with icons
function formatCuisineOption(cuisine) {
    if (!cuisine || !cuisine.id) return cuisine?.text || '';

    const cuisineIcons = {
        'american': 'hamburger',
        'asian': 'utensils',
        'barbecue': 'drumstick-bite',
        'breakfast': 'coffee',
        'burgers': 'hamburger',
        'cafe': 'coffee',
        'chinese': 'utensils',
        'desserts': 'ice-cream',
        'fast food': 'hamburger',
        'french': 'utensils',
        'greek': 'utensils',
        'indian': 'utensils',
        'italian': 'pizza-slice',
        'japanese': 'fish',
        'korean': 'utensils',
        'mediterranean': 'utensils',
        'mexican': 'pepper-hot',
        'pizza': 'pizza-slice',
        'seafood': 'fish',
        'steakhouse': 'drumstick-bite',
        'sushi': 'fish',
        'thai': 'pepper-hot',
        'vegetarian': 'leaf',
        'vietnamese': 'utensils'
    };

    const icon = cuisineIcons[cuisine.id.toLowerCase()] || 'utensils';
    return $(`<span><i class="fas fa-${icon} me-2"></i>${cuisine.text || ''}</span>`);
}

// Format selected cuisine
function formatCuisineSelection(cuisine) {
    if (!cuisine || !cuisine.id) return cuisine?.text || '';
    return $(`<span>${cuisine.text || ''}</span>`);
}

// Initialize Google Maps
async function initMap() {
    try {
        // Check if map container exists
        const mapElement = document.getElementById('map');
        if (!mapElement) return;

        // Initialize map
        appState.map = new google.maps.Map(mapElement, {
            center: { lat: 40.7128, lng: -74.0060 }, // Default to New York
            zoom: 12,
            mapTypeControl: false,
            streetViewControl: false,
            fullscreenControl: true,
            mapTypeId: google.maps.MapTypeId.ROADMAP
        });

        // Initialize geocoder
        appState.geocoder = new google.maps.Geocoder();

        // Add click listener to update location
        appState.map.addListener('click', (e) => {
            updateLocation(e.latLng);
        });

        // Check if we have existing coordinates
        const latInput = document.getElementById('latitude');
        const lngInput = document.getElementById('longitude');

        if (latInput && latInput.value && lngInput && lngInput.value) {
            const position = {
                lat: parseFloat(latInput.value),
                lng: parseFloat(lngInput.value)
            };
            updateLocation(position);
        }

    } catch (error) {
        console.error('Error initializing map:', error);
        if (window.showToast) {
            window.showToast.error('Failed to initialize map. Please refresh the page.');
        }
    }
}

// Initialize autocomplete
function initAutocomplete() {
    try {
        const searchInput = document.getElementById('restaurantSearch');
        if (!searchInput) return;

        // Create autocomplete
        appState.autocomplete = new google.maps.places.Autocomplete(searchInput, {
            componentRestrictions: { country: 'us' },
            fields: ['address_components', 'geometry', 'name', 'place_id'],
            types: ['establishment']
        });

        // Add listener for when a place is selected
        appState.placeChangedListener = appState.autocomplete.addListener('place_changed', () => {
            const place = appState.autocomplete.getPlace();
            if (!place.geometry) {
                console.warn('No details available for input: ' + place.name);
                return;
            }
            updateLocation(place.geometry.location);
        });
    } catch (error) {
        console.error('Error initializing autocomplete:', error);
    }
}

// Update location on map and form fields
function updateLocation(location) {
    if (!appState.map) return;

    // Update map center
    appState.map.setCenter(location);

    // Update or create marker
    if (!appState.marker) {
        appState.marker = new google.maps.Marker({
            position: location,
            map: appState.map,
            draggable: true
        });

        // Add dragend listener
        appState.marker.addListener('dragend', () => {
            updateFormFields(appState.marker.getPosition());
        });
    } else {
        appState.marker.setPosition(location);
    }

    // Update form fields
    updateFormFields(location);

    // Update zoom level
    appState.map.setZoom(15);
}

// Update form fields with location data
function updateFormFields(location) {
    const latInput = document.getElementById('latitude');
    const lngInput = document.getElementById('longitude');

    if (latInput && lngInput) {
        latInput.value = location.lat();
        lngInput.value = location.lng();
    }

    // Reverse geocode to get address
    if (appState.geocoder) {
        appState.geocoder.geocode({ location }, (results, status) => {
            if (status === 'OK' && results[0]) {
                const addressInput = document.getElementById('address');
                if (addressInput) {
                    addressInput.value = results[0].formatted_address;
                }
            }
        });
    }
}

// Set up search handlers
function setupSearchHandlers() {
    const searchButton = document.getElementById('searchButton');
    if (searchButton) {
        searchButton.addEventListener('click', () => {
            const searchInput = document.getElementById('restaurantSearch');
            if (searchInput && searchInput.value) {
                const request = {
                    query: searchInput.value,
                    fields: ['name', 'geometry', 'formatted_address', 'place_id']
                };

                const service = new google.maps.places.PlacesService(appState.map);
                service.findPlaceFromQuery(request, (results, status) => {
                    if (status === 'OK' && results && results[0]) {
                        updateLocation(results[0].geometry.location);
                    }
                });
            }
        });
    }
}

// Set up location services
function setupLocationServices() {
    const currentLocationBtn = document.getElementById('useCurrentLocation');
    if (currentLocationBtn) {
        currentLocationBtn.addEventListener('click', () => {
            if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition(
                    (position) => {
                        const pos = {
                            lat: position.coords.latitude,
                            lng: position.coords.longitude
                        };
                        updateLocation(pos);
                    },
                    (error) => {
                        console.error('Error getting current location:', error);
                        if (window.showToast) {
                            window.showToast.error('Unable to retrieve your location');
                        }
                    }
                );
            } else {
                if (window.showToast) {
                    window.showToast.error('Geolocation is not supported by your browser');
                }
            }
        });
    }
}

// Set up form event listeners
function setupFormEventListeners() {
    const clearSearchBtn = document.getElementById('clearSearch');
    if (clearSearchBtn) {
        clearSearchBtn.addEventListener('click', () => {
            const searchInput = document.getElementById('restaurantSearch');
            if (searchInput) {
                searchInput.value = '';
            }

            // Reset map to default view
            if (appState.map) {
                appState.map.setCenter({ lat: 40.7128, lng: -74.0060 });
                appState.map.setZoom(12);
            }

            // Remove marker
            if (appState.marker) {
                appState.marker.setMap(null);
                appState.marker = null;
            }

            // Clear form fields
            const latInput = document.getElementById('latitude');
            const lngInput = document.getElementById('longitude');
            const addressInput = document.getElementById('address');

            if (latInput) latInput.value = '';
            if (lngInput) lngInput.value = '';
            if (addressInput) addressInput.value = '';
        });
    }
}

// Clean up event listeners
function cleanup() {
    if (appState.placeChangedListener) {
        google.maps.event.removeListener(appState.placeChangedListener);
    }

    if (appState.marker) {
        appState.marker.setMap(null);
        appState.marker = null;
    }

    if (appState.map) {
        google.maps.event.clearInstanceListeners(appState.map);
    }
}

// Initialize Select2 for cuisine selection
function initializeSelect2() {
    const cuisineSelect = document.getElementById('cuisine');
    if (cuisineSelect && typeof jQuery !== 'undefined' && jQuery.fn.select2) {
        $(cuisineSelect).select2({
            theme: 'bootstrap-5',
            width: '100%',
            placeholder: 'Select cuisines',
            allowClear: true,
            closeOnSelect: false,
            tags: true
        });
    }
}

/**
 * Initialize the restaurant form
 * This is the main entry point called from the template
 */
function initializeRestaurantForm() {
    // Initialize form elements
    const form = document.getElementById('restaurantForm');
    if (!form) {
        console.error('Restaurant form not found');
        return;
    }

    // Initialize the map
    initMap();

    // Initialize autocomplete
    initAutocomplete();

    // Set up event listeners
    setupSearchHandlers();
    setupLocationServices();
    setupFormEventListeners();

    // Handle current location button
    const useCurrentLocationBtn = document.getElementById('useCurrentLocation');
    if (useCurrentLocationBtn && !useCurrentLocationBtn._locationHandlerAdded) {
        useCurrentLocationBtn._locationHandlerAdded = true;
        useCurrentLocationBtn.addEventListener('click', function() {
            if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition(
                    function(position) {
                        if (typeof google === 'undefined' || !google.maps) {
                            showAlert('Google Maps is not available. Please try again later.', 'danger');
                            return;
                        }

                        const geocoder = new google.maps.Geocoder();
                        const latlng = {
                            lat: position.coords.latitude,
                            lng: position.coords.longitude
                        };

                        geocoder.geocode({ location: latlng }, function(results, status) {
                            if (status === 'OK' && results[0]) {
                                fillAddressFields(results[0]);
                            } else {
                                showAlert('Unable to get your current location. Please try again.', 'danger');
                            }
                        });
                    },
                    function(error) {
                        let errorMessage = 'Error getting your location: ';
                        switch(error.code) {
                            case error.PERMISSION_DENIED:
                                errorMessage += 'User denied the request for geolocation.';
                                break;
                            case error.POSITION_UNAVAILABLE:
                                errorMessage += 'Location information is unavailable.';
                                break;
                            case error.TIMEOUT:
                                errorMessage += 'The request to get user location timed out.';
                                break;
                            case error.UNKNOWN_ERROR:
                                errorMessage += 'An unknown error occurred.';
                                break;
                        }
                        showAlert(errorMessage, 'danger');
                    }
                );
            } else {
                showAlert('Geolocation is not supported by your browser.', 'warning');
            }
        });
    }

    // Handle clear search button
    const clearSearchBtn = document.getElementById('clear_search');
    if (clearSearchBtn && !clearSearchBtn._handlerAdded) {
        clearSearchBtn._handlerAdded = true;
        clearSearchBtn.addEventListener('click', function() {
            const searchInput = document.getElementById('google_address');
            if (searchInput) {
                searchInput.value = '';
                searchInput.focus();
            }
        });
    }
}

/**
 * Utility function to retry async operations with exponential backoff
 * @param {Function} fn - Async function to retry
 * @param {Object} options - Retry options
 * @param {number} options.maxRetries - Maximum number of retries
 * @param {number} options.delay - Initial delay in ms
 * @param {string} options.description - Description for error messages
 * @returns {Promise} - Result of the async function
 */
async function withRetry(fn, { maxRetries = 3, delay = 1000, description = 'operation' } = {}) {
    let lastError;

    for (let attempt = 1; attempt <= maxRetries; attempt++) {
        try {
            return await fn();
        } catch (error) {
            lastError = error;
            if (attempt < maxRetries) {
                const waitTime = delay * Math.pow(2, attempt - 1);
                console.warn(`Attempt ${attempt} failed for ${description}. Retrying in ${waitTime}ms...`, error);
                await new Promise(resolve => setTimeout(resolve, waitTime));
            }
        }
    }

    throw new Error(`Failed after ${maxRetries} attempts: ${lastError.message}`);
}

/**
 * Handle API errors and provide user-friendly messages
 * @param {Error|Response} error - The error object or response
 * @returns {string} User-friendly error message
 */
function handleApiError(error) {
    console.error('API Error:', error);

    // Handle network errors
    if (error instanceof TypeError && error.message.includes('Failed to fetch')) {
        return 'Unable to connect to the server. Please check your internet connection and try again.';
    }

    // Handle HTTP error responses
    if (error instanceof Response) {
        switch (error.status) {
            case 400:
                return 'Invalid request. Please check your input and try again.';
            case 401:
                return 'Session expired. Please refresh the page and log in again.';
            case 403:
                return 'You do not have permission to perform this action.';
            case 404:
                return 'The requested resource was not found.';
            case 409:
                return 'A duplicate entry already exists. Please check your input.';
            case 422:
                return 'Validation error. Please check the form for errors.';
            case 429:
                return 'Too many requests. Please wait a moment and try again.';
            case 500:
                return 'An internal server error occurred. Please try again later.';
            default:
                return `An error occurred (${error.status}). Please try again.`;
        }
    }

    // Handle other types of errors
    return error.message || 'An unexpected error occurred. Please try again.';
}

/**
 * Submit form data to the server with retry logic
 * @param {HTMLFormElement} form - The form element to submit
 * @param {number} retries - Number of retry attempts remaining
 * @returns {Promise<Response>} The fetch response
 */
async function submitFormWithRetry(form, retries = 2) {
    const formData = new FormData(form);
    const url = form.action;
    const method = form.method.toUpperCase();

    try {
        const response = await fetch(url, {
            method,
            body: method === 'GET' ? null : formData,
            headers: {
                'Accept': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            },
            credentials: 'same-origin'
        });

        if (!response.ok) {
            // If unauthorized, don't retry
            if (response.status === 401) {
                throw response;
            }

            // If we have retries left, try again after a delay
            if (retries > 0) {
                const delay = 1000 * (3 - retries); // Exponential backoff
                await new Promise(resolve => setTimeout(resolve, delay));
                return submitFormWithRetry(form, retries - 1);
            }

            throw response;
        }

        return response;
    } catch (error) {
        if (retries > 0) {
            const delay = 1000 * (3 - retries);
            await new Promise(resolve => setTimeout(resolve, delay));
            return submitFormWithRetry(form, retries - 1);
        }
        throw error;
    }
}

/**
 * Handle server-side validation errors
 * @param {Object} errors - Object mapping field names to error messages
 */
function handleServerValidationErrors(errors) {
    if (!errors || typeof errors !== 'object') return;

    // Clear all existing errors first
    Object.keys(VALIDATION_RULES).forEach(fieldName => {
        const field = document.querySelector(`[name="${fieldName}"]`);
        if (field) clearFieldError(field);
    });

    // Show server validation errors
    Object.entries(errors).forEach(([fieldName, messages]) => {
        const field = document.querySelector(`[name="${fieldName}"]`);
        if (field) {
            // Join multiple error messages with line breaks
            const errorMessage = Array.isArray(messages) ? messages.join('\n') : messages;
            showFieldError(field, errorMessage);
        } else {
            // For non-field specific errors, show in the general error container
            ui.showError(Array.isArray(messages) ? messages[0] : messages);
        }
    });

    // Focus on first error field
    const firstErrorField = document.querySelector('.is-invalid');
    if (firstErrorField) {
        firstErrorField.focus();
    }
}

/**
 * Handle form submission with enhanced error handling
 */
async function handleFormSubmit(e) {
    e.preventDefault();
    const form = e.target;
    if (!form) return;

    // Show loading state
    ui.showFormLoading(true, 'Saving restaurant...');
    ui.disableForm(form, true);

    // Re-enable form if there's an error
    const onError = async (error) => {
        // Handle 422 Unprocessable Entity (validation errors)
        if (error.status === 422) {
            try {
                const errorData = await error.json();
                if (errorData.errors) {
                    handleServerValidationErrors(errorData.errors);
                    return;
                }
            } catch (e) {
                console.error('Error parsing validation errors:', e);
            }
        }

        const errorMessage = handleApiError(error);
        ui.showError(errorMessage);

        // Re-focus the first invalid field if any
        const firstInvalid = form.querySelector('.is-invalid') || form.querySelector(':invalid');
        if (firstInvalid) {
            firstInvalid.focus();
        }

        // If unauthorized, redirect to login after a delay
        if (error.status === 401) {
            setTimeout(() => {
                window.location.href = '/login?next=' + encodeURIComponent(window.location.pathname);
            }, 2000);
        }
    };

    try {
        // Submit the form with retry logic
        const response = await submitFormWithRetry(form);

        // Handle successful response
        if (response.redirected) {
            window.location.href = response.url;
            return;
        }

        // Handle JSON response
        const data = await response.json().catch(() => ({}));

        // Check for validation errors in successful response (some APIs return 200 with errors)
        if (data.errors) {
            handleServerValidationErrors(data.errors);
            return;
        }

        if (data.redirect) {
            window.location.href = data.redirect;
        } else if (data.success) {
            ui.showSuccess('Restaurant saved successfully!');
            if (data.redirect) {
                setTimeout(() => {
                    window.location.href = data.redirect;
                }, 1500);
            }
        } else {
            throw new Error(data.message || 'Unknown error occurred');
        }

    } catch (error) {
        onError(error);
    } finally {
        ui.showFormLoading(false);
        ui.disableForm(form, false);
    }
}

/**
 * Validate a single form field against its rules
 * @param {HTMLInputElement|HTMLSelectElement|HTMLTextAreaElement} field - The form field to validate
 * @returns {string|null} Error message if invalid, null if valid
 */
function validateField(field) {
    const fieldName = field.name;
    const value = field.value.trim();
    const rules = VALIDATION_RULES[fieldName];

    if (!rules) return null;

    // Required check
    if (rules.required && !value) {
        return rules.messages.required || 'This field is required';
    }

    // Skip further validation if field is empty and not required
    if (!value && !rules.required) return null;

    // Min length check
    if (rules.minLength && value.length < rules.minLength) {
        return rules.messages.minLength || `Must be at least ${rules.minLength} characters`;
    }

    // Max length check
    if (rules.maxLength && value.length > rules.maxLength) {
        return rules.messages.maxLength || `Cannot exceed ${rules.maxLength} characters`;
    }

    // Pattern check
    if (rules.pattern && !rules.pattern.test(value)) {
        return rules.messages.pattern || 'Invalid format';
    }

    // Custom validation function
    if (rules.validate && !rules.validate(value, field)) {
        return rules.messages.validate || 'Invalid value';
    }

    return null; // Field is valid
}

/**
 * Validate the entire form
 * @param {HTMLFormElement} form - The form to validate
 * @returns {boolean} True if form is valid, false otherwise
 */
function validateForm(form) {
    let isValid = true;
    const fields = form.querySelectorAll('input, select, textarea');

    fields.forEach(field => {
        const error = validateField(field);
        if (error) {
            isValid = false;
            showFieldError(field, error);
        } else {
            clearFieldError(field);
        }
    });

    return isValid;
}

/**
 * Show error message for a specific field
 * @param {HTMLElement} field - The form field
 * @param {string} message - The error message to display
 */
function showFieldError(field, message) {
    // Remove any existing error messages
    clearFieldError(field);

    // Add error class to field
    field.classList.add('is-invalid');

    // Create and append error message
    const errorDiv = document.createElement('div');
    errorDiv.className = 'invalid-feedback d-block';
    errorDiv.textContent = message;
    errorDiv.id = `${field.id || field.name}-error`;

    // Insert after the field
    field.parentNode.insertBefore(errorDiv, field.nextSibling);

    // Add ARIA attributes for accessibility
    field.setAttribute('aria-invalid', 'true');
    field.setAttribute('aria-describedby', errorDiv.id);
}

/**
 * Clear error message for a specific field
 * @param {HTMLElement} field - The form field
 */
function clearFieldError(field) {
    // Remove error class
    field.classList.remove('is-invalid');

    // Remove error message if it exists
    const errorId = `${field.id || field.name}-error`;
    const errorElement = document.getElementById(errorId);
    if (errorElement) {
        errorElement.remove();
    }

    // Clear ARIA attributes
    field.removeAttribute('aria-invalid');
    field.removeAttribute('aria-describedby');
}

/**
 * Initialize form event handlers
 */
function initFormHandlers() {
    const form = document.getElementById('restaurantForm');
    if (!form) return;

    // Handle form submission
    form.addEventListener('submit', (e) => {
        // First clear all previous errors
        form.querySelectorAll('.is-invalid').forEach(clearFieldError);

        // Validate form
        if (!validateForm(form)) {
            e.preventDefault();
            e.stopPropagation();

            // Focus on first invalid field
            const firstInvalid = form.querySelector('.is-invalid');
            if (firstInvalid) {
                firstInvalid.focus();
            }
        }
    });

    // Handle form reset
    const resetBtn = form.querySelector('button[type="reset"], input[type="reset"]');
    if (resetBtn) {
        resetBtn.addEventListener('click', () => {
            // Clear all errors and validation states
            form.querySelectorAll('.is-invalid').forEach(clearFieldError);
            ui.clearErrors();
            ui.disableForm(form, false);
        });
    }

    // Real-time validation on input/blur
    const validateOnInput = (e) => {
        const field = e.target;
        if (field.willValidate) {
            const error = validateField(field);
            if (error) {
                showFieldError(field, error);
            } else {
                clearFieldError(field);
            }
        }
    };

    // Add validation event listeners to all form fields
    form.querySelectorAll('input, select, textarea').forEach(field => {
        if (field.type !== 'submit' && field.type !== 'reset' && field.type !== 'button') {
            field.addEventListener('blur', validateOnInput);

            // For text inputs, also validate on input (but not for password fields)
            if (field.type === 'text' || field.type === 'email' || field.type === 'url' || field.type === 'tel') {
                field.addEventListener('input', (e) => {
                    // Only validate if the field already has an error
                    if (field.classList.contains('is-invalid')) {
                        validateOnInput(e);
                    }
                });
            }
        }
    });

    // Initialize any custom validation for specific fields
    initCustomValidations(form);
}

/**
 * Initialize custom validations for specific fields
 * @param {HTMLFormElement} form - The form element
 */
function initCustomValidations(form) {
    // Phone number formatting
    const phoneInput = form.querySelector('input[name="phone"]');
    if (phoneInput) {
        phoneInput.addEventListener('input', (e) => {
            let value = e.target.value.replace(/\D/g, '');
            if (value.length > 10) value = value.substring(0, 10);

            // Format as (123) 456-7890
            if (value.length > 0) {
                value = value.replace(/(\d{3})(\d{3})(\d{4})/, '($1) $2-$3');
            }

            e.target.value = value;
        });
    }

    // ZIP code formatting
    const zipInput = form.querySelector('input[name="zip_code"]');
    if (zipInput) {
        zipInput.addEventListener('input', (e) => {
            let value = e.target.value.replace(/\D/g, '');
            if (value.length > 5) {
                value = `${value.substring(0, 5)}-${value.substring(5, 9)}`;
            }
            if (value.length > 10) value = value.substring(0, 10);
            e.target.value = value;
        });
    }
}

// Initialize when DOM is fully loaded
document.addEventListener('DOMContentLoaded', function() {
    // Initialize UI elements
    ui.init();

    // Only auto-initialize if we're on a page with the restaurant form
    const form = document.getElementById('restaurantForm');
    if (form) {
        initializeRestaurantForm();
        initFormHandlers();
    }
});

// Make functions available globally
window.restaurantForm = Object.assign(window.restaurantForm || {}, {
    initGoogleMaps,
    fillAddressFields,
    initializeRestaurantForm,
    initSearch,
    searchPlaces,
    selectPlace,
    showAlert,
    formatCuisineOption,
    formatCuisineSelection,
    cleanup,
    handleFormSubmit,
    initFormHandlers
});
