/**
 * Search component for restaurant search functionality
 */

import { GoogleMapsLoader } from '../utils/google-maps.js';

document.addEventListener('DOMContentLoaded', () => {
  const searchInput = document.getElementById('restaurantSearchInput');
  const searchSuggestions = document.getElementById('searchSuggestions');

  if (!searchInput || !searchSuggestions) return;

  // Initialize search suggestions
  let autocomplete;

  const initAutocomplete = () => {
    if (typeof google === 'undefined' || !google.maps || !google.maps.places) {
      console.warn('Google Maps API not available for autocomplete');
      return;
    }

    autocomplete = new google.maps.places.Autocomplete(searchInput, {
      types: ['establishment'],
      componentRestrictions: { country: 'us' },
      fields: ['name', 'formatted_address', 'place_id'],
    });

    autocomplete.addListener('place_changed', () => {
      const place = autocomplete.getPlace();
      if (!place.place_id) return;

      // Redirect to the add restaurant page with place details
      window.location.href = `/restaurants/add?place_id=${place.place_id}`;
    });
  };

  // Load Google Maps API and initialize autocomplete
  if (window.GOOGLE_MAPS_API_KEY) {
    GoogleMapsLoader.loadApi(window.GOOGLE_MAPS_API_KEY, initAutocomplete, ['places'])
      .catch((error) => {
        console.error('Failed to load Google Maps API:', error);
      });
  } else {
    console.error('Google Maps API key not found. Please set window.GOOGLE_MAPS_API_KEY');
  }
});
