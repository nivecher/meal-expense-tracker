import { get, post } from '../utils/api-utils.js';

/**
 * Initialize the restaurant list page
 */
function init() {
  'use strict';

  const map_container = document.getElementById('map');
  if (!map_container) {
    console.log('Map container not found, skipping map initialization');
    return;
  }

  console.log('Map container found, initializing map...');

  initialize_restaurant_map(map_container);
}

function initialize_restaurant_map(map_container) {

  let map;
  let userLocationMarker;
  let markers = [];
  let userPosition = null;
  let searchCircle = null;
  let markerCluster = null;
  let currentRequest = null;

  const radiusSlider = document.getElementById('radius-slider');
  const radiusValue = document.getElementById('radius-value');
  const searchKeywordInput = document.getElementById('search-keyword');
  const searchButton = document.getElementById('search-button');
  const zoomInBtn = document.getElementById('zoomIn');
  const zoomOutBtn = document.getElementById('zoomOut');
  const resultsContainer = document.getElementById('search-results');
  const resultsCount = document.getElementById('results-count');

  const DEFAULT_ZOOM = 15;
  const MIN_ZOOM = 2;
  const MAX_ZOOM = 19;
  const DEFAULT_RADIUS = 5000;
  const MAX_RADIUS = 20000;

  const getUnitSystem = () => {
    const lang = (navigator.language || 'en-US').toLowerCase();
    if (lang.startsWith('en')) {
      console.log(`[Debug] Detected English ('${lang}'). Using miles.`);
      return { name: 'miles', multiplier: 0.000621371, radius_unit: 'mi' };
    }
    console.log(`[Debug] Non-English language ('${lang}'). Using kilometers.`);
    return { name: 'km', multiplier: 0.001, radius_unit: 'km' };
  };

  const unitSystem = getUnitSystem();

  const initMarkerCluster = () => {
    if (markerCluster) {
      map.removeLayer(markerCluster);
    }
    markerCluster = L.markerClusterGroup({
      maxClusterRadius: 40,
      spiderfyOnMaxZoom: true,
      showCoverageOnHover: false,
      zoomToBoundsOnClick: true,
    });
    map.addLayer(markerCluster);
  };

  const updateStatus = (message, type = 'info') => {
    const statusContainer = document.getElementById('map-status-container');
    if (!statusContainer) return;
    const alertClass = type === 'danger' ? 'alert-danger' : (type === 'success' ? 'alert-success' : 'alert-info');
    statusContainer.innerHTML = `<div class="alert ${alertClass} alert-dismissible fade show" role="alert">${message}<button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button></div>`;
  };

  const debounce = (func, wait) => {
    let timeout;
    return (...args) => {
      const later = () => {
        clearTimeout(timeout);
        func(...args);
      };
      clearTimeout(timeout);
      timeout = setTimeout(later, wait);
    };
  };

  const clearMarkers = () => {
    if (markerCluster) {
      markerCluster.clearLayers();
    }
    markers = [];
  };

  const createPopupContent = (restaurant) => {
    let content = `<div class="restaurant-popup"><h6 class="mb-1">${restaurant.name || 'Unnamed Restaurant'}</h6>`;
    if (restaurant.rating) content += `<div class="d-flex align-items-center mb-1"><div class="text-warning me-1">${'★'.repeat(Math.floor(restaurant.rating))}${'☆'.repeat(5 - Math.floor(restaurant.rating))}</div><small class="text-muted ms-1">${restaurant.rating.toFixed(1)}</small></div>`;
    if (restaurant.vicinity || restaurant.formatted_address) content += `<p class="mb-1 small"><i class="fas fa-map-marker-alt me-1"></i>${restaurant.vicinity || restaurant.formatted_address}</p>`;
    if (restaurant.types) content += `<div class="mb-2">${restaurant.types.slice(0, 3).map((type) => `<span class="badge bg-light text-dark me-1 mb-1">${type.replace(/_/g, ' ')}</span>`).join('')}</div>`;
    content += `<div class="d-flex justify-content-between align-items-center"><button class="btn btn-sm btn-outline-primary" data-place-id="${restaurant.place_id || ''}"><i class="fas fa-plus me-1"></i> Add</button><div class="btn-group">${restaurant.website ? `<a href="${restaurant.website}" target="_blank" rel="noopener noreferrer" class="btn btn-sm btn-outline-secondary"><i class="fas fa-external-link-alt"></i></a>` : ''}<button class="btn btn-sm btn-outline-secondary" data-lat="${restaurant.geometry.location.lat}" data-lng="${restaurant.geometry.location.lng}" title="Copy coordinates"><i class="fas fa-copy"></i></button></div></div></div>`;
    return content;
  };

  const calculateDistance = (lat1, lon1, lat2, lon2) => {
    const R = 6371; // Radius of the Earth in kilometers
    const dLat = (lat2 - lat1) * Math.PI / 180;
    const dLon = (lon2 - lon1) * Math.PI / 180;
    const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) + Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) * Math.sin(dLon / 2) * Math.sin(dLon / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    const distanceInKm = R * c;

    const userLocale = navigator.language || 'en-US';
    if (userLocale.startsWith('en-US') || userLocale.startsWith('en-GB')) {
      const distanceInMiles = distanceInKm * 0.621371;
      return { distance: distanceInMiles.toFixed(2), unit: 'mi' };
    }
    return { distance: distanceInKm.toFixed(2), unit: 'km' };
  };

  /**
   * Add a restaurant to the user's list
   * @param {string} placeId - The Google Places ID of the restaurant
   * @returns {Promise<Object>} The added restaurant data
   */
  const addRestaurant = async(placeId) => {
    if (!placeId) {
      updateStatus('Error: Missing place ID', 'danger');
      throw new Error('Missing place ID');
    }

    updateStatus('Adding restaurant to your list...', 'info');

    try {
      const result = await post('/restaurants/api/add', { place_id: placeId });
      updateStatus('Restaurant added successfully!', 'success');
      return result;
    } catch (error) {
      console.error('Error adding restaurant:', error);
      const errorMessage = error.message || 'Failed to add restaurant. Please try again.';
      updateStatus(errorMessage, 'danger');
      throw error;
    }
  };

  const updateSearchArea = (center, radius) => {
    if (searchCircle) {
      map.removeLayer(searchCircle);
    }

    searchCircle = L.circle([center.lat, center.lng], {
      radius,
      color: '#3388ff',
      weight: 2,
      fillColor: '#3388ff',
      fillOpacity: 0.1,
    }).addTo(map);

    if (!markers.length) {
      map.fitBounds(searchCircle.getBounds());
    }
  };

  const displaySearchResults = (results, userPosition) => {
    if (!resultsContainer) {
      console.error('Search results container not found');
      return;
    }

    clearMarkers();

    if (!Array.isArray(results) || results.length === 0) {
      resultsContainer.innerHTML = `
        <div class="alert alert-info m-3">
            <i class="fas fa-info-circle me-2"></i>
            No restaurants found. Try adjusting your search criteria or expanding the search radius.
        </div>`;
      return;
    }

    const validResults = results.filter((restaurant) =>
      restaurant &&
      restaurant.geometry?.location &&
      restaurant.geometry.location.lat &&
      restaurant.geometry.location.lng,
    );

    if (validResults.length === 0) {
      resultsContainer.innerHTML = `
        <div class="alert alert-warning m-3">
            <i class="fas fa-exclamation-triangle me-2"></i>
            No valid restaurant locations found in the results.
        </div>`;
      return;
    }

    if (userPosition) {
      validResults.forEach((restaurant) => {
        const { lat, lng } = restaurant.geometry.location;
        restaurant.distance = calculateDistance(
          userPosition.lat,
          userPosition.lng,
          lat,
          lng,
        );
      });
      validResults.sort((a, b) => (a.distance || Infinity) - (b.distance || Infinity));
    }

    const generateResultsHTML = (restaurants) => {
      const searchSummary = `
            <div class="search-summary mb-2 text-muted">
                Found ${restaurants.length} ${restaurants.length === 1 ? 'restaurant' : 'restaurants'}
            </div>`;

      const resultsList = restaurants.map((restaurant, index) => {
        const { name, geometry, vicinity, formatted_address, opening_hours, rating,
          user_ratings_total, price_level, place_id } = restaurant;
        const { lat, lng } = geometry.location;

        const distance = restaurant.distance ?
          (restaurant.distance < 1000 ?
            `${Math.round(restaurant.distance)}m` :
            `${(restaurant.distance / 1000).toFixed(1)}km`) :
          '';

        const ratingStars = rating ?
          `★${rating.toFixed(1)}${user_ratings_total ? ` (${user_ratings_total})` : ''}` :
          'Not rated';

        const priceIndicator = price_level ?
          `• ${'💲'.repeat(Math.min(price_level, 4))}` : '';

        const isOpenNow = opening_hours?.open_now !== undefined
          ? (opening_hours.open_now
            ? '<span class="badge bg-success">Open Now</span>'
            : '<span class="badge bg-danger">Closed</span>')
          : '';

        return `
                <div class="list-group-item list-group-item-action restaurant-item"
                     data-place-id="${place_id || index}"
                     data-lat="${lat}"
                     data-lng="${lng}">
                    <div class="d-flex w-100 justify-content-between align-items-start">
                        <h6 class="mb-1">
                            <i class="fas fa-utensils me-2"></i>
                            ${name || 'Unnamed Restaurant'}
                        </h6>
                        <div class="d-flex align-items-center">
                            ${isOpenNow}
                            ${distance ? `<small class="ms-2">${distance}</small>` : ''}
                        </div>
                    </div>
                    <p class="mb-1 text-muted small">
                        <i class="fas fa-map-marker-alt me-1"></i>
                        ${vicinity || formatted_address || 'Address not available'}
                    </p>
                    <div class="d-flex justify-content-between align-items-center">
                        <small class="text-warning">
                            <i class="fas fa-star"></i> ${ratingStars} ${priceIndicator}
                        </small>
                        <button class="btn btn-sm btn-outline-primary add-restaurant"
                                data-place-id="${place_id || index}">
                            <i class="fas fa-plus"></i> Add
                        </button>
                    </div>
                </div>`;
      }).join('');

      return `
            ${searchSummary}
            <div class="search-results-list" style="max-height: 70vh; overflow-y: auto;">
                <div class="list-group list-group-flush">
                    ${resultsList}
                </div>
            </div>`;
    };

    const createMarkers = (restaurants) => {
      const newMarkers = [];

      restaurants.forEach((restaurant) => {
        if (!restaurant.geometry?.location) return;

        const { lat, lng } = restaurant.geometry.location;
        const marker = L.marker([lat, lng], {
          title: restaurant.name,
          alt: restaurant.name || 'Restaurant',
          riseOnHover: true,
          customId: restaurant.place_id || `restaurant-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
        });

        const distance = restaurant.distance ?
          (restaurant.distance < 1000 ?
            `${Math.round(restaurant.distance)}m` :
            `${(restaurant.distance / 1000).toFixed(1)}km`) :
          '';

        const popupContent = createPopupContent(restaurant, distance);
        marker.bindPopup(popupContent, {
          maxWidth: 300,
          minWidth: 200,
          className: 'restaurant-popup',
        });

        marker.addTo(map);
        newMarkers.push(marker);

        const item = document.querySelector(`.restaurant-item[data-place-id="${restaurant.place_id}"]`);
        if (item) {
          marker.on('mouseover', () => {
            item.classList.add('bg-light');
            item.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
          });

          marker.on('mouseout', () => {
            item.classList.remove('bg-light');
          });

          item.addEventListener('mouseenter', () => {
            marker.openPopup();
          });

          item.addEventListener('mouseleave', () => {
            marker.closePopup();
          });
        }
      });

      if (markerCluster) {
        markerCluster.clearLayers();
        markerCluster.addLayers(newMarkers);
      }

      markers = newMarkers;
    };

    const setupResultItemInteractions = () => {
      document.querySelectorAll('.restaurant-item').forEach((item) => {
        item.addEventListener('click', function(e) {
          if (e.target.closest('.add-restaurant')) {
            return;
          }

          const lat = parseFloat(this.dataset.lat);
          const lng = parseFloat(this.dataset.lng);
          const { placeId } = this.dataset;

          if (isNaN(lat) || isNaN(lng)) {
            console.error('Invalid coordinates for restaurant item');
            return;
          }

          const marker = markers.find((m) =>
            m.options.customId === placeId ||
                    (m.getLatLng().lat === lat && m.getLatLng().lng === lng),
          );

          if (marker) {
            map.setView(marker.getLatLng(), map.getZoom(), {
              animate: true,
              duration: 0.5,
            });

            marker.openPopup();

            document.querySelectorAll('.restaurant-item').forEach((el) => {
              el.classList.remove('active');
            });
            this.classList.add('active');
          }
        });
      });

      document.querySelectorAll('.add-restaurant').forEach((button) => {
        const newButton = button.cloneNode(true);
        button.parentNode.replaceChild(newButton, button);

        newButton.addEventListener('click', (e) => {
          e.stopPropagation();
          const { placeId } = newButton.dataset;
          if (placeId) {
            addRestaurant(placeId);
          }
        });
      });
    };

    resultsContainer.innerHTML = generateResultsHTML(validResults);
    createMarkers(validResults);
    setupResultItemInteractions();

    if (markers.length > 0) {
      const group = L.featureGroup(markers);
      map.fitBounds(group.getBounds().pad(0.1));
    }

    if (searchCircle) {
      map.fitBounds(searchCircle.getBounds().pad(0.1));
    }
  };

  /**
   * Search for nearby restaurants based on user's location and search criteria
   * @returns {Promise<void>}
   */
  const searchNearbyRestaurants = async() => {
    if (!userPosition) {
      updateStatus('Please allow location access to search for nearby restaurants.', 'warning');
      return;
    }

    const radiusInKm = parseInt(radiusSlider.value, 10);
    const radiusInMeters = Math.min(radiusInKm * 1000, MAX_RADIUS);
    const keyword = searchKeywordInput.value.trim();

    if (currentRequest) {
      currentRequest.abort();
      currentRequest = null;
    }

    updateSearchArea(userPosition, radiusInMeters);
    updateStatus('Searching for nearby restaurants...', 'info');

    // Show loading state
    if (resultsContainer) {
      resultsContainer.innerHTML = `
        <div class="search-loading">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
            <p class="mt-2">Searching restaurants within ${radiusInKm} km...</p>
        </div>`;
    }

    // Set up abort controller for the request
    const controller = new AbortController();
    currentRequest = controller;

    try {
      // Prepare search parameters
      const params = {
        lat: userPosition.lat,
        lng: userPosition.lng,
        radius: radiusInMeters,
      };

      if (keyword) {
        params.keyword = keyword;
      }

      // Use our API utility to make the request
      const data = await get('/api/places/search', params, {
        signal: controller.signal,
      });

      // Display the search results
      displaySearchResults(data.results || [], userPosition);

      // Update status and result count
      const resultCount = data.results ? data.results.length : 0;
      updateStatus(`Found ${resultCount} restaurant${resultCount !== 1 ? 's' : ''}`, 'success');

      if (resultsCount) {
        resultsCount.textContent = resultCount;
      }
    } catch (error) {
      // Handle aborted requests
      if (error.name === 'AbortError') {
        console.log('Search was cancelled');
        return;
      }

      console.error('Error searching for restaurants:', error);

      // Show user-friendly error message
      const errorMessage = error.message || 'An error occurred while searching for restaurants.';
      updateStatus(`Error: ${errorMessage}`, 'danger');

      // Update UI with error state
      if (resultsContainer) {
        resultsContainer.innerHTML = `
          <div class="alert alert-danger m-3">
              <i class="fas fa-exclamation-triangle me-2"></i>
              Failed to load restaurants. ${errorMessage}
          </div>`;
      }
    } finally {
      // Clean up
      if (currentRequest === controller) {
        currentRequest = null;
      }

      // Trigger map load event if available
      if (map) {
        map.fire('load');
      }
    }
  };

  const geolocationSuccess = (position) => {
    console.log('Geolocation success:', position);

    userPosition = {
      lat: position.coords.latitude,
      lng: position.coords.longitude,
      accuracy: position.coords.accuracy || 100,
    };

    const mapLoading = document.getElementById('map-loading');
    const mapContainer = document.getElementById('map-container');
    if (mapLoading && mapContainer) {
      mapLoading.style.display = 'none';
      mapContainer.style.display = 'block';
    }

    updateStatus('Location found! Searching for nearby restaurants...', 'success');

    map.flyTo([userPosition.lat, userPosition.lng], DEFAULT_ZOOM, {
      duration: 1,
      easeLinearity: 0.25,
    });

    if (!userLocationMarker) {
      const pulseIcon = L.divIcon({
        className: 'user-location-marker',
        html: '<div class="pulse-marker"></div>',
        iconSize: [20, 20],
        iconAnchor: [10, 10],
        popupAnchor: [0, -10],
      });

      userLocationMarker = L.marker([userPosition.lat, userPosition.lng], {
        icon: pulseIcon,
        zIndexOffset: 1000,
        interactive: false,
      }).addTo(map);

      if (userPosition.accuracy) {
        L.circle([userPosition.lat, userPosition.lng], {
          radius: userPosition.accuracy,
          color: '#0d6efd',
          fillColor: '#0d6efd',
          fillOpacity: 0.1,
          weight: 1,
          className: 'accuracy-circle',
          interactive: false,
        }).addTo(map);
      }
    } else {
      userLocationMarker.setLatLng([userPosition.lat, userPosition.lng]);
    }

    const radius = radiusSlider ? parseInt(radiusSlider.value, 10) * 1000 : DEFAULT_RADIUS;
    updateSearchArea(userPosition, radius);

    searchNearbyRestaurants();
  };

  const geolocationError = (error) => {
    console.error('Geolocation error:', error);
    updateStatus(`Error detecting location: ${error.message}. You can still search manually.`, 'danger');
  };

  const setupEventListeners = () => {
    if (searchButton) {
      searchButton.addEventListener('click', searchNearbyRestaurants);
    }

    if (radiusSlider) {
      radiusSlider.addEventListener('input', () => {
        radiusValue.textContent = radiusSlider.value;
        if (userPosition) {
          const radius = parseInt(radiusSlider.value, 10) * 1000;
          updateSearchArea(userPosition, radius);
          debounce(searchNearbyRestaurants, 500)();
        }
      });
    }

    if (searchKeywordInput) {
      searchKeywordInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
          searchNearbyRestaurants();
        }
      });
    }

    if (zoomInBtn) {
      zoomInBtn.addEventListener('click', () => {
        map.zoomIn();
      });
    }

    if (zoomOutBtn) {
      zoomOutBtn.addEventListener('click', () => {
        map.zoomOut();
      });
    }
  };

  // ... (rest of the file)

  const initMap = async() => {
    updateStatus('Initializing map...', 'info');

    try {
      map = L.map('map', {
        center: [20, 0],
        zoom: 2,
        zoomControl: false,
        preferCanvas: true,
        fadeAnimation: true,
        zoomAnimation: true,
        minZoom: MIN_ZOOM,
        maxZoom: MAX_ZOOM,
      });

      // Initialize the map tile layer
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        maxZoom: MAX_ZOOM,
        minZoom: MIN_ZOOM,
      }).addTo(map);

      initMarkerCluster();

      L.control.zoom({
        position: 'topright',
      }).addTo(map);

      L.control.scale({
        imperial: unitSystem.name === 'miles',
        metric: unitSystem.name === 'km',
        maxWidth: 200,
        position: 'bottomright',
      }).addTo(map);

      const locateControl = L.control.locate({
        position: 'topleft',
        drawCircle: true,
        showPopup: false,
        locateOptions: {
          maxZoom: DEFAULT_ZOOM,
          enableHighAccuracy: true,
          timeout: 10000,
          maximumAge: 0,
        },
        strings: {
          title: 'Show my location',
          popup: 'You are within {distance} {unit} from this point',
          outsideMapBoundsMsg: 'You seem located outside the map bounds',
        },
        onLocationError: (err) => {
          updateStatus(`Location error: ${err.message}`, 'danger');
          console.error('Location error:', err);
        },
        onLocationOutsideMapBounds: () => {
          updateStatus('Your location is outside the map bounds', 'warning');
        },
      }).addTo(map);

      locateControl.start();
      setupEventListeners();

      if (navigator.geolocation) {
        try {
          updateStatus('Detecting your location...', 'info');
          const position = await getCurrentPosition({
            enableHighAccuracy: true,
            timeout: 10000,
            maximumAge: 0,
          });
          geolocationSuccess(position);
        } catch (error) {
          geolocationError(error);
        }
      } else {
        updateStatus('Geolocation is not supported by your browser.', 'warning');
      }
    } catch (error) {
      console.error('Error initializing map:', error);
      updateStatus('Failed to initialize map. Please refresh the page to try again.', 'danger');
    }

    tileLayer.on('loading', () => {
      updateStatus('Loading map data...', 'info');
    });
    tileLayer.on('load', () => {
      updateStatus('Map loaded', 'success');
    });

    document.getElementById('map-loading').style.display = 'none';
    const mapContainer = document.getElementById('map-container');
    if (mapContainer) {
      mapContainer.style.display = 'block';
      setTimeout(() => map.invalidateSize(), 100);
    }
  };

  initMap();

  document.body.addEventListener('click', (e) => {
    if (e.target.closest('[data-place-id]')) {
      addRestaurant(e.target.closest('[data-place-id]').dataset.placeId);
    }
    if (e.target.closest('[data-lat][data-lng]')) {
      const btn = e.target.closest('[data-lat][data-lng]');
      if (btn.title === 'Copy coordinates') {
        copyCoordinates(btn.dataset.lat, btn.dataset.lng);
      }
    }
  });

  document.body.addEventListener('mouseover', (e) => {
    if (e.target.closest('.list-group-item-action[data-lat]')) {
      centerMapOnRestaurant(e.target.closest('.list-group-item-action[data-lat]'));
    }
  });
}

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}

// Export for testing and explicit initialization
export { init };
