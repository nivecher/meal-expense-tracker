/**
 * Enhanced Restaurant Search Component
 *
 * Provides an intuitive search interface with advanced controls for finding restaurants.
 * Features radius control, multiple search modes, and smart filtering.
 */

import { cuisineService } from '../services/cuisine-service.js';

export class EnhancedRestaurantSearch {
  constructor(container, options = {}) {
    this.container = container;
    this.options = {
      onSelect: options.onSelect || (() => {}),
      onError: options.onError || (() => {}),
      onResults: options.onResults || (() => {}),
      defaultRadiusMiles: options.defaultRadiusMiles || 3.1, // ~5km default
      maxRadiusMiles: options.maxRadiusMiles || 31.1, // ~50km max
      ...options,
    };

    this.currentLocation = null;
    this.searchMode = 'nearby'; // 'nearby', 'text', 'address'
    this.isSearching = false;
    this.locale = this.detectLocale();

    this.init();
  }

  detectLocale() {
    // Detect user's locale for unit preferences
    const lang = navigator.language || navigator.userLanguage || 'en-US';

    // Countries that typically use miles
    const milesCountries = ['US', 'LR', 'MM'];
    const countryCode = lang.split('-')[1] || 'US';

    return {
      language: lang,
      country: countryCode,
      useMiles: milesCountries.includes(countryCode),
      unit: milesCountries.includes(countryCode) ? 'miles' : 'km',
    };
  }

  init() {
    this.render();
    this.bindEvents();
    this.getCurrentLocation();
    this.populateCuisineFilter();
  }

  async populateCuisineFilter() {
    const cuisineFilter = this.container.querySelector('#cuisine-filter');
    if (!cuisineFilter) return;

    try {
      const cuisineData = await cuisineService.loadCuisineData();
      const cuisineNames = cuisineService.getCuisineNames();

      // Clear existing options except "Any cuisine"
      cuisineFilter.innerHTML = '<option value="">Any cuisine</option>';

      // Add cuisine options
      cuisineNames.forEach((name) => {
        const option = document.createElement('option');
        option.value = name.toLowerCase();
        option.textContent = name;
        cuisineFilter.appendChild(option);
      });
    } catch (error) {
      console.error('Failed to populate cuisine filter:', error);
    }
  }

  render() {
    this.container.innerHTML = `
      <div class="enhanced-restaurant-search">
        <!-- Search Mode Toggle -->
        <div class="search-mode-toggle mb-3">
          <div class="btn-group w-100" role="group">
            <input type="radio" class="btn-check" name="searchMode" id="nearby-mode" value="nearby" checked>
            <label class="btn btn-outline-primary" for="nearby-mode">
              <i class="fas fa-map-marker-alt me-2"></i>Nearby
            </label>

            <input type="radio" class="btn-check" name="searchMode" id="text-mode" value="text">
            <label class="btn btn-outline-primary" for="text-mode">
              <i class="fas fa-search me-2"></i>Search
            </label>

            <input type="radio" class="btn-check" name="searchMode" id="address-mode" value="address">
            <label class="btn btn-outline-primary" for="address-mode">
              <i class="fas fa-map-pin me-2"></i>Address
            </label>
          </div>
        </div>

        <!-- Search Inputs -->
        <div class="search-inputs">
          <!-- Nearby Search -->
          <div id="nearby-search" class="search-mode-content">
            <div class="mb-3">
              <label for="radius-slider" class="form-label">
                Search Radius: <span id="radius-display">3.1 miles</span>
              </label>
              <input type="range" class="form-range" id="radius-slider"
                     min="0.1" max="31.1" step="0.1" value="3.1">
              <div class="d-flex justify-content-between text-muted small">
                <span>0.1 miles</span>
                <span>31.1 miles</span>
              </div>
              <div class="form-text">
                <i class="fas fa-info-circle me-1"></i>
                Search within this distance from your location
              </div>
            </div>

            <div class="mb-3">
              <label for="nearby-keyword" class="form-label">Restaurant Name (Optional)</label>
              <input type="text" class="form-control" id="nearby-keyword"
                     placeholder="e.g., Italian, Pizza, McDonald's...">
              <div class="form-text">
                <i class="fas fa-info-circle me-1"></i>
                Leave blank to find all restaurants, or specify a name/cuisine type
              </div>
            </div>
          </div>

          <!-- Text Search -->
          <div id="text-search" class="search-mode-content d-none">
            <div class="mb-3">
              <label for="text-query" class="form-label">Search Query</label>
              <input type="text" class="form-control" id="text-query"
                     placeholder="e.g., 'Best Italian restaurant near me'">
            </div>
          </div>

          <!-- Address Search -->
          <div id="address-search" class="search-mode-content d-none">
            <div class="mb-3">
              <label for="address-input" class="form-label">Address or Location</label>
              <input type="text" class="form-control" id="address-input"
                     placeholder="Enter address, city, or landmark...">
              <div class="form-text">
                <i class="fas fa-info-circle me-1"></i>
                Search for restaurants near this location
              </div>
            </div>

            <div class="mb-3">
              <label for="address-radius" class="form-label">
                Search Radius: <span id="address-radius-display">3.1 miles</span>
              </label>
              <input type="range" class="form-range" id="address-radius"
                     min="0.1" max="31.1" step="0.1" value="3.1">
              <div class="d-flex justify-content-between text-muted small">
                <span>0.1 miles</span>
                <span>31.1 miles</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Advanced Filters -->
        <div class="advanced-filters mb-3">
          <button class="btn btn-outline-secondary btn-sm w-100" type="button"
                  data-bs-toggle="collapse" data-bs-target="#filter-options">
            <i class="fas fa-filter me-2"></i>Advanced Filters
            <i class="fas fa-chevron-down ms-2"></i>
          </button>

          <div class="collapse mt-3" id="filter-options">
            <div class="card">
              <div class="card-body">
                <div class="row g-3">
                  <div class="col-md-6">
                    <label for="cuisine-filter" class="form-label">Cuisine Type</label>
                    <select class="form-select" id="cuisine-filter">
                      <option value="">Any cuisine</option>
                      <!-- Options will be populated by JavaScript -->
                    </select>
                  </div>

                  <div class="col-md-6">
                    <label for="min-rating" class="form-label">Minimum Rating</label>
                    <select class="form-select" id="min-rating">
                      <option value="">Any rating</option>
                      <option value="4.5">4.5+ stars</option>
                      <option value="4.0">4.0+ stars</option>
                      <option value="3.5">3.5+ stars</option>
                      <option value="3.0">3.0+ stars</option>
                    </select>
                  </div>

                  <div class="col-md-6">
                    <label for="max-price" class="form-label">Maximum Price Level</label>
                    <select class="form-select" id="max-price">
                      <option value="">Any price</option>
                      <option value="1">$ (Budget)</option>
                      <option value="2">$$ (Moderate)</option>
                      <option value="3">$$$ (Expensive)</option>
                      <option value="4">$$$$ (Very Expensive)</option>
                    </select>
                  </div>

                  <div class="col-md-6">
                    <label for="max-results" class="form-label">Max Results</label>
                    <select class="form-select" id="max-results">
                      <option value="10">10 results</option>
                      <option value="15">15 results</option>
                      <option value="20" selected>20 results</option>
                    </select>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Search Button -->
        <div class="d-grid mb-3">
          <button class="btn btn-primary btn-lg" id="search-btn" type="button">
            <i class="fas fa-search me-2"></i>
            <span id="search-btn-text">Search Nearby Restaurants</span>
          </button>
        </div>

        <!-- Location Status -->
        <div id="location-status" class="alert alert-info d-none">
          <i class="fas fa-info-circle me-2"></i>
          <span id="location-status-text">Getting your location...</span>
        </div>

        <!-- Search Results -->
        <div id="search-results" class="mt-3">
          <div class="text-center text-muted py-4">
            <i class="fas fa-utensils fa-3x mb-2"></i>
            <p>Choose a search mode and click search to find restaurants</p>
          </div>
        </div>
      </div>
    `;
  }

  bindEvents() {
    // Search mode toggle
    this.container.querySelectorAll('input[name="searchMode"]').forEach((radio) => {
      radio.addEventListener('change', (e) => {
        this.switchSearchMode(e.target.value);
      });
    });

    // Radius sliders
    const radiusSlider = this.container.querySelector('#radius-slider');
    const addressRadiusSlider = this.container.querySelector('#address-radius');

    radiusSlider?.addEventListener('input', (e) => {
      this.updateRadiusDisplay('radius-display', e.target.value);
    });

    addressRadiusSlider?.addEventListener('input', (e) => {
      this.updateRadiusDisplay('address-radius-display', e.target.value);
    });

    // Search button
    this.container.querySelector('#search-btn').addEventListener('click', () => {
      this.performSearch();
    });

    // Enter key on inputs
    this.container.querySelectorAll('input[type="text"]').forEach((input) => {
      input.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
          this.performSearch();
        }
      });
    });
  }

  switchSearchMode(mode) {
    this.searchMode = mode;

    // Hide all mode content
    this.container.querySelectorAll('.search-mode-content').forEach((content) => {
      content.classList.add('d-none');
    });

    // Show selected mode content
    this.container.querySelector(`#${mode}-search`).classList.remove('d-none');

    // Update search button text
    const searchBtnText = this.container.querySelector('#search-btn-text');
    const buttonTexts = {
      nearby: 'Search Nearby Restaurants',
      text: 'Search Restaurants',
      address: 'Search Near Address',
    };
    searchBtnText.textContent = buttonTexts[mode];
  }

  updateRadiusDisplay(displayId, value) {
    const display = this.container.querySelector(`#${displayId}`);
    if (display) {
      const miles = parseFloat(value);
      const km = miles * 1.60934;

      if (this.locale.useMiles) {
        display.textContent = `${miles.toFixed(1)} miles`;
      } else {
        display.textContent = `${km.toFixed(1)} km`;
      }
    }
  }

  async getCurrentLocation() {
    const statusDiv = this.container.querySelector('#location-status');
    const statusText = this.container.querySelector('#location-status-text');

    statusDiv.classList.remove('d-none');
    statusText.textContent = 'Getting your location...';

    try {
      const position = await this.getCurrentPosition();
      this.currentLocation = {
        lat: position.coords.latitude,
        lng: position.coords.longitude,
      };

      statusDiv.classList.remove('alert-info');
      statusDiv.classList.add('alert-success');
      statusText.innerHTML = '<i class="fas fa-check-circle me-2"></i>Location found! You can now search for nearby restaurants.';

      // Hide status after 3 seconds
      setTimeout(() => {
        statusDiv.classList.add('d-none');
      }, 3000);

    } catch (error) {
      statusDiv.classList.remove('alert-info');
      statusDiv.classList.add('alert-warning');
      statusText.innerHTML = '<i class="fas fa-exclamation-triangle me-2"></i>Location access denied. You can still search by address or text.';

      // Hide status after 5 seconds
      setTimeout(() => {
        statusDiv.classList.add('d-none');
      }, 5000);
    }
  }

  getCurrentPosition() {
    return new Promise((resolve, reject) => {
      if (!navigator.geolocation) {
        reject(new Error('Geolocation is not supported'));
        return;
      }

      navigator.geolocation.getCurrentPosition(resolve, reject, {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 300000, // 5 minutes
      });
    });
  }

  async performSearch() {
    if (this.isSearching) return;

    this.isSearching = true;
    const searchBtn = this.container.querySelector('#search-btn');
    const originalText = searchBtn.innerHTML;

    // Show loading state
    searchBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Searching...';
    searchBtn.disabled = true;

    try {
      let searchParams = {};

      switch (this.searchMode) {
        case 'nearby':
          if (!this.currentLocation) {
            throw new Error('Location not available. Please allow location access or use a different search mode.');
          }
          searchParams = {
            lat: this.currentLocation.lat,
            lng: this.currentLocation.lng,
            radius_miles: parseFloat(this.container.querySelector('#radius-slider').value),
            keyword: this.container.querySelector('#nearby-keyword').value.trim(),
          };
          break;

        case 'text':
          const query = this.container.querySelector('#text-query').value.trim();
          if (!query) {
            throw new Error('Please enter a search query.');
          }
          searchParams = {
            query,
            lat: this.currentLocation?.lat,
            lng: this.currentLocation?.lng,
          };
          break;

        case 'address':
          const address = this.container.querySelector('#address-input').value.trim();
          if (!address) {
            throw new Error('Please enter an address or location.');
          }
          // For address search, we'd need to geocode the address first
          // For now, we'll use the current location if available
          if (!this.currentLocation) {
            throw new Error('Address search requires location access. Please allow location access or use text search.');
          }
          searchParams = {
            lat: this.currentLocation.lat,
            lng: this.currentLocation.lng,
            radius_miles: parseFloat(this.container.querySelector('#address-radius').value),
            keyword: address,
          };
          break;
      }

      // Add filters
      const filters = this.getFilters();
      searchParams = { ...searchParams, ...filters };

      // Perform search
      const results = await this.searchRestaurants(searchParams);

      // Display results
      this.displayResults(results);

      // Call callback
      this.options.onResults(results);

    } catch (error) {
      console.error('Search error:', error);
      this.options.onError(error);
      this.showError(error.message);
    } finally {
      // Reset button state
      searchBtn.innerHTML = originalText;
      searchBtn.disabled = false;
      this.isSearching = false;
    }
  }

  getFilters() {
    return {
      cuisine: this.container.querySelector('#cuisine-filter').value,
      minRating: parseFloat(this.container.querySelector('#min-rating').value) || undefined,
      maxPriceLevel: parseInt(this.container.querySelector('#max-price').value, 10) || undefined,
      maxResults: parseInt(this.container.querySelector('#max-results').value, 10) || 20,
    };
  }

  async searchRestaurants(params) {
    // Use the API endpoint we created
    const queryParams = new URLSearchParams();

    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        queryParams.append(key, value);
      }
    });

    const response = await fetch(`/restaurants/api/places/search?${queryParams}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`Search failed: ${response.status} ${response.statusText}`);
    }

    const data = await response.json();
    return data.data;
  }

  displayResults(results) {
    const resultsContainer = this.container.querySelector('#search-results');

    if (!results.results || results.results.length === 0) {
      resultsContainer.innerHTML = `
        <div class="text-center text-muted py-4">
          <i class="fas fa-search fa-3x mb-2"></i>
          <p>No restaurants found. Try adjusting your search criteria.</p>
        </div>
      `;
      return;
    }

    const resultsHtml = results.results.map((restaurant) => {
      // Parse address for better display
      const address = this.parseAddress(restaurant);

      return `
      <div class="card mb-3 restaurant-card" data-place-id="${restaurant.place_id}">
        <div class="card-body">
          <div class="d-flex justify-content-between align-items-start">
            <div class="flex-grow-1">
              <h5 class="card-title">${restaurant.name}</h5>
              <div class="text-muted small">
                <div><i class="fas fa-map-marker-alt me-1"></i>${address.street}</div>
                ${address.cityStateZip ? `<div class="ms-3">${address.cityStateZip}</div>` : ''}
              </div>

              <div class="d-flex align-items-center gap-3">
                ${restaurant.rating ? `
                  <div class="restaurant-rating">
                    <i class="fas fa-star"></i> ${restaurant.rating}
                    <small class="text-muted">(${restaurant.user_ratings_total || 0} reviews)</small>
                  </div>
                ` : ''}

                ${restaurant.price_level ? `
                  <div class="price-level">
                    ${'$'.repeat(restaurant.price_level)}
                  </div>
                ` : ''}

                ${restaurant.business_status ? `
                  <span class="badge ${restaurant.business_status === 'OPERATIONAL' ? 'bg-success' : 'bg-warning'}">
                    ${restaurant.business_status}
                  </span>
                ` : ''}
              </div>
            </div>

            <button class="btn btn-outline-primary btn-sm" onclick="addToMyRestaurants('${restaurant.place_id}')">
              <i class="fas fa-plus me-1"></i>Add
            </button>
          </div>
        </div>
      </div>
    `;
    }).join('');

    const searchParams = results.search_params || {};
    const radiusDisplay = searchParams.radius_miles
      ? `${searchParams.radius_miles.toFixed(1)} miles`
      : 'specified area';

    resultsContainer.innerHTML = `
      <div class="search-results-header mb-3">
        <h6>Found ${results.results.length} restaurant${results.results.length !== 1 ? 's' : ''}</h6>
        ${searchParams.radius_miles ? `
          <small class="text-muted">
            <i class="fas fa-map-marker-alt me-1"></i>
            Within ${radiusDisplay} of your location
          </small>
        ` : ''}
      </div>
      ${resultsHtml}
    `;
  }

  showError(message) {
    const resultsContainer = this.container.querySelector('#search-results');
    resultsContainer.innerHTML = `
      <div class="alert alert-danger">
        <i class="fas fa-exclamation-triangle me-2"></i>
        ${message}
      </div>
    `;
  }

  parseAddress(restaurant) {
    // First, try to use structured address data if available (from details API)
    if (restaurant.address && restaurant.city && restaurant.state) {
      const street = restaurant.address;
      const cityState = restaurant.postal_code
        ? `${restaurant.city}, ${restaurant.state} ${restaurant.postal_code}`
        : `${restaurant.city}, ${restaurant.state}`;

      return {
        street,
        cityStateZip: cityState,
      };
    }

    // Fallback to parsing formatted_address or vicinity from search results
    const formatted = restaurant.formatted_address || restaurant.vicinity || '';

    if (!formatted) {
      return { street: 'Address not available', cityStateZip: '' };
    }

    // Enhanced parsing for search results - handle various formats
    // Try to extract state information from the address string
    const stateRegex = /\b([A-Z]{2})\b/g;
    const states = formatted.match(stateRegex);

    if (states && states.length > 0) {
      // Found state abbreviation, try to parse around it
      const state = states[0];
      const stateIndex = formatted.indexOf(state);

      // Extract everything after the state (should include city)
      const afterState = formatted.substring(stateIndex).trim();
      const beforeState = formatted.substring(0, stateIndex).trim();

      // Try to find city before state
      const parts = beforeState.split(',').map((p) => p.trim());
      if (parts.length > 0) {
        const street = parts[0];
        const city = parts.length > 1 ? parts[parts.length - 1] : '';

        return {
          street,
          cityStateZip: city ? `${city}, ${afterState}` : afterState,
        };
      }
    }

    // Split by commas and clean up
    const parts = formatted.split(',').map((part) => part.trim());

    if (parts.length >= 4) {
      // Format: "Street, City, State ZIP, Country"
      const street = parts[0];
      const city = parts[1];
      const stateZip = parts[2];

      return {
        street,
        cityStateZip: `${city}, ${stateZip}`,
      };
    } else if (parts.length === 3) {
      // Format: "Street, City, State ZIP" or "Street, City, Country"
      const street = parts[0];
      const city = parts[1];
      const lastPart = parts[2];

      // Check if last part contains state abbreviation or full state name
      const stateRegex = /\b[A-Z]{2}\b|\b(Alabama|Alaska|Arizona|Arkansas|California|Colorado|Connecticut|Delaware|Florida|Georgia|Hawaii|Idaho|Illinois|Indiana|Iowa|Kansas|Kentucky|Louisiana|Maine|Maryland|Massachusetts|Michigan|Minnesota|Mississippi|Missouri|Montana|Nebraska|Nevada|New Hampshire|New Jersey|New Mexico|New York|North Carolina|North Dakota|Ohio|Oklahoma|Oregon|Pennsylvania|Rhode Island|South Carolina|South Dakota|Tennessee|Texas|Utah|Vermont|Virginia|Washington|West Virginia|Wisconsin|Wyoming)\b/i;

      if (stateRegex.test(lastPart)) {
        // Contains state information
        return {
          street,
          cityStateZip: `${city}, ${lastPart}`,
        };
      }
      // Might be country or other info, include it anyway for completeness
      return {
        street,
        cityStateZip: `${city}, ${lastPart}`,
      };

    } else if (parts.length === 2) {
      // Format: "Street, City State" or "Street, City"
      const street = parts[0];
      const cityState = parts[1];

      // Try to extract state from cityState if it's in format "City State ZIP"
      const stateMatch = cityState.match(/\b([A-Z]{2})\s+\d{5}(-\d{4})?$/);
      if (stateMatch) {
        const cityOnly = cityState.replace(/\s+[A-Z]{2}\s+\d{5}(-\d{4})?$/, '');
        const stateZip = cityState.match(/\s+([A-Z]{2}\s+\d{5}(-\d{4})?)$/)[1];
        return {
          street,
          cityStateZip: `${cityOnly}, ${stateZip}`,
        };
      }

      return {
        street,
        cityStateZip: cityState,
      };
    }
    // Single part or fallback - try to extract any state information
    const stateMatch = formatted.match(/\b([A-Z]{2})\b/);
    if (stateMatch) {
      const beforeState = formatted.substring(0, stateMatch.index).trim();
      const afterState = formatted.substring(stateMatch.index).trim();
      return {
        street: beforeState,
        cityStateZip: afterState,
      };
    }

    return {
      street: formatted,
      cityStateZip: '',
    };

  }
}

// Note: Restaurant selection is now handled by the global addToMyRestaurants function
