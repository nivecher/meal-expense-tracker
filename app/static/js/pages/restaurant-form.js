/**
 * Restaurant Form Page Module
 * Handles form submission and initialization for restaurant addition/editing
 */

// Import necessary modules
import { loadGoogleMapsAPI } from '../services/google-maps.service.js';

// Initialize the page module
export async function init() {
    try {
        // Initialize Google Maps if needed
        if (window.GOOGLE_MAPS_API_KEY) {
            await loadGoogleMapsAPI();
            initMap();
            initAutocomplete();
        }

        // Initialize form validation and submission
        initForm();

    } catch (error) {
        console.error('Error initializing restaurant form:', error);
    }
}

// Initialize the map
function initMap() {
    try {
        const mapElement = document.getElementById('map');
        if (!mapElement) return;

        const defaultLocation = { lat: 40.7128, lng: -74.0060 }; // Default to New York
        const map = new google.maps.Map(mapElement, {
            center: defaultLocation,
            zoom: 12,
            mapTypeControl: false,
            streetViewControl: false,
            fullscreenControl: true,
            zoomControl: true,
            gestureHandling: 'auto'
        });

        // Store map instance for later use
        window.restaurantMap = map;

    } catch (error) {
        console.error('Error initializing map:', error);
    }
}

// Initialize address autocomplete
function initAutocomplete() {
    try {
        const addressInput = document.getElementById('address');
        if (!addressInput) return;

        const autocomplete = new google.maps.places.Autocomplete(addressInput, {
            fields: ['formatted_address', 'geometry', 'name', 'place_id'],
            types: ['address']
        });

        autocomplete.addListener('place_changed', () => {
            const place = autocomplete.getPlace();
            if (!place.geometry) {
                console.log('No details available for input: ' + place.name);
                return;
            }

            // Update map view
            if (window.restaurantMap) {
                window.restaurantMap.setCenter(place.geometry.location);
                window.restaurantMap.setZoom(17);
            }

            // Update form fields
            if (place.name) {
                const nameInput = document.getElementById('name');
                if (nameInput && !nameInput.value) {
                    nameInput.value = place.name;
                }
            }
        });

    } catch (error) {
        console.error('Error initializing autocomplete:', error);
    }
}

// Initialize form submission
function initForm() {
    const form = document.getElementById('restaurant-form');
    if (!form) return;

    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const submitButton = form.querySelector('button[type="submit"]');
        const originalText = submitButton.innerHTML;

        try {
            // Show loading state
            submitButton.disabled = true;
            submitButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Saving...';

            // Submit form data
            const formData = new FormData(form);
            const response = await fetch(form.action, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });

            const result = await response.json();

            if (response.ok) {
                // Redirect on success
                window.location.href = result.redirect || '/restaurants';
            } else {
                // Show error message
                alert(result.error || 'An error occurred. Please try again.');
                submitButton.disabled = false;
                submitButton.innerHTML = originalText;
            }

        } catch (error) {
            console.error('Error submitting form:', error);
            alert('An error occurred. Please try again.');
            submitButton.disabled = false;
            submitButton.innerHTML = originalText;
        }
    });
}

// Export for testing
export const __test__ = {
    initMap,
    initAutocomplete,
    initForm
};
