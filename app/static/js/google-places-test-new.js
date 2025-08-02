/**
 * Google Places API Test Page
 *
 * This script provides a clean, class-based implementation for testing
 * the Google Places API integration.
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

      // Check if Google Maps API is already loaded
      if (window.google && window.google.maps) {
        await this.initMap();
      } else {
        // Load the Google Maps JavaScript API with the Places library
        const script = document.createElement('script');
        script.src = `https://maps.googleapis.com/maps/api/js?key=${apiKey}&libraries=places,marker&callback=initGoogleMaps`;
        script.async = true;
        script.defer = true;
        script.onerror = () => {
          this.showError('Failed to load Google Maps API');
        };

        // Define the initGoogleMaps function in the global scope
        window.initGoogleMaps = () => this.initMap();

        document.head.appendChild(script);
      }
    } catch (error) {
      console.error('Error initializing Google Maps:', error);
      this.showError(`Error initializing Google Maps: ${error.message}`);
    }
  }

  /**
     * Initialize the map and set up event listeners
     */
  async initMap () {
    try {
      const mapElement = document.getElementById('map');
      if (!mapElement) {
        throw new Error('Map element not found');
      }

      // Load required libraries
      const { Map } = await google.maps.importLibrary('maps');

      // Initialize the map
      this.map = new Map(mapElement, {
        center: { lat: 40.7128, lng: -74.0060 }, // Default to NYC
        zoom: 12,
        mapId: 'DEMO_MAP_ID',
        mapTypeControl: false,
        streetViewControl: false,
        fullscreenControl: true,
        zoomControl: true,
        clickableIcons: false,
        gestureHandling: 'greedy',
      });

      // Initialize info window
      this.infoWindow = new google.maps.InfoWindow({
        maxWidth: 300,
        disableAutoPan: true,
      });

      // Set up event listeners
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

      console.log('Google Maps and Places API initialized successfully');

    } catch (error) {
      console.error('Error initializing map:', error);
      this.showError(`Error initializing map: ${error.message}`);
    }
  }

  /**
     * Handle search button click
     */
  async handleSearch () {
    const locationInput = document.getElementById('location-input');
    const location = locationInput.value.trim();

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
     */
  geocodeAddress (geocoder, address) {
    return new Promise((resolve, reject) => {
      geocoder.geocode({ address }, (results, status) => {
        if (status === 'OK' && results[0]) {
          resolve(results[0]);
        } else {
          reject(new Error(`Geocode was not successful: ${status}`));
        }
      });
    });
  }

  /**
     * Search for restaurants near a location
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
        this.showError('No restaurants found in this area');
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

            return response.place || response;
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
        this.createMarker(place);
      });

      // Display the results
      this.displayResults(validPlaces);

      return validPlaces;

    } catch (error) {
      console.error('Error searching nearby:', error);
      this.showError(`Error searching for restaurants: ${error.message}`);
      throw error;
    }
  }

  /**
     * Create a marker for a place
     */
  createMarker (place) {
    if (!place.geometry || !place.geometry.location) return;

    const marker = new google.maps.Marker({
      map: this.map,
      position: place.geometry.location,
      title: place.displayName || place.name || 'Unnamed Place',
      animation: google.maps.Animation.DROP,
    });

    this.markers.push(marker);

    // Add click listener to show place details
    marker.addListener('click', () => {
      this.showPlaceDetails(place);
    });

    return marker;
  }

  /**
     * Show details for a place in an info window
     */
  showPlaceDetails (place) {
    if (!place) return;

    let content = `<div class="place-details">
            <h3>${place.displayName || place.name || 'Unnamed Place'}</h3>`;

    // Add photo if available
    if (place.photos && place.photos.length > 0) {
      try {
        const photo = place.photos[0];
        const photoUrl = photo.getUrl ? photo.getUrl({ maxWidth: 400 }) : null;
        if (photoUrl) {
          content += `<div class="place-photo">
                        <img src="${photoUrl}" alt="${place.displayName || place.name || 'Restaurant'}"
                             style="max-width: 100%; height: auto; border-radius: 4px; margin-bottom: 10px;">
                    </div>`;
        }
      } catch (error) {
        console.error('Error getting photo URL:', error);
      }
    }

    if (place.formattedAddress || place.vicinity) {
      content += `<p><i class="fas fa-map-marker-alt"></i> ${place.formattedAddress || place.vicinity}</p>`;
    }

    if (place.rating) {
      const rating = place.rating ? place.rating.toFixed(1) : 'N/A';
      const reviews = place.userRatingCount || 0;
      content += `<p>Rating: ${rating} (${reviews} reviews)</p>`;
    }

    if (place.priceLevel) {
      const priceLevels = ['$', '$$', '$$$', '$$$$', '$$$$$'];
      content += `<p>Price: ${priceLevels[place.priceLevel - 1] || 'N/A'}</p>`;
    }

    if (place.regularOpeningHours) {
      const status = place.regularOpeningHours.openNow ? 'Open' : 'Closed';
      content += `<p>Status: ${status}</p>`;
    }

    if (place.websiteURI || place.website) {
      const websiteUrl = place.websiteURI || place.website;
      content += `<p><a href="${websiteUrl}" target="_blank" rel="noopener noreferrer">Website</a></p>`;
    }

    if (place.nationalPhoneNumber || place.formatted_phone_number) {
      const phoneNumber = place.nationalPhoneNumber || place.formatted_phone_number;
      content += `<p>Phone: ${phoneNumber}</p>`;
    }

    content += '</div>';

    this.infoWindow.setContent(content);
    this.infoWindow.open(this.map, this.markers.find((m) => m.getTitle() === (place.displayName || place.name)));
  }

  /**
     * Display search results in the results container
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
                <h4>${place.displayName || place.name || 'Unnamed Place'}</h4>`;

      if (place.formattedAddress || place.vicinity) {
        content += `<p>${place.formattedAddress || place.vicinity}</p>`;
      }

      if (place.rating) {
        const rating = place.rating.toFixed(1);
        const reviews = place.userRatingCount || 0;
        content += `<p>Rating: ${rating} (${reviews} reviews)</p>`;
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
     * Clear all markers from the map
     */
  clearMarkers () {
    this.markers.forEach((marker) => marker.setMap(null));
    this.markers = [];
  }

  /**
     * Show an error message to the user
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
