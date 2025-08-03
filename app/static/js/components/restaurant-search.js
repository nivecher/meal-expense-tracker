/**
 * Restaurant Search Component
 *
 * Provides a UI for searching restaurants using Google Places API
 */

import { googlePlacesService } from '../services/google-places.js';

export class RestaurantSearch {
  /**
     * Create a new RestaurantSearch instance
     * @param {Object} options - Configuration options
     * @param {HTMLElement} options.container - Container element for the search UI
     * @param {Function} options.onSelect - Callback when a restaurant is selected
     * @param {Function} options.onError - Error handler callback
     */
  constructor (options) {
    this.container = options.container;
    this.onSelect = options.onSelect || (() => {});
    this.onError = options.onError || console.error;

    this.currentLocation = null;
    this.isLoading = false;

    this.init();
  }

  /**
     * Initialize the search component
     */
  init () {
    this.render();
    this.bindEvents();
    this.getCurrentLocation();
  }

  /**
     * Render the search UI
     */
  render () {
    this.container.innerHTML = `
            <div class="card mb-4">
                <div class="card-header">
                    <h5 class="mb-0">
                        <i class="fas fa-search-location me-2"></i>
                        Find Restaurants
                    </h5>
                </div>
                <div class="card-body">
                    <div class="input-group mb-3">
                        <input type="text"
                               class="form-control"
                               id="search-query"
                               placeholder="Search for restaurants..."
                               autocomplete="off">
                        <button class="btn btn-primary" id="search-button" type="button">
                            <i class="fas fa-search"></i> Search
                        </button>
                    </div>

                    <div class="d-flex align-items-center mb-3">
                        <label class="form-label mb-0 me-2">Search Radius:</label>
                        <input type="range"
                               class="form-range flex-grow-1 me-2"
                               id="radius-slider"
                               min="100"
                               max="50000"
                               step="100"
                               value="5000">
                        <span id="radius-value" class="text-muted small">5 km</span>
                    </div>

                    <div id="search-results" class="mt-3">
                        <div class="text-center text-muted py-4">
                            <i class="fas fa-utensils fa-3x mb-2"></i>
                            <p>Search for restaurants near you</p>
                        </div>
                    </div>
                </div>
            </div>
        `;

    // Cache DOM elements
    this.elements = {
      searchInput: this.container.querySelector('#search-query'),
      searchButton: this.container.querySelector('#search-button'),
      radiusSlider: this.container.querySelector('#radius-slider'),
      radiusValue: this.container.querySelector('#radius-value'),
      resultsContainer: this.container.querySelector('#search-results'),
    };
  }

  /**
     * Bind event listeners
     */
  bindEvents () {
    // Search button click
    this.elements.searchButton.addEventListener('click', () => this.handleSearch());

    // Enter key in search input
    this.elements.searchInput.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') {
        this.handleSearch();
      }
    });

    // Update radius display when slider changes
    this.elements.radiusSlider.addEventListener('input', (e) => {
      this.updateRadiusDisplay(e.target.value);
    });
  }

  /**
     * Update the radius display value
     * @param {number} radius - Radius in meters
     */
  updateRadiusDisplay (radius) {
    const km = Math.round(radius / 100) / 10;
    this.elements.radiusValue.textContent = `${km} km`;
  }

  /**
   * Get the user's current location with fallback to default location
   */
  async getCurrentLocation () {
    // Default to a central location if geolocation fails
    const defaultLocation = {
      lat: 40.7128, // Default to New York City
      lng: -74.0060,
    };

    // If we already have a location, use it
    if (this.currentLocation) {
      return;
    }

    // If geolocation is not available, use default
    if (!navigator.geolocation) {
      console.warn('Geolocation is not supported by this browser');
      this.currentLocation = defaultLocation;
      this.onError('Geolocation is not supported by your browser. Using default location.');
      return;
    }

    this.setLoading(true);

    // Create a promise wrapper for geolocation
    const getPosition = () => {
      return new Promise((resolve, reject) => {
        navigator.geolocation.getCurrentPosition(resolve, reject, {
          enableHighAccuracy: false, // Faster response with less accuracy
          timeout: 10000, // 10 seconds timeout
          maximumAge: 15 * 60 * 1000, // Cache for 15 minutes
        });
      });
    };

    try {
      // Try to get the current position with a timeout
      const position = await Promise.race([
        getPosition(),
        new Promise((_, reject) =>
          setTimeout(() => reject(new Error('Location request timed out')), 10000),
        ),
      ]);

      this.currentLocation = {
        lat: position.coords.latitude,
        lng: position.coords.longitude,
      };
      console.log('Using current location:', this.currentLocation);
    } catch (error) {
      console.warn('Error getting location:', error.message);
      // Use default location as fallback
      this.currentLocation = defaultLocation;

      // Provide appropriate error message
      let errorMessage = 'Using default location. You can still search manually.';
      if (error.code === error.PERMISSION_DENIED) {
        errorMessage = `Location access was denied. ${errorMessage}`;
      } else if (error.code === error.TIMEOUT) {
        errorMessage = `Location request timed out. ${errorMessage}`;
      } else if (error.code === error.POSITION_UNAVAILABLE) {
        errorMessage = `Location information is unavailable. ${errorMessage}`;
      }

      this.onError(errorMessage);
    } finally {
      this.setLoading(false);
    }
  }

  /**
   * Handle search action
   */
  async handleSearch () {
    if (this.isLoading) return;

    // Get search input values
    const searchInput = this.elements.searchInput;
    const query = searchInput ? searchInput.value.trim() : '';
    const radius = this.elements.radiusSlider ? parseInt(this.elements.radiusSlider.value, 10) : 5000; // Default to 5km

    // If we don't have a location yet, try to get it
    if (!this.currentLocation) {
      this.setLoading(true);
      try {
        await this.getCurrentLocation();
        // If we still don't have a location after getCurrentLocation, use default
        if (!this.currentLocation) {
          this.currentLocation = {
            lat: 40.7128,
            lng: -74.0060,
          };
        }
      } catch (error) {
        console.error('Location error:', error);
        // Continue with default location
        this.currentLocation = {
          lat: 40.7128, // Default to NYC
          lng: -74.0060,
        };
      } finally {
        this.setLoading(false);
      }
    }

    this.setLoading(true);

    try {
      // Initialize Google Places service if not already done
      if (!googlePlacesService.initialized) {
        await googlePlacesService.init();
      }

      console.log('Searching with query:', query || '(no query, using location)');
      console.log('Current location:', this.currentLocation);

      try {
        let response;

        if (query) {
          // Text-based search with location bias
          console.log('Performing text-based search with location bias...');
          response = await googlePlacesService.searchNearby(
            this.currentLocation,
            {
              keyword: query,
              radius: 50000, // Wider radius for text search
              maxResults: 20,
            }
          );
        } else {
          // Location-based search (no query)
          console.log('Performing location-based search...');
          response = await googlePlacesService.searchNearby(
            this.currentLocation,
            {
              keyword: 'restaurant',
              radius: radius,
              maxResults: 20,
            }
          );
        }

        console.log('Search response:', response);

        // The response should be an object with a results array and status
        if (!response || !response.results || !Array.isArray(response.results)) {
          console.error('Invalid response format from Google Places API:', response);
          this.displayResults([]);
          this.onError('Invalid response from search service. Please try again.');
          return;
        }

        const { results } = response;

        if (results.length === 0) {
          console.log('No restaurants found for the given criteria');
          this.displayResults([]);
          this.onError('No restaurants found. Try adjusting your search or location.');
          return;
        }

        console.log(`Found ${results.length} restaurants`);
        this.displayResults(results);
      } catch (error) {
        console.error('Error in search:', error);
        this.displayResults([]);
        this.onError(`Error searching for restaurants: ${error.message || 'Unknown error'}`);
        throw error; // Re-throw to be caught by the outer try-catch
      }
    } catch (error) {
      console.error('Search error:', error);
      this.onError(`Error searching for restaurants: ${error.message}`);
      this.displayResults([]);
    } finally {
      this.setLoading(false);
    }
  }

  /**
   * Display search results in the UI
   * @param {Array<Object>} results - Array of restaurant objects from Google Places API
   */
  displayResults (results) {
    console.log('Displaying results:', results);
    const { resultsContainer } = this.elements;

    // Clear previous results and errors
    resultsContainer.innerHTML = '';

    // Check if results is not an array or is empty
    if (!Array.isArray(results) || results.length === 0) {
      resultsContainer.innerHTML = `
        <div class="alert alert-info">
          No restaurants found. Try adjusting your search criteria.
        </div>
      `;
      return;
    }

    try {
      // Create a row to contain the restaurant cards
      const row = document.createElement('div');
      row.className = 'row';

      // Process each restaurant in the results
      results.forEach((restaurant, index) => {
        // Skip if restaurant is not an object
        if (typeof restaurant !== 'object' || restaurant === null) {
          console.warn(`Skipping invalid restaurant at index ${index}:`, restaurant);
          return;
        }

        // Log restaurant data for debugging
        console.log(`Processing restaurant ${index + 1}/${results.length}:`, restaurant);

        // Extract restaurant details with fallbacks
        const name = restaurant.displayName?.text || restaurant.name || 'Unnamed Restaurant';
        const address = this.formatAddress(restaurant);
        const rating = typeof restaurant.rating === 'number' ? restaurant.rating : 'N/A';
        const userRatingsTotal = restaurant.user_ratings_total || restaurant.userRatingCount || 0;
        const priceLevel = restaurant.price_level || restaurant.priceLevel || 0;
        const placeId = restaurant.place_id || restaurant.id || '';

        // Get photo URL
        const photoUrl = this.getPhotoUrl(restaurant);

        // Create restaurant card
        const col = document.createElement('div');
        col.className = 'col-md-6 col-lg-4 mb-4';

        // Create card element
        const card = document.createElement('div');
        card.className = 'card h-100 restaurant-card';
        card.setAttribute('data-place-id', placeId);

        // Build card content
        const cardContent = `
          ${photoUrl ? `
            <img src="${photoUrl}"
                 class="card-img-top"
                 alt="${name}"
                 style="height: 200px; object-fit: cover;">
          ` : `
            <div class="card-img-top bg-light d-flex align-items-center justify-content-center"
                 style="height: 200px;">
              <i class="fas fa-utensils fa-4x text-muted"></i>
            </div>
          `}

          <div class="card-body d-flex flex-column">
            <h5 class="card-title">${name}</h5>

            ${rating !== 'N/A' ? `
              <div class="d-flex align-items-center mb-2">
                <div class="text-warning me-2">
                  ${this.renderRating(rating)}
                </div>
                <span class="text-muted small">
                  (${userRatingsTotal} ${userRatingsTotal === 1 ? 'review' : 'reviews'})
                </span>
              </div>
            ` : ''}

            ${priceLevel > 0 ? `
              <div class="mb-2">
                <span class="badge bg-light text-dark">${'$'.repeat(priceLevel)}</span>
              </div>
            ` : ''}

            <p class="card-text text-muted small flex-grow-1">
              <i class="fas fa-map-marker-alt me-1"></i> ${address}
            </p>

            <button class="btn btn-primary btn-sm mt-2 add-restaurant-btn"
                    data-place-id="${placeId}">
              <i class="fas fa-plus me-1"></i> Add to List
            </button>
          </div>
        `;

        // Set the card content and append to column
        card.innerHTML = cardContent;
        col.appendChild(card);

        // Add click handler for the add restaurant button
        const addButton = card.querySelector('.add-restaurant-btn');
        if (addButton) {
          addButton.addEventListener('click', (e) => {
            e.stopPropagation();
            this.selectRestaurant(placeId);
          });
        }

        // Add click handler for the entire card
        card.addEventListener('click', (e) => {
          // Don't trigger if the click was on a button or link
          if (e.target.tagName === 'BUTTON' || e.target.tagName === 'A' || e.target.closest('button, a')) {
            return;
          }
          // Trigger the restaurant selection
          this.selectRestaurant(placeId);
        });

        // Add column to row
        row.appendChild(col);
      }); // End of forEach

      // Add row to results container
      resultsContainer.appendChild(row);

    } catch (error) {
      console.error('Error displaying results:', error);
      resultsContainer.innerHTML = `
        <div class="alert alert-danger">
          An error occurred while displaying results. Please try again.
        </div>
      `;
    }
  }

  /**
   * Format a restaurant's address from its components
   * @param {Object} restaurant - Restaurant object from Google Places API
   * @returns {string} Formatted address string
   */
  formatAddress (restaurant) {
    if (!restaurant) return 'Address not available';

    // Use formatted address if available
    if (restaurant.formatted_address) return restaurant.formatted_address;
    if (restaurant.formattedAddress) return restaurant.formattedAddress;

    // Try to construct address from components if available
    if (restaurant.address_components) {
      return restaurant.address_components
        .map((component) => component.long_name)
        .join(', ');
    }

    if (restaurant.vicinity) {
      return restaurant.vicinity;
    }

    return 'Address not available';
  }

  /**
   * Get a photo URL for a restaurant
   * @param {Object} restaurant - Restaurant object from Google Places API
   * @returns {string|null} Photo URL or null if not available
   */
  getPhotoUrl (restaurant) {
    if (!restaurant || !restaurant.photos || restaurant.photos.length === 0) {
      return null;
    }

    const photo = restaurant.photos[0];
    if (!photo) {
      return null;
    }

    if (photo.getUrl) {
      // Google Maps JavaScript API v3
      return photo.getUrl();
    } else if (photo.photo_reference) {
      // Google Places API v2
      return `https://maps.googleapis.com/maps/api/place/photo?maxwidth=400&photoreference=${photo.photo_reference}&key=${this.apiKey}`;
    } else if (photo.url) {
      // Direct URL
      return photo.url;
    }

    return null;
  }

  /**
   * Render a single restaurant card
   * @param {Object} restaurant - Restaurant data
   * @returns {string} HTML string for the restaurant card
   */
  renderRestaurantCard (restaurant) {
    const name = restaurant.displayName?.text || restaurant.name || 'Unnamed Restaurant';
    const address = this.formatAddress(restaurant);
    const rating = typeof restaurant.rating === 'number' ? restaurant.rating : 0;
    const userRatingsTotal = restaurant.user_ratings_total || restaurant.userRatingCount || 0;
    const priceLevel = restaurant.price_level || restaurant.priceLevel || 0;
    const placeId = restaurant.place_id || restaurant.id || '';
    const photoUrl = this.getPhotoUrl(restaurant);

    return `
      <div class="col-md-6 col-lg-4 mb-4">
        <div class="card h-100">
          ${photoUrl ? `
            <img src="${photoUrl}"
                 class="card-img-top"
                 alt="${name}"
                 style="height: 180px; object-fit: cover;">
          ` : `
            <div class="card-img-top bg-light d-flex align-items-center justify-content-center"
                 style="height: 180px;">
              <i class="fas fa-utensils fa-4x text-muted"></i>
            </div>
          `}
          <div class="card-body d-flex flex-column">
            <h5 class="card-title">${name}</h5>
            <p class="card-text text-muted small flex-grow-1">
              <i class="fas fa-map-marker-alt me-1"></i> ${address}
            </p>
            ${rating > 0 ? `
              <div class="d-flex align-items-center mb-2">
                <div class="text-warning me-2">
                  ${this.renderRating(rating)}
                </div>
                <span class="text-muted small">
                  (${userRatingsTotal} ${userRatingsTotal === 1 ? 'review' : 'reviews'})
                </span>
              </div>
            ` : ''}
            ${priceLevel > 0 ? `
              <div class="mb-2">
                <span class="badge bg-light text-dark">${'$'.repeat(priceLevel)}</span>
              </div>
            ` : ''}
            <button class="btn btn-primary btn-sm mt-auto select-restaurant"
                    data-restaurant-id="${placeId}">
              <i class="fas fa-plus me-1"></i> Add to My Restaurants
            </button>
          </div>
        </div>
      </div>
    `;
  }

  /**
   * Display search results in the UI
   * @param {Array<Object>} results - Array of restaurant objects from Google Places API
   */
  displayResults (results) {
    const { resultsContainer } = this.elements;

    // Clear previous results
    resultsContainer.innerHTML = '';

    // Check if results is not an array or is empty
    if (!Array.isArray(results) || results.length === 0) {
      resultsContainer.innerHTML = `
        <div class="col-12">
          <div class="alert alert-info mb-0">
            No restaurants found. Try adjusting your search criteria.
          </div>
        </div>
      `;
      return;
    }

    try {
      // Create a row to contain all restaurant cards
      const row = document.createElement('div');
      row.className = 'row g-3';

      // Add each restaurant card to the row
      results.forEach((restaurant) => {
        if (restaurant) {
          row.insertAdjacentHTML('beforeend', this.renderRestaurantCard(restaurant));
        }
      });

      // Add the row to the container
      resultsContainer.appendChild(row);

      // Add event listeners to the select buttons
      resultsContainer.querySelectorAll('.select-restaurant').forEach((button) => {
        button.addEventListener('click', (e) => {
          e.preventDefault();
          const { restaurantId } = e.currentTarget.dataset;
          const restaurant = results.find((r) => (r.place_id || r.id) === restaurantId);
          if (restaurant) {
            this.onSelect(restaurant);
          }
        });
      });

    } catch (error) {
      console.error('Error displaying results:', error);
      resultsContainer.innerHTML = `
        <div class="col-12">
          <div class="alert alert-danger mb-0">
            An error occurred while displaying results. Please try again.
          </div>
        </div>
      `;
    }
  }

  /**
     * Render rating stars
     * @param {number} rating - Rating from 0 to 5
     * @returns {string} HTML string with star icons
     */
  renderRating (rating) {
    const fullStars = Math.floor(rating);
    const hasHalfStar = rating % 1 >= 0.5;
    const emptyStars = 5 - fullStars - (hasHalfStar ? 1 : 0);

    let stars = '';

    // Full stars
    stars += '<i class="fas fa-star"></i>'.repeat(fullStars);

    // Half star
    if (hasHalfStar) {
      stars += '<i class="fas fa-star-half-alt"></i>';
    }

    // Empty stars
    stars += '<i class="far fa-star"></i>'.repeat(emptyStars);

    return stars;
  }

  /**
     * Handle restaurant selection
     * @param {string} placeId - Google Place ID
     */
  async selectRestaurant (placeId) {
    try {
      this.setLoading(true);
      const details = await googlePlacesService.getPlaceDetails(placeId);
      this.onSelect(details);
    } catch (error) {
      this.onError(`Error getting restaurant details: ${error.message}`);
    } finally {
      this.setLoading(false);
    }
  }

  /**
     * Set loading state
     * @param {boolean} isLoading - Whether the component is loading
     */
  setLoading (isLoading) {
    this.isLoading = isLoading;
    this.elements.searchButton.disabled = isLoading;
    this.elements.searchInput.readOnly = isLoading;

    // Update button text
    if (isLoading) {
      this.elements.searchButton.innerHTML = '<span class="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true"></span> Searching...';
    } else {
      this.elements.searchButton.innerHTML = '<i class="fas fa-search"></i> Search';
    }

    // Show/hide the loading indicator
    const loadingIndicator = document.getElementById('loading-indicator');
    if (loadingIndicator) {
      if (isLoading) {
        loadingIndicator.classList.remove('d-none');
      } else {
        loadingIndicator.classList.add('d-none');
      }
    }
  }
}

export default RestaurantSearch;
