/**
 * Restaurant Details Page Functionality
 *
 * Handles the interactive elements of the restaurant details page,
 * including edit mode toggling and map initialization.
 */

import GoogleMapsLoader from './utils/google-maps-loader.js';

// Global map reference
let map = null;

document.addEventListener('DOMContentLoaded', () => {
  initializeTooltips();
  initializeMap();
  setupEditModeToggle();
});

/**
 * Initialize Bootstrap tooltips
 */
function initializeTooltips() {
  const tooltipTriggerList = [].slice.call(
    document.querySelectorAll('[data-bs-toggle="tooltip"]'),
  );

  tooltipTriggerList.forEach((tooltipTriggerEl) => {
    new bootstrap.Tooltip(tooltipTriggerEl);
  });
}

/**
 * Initialize map if container exists
 */
function initializeMap() {
  const mapContainer = document.getElementById('map-container');
  if (!mapContainer) return;

  const lat = parseFloat(mapContainer.dataset.lat);
  const lng = parseFloat(mapContainer.dataset.lng);
  const name = mapContainer.dataset.name || 'Restaurant Location';

  // Check if we have valid coordinates
  if (isNaN(lat) || isNaN(lng)) {
    showMapPlaceholder(mapContainer, 'No location data available');
    return;
  }

  // Load Google Maps API and initialize the map
  if (window.GOOGLE_MAPS_API_KEY) {
    GoogleMapsLoader.loadApi(window.GOOGLE_MAPS_API_KEY, () => {
      try {
        const location = { lat, lng };

        const mapOptions = {
          zoom: 15,
          center: location,
          mapTypeId: 'roadmap',
          ...(window.GOOGLE_MAPS_MAP_ID && { mapId: window.GOOGLE_MAPS_MAP_ID }),
          ...(!window.GOOGLE_MAPS_MAP_ID && {
            styles: [
              {
                featureType: 'poi',
                elementType: 'labels',
                stylers: [{ visibility: 'off' }],
              },
            ]
          })
        };

        // Create a new map centered at the restaurant location
        map = new google.maps.Map(mapContainer, mapOptions);

        // Add a marker for the restaurant using AdvancedMarkerElement
        new google.maps.marker.AdvancedMarkerElement({
          position: location,
          map,
          title: name,
        });
      } catch (error) {
        console.error('Error initializing Google Maps:', error);
        showMapPlaceholder(mapContainer, 'Error loading map');
      }
    }, ['maps']).catch((error) => {
      console.error('Failed to load Google Maps API:', error);
      showMapPlaceholder(mapContainer, 'Failed to load map');
    });
  } else {
    console.error('Google Maps API key not found. Please set window.GOOGLE_MAPS_API_KEY');
    showMapPlaceholder(mapContainer, 'Map configuration error');
  }
}

/**
 * Show a placeholder when map cannot be loaded
 * @param {HTMLElement} container - The map container element
 * @param {string} message - The message to display
 */
function showMapPlaceholder(container, message) {
  container.innerHTML = `
    <div class="ratio ratio-16x9 bg-light">
      <div class="d-flex align-items-center justify-content-center h-100">
        <div class="text-center">
          <i class="fas fa-map-marker-alt fa-3x text-primary mb-2"></i>
          <p class="mb-0">${message}</p>
        </div>
      </div>
    </div>
  `;
}

/**
 * Set up the edit mode toggle functionality
 */
function setupEditModeToggle() {
  const editToggle = document.getElementById('edit-toggle');
  const viewMode = document.getElementById('view-mode');
  const editForm = document.getElementById('edit-form');
  const cancelEdit = document.getElementById('cancel-edit');

  if (!editToggle || !viewMode || !editForm || !cancelEdit) return;

  // Toggle to edit mode
  editToggle.addEventListener('click', () => {
    viewMode.classList.add('d-none');
    editForm.classList.remove('d-none');
    editToggle.classList.add('d-none');

    // Scroll to the form if needed
    editForm.scrollIntoView({ behavior: 'smooth', block: 'start' });
  });

  // Cancel edit mode
  cancelEdit.addEventListener('click', () => {
    viewMode.classList.remove('d-none');
    editForm.classList.add('d-none');
    editToggle.classList.remove('d-none');
  });
}

/**
 * Format currency values consistently
 * @param {number} amount - The amount to format
 * @returns {string} Formatted currency string
 */
function formatCurrency(amount) {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount);
}

/**
 * Format date strings consistently
 * @param {string} dateString - ISO date string
 * @returns {string} Formatted date string
 */
function formatDate(dateString) {
  const options = { year: 'numeric', month: 'short', day: 'numeric' };
  return new Date(dateString).toLocaleDateString(undefined, options);
}

// Export functions for testing
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    initializeTooltips,
    initializeMap,
    setupEditModeToggle,
    formatCurrency,
    formatDate,
  };
}
