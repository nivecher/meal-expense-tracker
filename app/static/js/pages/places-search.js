/**
 * Places Search Page
 *
 * Handles map-based restaurant search functionality and restaurant management.
 * This replaces the inline JavaScript in the places_search.html template.
 */

// Enhanced toast notification function with action buttons
function showLocalToast(title, message, type = 'info', actions = null) {
  const toastContainer = document.getElementById('toastContainer');
  if (!toastContainer) return;

  const toastId = `toast-${Date.now()}`;
  const bgClass =
        type === 'error'
          ? 'bg-danger'
          : type === 'success'
            ? 'bg-success'
            : type === 'warning'
              ? 'bg-warning'
              : 'bg-info';
  const textClass = type === 'warning' ? 'text-dark' : 'text-white';

  // Build action buttons HTML - using event delegation instead of onclick
  let actionsHtml = '';
  if (actions && actions.length > 0) {
    actionsHtml = `
            <div class="mt-2">
                ${actions
    .map(
      (action, _index) => `
                    <button class="btn btn-sm ${action.class || 'btn-light'} me-2"
                            data-action="${action.action || 'default'}"
                            data-action-data='${JSON.stringify(action.data || {})}'>
                        ${action.icon ? `<i class="${action.icon} me-1"></i>` : ''}${action.text}
                    </button>
                `,
    )
    .join('')}
            </div>
        `;
  }

  const toastHtml = `
        <div id="${toastId}" class="toast" role="alert" aria-live="assertive" aria-atomic="true">
            <div class="toast-header ${bgClass} ${textClass}">
                <i class="fas fa-${type === 'error' ? 'exclamation-triangle' : type === 'success' ? 'check-circle' : type === 'warning' ? 'exclamation-triangle' : 'info-circle'} me-2"></i>
                <strong class="me-auto">${title}</strong>
                <button type="button" class="btn-close ${type === 'warning' ? 'btn-close-dark' : 'btn-close-white'}" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
            <div class="toast-body">
                ${message}
                ${actionsHtml}
            </div>
        </div>
    `;

  toastContainer.insertAdjacentHTML('beforeend', toastHtml);

  const toastElement = document.getElementById(toastId);

  // Handle action button clicks using event delegation
  toastElement.addEventListener('click', (e) => {
    const button = e.target.closest('button[data-action]');
    if (button) {
      const { action } = button.dataset;
      const actionData = JSON.parse(button.dataset.actionData || '{}');

      if (action === 'navigate') {
        window.location.href = actionData.url;
      } else if (action === 'default') {
        // Handle default actions based on button text or other attributes
        const buttonText = button.textContent.trim();
        if (buttonText.includes('View Restaurant')) {
          window.location.href = actionData.url;
        } else if (buttonText.includes('Update Info')) {
          window.location.href = actionData.editUrl;
        }
      }
    }
  });

  // Auto-dismiss toasts, including warnings and success with actions
  const autohide = type !== 'error';
  const delay = type === 'warning' ? 7000 : type === 'success' ? 4000 : 5000;
  const toast = new bootstrap.Toast(toastElement, {
    autohide,
    delay: autohide ? delay : 0,
  });

  toast.show();

  // Remove toast element after it's hidden
  toastElement.addEventListener('hidden.bs.toast', () => {
    toastElement.remove();
  });

  // Return a small handle so callers can dismiss this toast when needed
  return {
    id: toastId,
    hide: () => {
      try {
        toast.hide();
      } catch {
        /* no-op */
      }
    },
  };
}

// Global function to add restaurant to user's list
window.addToMyRestaurants = async function(placeId) {
  try {
    // Validate placeId
    if (!placeId || placeId === 'null' || placeId === 'undefined') {
      throw new Error(`Invalid place ID: ${placeId}`);
    }

    // Get configuration from data attributes
    const config = window.PLACES_SEARCH_CONFIG || {};
    const { csrfToken } = config;
    const { addRestaurantUrl } = config;

    if (!csrfToken || !addRestaurantUrl) {
      throw new Error('Missing configuration for restaurant addition');
    }

    // Show loading state and keep a handle to dismiss it later
    const addingToast = showLocalToast(
      'Adding Restaurant',
      'Adding restaurant to your list...',
      'info',
    );

    // Get restaurant details
    const response = await fetch(`/restaurants/api/places/details/${placeId}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`Failed to get restaurant details: ${response.status}`);
    }

    const restaurantData = await response.json();

    // Create form data for adding restaurant
    const formData = new FormData();
    formData.append('csrf_token', csrfToken);
    formData.append('name', restaurantData.name || '');
    formData.append('type', 'restaurant');
    formData.append('description', restaurantData.description || '');
    formData.append('address', restaurantData.address || '');
    formData.append('city', restaurantData.city || '');
    formData.append('state', restaurantData.state || '');
    formData.append('postal_code', restaurantData.postal_code || '');
    formData.append('country', restaurantData.country || '');
    formData.append('phone', restaurantData.phone || '');
    formData.append('website', restaurantData.website || '');
    formData.append('email', restaurantData.email || '');
    formData.append('google_place_id', restaurantData.google_place_id || '');
    formData.append('cuisine', restaurantData.cuisine || '');
    formData.append('service_level', restaurantData.service_level || '');
    formData.append('is_chain', restaurantData.is_chain ? 'true' : 'false');
    formData.append('rating', restaurantData.rating || '');
    formData.append('notes', restaurantData.notes || '');

    // Submit the form
    const addResponse = await fetch(addRestaurantUrl, {
      method: 'POST',
      headers: {
        'X-Requested-With': 'XMLHttpRequest',
      },
      body: formData,
    });

    const responseData = await addResponse.json();

    if (addResponse.status === 201) {
      // Hide the adding toast before showing the success toast
      if (addingToast && addingToast.hide) addingToast.hide();
      // Success - new restaurant created
      const restaurantId = responseData.restaurant_id;

      showLocalToast('Success', 'Restaurant added to your list!', 'success', [
        {
          text: 'View Restaurant',
          icon: 'fas fa-eye',
          class: 'btn-light',
          action: 'navigate',
          data: { url: `/restaurants/${restaurantId}` },
        },
      ]);
    } else if (addResponse.status === 409) {
      // Hide the adding toast before showing the conflict toast
      if (addingToast && addingToast.hide) addingToast.hide();
      // Conflict - restaurant already exists
      const restaurantId = responseData.restaurant_id;

      showLocalToast('Restaurant Already Exists', responseData.message, 'warning', [
        {
          text: 'View Restaurant',
          icon: 'fas fa-eye',
          class: 'btn-outline-primary',
          action: 'navigate',
          data: { url: `/restaurants/${restaurantId}` },
        },
        {
          text: 'Update Info',
          icon: 'fas fa-edit',
          class: 'btn-outline-warning',
          action: 'navigate',
          data: { url: `/restaurants/${restaurantId}/edit` },
        },
      ]);
    } else {
      if (addingToast && addingToast.hide) addingToast.hide();
      // Other error
      throw new Error(responseData.message || 'Failed to add restaurant');
    }
  } catch {
    console.error('Error adding restaurant:', error);
    showLocalToast('Error', error.message, 'error');
  }
};

// Initialize the map-based restaurant search when DOM is ready
document.addEventListener('DOMContentLoaded', async() => {
  const container = document.getElementById('map-restaurant-search-container');

  if (container) {
    try {
      // Import the MapRestaurantSearch component
      const { MapRestaurantSearch } = await import(
        '/static/js/components/map-restaurant-search.js'
      );

      // Get configuration from data attributes
      const config = window.PLACES_SEARCH_CONFIG || {};

      // Initialize the map-based search component
      const mapSearch = new MapRestaurantSearch(container, {
        googleMapsApiKey: window.GOOGLE_MAPS_API_KEY,
        googleMapsMapId: config.googleMapsMapId,
        onSelect(restaurant) {
          console.log('Restaurant selected:', restaurant);
          // Handle restaurant selection
        },
        onError(error) {
          console.error('Search error:', error);
          showLocalToast('Search Error', error.message, 'error');
        },
        onResults(results) {
          console.log('Search results:', results);
          // Handle search results
        },
      });

      // Make the component globally accessible for debugging
      window.mapSearch = mapSearch;
    } catch {
      console.error('Failed to initialize map-based search:', error);
      container.innerHTML = `
                <div class="alert alert-danger">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    Failed to load the map-based restaurant search. Please refresh the page and try again.
                </div>
            `;
    }
  }
});
