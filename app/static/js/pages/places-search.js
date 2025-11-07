/**
 * Places Search Page
 *
 * Handles map-based restaurant search functionality and restaurant management.
 * This replaces the inline JavaScript in the places_search.html template.
 */

import { toast } from '../utils/notifications.js';

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

    // Show loading state
    toast.info('Adding restaurant to your list...');

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

    // Create JSON data for adding restaurant
    const requestData = {
      name: restaurantData.name || '',
      type: 'restaurant',
      description: restaurantData.description || '',
      address_line_1: restaurantData.address_line_1 || '',
      address_line_2: restaurantData.address_line_2 || '',
      city: restaurantData.city || '',
      state: restaurantData.state || '',
      postal_code: restaurantData.postal_code || '',
      country: restaurantData.country || '',
      phone: restaurantData.phone || '',
      website: restaurantData.website || '',
      email: restaurantData.email || '',
      google_place_id: restaurantData.google_place_id || '',
      cuisine: restaurantData.cuisine || '',
      service_level: restaurantData.service_level || '',
      is_chain: restaurantData.is_chain ? true : false,
      rating: restaurantData.rating || '',
      notes: restaurantData.notes || '',
    };

    // Submit the form
    const addResponse = await fetch(addRestaurantUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken,
        'X-Requested-With': 'XMLHttpRequest',
      },
      body: JSON.stringify(requestData),
    });

    const responseData = await addResponse.json();

    if (addResponse.status === 200 || addResponse.status === 201) {
      // Success - new restaurant created
      toast.success('Restaurant added to your list!');
    } else if (addResponse.status === 409) {
      // Conflict - restaurant already exists
      console.log('409 Response data:', responseData);

      // Extract restaurant ID from the error data
      const restaurantId = responseData.error?.existing_restaurant?.id ||
                          responseData.redirect_url?.split('/').pop() ||
                          responseData.restaurant_id;

      console.log('Restaurant ID:', restaurantId);

      // Build the correct URLs
      const viewUrl = `/restaurants/${restaurantId}`;
      const editUrl = `/restaurants/${restaurantId}/edit`;

      console.log('View URL:', viewUrl);
      console.log('Edit URL:', editUrl);

      toast.warning(responseData.message);
    } else {
      // Other error
      throw new Error(responseData.message || 'Failed to add restaurant');
    }
  } catch (error) {
    console.error('Error adding restaurant:', error);
    toast.error(error.message);
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

      // Debug: Log configuration values
      console.log('Places search config:', config);
      console.log('Google Maps API Key:', window.GOOGLE_MAPS_API_KEY);
      console.log('Google Maps Map ID:', config.googleMapsMapId);

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
          toast.error(error.message);
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
