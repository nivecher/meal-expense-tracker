/**
 * Restaurant Places Search Page - Enhanced
 * Uses consolidated utilities and Google Maps integration with map display
 */

import { logger } from '../utils/core-utils.js';
import { showSuccessToast, showErrorToast, showLoadingOverlay } from '../utils/ui-utils.js';
import { post } from '../utils/api-utils.js';
import { googleMapsManager, googleMapsService, googlePlacesService } from '../utils/google-maps.js';

// Page state
let currentLoadingOverlay = null;
let map = null;
let markers = [];
let infoWindow = null;

/**
 * Create restaurant card HTML
 */
function createRestaurantCard(restaurant) {
  const rating = restaurant.rating ? `
    <div class="mb-2">
      <span class="badge bg-warning text-dark">
        <i class="fas fa-star"></i> ${restaurant.rating}
      </span>
      ${restaurant.userRatingsTotal ? `<small class="text-muted ms-1">(${restaurant.userRatingsTotal} reviews)</small>` : ''}
    </div>
  ` : '';

  const photo = restaurant.photos?.[0] ? `
    <img src="${restaurant.photos[0].url}" alt="${restaurant.name}" class="card-img-top" style="height: 200px; object-fit: cover;">
  ` : '';

  return `
    <div class="col-md-6 col-lg-4 mb-4">
      <div class="card h-100">
        ${photo}
        <div class="card-body">
          <h5 class="card-title">${restaurant.name}</h5>
          <p class="card-text text-muted small">${restaurant.address}</p>
          ${rating}
          <button class="btn btn-primary select-restaurant" data-restaurant='${JSON.stringify(restaurant)}'>
            <i class="fas fa-plus"></i> Add This Restaurant
          </button>
        </div>
      </div>
    </div>
  `;
}

/**
 * Handle restaurant selection
 */
async function selectRestaurant(restaurantData) {
  try {
    const restaurant = JSON.parse(restaurantData);

    // Show loading
    currentLoadingOverlay = showLoadingOverlay('Adding restaurant...');

    // Prepare data for submission
    const data = {
      name: restaurant.name,
      address: restaurant.address,
      placeId: restaurant.placeId,
      latitude: restaurant.location?.lat,
      longitude: restaurant.location?.lng,
      rating: restaurant.rating,
      priceLevel: restaurant.priceLevel,
    };

    // Submit to server
    const response = await post('/restaurants/add-from-google-places', data);

    if (response.success) {
      showSuccessToast('Restaurant added successfully!');

      // Redirect to restaurant details or form
      if (response.redirect_url) {
        setTimeout(() => {
          window.location.href = response.redirect_url;
        }, 1000);
      }
    } else {
      throw new Error(response.message || 'Failed to add restaurant');
    }

  } catch (error) {
    logger.error('Failed to add restaurant:', error);

    // Handle structured error responses for enhanced UX
    if (error.error && error.error.code === 'DUPLICATE_GOOGLE_PLACE_ID') {
      // Show enhanced modal for Google Place ID duplicates
      showDuplicateGooglePlaceIdModal(error.error);
    } else if (error.error && error.error.code === 'DUPLICATE_RESTAURANT') {
      // Show enhanced modal for name/city duplicates
      showDuplicateRestaurantModal(error.error);
    } else if (error.message && error.message.includes('Google Place ID')) {
      showErrorToast('This restaurant already exists in your list. Please search for it in your existing restaurants.');
    } else if (error.message && error.message.includes('already exists')) {
      showErrorToast('A similar restaurant already exists. Please check your existing restaurants or modify the details.');
    } else {
      showErrorToast('Failed to add restaurant. Please check your connection and try again.');
    }
  } finally {
    if (currentLoadingOverlay) {
      currentLoadingOverlay.hide();
      currentLoadingOverlay = null;
    }
  }
}

/**
 * Display search results
 */
function displayResults(restaurants) {
  const resultsContainer = document.getElementById('search-results');

  if (!resultsContainer) {
    logger.warn('Results container not found');
    return;
  }

  if (!restaurants || !restaurants.length) {
    resultsContainer.innerHTML = `
      <div class="text-center py-4">
        <i class="fas fa-search fa-3x text-muted mb-3"></i>
        <h4>No restaurants found</h4>
        <p class="text-muted">Try searching with a different term or location.</p>
      </div>
    `;
    return;
  }

  resultsContainer.innerHTML = restaurants.map((restaurant) => createRestaurantCard(restaurant)).join('');

  // Add event listeners to select buttons
  resultsContainer.querySelectorAll('.select-restaurant').forEach((button) => {
    button.addEventListener('click', () => selectRestaurant(button.dataset.restaurant));
  });

  logger.info(`Displayed ${restaurants.length} restaurant results`);
}

/**
 * Initialize the map
 */
async function initMap() {
  try {
    const mapElement = document.getElementById('map');
    if (!mapElement) {
      logger.warn('Map container not found');
      return false;
    }

    // Hide map overlay once initialized
    const mapOverlay = document.getElementById('map-overlay');

    // Get user's current location or use default
    let userLocation = { lat: 40.7128, lng: -74.0060 }; // Default to NYC

    try {
      const position = await getCurrentLocation();
      if (position) {
        userLocation = position;
      }
    } catch (error) {
      logger.info('Using default location (geolocation unavailable)');
    }

    // Create the map
    map = new google.maps.Map(mapElement, {
      zoom: 13,
      center: userLocation,
      mapTypeId: google.maps.MapTypeId.ROADMAP,
      styles: [
        {
          featureType: 'poi.business',
          elementType: 'labels',
          stylers: [{ visibility: 'on' }],
        },
      ],
    });

    // Create info window
    infoWindow = new google.maps.InfoWindow();

    // Hide the loading overlay
    if (mapOverlay) {
      mapOverlay.style.display = 'none';
    }

    logger.info('Map initialized successfully');
    return true;
  } catch (error) {
    logger.error('Failed to initialize map:', error);
    return false;
  }
}

/**
 * Get user's current location
 */
function getCurrentLocation() {
  return new Promise((resolve, reject) => {
    if (!navigator.geolocation) {
      reject(new Error('Geolocation not supported'));
      return;
    }

    navigator.geolocation.getCurrentPosition(
      (position) => {
        resolve({
          lat: position.coords.latitude,
          lng: position.coords.longitude,
        });
      },
      (error) => {
        reject(error);
      },
      {
        enableHighAccuracy: true,
        timeout: 5000,
        maximumAge: 0,
      },
    );
  });
}

/**
 * Clear existing markers
 */
function clearMarkers() {
  markers.forEach((marker) => marker.setMap(null));
  markers = [];
}

/**
 * Create a marker for a restaurant
 */
function createMarker(restaurant) {
  if (!restaurant.location || !map) return null;

  const marker = new google.maps.Marker({
    position: restaurant.location,
    map,
    title: restaurant.name,
    icon: {
      url: 'https://maps.google.com/mapfiles/ms/icons/restaurant.png',
      scaledSize: new google.maps.Size(32, 32),
    },
  });

  // Add click listener to show info window
  marker.addListener('click', () => {
    const content = `
      <div style="max-width: 250px;">
        <h6>${restaurant.name}</h6>
        <p class="small text-muted mb-1">${restaurant.address}</p>
        ${restaurant.rating ? `<div class="mb-2"><span class="badge bg-warning text-dark">★ ${restaurant.rating}</span></div>` : ''}
        <button class="btn btn-sm btn-primary select-from-map" data-restaurant='${JSON.stringify(restaurant)}'>
          <i class="fas fa-plus me-1"></i>Add Restaurant
        </button>
      </div>
    `;

    infoWindow.setContent(content);
    infoWindow.open(map, marker);
  });

  markers.push(marker);
  return marker;
}

/**
 * Handle search form submission
 */
async function handleSearch(event) {
  event.preventDefault();

  const formData = new FormData(event.target);
  const query = formData.get('query')?.trim();

  if (!query) {
    showErrorToast('Please enter a restaurant name or location');
    return;
  }

  try {
    // Show loading
    const loadingIndicator = document.getElementById('loading-indicator');
    if (loadingIndicator) {
      loadingIndicator.style.display = 'block';
    }

    // Clear existing markers
    clearMarkers();

    // Search for restaurants using the Places service
    const results = await googlePlacesService.searchRestaurants(query);

    if (results && results.restaurants && results.restaurants.length > 0) {
      // Display results in the sidebar
      displayResults(results.restaurants);

      // Add markers to the map
      results.restaurants.forEach((restaurant) => {
        if (restaurant.location) {
          createMarker(restaurant);
        }
      });

      // Fit map to show all markers if we have any
      if (markers.length > 0) {
        const bounds = new google.maps.LatLngBounds();
        markers.forEach((marker) => bounds.extend(marker.getPosition()));
        map.fitBounds(bounds);

        // Don't zoom in too much for single results
        if (markers.length === 1) {
          map.setZoom(Math.min(map.getZoom(), 16));
        }
      }

      showSuccessToast(`Found ${results.restaurants.length} restaurants`);
    } else {
      displayResults([]);
      showErrorToast('No restaurants found for your search');
    }

  } catch (error) {
    logger.error('Restaurant search failed:', error);
    showErrorToast('Search failed. Please try again.');
    displayResults([]);
  } finally {
    const loadingIndicator = document.getElementById('loading-indicator');
    if (loadingIndicator) {
      loadingIndicator.style.display = 'none';
    }
  }
}

/**
 * Set up search functionality
 */
function setupSearch() {
  const searchForm = document.getElementById('google-search-form');
  const searchInput = document.getElementById('restaurant-query');

  if (!searchForm || !searchInput) {
    logger.warn('Search form elements not found');
    return;
  }

  searchForm.addEventListener('submit', handleSearch);

  // Auto-focus search input
  searchInput.focus();
}

/**
 * Initialize the restaurant search application
 */
async function initializeApp() {
  try {
    logger.info('Initializing restaurant places search...');

    // Wait for API key to be available (with timeout)
    let attempts = 0;
    const maxAttempts = 50; // Wait up to 5 seconds (50 * 100ms)

    while (!window.GOOGLE_MAPS_API_KEY && attempts < maxAttempts) {
      await new Promise((resolve) => setTimeout(resolve, 100));
      attempts++;
    }

    // Check if API key is available after waiting
    if (!window.GOOGLE_MAPS_API_KEY) {
      throw new Error('Google Maps API key is not configured');
    }

    // Initialize Google Maps service for places
    await googleMapsService.initializeForPlaces();

    // Double-check that the API is loaded
    if (!window.google?.maps?.places) {
      throw new Error('Google Maps Places library not available after loading');
    }

    // Initialize the Places service
    await googlePlacesService.init();

    // Initialize the map
    const mapInitialized = await initMap();
    if (!mapInitialized) {
      logger.warn('Map initialization failed, continuing without map');
    }

    // Set up search functionality
    setupSearch();

    // Set up event listeners for map-based restaurant selection
    document.addEventListener('click', (event) => {
      if (event.target.classList.contains('select-from-map')) {
        selectRestaurant(event.target.dataset.restaurant);
      }
    });

    logger.info('Restaurant places search initialized successfully');

  } catch (error) {
    logger.error('Failed to initialize restaurant places search:', error);
    showErrorToast('Failed to initialize search. Please check your connection and refresh the page.');

    // Still set up basic search functionality
    setupSearch();
  }
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initializeApp);
} else {
  // DOM is already loaded
  initializeApp().catch((error) => {
    logger.error('Unhandled error in initializeApp:', error);
  });
}

/**
 * Show modal for duplicate Google Place ID errors
 */
function showDuplicateGooglePlaceIdModal(error) {
  const { existing_restaurant, google_place_id } = error;

  showDuplicateRestaurantModal({
    title: 'Restaurant Already Exists',
    message: `You already have "${existing_restaurant.full_name}" in your restaurants.`,
    details: 'This restaurant has the same Google Place ID and cannot be added again.',
    existing_restaurant,
    primaryAction: {
      label: 'View Existing Restaurant',
      url: `/restaurants/${existing_restaurant.id}`,
    },
    secondaryAction: {
      label: 'Add Expense',
      url: `/expenses/add?restaurant_id=${existing_restaurant.id}`,
    },
  });
}

/**
 * Show modal for duplicate restaurant (name/city) errors
 */
function showDuplicateRestaurantModal(error) {
  if (typeof error === 'object' && error.existing_restaurant) {
    // Called with structured error object
    const { existing_restaurant, name, city } = error;

    showDuplicateModal({
      title: 'Similar Restaurant Found',
      message: `You already have a restaurant named "${name}"${city ? ` in ${city}` : ''}.`,
      details: 'This might be the same restaurant. You can view the existing one or modify your input to make it unique.',
      existing_restaurant,
      primaryAction: {
        label: 'View Existing Restaurant',
        url: `/restaurants/${existing_restaurant.id}`,
      },
      secondaryAction: {
        label: 'Continue Adding',
        action: () => showWarningToast('Please modify the restaurant name or location to make it unique.'),
      },
    });
  } else {
    // Called with options object (from the first function)
    showDuplicateModal(error);
  }
}

/**
 * Generic modal for duplicate restaurant conflicts
 */
function showDuplicateModal(options) {
  const {
    title,
    message,
    details,
    existing_restaurant,
    primaryAction,
    secondaryAction,
  } = options;

  const modalHtml = `
    <div class="modal fade duplicate-restaurant-modal" id="duplicateRestaurantModal" tabindex="-1" aria-labelledby="duplicateRestaurantModalLabel" aria-hidden="true">
      <div class="modal-dialog modal-dialog-centered">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title" id="duplicateRestaurantModalLabel">
              <i class="fas fa-exclamation-triangle text-warning me-2"></i>
              ${title}
            </h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
          </div>
          <div class="modal-body">
            <div class="alert alert-warning" role="alert">
              <strong>${message}</strong>
              <br><small class="text-muted">${details}</small>
            </div>

            <div class="card mt-3">
              <div class="card-body">
                <h6 class="card-title">
                  <i class="fas fa-utensils me-2"></i>
                  ${existing_restaurant.full_name}
                </h6>
                <div class="d-flex gap-2 mt-2">
                  <a href="/restaurants/${existing_restaurant.id}" class="btn btn-sm btn-outline-primary">
                    <i class="fas fa-eye me-1"></i>
                    View Details
                  </a>
                  <a href="/expenses/add?restaurant_id=${existing_restaurant.id}" class="btn btn-sm btn-outline-success">
                    <i class="fas fa-plus me-1"></i>
                    Add Expense
                  </a>
                </div>
              </div>
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
            ${secondaryAction ? `
              <button type="button" class="btn btn-warning" id="secondaryActionBtn">
                ${secondaryAction.label}
              </button>
            ` : ''}
            <button type="button" class="btn btn-primary" id="primaryActionBtn">
              ${primaryAction.label}
            </button>
          </div>
        </div>
      </div>
    </div>
  `;

  // Remove existing modal if any
  const existingModal = document.getElementById('duplicateRestaurantModal');
  if (existingModal) {
    existingModal.remove();
  }

  // Add modal to DOM
  document.body.insertAdjacentHTML('beforeend', modalHtml);

  const modalElement = document.getElementById('duplicateRestaurantModal');

  // Add event listeners
  const primaryBtn = modalElement.querySelector('#primaryActionBtn');
  const secondaryBtn = modalElement.querySelector('#secondaryActionBtn');

  if (primaryBtn) {
    primaryBtn.addEventListener('click', () => {
      if (primaryAction.url) {
        window.location.href = primaryAction.url;
      } else if (primaryAction.action) {
        primaryAction.action();
      }
    });
  }

  if (secondaryBtn && secondaryAction) {
    secondaryBtn.addEventListener('click', () => {
      if (secondaryAction.url) {
        window.location.href = secondaryAction.url;
      } else if (secondaryAction.action) {
        secondaryAction.action();
        const bsModal = bootstrap.Modal.getInstance(modalElement);
        if (bsModal) bsModal.hide();
      }
    });
  }

  // Show modal
  const bsModal = new bootstrap.Modal(modalElement);
  bsModal.show();

  // Clean up modal after hiding
  modalElement.addEventListener('hidden.bs.modal', () => {
    modalElement.remove();
  });
}

// Export for testing
export { setupSearch, handleSearch, displayResults, selectRestaurant, initializeApp, initMap, clearMarkers, createMarker };
