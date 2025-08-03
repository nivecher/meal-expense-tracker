/**
 * Google Places API Test Page
 *
 * This script initializes the Google Maps and Places API for the test page.
 * It uses the API key provided in the window.GOOGLE_MAPS_API_KEY variable.
 */

// Import the GooglePlacesService from the services directory
import { googlePlacesService } from './services/google-places.js';
import { logger } from './utils/logger.js';
import GoogleMapsLoader from './utils/google-maps-loader.js';

// Error display element
const errorElement = document.getElementById('error-message');

// Check if we have the API key
if (!window.GOOGLE_MAPS_API_KEY) {
  const errorMsg = 'Google Maps API key not found. Please check your configuration.';
  console.error(errorMsg);
  if (errorElement) {
    errorElement.textContent = errorMsg;
  }
  throw new Error(errorMsg);
}

class GooglePlacesTest {
  constructor() {
    this.map = null;
    this.markers = [];
    this.infoWindow = null;
    this.placesService = null;

    // Bind methods
    this.init = this.init.bind(this);
    this.initMap = this.initMap.bind(this);
    this.handleSearch = this.handleSearch.bind(this);
    this.searchNearby = this.searchNearby.bind(this);
    this.createMarker = this.createMarker.bind(this);
    this.showPlaceDetails = this.showPlaceDetails.bind(this);
    this.displayResults = this.displayResults.bind(this);
    this.clearMarkers = this.clearMarkers.bind(this);
    this.showError = this.showError.bind(this);
    this.geocodeAddress = this.geocodeAddress.bind(this);
  }

  /**
   * Initialize the Google Maps and Places API
   * @returns {Promise<boolean>} True if initialization was successful
   */
  async init() {
    try {
      // Show loading state
      if (errorElement) {
        errorElement.textContent = 'Initializing Google Maps...';
        errorElement.className = 'info-message';
      }

      // Initialize the Google Places Service
      await googlePlacesService.init(window.GOOGLE_MAPS_API_KEY);

      // Initialize the map
      await this.initMap();

      // Set up event listeners
      this.setupEventListeners();

      // Clear any loading/error messages
      if (errorElement) {
        errorElement.textContent = '';
        errorElement.className = '';
      }

      console.log('Google Places Test initialized successfully');
      return true;

    } catch (error) {
      const errorMessage = `Error initializing Google Places Test: ${error.message}`;
      console.error(errorMessage, error);

      if (errorElement) {
        errorElement.className = 'error-message';
        errorElement.textContent = `Failed to initialize: ${error.message}`;
      }

      return false;
    }
  }

  /**
   * Try to get the user's current location using the Geolocation API
   * @private
   * @returns {Promise<void>}
   */
  async getCurrentLocation() {
    return new Promise((resolve) => {
      if (!navigator.geolocation) {
        logger.info('Geolocation is not supported by this browser');
        resolve();
        return;
      }

      const options = {
        enableHighAccuracy: true,
        timeout: 5000,
        maximumAge: 0,
      };

      navigator.geolocation.getCurrentPosition(
        (position) => {
          const pos = {
            lat: position.coords.latitude,
            lng: position.coords.longitude,
          };

          // Center the map on the user's location
          if (this.map) {
            this.map.setCenter(pos);
            this.map.setZoom(14);

            // Optionally search for nearby places
            this.searchNearby(pos).catch((error) => {
              logger.error('Error searching nearby places:', error);
            });
          }

          resolve();
        },
        (error) => {
          const errorMessage = 'Unable to retrieve your location';
          logger.warn(errorMessage, { error });
          resolve(); // Resolve anyway to continue initialization
        },
        options,
      );
    });
  }

  /**
   * Initialize the map
   * @private
   * @returns {Promise<boolean>} True if map initialization was successful
   */
  async initMap() {
    const mapElement = document.getElementById('map');
    if (!mapElement) {
      throw new Error('Map container element not found');
    }

    try {
      // Default to New York if no location is set
      const defaultLocation = { lat: 40.7128, lng: -74.0060 };

      // Create a new map centered on the default location
      this.map = new google.maps.Map(mapElement, {
        center: defaultLocation,
        zoom: 12,
        mapTypeControl: true,
        streetViewControl: true,
        fullscreenControl: true,
        mapTypeControlOptions: {
          style: google.maps.MapTypeControlStyle.HORIZONTAL_BAR,
          position: google.maps.ControlPosition.TOP_RIGHT,
        },
        zoomControl: true,
        zoomControlOptions: {
          position: google.maps.ControlPosition.RIGHT_CENTER,
        },
        // Add gesture handling to prevent map dragging on mobile when scrolling
        gestureHandling: 'auto',
      });

      // Create a new Places service
      this.placesService = new google.maps.places.PlacesService(this.map);

      // Create a new info window for place details
      // Create a new info window
      this.infoWindow = new google.maps.InfoWindow();

      // Add a click listener to close the info window when clicking the map
      this.map.addListener('click', () => {
        if (this.infoWindow) {
          this.infoWindow.close();
        }
      });

      // Try to get the user's current location
      this.getCurrentLocation();

      logger.info('Map initialized successfully');
      return true;

    } catch (error) {
      const errorMessage = 'Failed to initialize map';
      console.error(`${errorMessage}:`, error);
      this.showError('Failed to initialize the map. Please try again.');
      if (logger) {
        logger.error(errorMessage, { error });
      }
      return false;
    }
  }

  /**
     * Set up event listeners for the map and UI elements
     */
  setupEventListeners() {
    const searchButton = document.getElementById('search-button');
    const locationInput = document.getElementById('location-input');

    if (searchButton) {
      searchButton.addEventListener('click', this.handleSearch);
    }

    if (locationInput) {
      locationInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
          this.handleSearch();
        }
      });
    }
  }

  /**
   * Handle search button click
   * @returns {Promise<void>}
   */
  async handleSearch() {
    const locationInput = document.getElementById('location-input');
    const keywordInput = document.getElementById('keyword-input');
    const location = locationInput?.value?.trim();
    const keyword = keywordInput?.value?.trim();

    if (!location) {
      this.showError('Please enter a location');
      return;
    }

    try {
      // Show loading state
      this.showLoading(true);

      // Use the Geocoding API to get coordinates for the location
      const geocoder = new google.maps.Geocoder();
      const geocodeResult = await this.geocodeAddress(geocoder, location);

      if (!geocodeResult || !geocodeResult.geometry || !geocodeResult.geometry.location) {
        this.showError('Could not find the specified location');
        return;
      }

      // Center the map on the searched location
      this.map.setCenter(geocodeResult.geometry.location);
      this.map.setZoom(14);

      // Search for nearby restaurants
      await this.searchNearby(geocodeResult.geometry.location, keyword);

    } catch (error) {
      console.error('Error handling search:', error);
      this.showError(`Error performing search: ${error.message}`);
    } finally {
      // Hide loading state
      this.showLoading(false);
    }
  }

  /**
   * Search for restaurants near a location
   * @param {Object} location - The location to search near
   * @param {string} [keyword] - Optional keyword to search for
   * @returns {Promise<Array>} - Array of restaurant results
   */
  async searchNearby(location, keyword) {
    try {
      // Clear any existing markers
      this.clearMarkers();

      // Show loading state
      this.showLoading(true);

      // Use the GooglePlacesService to search for nearby restaurants
      const { results, status } = await googlePlacesService.searchNearby(
        {
          lat: location.lat(),
          lng: location.lng(),
        },
        {
          keyword: keyword || '',
          radius: 5000, // 5km radius
          maxResults: 20,
        },
      );

      if (status === 'OK' && results && results.length > 0) {
        // Add markers for each result
        results.forEach((place) => {
          this.createMarker(place);
        });

        // Display the results in the UI
        this.displayResults(results);

        // Return the results
        return results;
      }
      throw new Error('No results found');

    } catch (error) {
      console.error('Error searching nearby:', error);
      this.showError(`Error searching for restaurants: ${error.message}`);
      throw error;
    }
  }

  /**
     * Create a marker for a place
     * @param {Object} place - The place to create a marker for
     * @returns {google.maps.Marker} The created marker
     */
  createMarker(place) {
    if (!place.geometry?.location) return null;

    const marker = new google.maps.Marker({
      map: this.map,
      position: place.geometry.location,
      title: place.name || '',
      animation: google.maps.Animation.DROP,
    });

    // Add click listener to show place details
    marker.addListener('click', () => {
      this.showPlaceDetails(place);
    });

    this.markers.push(marker);
    return marker;
  }

  /**
     * Show details for a place in the info window
     */
  showPlaceDetails(place) {
    let content = `<div class="place-details">
        <h3>${place.name || 'No name'}</h3>`;

    if (place.formatted_address) {
      content += `<p>${place.formatted_address}</p>`;
    }

    if (place.rating) {
      content += `<p>Rating: ${place.rating} (${place.user_ratings_total || 0} reviews)</p>`;
    }

    if (place.price_level) {
      const priceLevels = ['$', '$$', '$$$', '$$$$', '$$$$$'];
      content += `<p>Price: ${priceLevels[place.price_level - 1] || 'N/A'}</p>`;
    }

    if (place.opening_hours) {
      const status = place.opening_hours.open_now ? 'Open' : 'Closed';
      content += `<p>Status: ${status}</p>`;
    }

    if (place.website) {
      content += `<p><a href="${place.website}" target="_blank">Website</a></p>`;
    }

    if (place.formatted_phone_number) {
      content += `<p>Phone: ${place.formatted_phone_number}</p>`;
    }

    content += '</div>';

    this.infoWindow.setContent(content);
    this.infoWindow.open(this.map, this.markers.find((m) => m.getTitle() === place.name));
  }

  /**
     * Display search results in the results container
     * @param {Array} places - Array of place objects to display
     */
  displayResults(places) {
    const resultsContainer = document.getElementById('results');

    if (!resultsContainer) {
      console.error('Results container not found');
      return;
    }

    if (!places || places.length === 0) {
      resultsContainer.innerHTML = '<p>No results found</p>';
      return;
    }

    const resultsList = document.createElement('ul');
    resultsList.className = 'results-list';

    places.forEach((place) => {
      const listItem = document.createElement('li');
      listItem.className = 'result-item';

      let content = `
            <div class="result-content">
                <h4>${place.name || 'Unnamed Place'}</h4>
        `;

      if (place.vicinity) {
        content += `<p>${place.vicinity}</p>`;
      }

      if (place.rating) {
        content += `<p>Rating: ${place.rating} (${place.user_ratings_total || 0} reviews)</p>`;
      }

      if (place.price_level) {
        content += `<p>Price level: ${'$'.repeat(place.price_level)}</p>`;
      }

      content += '</div>';

      listItem.innerHTML = content;

      // Add click handler to show details
      listItem.addEventListener('click', () => {
        this.showPlaceDetails(place);
        if (place.geometry?.location) {
          this.map.panTo(place.geometry.location);
          this.map.setZoom(15);
        }
      });

      resultsList.appendChild(listItem);
    });

    resultsContainer.innerHTML = '';
    resultsContainer.appendChild(resultsList);
  }

  /**
     * Clear all markers from the map
     */
  clearMarkers() {
    this.markers.forEach((marker) => marker.setMap(null));
    this.markers = [];
  }

  /**
     * Show an error message to the user
     * @param {string} message - The error message to display
     */
  showError(message) {
    const errorContainer = document.getElementById('error-message');
    if (errorContainer) {
      errorContainer.textContent = message;
      errorContainer.style.display = 'block';
    }

    console.error(message);
  }

  /**
     * Display search results in the results container
     * @param {Array} places - Array of place objects to display
     */
  displayResults(places) {
    const resultsContainer = document.getElementById('results');

    if (!resultsContainer) {
      console.error('Results container not found');
      return;
    }

    if (!places || places.length === 0) {
      resultsContainer.innerHTML = '<p>No results found</p>';
      return;
    }

    const resultsList = document.createElement('ul');
    resultsList.className = 'results-list';

    places.forEach((place) => {
      const listItem = document.createElement('li');
      listItem.className = 'result-item';

      let content = `<div class="result-content">
                <h4>${place.name || 'Unnamed Place'}</h4>`;

      if (place.vicinity) {
        content += `<p>${place.vicinity}</p>`;
      }

      if (place.rating) {
        content += `<p>Rating: ${place.rating} (${place.user_ratings_total || 0} reviews)</p>`;
      }

      content += '</div>';

      listItem.innerHTML = content;

      // Add click handler to show details
      listItem.addEventListener('click', () => {
        this.showPlaceDetails(place);
        this.map.panTo(place.geometry.location);
        this.map.setZoom(15);
      });

      resultsList.appendChild(listItem);
    });

    resultsContainer.innerHTML = '';
    resultsContainer.appendChild(resultsList);
  }

  /**
     * Show an error message to the user
     * @param {string} message - The error message to display
     */
  showError(message) {
    const errorContainer = document.getElementById('error-message');
    if (errorContainer) {
      errorContainer.textContent = message;
      errorContainer.style.display = 'block';

      // Hide the error after 5 seconds
      setTimeout(() => {
        errorContainer.style.display = 'none';
      }, 5000);
    }

    console.error(message);
  }

  /**
   * Show or hide the loading indicator
   * @param {boolean} isLoading - Whether to show the loading indicator
   */
  showLoading(isLoading) {
    const loadingElement = document.getElementById('loading-indicator');
    if (loadingElement) {
      loadingElement.style.display = isLoading ? 'block' : 'none';
    }
  }

  /**
   * Geocode an address
   * @param {string} address - The address to geocode
   * @returns {Promise<google.maps.GeocoderResult>} - The geocoding result
   */
  async geocodeAddress(address) {
    try {
      const geocoder = new google.maps.Geocoder();
      const response = await new Promise((resolve, reject) => {
        geocoder.geocode({ address }, (results, status) => {
          if (status === 'OK' && results?.[0]) {
            resolve(results[0]);
          } else {
            reject(new Error(`Geocode was not successful: ${status}`));
          }
        });
      });

      if (!response) {
        this.showError('No results found');
        return null;
      }

      return response;

    } catch (error) {
      console.error('Error geocoding address:', error);
      this.showError(`Error geocoding address: ${error.message}`);
      throw error;
    }
  }
}

// Initialize the application when the Google Maps API is ready
window.initGooglePlacesTest = async function() {
  try {
    // Create a new instance of the GooglePlacesTest controller
    const app = new GooglePlacesTest();

    // Initialize the application
    const initialized = await app.init();

    if (!initialized) {
      throw new Error('Failed to initialize Google Places Test');
    }

    // Store the app instance on the window for debugging if needed
    window.googlePlacesTest = app;

  } catch (error) {
    console.error('Failed to initialize application:', error);
    if (errorElement) {
      errorElement.className = 'error-message';
      errorElement.textContent = `Failed to initialize: ${error.message}. Please check the console for details.`;
    }
  }
};

// Initialize the application when the DOM is fully loaded
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    if (window.google && window.google.maps) {
      window.initGooglePlacesTest();
    }
  });
} else {
  if (window.google && window.google.maps) {
    window.initGooglePlacesTest();
  }
}
