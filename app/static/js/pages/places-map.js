/**
 * Places Map Page
 * Dedicated page for viewing user's restaurants on a map.
 * Uses PlacesMapView component (My Restaurants, Nearby, Find New modes).
 */

import { PlacesMapView } from '../components/places-map-view.js';
import { toast } from '../utils/notifications.js';

window.addToMyRestaurants = async function addToMyRestaurants(placeId) {
  try {
    if (!placeId || placeId === 'null' || placeId === 'undefined') {
      throw new Error(`Invalid place ID: ${placeId}`);
    }

    const configElement = document.getElementById('places-map-config');
    const mapConfig = configElement ? JSON.parse(configElement.textContent) : {};
    const csrfToken = mapConfig.csrfToken || '';
    const addRestaurantUrl = mapConfig.addRestaurantUrl || '';

    if (!csrfToken || !addRestaurantUrl) {
      throw new Error('Missing configuration for restaurant addition');
    }

    toast.info('Adding restaurant to your list...');

    const detailsResponse = await fetch(`/restaurants/api/places/details/${placeId}?include_enterprise=false`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!detailsResponse.ok) {
      throw new Error(`Failed to get restaurant details: ${detailsResponse.status}`);
    }

    const restaurantData = await detailsResponse.json();

    const requestData = {
      name: restaurantData.name || '',
      type: restaurantData.type || 'restaurant',
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
      price_level: restaurantData.price_level ?? null,
      is_chain: restaurantData.is_chain ? true : false,
      rating: restaurantData.rating || '',
      notes: restaurantData.notes || '',
      latitude: restaurantData.latitude ?? null,
      longitude: restaurantData.longitude ?? null,
    };

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
      toast.success('Restaurant added to your list!');
      return {
        success: true,
        exists: false,
        restaurantId: responseData?.restaurant_id || null,
      };
    }

    if (addResponse.status === 409) {
      toast.warning(responseData.message || 'Restaurant already exists in your list.');
      return {
        success: false,
        exists: true,
        restaurantId: responseData?.restaurant_id || null,
      };
    }

    throw new Error(responseData.message || 'Failed to add restaurant');
  } catch (error) {
    toast.error(error?.message || 'Failed to add restaurant');
    throw error;
  }
};

document.addEventListener('DOMContentLoaded', () => {
  const container = document.getElementById('places-map-container');
  if (!container) return;

  try {
    container.placesMapView = new PlacesMapView(container, {
      onError: (err) => toast.error(err?.message || 'Map error'),
    });
  } catch (err) {
    toast.error(err?.message || 'Failed to load map.');
    const sidebar = document.getElementById('places-sidebar-content');
    if (sidebar) {
      sidebar.innerHTML =
        '<div class="alert alert-danger mb-0"><i class="fas fa-exclamation-triangle me-2"></i>Failed to load map. Check the console for details.</div>';
    }
  }
});
