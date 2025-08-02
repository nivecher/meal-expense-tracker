/**
 * Search component for restaurant search functionality
 */

document.addEventListener('DOMContentLoaded', () => {
  const searchInput = document.getElementById('restaurantSearchInput');
  const searchSuggestions = document.getElementById('searchSuggestions');

  if (!searchInput || !searchSuggestions) return;

  // Initialize Google Maps API key if it's not already set
  if (typeof google === 'undefined' || !google.maps) {
    const script = document.createElement('script');
    script.src = `https://maps.googleapis.com/maps/api/js?key=${window.GOOGLE_MAPS_API_KEY}&libraries=places`;
    script.async = true;
    script.defer = true;
    document.head.appendChild(script);
  }

  // Initialize search suggestions
  let autocomplete;

  function initAutocomplete () {
    if (typeof google === 'undefined' || !google.maps.places) {
      setTimeout(initAutocomplete, 100);
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
  }

  // Initialize when Google Maps API is loaded
  if (typeof google !== 'undefined' && google.maps && google.maps.places) {
    initAutocomplete();
  } else {
    window.initAutocomplete = initAutocomplete;
  }
});
