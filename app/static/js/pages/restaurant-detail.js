/**
 * Restaurant Detail Page JavaScript
 * Handles Google Places integration and other interactive elements
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize elements
    const syncButton = document.getElementById('sync-google-places');
    const syncSpinner = document.getElementById('sync-spinner');
    const lastSynced = document.getElementById('last-synced');

    // Only proceed if we're on a restaurant detail page with sync button
    if (!syncButton) return;

    // Handle Google Places sync
    syncButton.addEventListener('click', async function(e) {
        e.preventDefault();

        // Get restaurant ID from data attribute
        const restaurantId = syncButton.dataset.restaurantId;
        if (!restaurantId) {
            showAlert('error', 'Invalid restaurant ID');
            return;
        }

        // Show loading state
        syncButton.disabled = true;
        syncSpinner.classList.remove('d-none');

        try {
            const response = await fetch(`/restaurants/${restaurantId}/sync-google`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                credentials: 'same-origin'
            });

            const data = await response.json();

            if (data.success) {
                // Update the form fields with the synced data
                updateFormFields(data.restaurant);

                // Update last synced time
                if (lastSynced) {
                    lastSynced.textContent = new Date().toLocaleString();
                }

                showAlert('success', 'Restaurant data synced successfully');
            } else {
                showAlert('error', data.message || 'Failed to sync restaurant data');
            }
        } catch (error) {
            console.error('Error syncing with Google Places:', error);
            showAlert('error', 'An error occurred while syncing with Google Places');
        } finally {
            // Reset button state
            syncButton.disabled = false;
            syncSpinner.classList.add('d-none');
        }
    });

    /**
     * Update form fields with synced data
     */
    function updateFormFields(data) {
        const fieldMap = {
            'name': 'Restaurant Name',
            'address': 'Address',
            'city': 'City',
            'state': 'State',
            'postal_code': 'Postal Code',
            'phone': 'Phone',
            'website': 'Website',
            'rating': 'Rating',
            'type': 'Type'
        };

        // Update each field if it exists in the form
        Object.entries(fieldMap).forEach(([key, label]) => {
            if (key in data) {
                // Try to find input by name or label
                let input = document.querySelector(`[name="${key}"]`) ||
                           document.querySelector(`label:contains('${label}')`)?.nextElementSibling;

                if (input) {
                    // Handle different input types
                    if (input.type === 'checkbox') {
                        input.checked = Boolean(data[key]);
                    } else if (input.tagName === 'SELECT') {
                        const option = Array.from(input.options).find(opt =>
                            opt.value.toLowerCase() === String(data[key]).toLowerCase()
                        );
                        if (option) {
                            option.selected = true;
                        }
                    } else {
                        input.value = data[key] || '';
                    }

                    // Trigger change event for any listeners
                    input.dispatchEvent(new Event('change', { bubbles: true }));
                }
            }
        });
    }

    /**
     * Show alert message
     */
    function showAlert(type, message) {
        // Remove any existing alerts
        const existingAlerts = document.querySelectorAll('.alert');
        existingAlerts.forEach(alert => alert.remove());

        // Create new alert
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show mt-3`;
        alertDiv.role = 'alert';
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;

        // Insert after the form title or at the top of the form
        const formTitle = document.querySelector('h1, h2, h3');
        if (formTitle) {
            formTitle.after(alertDiv);
        } else {
            const form = document.querySelector('form');
            if (form) {
                form.prepend(alertDiv);
            }
        }

        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alertDiv);
            bsAlert.close();
        }, 5000);
    }
});

// Helper function to initialize Google Places Autocomplete
function initGooglePlacesAutocomplete(inputId, onPlaceSelected) {
    if (!window.google || !window.google.maps || !window.google.maps.places) {
        console.error('Google Maps JavaScript API not loaded');
        return null;
    }

    const input = document.getElementById(inputId);
    if (!input) return null;

    const autocomplete = new google.maps.places.Autocomplete(input, {
        types: ['establishment'],
        fields: ['place_id', 'name', 'formatted_address', 'geometry']
    });

    autocomplete.addListener('place_changed', () => {
        const place = autocomplete.getPlace();
        if (onPlaceSelected && typeof onPlaceSelected === 'function') {
            onPlaceSelected(place);
        }
    });

    return autocomplete;
}
