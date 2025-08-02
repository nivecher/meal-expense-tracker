/**
 * Google Places API Test Page
 *
 * This script initializes the Google Maps and Places API for the test page.
 * It fetches the API key from the backend and initializes the map and places service.
 */

class GooglePlacesTest {
  constructor () {
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
     * @returns {Promise<void>}
     */
  async init () {
    try {
      // Get the API key from our backend
      const response = await fetch('/api/config/google-maps-key');
      const data = await response.json();

      if (data.error) {
        throw new Error(data.error);
      }

      const { apiKey } = data;
      if (!apiKey) {
        throw new Error('No API key returned from server');
      }

      // Bind initializeMap to the window with proper 'this' context
      window.initializeMap = this.initMap.bind(this);

      // Check if Google Maps API is already loaded
      if (window.google?.maps) {
        await this.initMap();
      } else {
        // Load the Google Maps JavaScript API with the Places library
        const script = document.createElement('script');
        script.src = `https://maps.googleapis.com/maps/api/js?key=${apiKey}&libraries=places,marker&callback=initializeMap`;
        script.async = true;
        script.defer = true;
        script.onerror = () => {
          this.showError('Failed to load Google Maps API');
        };

        document.head.appendChild(script);
      }
    } catch (error) {
      console.error('Error initializing Google Maps:', error);
      this.showError(`Error initializing Google Maps: ${error.message}`);
    }
  }

  /**
     * Initialize the map and set up event listeners
     * @returns {Promise<void>}
     */
  async initMap () {
    try {
      const mapElement = document.getElementById('map');
      if (!mapElement) {
        throw new Error('Map element not found');
      }

      // Initialize the map
      const { Map } = await google.maps.importLibrary('maps');

      this.map = new Map(mapElement, {
        center: { lat: 40.7128, lng: -74.0060 }, // Default to NYC
        zoom: 12,
        mapId: 'DEMO_MAP_ID',
      });

      // Initialize info window
      this.infoWindow = new google.maps.InfoWindow();

      // Set up event listeners
      this.setupEventListeners();

      console.log('Google Maps and Places API initialized successfully');
    } catch (error) {
      console.error('Error initializing map:', error);
      this.showError(`Error initializing map: ${error.message}`);
    }
  }

  /**
     * Set up event listeners for the map and UI elements
     */
  setupEventListeners () {
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
  async handleSearch () {
    const locationInput = document.getElementById('location-input');
    const location = locationInput?.value?.trim();

    if (!location) {
      this.showError('Please enter a location');
      return;
    }

    try {
      // Use the Geocoding API to get coordinates for the location
      const geocoder = new google.maps.Geocoder();
      const geocodeResult = await this.geocodeAddress(geocoder, location);

      if (!geocodeResult) {
        this.showError('Could not find the specified location');
        return;
      }

      // Center the map on the location
      const { location: latLng, viewport } = geocodeResult.geometry;
      this.map.setCenter(latLng);

      if (viewport) {
        this.map.fitBounds(viewport);
      } else {
        this.map.setZoom(14);
      }

      // Search for restaurants near the location
      await this.searchNearby(latLng);

    } catch (error) {
      console.error('Error searching location:', error);
      this.showError(`Error searching location: ${error.message}`);
    }
  }

  /**
     * Geocode an address to get its coordinates
     * @param {google.maps.Geocoder} geocoder - The Geocoder instance
     * @param {string} address - The address to geocode
     * @returns {Promise<google.maps.GeocoderResult>}
     */
  geocodeAddress (geocoder, address) {
    return new Promise((resolve, reject) => {
      geocoder.geocode({ address }, (results, status) => {
        if (status === 'OK' && results?.[0]) {
          resolve(results[0]);
        } else {
          reject(new Error(`Geocode was not successful: ${status}`));
        }
      });
    });
  }

  /**
     * Search for restaurants near a location
     * @param {google.maps.LatLng} location - The location to search around
     * @returns {Promise<Array>} - Array of nearby places
     */
  async searchNearby (location) {
    this.clearMarkers();

    try {
      const { Place } = await google.maps.importLibrary('places');

      // Create a search request
      const request = {
        query: 'restaurant',
        location,
        radius: 1000, // 1km radius
        fields: [
          'displayName',
          'formattedAddress',
          'location',
          'rating',
          'userRatingCount',
          'priceLevel',
          'types',
          'photos',
          'regularOpeningHours',
          'businessStatus',
          'websiteURI',
          'nationalPhoneNumber',
          'googleMapsURI',
          'addressComponents',
          'iconBackgroundColor',
          'primaryType',
          'utcOffsetMinutes',
          'viewport',
        ],
      };

      // Use the new Place.searchByText method
      const { places } = await Place.searchByText(request);

      if (!places || places.length === 0) {
        showError('No restaurants found in this area');
        return [];
      }

      // Get additional details for each place
      const placesWithDetails = await Promise.all(
        places.map(async (place) => {
          try {
            // Fetch additional details
            const response = await place.fetchFields({
              fields: [
                'displayName',
                'formattedAddress',
                'location',
                'rating',
                'userRatingCount',
                'priceLevel',
                'types',
                'photos',
                'regularOpeningHours',
                'businessStatus',
                'websiteURI',
                'nationalPhoneNumber',
                'googleMapsURI',
                'addressComponents',
                'iconBackgroundColor',
                'primaryType',
                'utcOffsetMinutes',
                'viewport',
              ],
            });

            const placeDetails = response.place || response;
            return placeDetails;
          } catch (error) {
            console.error('Error fetching place details:', error);
            return place; // Return basic place info if details fail
          }
        }),
      );

      // Filter out any null results
      const validPlaces = placesWithDetails.filter((place) => place);

      // Create markers for each place
      validPlaces.forEach((place) => {
        createMarker(place);
      });

      // Display the results
      displayResults(validPlaces);

      return validPlaces;

    } catch (error) {
      console.error('Error searching nearby:', error);
      showError(`Error searching for restaurants: ${error.message}`);
      throw error;
    }
  }

  /**
     * Create a marker for a place
     * @param {Object} place - The place to create a marker for
     * @returns {google.maps.Marker} The created marker
     */
  createMarker (place) {
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
  showPlaceDetails (place) {
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
  displayResults (places) {
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
  clearMarkers () {
    this.markers.forEach((marker) => marker.setMap(null));
    this.markers = [];
  }

  /**
     * Show an error message to the user
     * @param {string} message - The error message to display
     */
  showError (message) {
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
  displayResults (places) {
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
  showError (message) {
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
     * Geocode an address
     * @param {string} address - The address to geocode
     * @returns {Promise<google.maps.GeocoderResult>} - The geocoding result
     */
  async geocodeAddress (address) {
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

// Initialize the application when the DOM is fully loaded
document.addEventListener('DOMContentLoaded', () => {
  // Create a new instance of the GooglePlacesTest controller
  const app = new GooglePlacesTest();

  // Initialize the application
  app.init().catch((error) => {
    console.error('Failed to initialize application:', error);
  });
});
