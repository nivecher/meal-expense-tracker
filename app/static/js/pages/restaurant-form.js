/**
 * Restaurant Form Page Module
 * Handles form submission and initialization for restaurant addition/editing
 */

// Global variables
let map;
let marker;
let autocomplete;
let geocoder;
let placeService;

// Flag to track if the module is initialized
let isInitialized = false;

// Initialize the page module
export async function init() {
    try {
        // Check if the module is already initialized
        if (isInitialized) {
            return;
        }

        // Initialize the map and services
        await initMap();
        initSearch();
        initLocationButton();
        initForm();

        isInitialized = true;

    } catch (error) {
        console.error('Error initializing restaurant form:', error);
        showError('Failed to initialize the form. Please refresh the page and try again.');
        throw error; // Re-throw to allow the caller to handle the error
    }
}

// Initialize the map
async function initMap() {
    try {
        const mapElement = document.getElementById('map');
        if (!mapElement) {
            throw new Error('Map element not found');
        }

        // Default to New York
        const defaultLocation = { lat: 40.7128, lng: -74.0060 };

        // Create the map
        map = new google.maps.Map(mapElement, {
            center: defaultLocation,
            zoom: 12,
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

        // Initialize services
        geocoder = new google.maps.Geocoder();
        placeService = new google.maps.places.PlacesService(map);

        // Add marker
        marker = new google.maps.Marker({
            map: map,
            draggable: true,
            animation: google.maps.Animation.DROP
        });

        // Update form fields when marker is dragged
        marker.addListener('dragend', () => {
            updateFormFromLocation(marker.getPosition());
        });

        // Center the map on user's current location if available
        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(
                (position) => {
                    const pos = new google.maps.LatLng(
                        position.coords.latitude,
                        position.coords.longitude
                    );
                    map.setCenter(pos);
                    updateFormFromLocation(pos);
                },
                () => {
                    // Handle location access denied
                    map.setCenter(defaultLocation);
                }
            );
        } else {
            // Browser doesn't support Geolocation
            map.setCenter(defaultLocation);
        }

        return map;

    } catch (error) {
        console.error('Error initializing map:', error);
        showError('Failed to load the map. Please refresh the page and try again.');
        throw error;
    }
}

// Initialize search functionality
function initSearch() {
    const searchInput = document.getElementById('restaurant-search');
    if (!searchInput) return;

    try {
        // Create autocomplete for search input
        autocomplete = new google.maps.places.Autocomplete(searchInput, {
            types: ['establishment', 'geocode'],
            fields: ['name', 'formatted_address', 'geometry', 'place_id', 'address_components']
        });

        // When a place is selected from the dropdown
        autocomplete.addListener('place_changed', () => {
            const place = autocomplete.getPlace();
            if (!place.geometry) {
                console.log('No details available for input: ' + place.name);
                return;
            }

            // Update map and form with selected place
            updateMapAndForm(place);
        });
    } catch (error) {
        console.error('Error initializing search:', error);
        showError('Failed to initialize search. Please refresh the page and try again.');
    }
}

// Initialize location button
function initLocationButton() {
    const locationButton = document.getElementById('use-location');
    if (!locationButton) return;

    locationButton.addEventListener('click', () => {
        if (!navigator.geolocation) {
            showError('Geolocation is not supported by your browser.');
            return;
        }

        toggleLoading(true);

        navigator.geolocation.getCurrentPosition(
            async (position) => {
                try {
                    const pos = {
                        lat: position.coords.latitude,
                        lng: position.coords.longitude
                    };

                    // Update map and marker
                    map.setCenter(pos);
                    map.setZoom(17);

                    if (marker) {
                        marker.setPosition(pos);
                        marker.setVisible(true);
                    }

                    // Reverse geocode to get address details
                    const response = await new Promise((resolve, reject) => {
                        if (!geocoder) {
                            reject(new Error('Geocoder not initialized'));
                            return;
                        }

                        geocoder.geocode({ location: pos }, (results, status) => {
                            if (status === 'OK' && results[0]) {
                                resolve(results[0]);
                            } else {
                                reject(new Error('Geocoder failed with status: ' + status));
                            }
                        });
                    });

                    // Update form with geocoded address
                    const addressComponents = response.address_components || [];
                    const formData = {
                        address: getAddressComponent(addressComponents, 'street_number') + ' ' +
                                 getAddressComponent(addressComponents, 'route'),
                        city: getAddressComponent(addressComponents, 'locality') ||
                              getAddressComponent(addressComponents, 'postal_town'),
                        state_province: getAddressComponent(addressComponents, 'administrative_area_level_1'),
                        postal_code: getAddressComponent(addressComponents, 'postal_code'),
                        country: getAddressComponent(addressComponents, 'country'),
                        latitude: pos.lat,
                        longitude: pos.lng
                    };

                    // Update form fields
                    Object.entries(formData).forEach(([field, value]) => {
                        const input = document.getElementById(field);
                        if (input && value) {
                            input.value = value;
                        }
                    });

                    // If we have a place name, update the name field
                    if (response.formatted_address) {
                        const nameInput = document.getElementById('name');
                        if (nameInput && !nameInput.value) {
                            // Try to get a meaningful name from the address components
                            const name = response.name ||
                                       response.formatted_address.split(',')[0] ||
                                       'My Location';
                            nameInput.value = name;
                        }
                    }

                } catch (error) {
                    console.error('Error processing location:', error);
                    showError('Unable to get address details for your location. Please enter the address manually.');
                } finally {
                    toggleLoading(false);
                }
            },
            (error) => {
                console.error('Error getting location:', error);
                let errorMessage = 'Unable to retrieve your location. ';

                switch(error.code) {
                    case error.PERMISSION_DENIED:
                        errorMessage += 'Please enable location access in your browser settings.';
                        break;
                    case error.POSITION_UNAVAILABLE:
                        errorMessage += 'Location information is unavailable.';
                        break;
                    case error.TIMEOUT:
                        errorMessage += 'The request to get your location timed out.';
                        break;
                    default:
                        errorMessage += 'Please try again or enter an address manually.';
                }

                showError(errorMessage);
                toggleLoading(false);
            },
            {
                enableHighAccuracy: true,
                timeout: 10000,  // 10 seconds
                maximumAge: 60000 // 1 minute
            }
        );
    });
}

// Update map and form with place data
function updateMapAndForm(place) {
    try {
        toggleLoading(true);

        // Update map view
        if (place.geometry && place.geometry.viewport) {
            map.fitBounds(place.geometry.viewport);
        } else if (place.geometry && place.geometry.location) {
            map.setCenter(place.geometry.location);
            map.setZoom(17);
        }

        // Update marker
        if (place.geometry && place.geometry.location) {
            marker.setPosition(place.geometry.location);
            marker.setVisible(true);

            // Update form fields from the place data
            updateFormFields(place);

            // Also update the hidden lat/lng fields
            const latInput = document.getElementById('latitude');
            const lngInput = document.getElementById('longitude');
            if (latInput) latInput.value = place.geometry.location.lat();
            if (lngInput) lngInput.value = place.geometry.location.lng();
        }

        // If this is a place with a name, update the name field
        if (place.name) {
            const nameInput = document.getElementById('name');
            if (nameInput && !nameInput.value) {
                nameInput.value = place.name;
            }
        }

    } catch (error) {
        console.error('Error updating map and form:', error);
        showError('Failed to update location. Please try again.');
    } finally {
        toggleLoading(false);
    }
}

// Helper function to get address components
function getAddressComponent(components, type) {
    const component = components.find(c => c.types.includes(type));
    return component ? component.long_name : '';
}

// Update form fields from place data
function updateFormFields(place) {
    const addressComponents = place.address_components || [];
    const formData = {
        name: place.name || '',
        address: `${getAddressComponent(addressComponents, 'street_number')} ${getAddressComponent(addressComponents, 'route')}`.trim(),
        city: getAddressComponent(addressComponents, 'locality') || getAddressComponent(addressComponents, 'postal_town'),
        state_province: getAddressComponent(addressComponents, 'administrative_area_level_1'),
        postal_code: getAddressComponent(addressComponents, 'postal_code'),
        country: getAddressComponent(addressComponents, 'country'),
        latitude: place.geometry.location.lat(),
        longitude: place.geometry.location.lng()
    };

    // Update form fields
    Object.entries(formData).forEach(([field, value]) => {
        const input = document.getElementById(field);
        if (input && value) {
            input.value = value;
        }
    });
}

// Toggle loading state
function toggleLoading(isLoading) {
    const submitButton = document.getElementById('submit-button');
    const loadingSpinner = document.getElementById('loading-spinner');
    const mapContainer = document.getElementById('map');
    const loadingOverlay = document.getElementById('loading-overlay');

    // Toggle form controls
    if (submitButton) {
        submitButton.disabled = isLoading;
    }

    // Toggle loading spinner on submit button
    if (loadingSpinner) {
        loadingSpinner.style.display = isLoading ? 'inline-block' : 'none';
    }

    // Toggle map loading overlay
    if (mapContainer && loadingOverlay) {
        if (isLoading) {
            loadingOverlay.classList.remove('d-none');
            mapContainer.style.opacity = '0.5';
            mapContainer.style.pointerEvents = 'none';
        } else {
            loadingOverlay.classList.add('d-none');
            mapContainer.style.opacity = '1';
            mapContainer.style.pointerEvents = 'auto';
        }
    }

    // Toggle cursor style on body
    document.body.style.cursor = isLoading ? 'wait' : 'default';
}

// Update form fields from geocoded location
async function updateFormFromLocation(location) {
    try {
        if (!geocoder) return;

        toggleLoading(true);

        // Reverse geocode the location to get address components
        const response = await new Promise((resolve, reject) => {
            geocoder.geocode({ location }, (results, status) => {
                if (status === 'OK' && results[0]) {
                    resolve(results[0]);
                } else {
                    reject(new Error('Geocoder failed with status: ' + status));
                }
            });
        });

        const addressComponents = response.address_components || [];
        const formData = {
            address: getAddressComponent(addressComponents, 'street_number') + ' ' +
                     getAddressComponent(addressComponents, 'route'),
            city: getAddressComponent(addressComponents, 'locality') ||
                  getAddressComponent(addressComponents, 'postal_town'),
            state_province: getAddressComponent(addressComponents, 'administrative_area_level_1'),
            postal_code: getAddressComponent(addressComponents, 'postal_code'),
            country: getAddressComponent(addressComponents, 'country'),
            latitude: location.lat(),
            longitude: location.lng()
        };

        // Update form fields
        Object.entries(formData).forEach(([field, value]) => {
            const input = document.getElementById(field);
            if (input && value) {
                input.value = value;
            }
        });

    } catch (error) {
        console.error('Error updating form from location:', error);
        showError('Could not get address details for this location. Please try again.');
    } finally {
        toggleLoading(false);
    }
}

// Show success message to user
function showSuccess(message) {
    const container = document.getElementById('success-container');
    const messageEl = document.getElementById('success-message');

    if (container && messageEl) {
        messageEl.textContent = message;
        container.classList.remove('d-none');

        // Auto-hide success message after 5 seconds
        setTimeout(() => {
            container.classList.add('d-none');
        }, 5000);

        // Add click handler for close button
        const closeBtn = container.querySelector('.btn-close');
        if (closeBtn) {
            const closeHandler = () => {
                container.classList.add('d-none');
                closeBtn.removeEventListener('click', closeHandler);
            };
            closeBtn.addEventListener('click', closeHandler);
        }
    } else {
        console.log('Success:', message);
    }
}

// Show error message to user
function showError(message) {
    const container = document.getElementById('error-container');
    const messageEl = document.getElementById('error-message');

    if (container && messageEl) {
        messageEl.textContent = message;
        container.classList.remove('d-none');

        // Auto-hide error after 5 seconds
        setTimeout(() => {
            container.classList.add('d-none');
        }, 5000);

        // Add click handler for close button
        const closeBtn = container.querySelector('.btn-close');
        if (closeBtn) {
            const closeHandler = () => {
                container.classList.add('d-none');
                closeBtn.removeEventListener('click', closeHandler);
            };
            closeBtn.addEventListener('click', closeHandler);
        }
    } else {
        console.error('Error container not found. Message:', message);
    }
}

// Initialize form submission
function initForm() {
    const form = document.getElementById('restaurant-form');
    if (!form) return;

    // Handle form submission
    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        // Reset previous validation states
        const invalidInputs = form.querySelectorAll('.is-invalid');
        invalidInputs.forEach(input => input.classList.remove('is-invalid'));

        const errorMessages = form.querySelectorAll('.invalid-feedback');
        errorMessages.forEach(msg => msg.remove());

        const submitButton = form.querySelector('button[type="submit"]');
        const originalText = submitButton ? submitButton.innerHTML : '';

        // Show loading state
        toggleLoading(true);
        if (submitButton) {
            submitButton.disabled = true;
            submitButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Saving...';
        }

        try {
            // Get form data
            const formData = new FormData(form);

            // Add CSRF token if available
            const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;
            const headers = {
                'X-Requested-With': 'XMLHttpRequest'
            };

            if (csrfToken) {
                headers['X-CSRFToken'] = csrfToken;
            }

            // Submit form via AJAX
            const response = await fetch(form.action, {
                method: 'POST',
                body: formData,
                headers: headers
            });

            let result;
            try {
                result = await response.json();
            } catch (jsonError) {
                console.error('Error parsing JSON response:', jsonError);
                throw new Error('Invalid response from server');
            }

            if (response.ok) {
                // Show success message
                showSuccess(result.message || 'Restaurant saved successfully!');

                // Redirect on success after a short delay
                if (result.redirect || result.redirect_url) {
                    setTimeout(() => {
                        window.location.href = result.redirect || result.redirect_url;
                    }, 1500);
                }
            } else {
                // Show error message
                showError(result.message || result.error || 'Failed to save restaurant. Please check the form for errors.');

                // Handle form errors if any
                if (result.errors) {
                    Object.entries(result.errors).forEach(([field, messages]) => {
                        const input = form.querySelector(`[name="${field}"]`);
                        const feedback = form.querySelector(`.invalid-feedback[data-field="${field}"]`);

                        if (input) {
                            input.classList.add('is-invalid');

                            // Find or create feedback element
                            let feedbackElement = feedback;
                            if (!feedbackElement) {
                                feedbackElement = document.createElement('div');
                                feedbackElement.className = 'invalid-feedback';
                                feedbackElement.setAttribute('data-field', field);
                                input.parentNode.insertBefore(feedbackElement, input.nextSibling);
                            }

                            // Show error message
                            feedbackElement.textContent = Array.isArray(messages) ? messages[0] : messages;
                            feedbackElement.style.display = 'block';

                            // Focus on first invalid field
                            if (!document.querySelector('.is-invalid:focus')) {
                                input.focus();
                            }
                        }
                    });
                }
            }
        } catch (error) {
            console.error('Error submitting form:', error);
            showError('An unexpected error occurred. Please try again.');
        } finally {
            toggleLoading(false);
            // Reset button state
            if (submitButton) {
                submitButton.disabled = false;
                submitButton.innerHTML = originalText;
            }
        }
    });

    // Add event listeners to clear validation on input
    const formInputs = form.querySelectorAll('input, select, textarea');
    formInputs.forEach(input => {
        input.addEventListener('input', () => {
            if (input.classList.contains('is-invalid')) {
                input.classList.remove('is-invalid');
                const feedback = input.nextElementSibling;
                if (feedback && feedback.classList.contains('invalid-feedback')) {
                    feedback.style.display = 'none';
                }
            }
        });
    });
}

// Export for testing
export const __test__ = {
    initMap,
    initSearch,
    initLocationButton,
    updateMapAndForm,
    updateFormFields,
    initForm
};

// Initialize the form when the DOM is fully loaded
document.addEventListener('DOMContentLoaded', () => {
    init().catch(error => {
        console.error('Error initializing restaurant form:', error);
    });
});
