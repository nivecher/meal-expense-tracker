/**
 * Restaurant Details Page Functionality
 *
 * Handles the interactive elements of the restaurant details page,
 * including edit mode toggling and map initialization.
 */

import { GoogleMapsLoader } from '../utils/google-maps.js';

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
    console.log('Restaurant Detail: Loading Google Maps API');
    GoogleMapsLoader.loadApi(window.GOOGLE_MAPS_API_KEY, async() => {
      try {
        console.log('Restaurant Detail: Google Maps API loaded successfully');
        console.log('Restaurant Detail: Available Google Maps:', window.google?.maps);
        console.log('Restaurant Detail: Available libraries:', Object.keys(window.google?.maps || {}));

        // Always try to import the marker library explicitly for newer API versions
        if (window.google?.maps?.importLibrary) {
          console.log('Restaurant Detail: Importing marker library using importLibrary...');
          try {
            const markerLibrary = await window.google.maps.importLibrary('marker');
            console.log('Restaurant Detail: Marker library imported successfully:', markerLibrary);
            // Make marker library available on the google.maps namespace for compatibility
            if (!window.google.maps.marker && markerLibrary) {
              window.google.maps.marker = markerLibrary;
            }
            // Also make AdvancedMarkerElement available directly on maps for compatibility
            if (markerLibrary?.AdvancedMarkerElement && !window.google.maps.AdvancedMarkerElement) {
              window.google.maps.AdvancedMarkerElement = markerLibrary.AdvancedMarkerElement;
            }
          } catch (importError) {
            console.warn('Restaurant Detail: Failed to import marker library:', importError);
          }
        } else {
          console.log('Restaurant Detail: Using legacy Google Maps API (importLibrary not available)');
        }

        const location = { lat, lng };
        console.log('Restaurant Detail: Creating map at location:', location);

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
            ],
          }),
        };

        // Create a new map centered at the restaurant location
        map = new google.maps.Map(mapContainer, mapOptions);
        console.log('Restaurant Detail: Map created successfully');

        // Add a marker for the restaurant with fallback support
        createMarker(map, location, name);
      } catch (error) {
        console.error('Restaurant Detail: Error initializing Google Maps:', error);
        showMapPlaceholder(mapContainer, 'Error loading map');
      }
    }, ['maps']).catch((error) => {
      console.error('Restaurant Detail: Failed to load Google Maps API:', error);
      showMapPlaceholder(mapContainer, 'Failed to load map');
    });
  } else {
    console.error('Restaurant Detail: Google Maps API key not found. Please set window.GOOGLE_MAPS_API_KEY');
    showMapPlaceholder(mapContainer, 'Map configuration error');
  }
}

/**
 * Create a marker with fallback support
 * @param {google.maps.Map} map - The map instance
 * @param {object} position - The position {lat, lng}
 * @param {string} title - The marker title
 */
function createMarker(map, position, title) {
  console.log('Restaurant Detail: Creating marker with position:', position, 'title:', title);
  console.log('Restaurant Detail: Google Maps object:', window.google?.maps);
  console.log('Restaurant Detail: Marker namespace:', window.google?.maps?.marker);

  try {
    // Check for AdvancedMarkerElement availability in multiple locations
    const hasAdvancedMarkerInMarker = window.google?.maps?.marker?.AdvancedMarkerElement;
    const hasAdvancedMarkerDirect = window.google?.maps?.AdvancedMarkerElement;
    const hasAdvancedMarker = hasAdvancedMarkerInMarker || hasAdvancedMarkerDirect;

    console.log('Restaurant Detail: AdvancedMarkerElement in marker namespace:', !!hasAdvancedMarkerInMarker);
    console.log('Restaurant Detail: AdvancedMarkerElement in maps namespace:', !!hasAdvancedMarkerDirect);
    console.log('Restaurant Detail: google.maps.marker available:', !!window.google?.maps?.marker);

    if (hasAdvancedMarker) {
      console.log('Restaurant Detail: Using AdvancedMarkerElement for marker');
      const AdvancedMarkerElement = hasAdvancedMarkerInMarker || hasAdvancedMarkerDirect;
      const marker = new AdvancedMarkerElement({
        position,
        map,
        title,
      });
      console.log('Restaurant Detail: AdvancedMarkerElement created successfully', marker);
    } else {
      // Fallback to standard Marker
      console.log('Restaurant Detail: Using standard Marker (AdvancedMarkerElement not available)');
      const marker = new google.maps.Marker({
        position,
        map,
        title,
        icon: {
          url: 'https://maps.google.com/mapfiles/ms/icons/red-dot.png',
          scaledSize: new google.maps.Size(32, 32),
          origin: new google.maps.Point(0, 0),
          anchor: new google.maps.Point(16, 32),
        },
      });
      console.log('Restaurant Detail: Standard Marker created successfully', marker);
    }
  } catch (error) {
    console.error('Restaurant Detail: Error creating marker:', error);

    // Last resort: try basic marker without custom icon
    try {
      console.log('Restaurant Detail: Trying basic marker as last resort');
      new google.maps.Marker({
        position,
        map,
        title,
      });
      console.log('Restaurant Detail: Basic marker created successfully');
    } catch (fallbackError) {
      console.error('Restaurant Detail: Failed to create fallback marker:', fallbackError);
      console.log('Restaurant Detail: Marker creation completely failed, map will load without marker');
    }
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
    createMarker,
    setupEditModeToggle,
    formatCurrency,
    formatDate,
  };
}
