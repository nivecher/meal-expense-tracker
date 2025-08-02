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
      lng: -74.0060
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
          setTimeout(() => reject(new Error('Location request timed out')), 10000)
        )
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
        errorMessage = 'Location access was denied. ' + errorMessage;
      } else if (error.code === error.TIMEOUT) {
        errorMessage = 'Location request timed out. ' + errorMessage;
      } else if (error.code === error.POSITION_UNAVAILABLE) {
        errorMessage = 'Location information is unavailable. ' + errorMessage;
      }

      this.onError(errorMessage);
    } finally {
      this.setLoading(false);
    }
  }

  /**
     * Handle search action
     */
  /**
   * Handle search action
   */
  async handleSearch () {
    if (this.isLoading) return;

    // Get search input values
    const searchInput = this.container.querySelector('.search-input');
    const query = searchInput ? searchInput.value.trim() : '';
    const radiusSelect = this.container.querySelector('.radius-select');
    const radius = radiusSelect ? parseInt(radiusSelect.value, 10) : 5000; // Default to 5km

    // If we don't have a location yet, try to get it
    if (!this.currentLocation) {
      this.setLoading(true);
      try {
        await this.getCurrentLocation();
        // If we still don't have a location after getCurrentLocation, use default
        if (!this.currentLocation) {
          this.currentLocation = {
            lat: 40.7128,
            lng: -74.0060
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

      console.log('Searching with location:', this.currentLocation);
      const results = await googlePlacesService.searchNearby(
        this.currentLocation,
        {
          keyword: query || 'restaurant',
          radius: radius,
          maxResults: 20,
        }
      );

      this.displayResults(results);

      if (!results || results.length === 0) {
        this.displayResults([]);
        this.onError('No restaurants found. Try adjusting your search or location.');
        return;
      }

      this.displayResults(results);
    } catch (error) {
      console.error('Search error:', error);
      this.onError(`Error searching for restaurants: ${error.message}`);
      this.displayResults([]);
    } finally {
      this.setLoading(false);
    }
  }

  /**
     * Display search results
     * @param {Array} results - Array of restaurant objects
     */
  displayResults (results) {
    console.log('Raw results:', results); // Debug log

    if (!results || results.length === 0) {
      this.elements.resultsContainer.innerHTML = `
                <div class="alert alert-info">
                    No restaurants found. Try adjusting your search criteria.
                </div>
            `;
      return;
    }

    const resultsHtml = results.map((restaurant) => {
      console.log('Processing restaurant:', restaurant); // Debug log

      // Handle photo URL - support both direct URLs and photo objects with getUrl()
      let photoUrl = '';
      if (restaurant.photos && restaurant.photos.length > 0) {
        const firstPhoto = restaurant.photos[0];
        if (typeof firstPhoto === 'string') {
          photoUrl = firstPhoto;
        } else if (typeof firstPhoto.getUrl === 'function') {
          // If we have a getUrl function, use it to get the URL
          photoUrl = firstPhoto.getUrl({ maxWidth: 400 });
        } else if (firstPhoto.url) {
          // Fall back to the url property if available
          photoUrl = firstPhoto.url;
        } else if (firstPhoto.name) {
          // For v3 API, we might need to construct the URL
          photoUrl = `https://maps.googleapis.com/maps/api/place/photo?maxwidth=400&photoreference=${firstPhoto.name.split('/').pop()}&key=${googlePlacesService.apiKey}`;
        }
      }

      // Format address - use formatted_address if available, otherwise use formattedAddress or construct from components
      let address = restaurant.formatted_address || restaurant.formattedAddress || 'Address not available';

      // If we have address components but no formatted address, try to construct one
      if (address === 'Address not available' && restaurant.address_components) {
        const components = restaurant.address_components || [];
        const streetNumber = components.find((c) => c.types.includes('street_number'))?.long_name || '';
        const route = components.find((c) => c.types.includes('route'))?.long_name || '';
        const locality = components.find((c) => c.types.includes('locality'))?.long_name || '';
        const adminArea = components.find((c) => c.types.includes('administrative_area_level_1'))?.long_name || '';
        const postalCode = components.find((c) => c.types.includes('postal_code'))?.long_name || '';
        const country = components.find((c) => c.types.includes('country'))?.long_name || '';

        address = [
          [streetNumber, route].filter(Boolean).join(' '),
          locality,
          [adminArea, postalCode].filter(Boolean).join(' '),
          country,
        ].filter(Boolean).join(', ');
      }

      // Get the display name - handle both v2 and v3 API formats
      const displayName = restaurant.displayName?.text || restaurant.name || 'Unnamed Restaurant';

      // Get rating and user ratings count
      const rating = restaurant.rating || 0;
      const userRatingsTotal = restaurant.user_ratings_total || restaurant.userRatingCount || 0;

      // Get price level (1-4, where 1 is $, 4 is $$$$)
      const priceLevel = restaurant.price_level || restaurant.priceLevel || 0;

      // Get place ID
      const placeId = restaurant.place_id || restaurant.id || '';

      return `
            <div class="card mb-3">
                <div class="row g-0">
                    ${photoUrl ? `
                        <div class="col-md-4">
                            <img src="${photoUrl}"
                                 class="img-fluid rounded-start h-100"
                                 alt="${displayName}"
                                 style="object-fit: cover; height: 150px; width: 100%;">
                        </div>
                    ` : ''}
                    <div class="col-md-8">
                        <div class="card-body">
                            <h5 class="card-title">${displayName}</h5>
                            <p class="card-text text-muted">
                                <i class="fas fa-map-marker-alt me-1"></i>
                                ${address}
                            </p>
                            <div class="d-flex justify-content-between align-items-center">
                                ${rating > 0 ? `
                                    <div class="rating">
                                        ${this.renderRating(rating)}
                                        <span class="ms-1 small text-muted">
                                            (${userRatingsTotal})
                                        </span>
                                    </div>
                                ` : ''}
                                ${priceLevel > 0 ? `
                                    <div class="price-level">
                                        ${'$'.repeat(priceLevel)}
                                    </div>
                                ` : ''}
                            </div>
                            <div class="mt-2">
                                <button class="btn btn-sm btn-outline-primary select-restaurant"
                                        data-restaurant-id="${placeId}">
                                    <i class="fas fa-plus me-1"></i> Add to My Restaurants
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>`;
    }).join('');

    this.elements.resultsContainer.innerHTML = resultsHtml;

    // Add event listeners to the select buttons
    this.container.querySelectorAll('.select-restaurant').forEach((button) => {
      button.addEventListener('click', (e) => {
        const { restaurantId } = e.target.closest('button').dataset;
        const restaurant = results.find((r) => (r.place_id || r.id) === restaurantId);
        if (restaurant) {
          this.onSelect(restaurant);
        }
      });
    });
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
