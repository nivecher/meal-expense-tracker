/**
 * Restaurant Form Initialization
 * Handles the initialization of the restaurant form page
 */

// Initialize the restaurant form when the DOM is fully loaded
document.addEventListener('DOMContentLoaded', () => {
    // Check if Google Maps API key is available
    if (!window.GOOGLE_MAPS_API_KEY) {
        console.error('Google Maps API key is not set');
        showError('Google Maps integration is not properly configured. Please contact support.');
        return;
    }

    // Load the Google Maps API with the Places library
    const script = document.createElement('script');
    script.src = `https://maps.googleapis.com/maps/api/js?key=${window.GOOGLE_MAPS_API_KEY}&libraries=places&callback=initRestaurantForm`;
    script.async = true;
    script.defer = true;

    // Define the global callback function
    window.initRestaurantForm = async function() {
        try {
            // Import and initialize the restaurant form module
            const module = await import('/static/js/pages/restaurant-form.js');
            if (module && typeof module.init === 'function') {
                await module.init();
            } else {
                throw new Error('Restaurant form module not properly exported');
            }
        } catch (error) {
            console.error('Error initializing restaurant form:', error);
            showError('Failed to initialize the form. Please refresh the page and try again.');
        }
    };

    // Handle script loading errors
    script.onerror = () => {
        console.error('Failed to load Google Maps API');
        showError('Failed to load Google Maps. Please check your internet connection and try again.');
    };

    // Add the script to the document
    document.head.appendChild(script);

    // Initialize Select2 for any select elements
    if (window.jQuery && jQuery.fn.select2) {
        jQuery('select').select2({
            theme: 'bootstrap-5',
            width: '100%',
            placeholder: 'Select an option',
            allowClear: true
        });
    }
});

/**
 * Show an error message to the user
 * @param {string} message - The error message to display
 */
function showError(message) {
    const errorContainer = document.getElementById('error-container');
    if (errorContainer) {
        errorContainer.textContent = message;
        errorContainer.classList.remove('d-none');
    }
}
