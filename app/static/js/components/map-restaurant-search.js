/**
 * Map-Based Restaurant Search Component
 *
 * Provides a map-based interface for finding restaurants with photos, ratings, and reviews.
 * Features Google Maps integration with restaurant markers and detailed result cards.
 */

export class MapRestaurantSearch {
  constructor(container, options = {}) {
    this.container = container;
    this.options = {
      onSelect: options.onSelect || (() => {}),
      onError: options.onError || (() => {}),
      onResults: options.onResults || (() => {}),
      defaultRadiusMiles: options.defaultRadiusMiles || 3.1, // ~5km default
      maxRadiusMiles: options.maxRadiusMiles || 31.1, // ~50km max
      googleMapsApiKey: options.googleMapsApiKey || '',
      googleMapsMapId: options.googleMapsMapId || '',
      ...options,
    };

    this.map = null;
    this.markers = [];
    this.currentLocation = null;
    this.currentLocationMarker = null;
    this.searchMode = 'nearby'; // 'nearby', 'text', 'address'
    this.isSearching = false;
    this.locale = this.detectLocale();
    this.selectedRestaurant = null;

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
      unit: milesCountries.includes(countryCode) ? 'miles' : 'km'
    };
  }

  async init() {
    await this.loadGoogleMaps();
    await this.waitForGoogleMaps();
    this.render();
    this.bindEvents();
    this.getCurrentLocation();
  }

  async loadGoogleMaps() {
    if (window.google && window.google.maps) {
      return; // Already loaded
    }

    return new Promise((resolve, reject) => {
      const script = document.createElement('script');
      script.src = `https://maps.googleapis.com/maps/api/js?key=${this.options.googleMapsApiKey}&libraries=places,marker&loading=async`;
      script.async = true;
      script.onload = resolve;
      script.onerror = reject;
      document.head.appendChild(script);
    });
  }

  async waitForGoogleMaps() {
    // Wait for Google Maps API to be fully loaded including marker library
    return new Promise((resolve) => {
      const checkGoogleMaps = () => {
        if (window.google &&
            window.google.maps &&
            window.google.maps.Map &&
            window.google.maps.marker &&
            window.google.maps.marker.AdvancedMarkerElement) {
          resolve();
        } else {
          setTimeout(checkGoogleMaps, 100);
        }
      };
      checkGoogleMaps();
    });
  }

  render() {
    // Add CSS for enhanced card interactions
    if (!document.getElementById('map-restaurant-search-styles')) {
      const style = document.createElement('style');
      style.id = 'map-restaurant-search-styles';
      style.textContent = `
        .restaurant-card {
          transition: all 0.2s ease;
          border: 2px solid transparent;
        }

        .restaurant-card:hover {
          transform: translateY(-2px);
          box-shadow: 0 4px 12px rgba(0,0,0,0.15) !important;
          border-color: #dee2e6;
        }

        .restaurant-card.border-primary {
          border-color: #0d6efd !important;
          box-shadow: 0 0 0 0.2rem rgba(13, 110, 253, 0.25) !important;
        }

        .badge.bg-danger {
          transition: all 0.2s ease;
        }

        .restaurant-card:hover .badge.bg-danger {
          transform: scale(1.1);
        }
      `;
      document.head.appendChild(style);
    }

    this.container.innerHTML = `
      <div class="map-restaurant-search">
        <div class="row g-4">
          <!-- Left Column: Map -->
          <div class="col-lg-8">
            <div class="map-container">
              <div id="restaurant-map" style="height: 500px; border-radius: 8px; border: 1px solid #dee2e6;"></div>
            </div>
          </div>

          <!-- Right Column: Search Controls -->
          <div class="col-lg-4">
            <div class="search-panel bg-light p-3 rounded">
              <h6 class="mb-3">
                <i class="fas fa-search me-2"></i>Search & Filters
              </h6>

              <!-- Main Search -->
              <div class="mb-3">
                <label for="search-input" class="form-label">Find Restaurants</label>
                <div class="input-group">
                  <input type="text" class="form-control" id="search-input" placeholder="Name, cuisine, location...">
                  <button class="btn btn-primary" type="button" id="search-btn">
                    <i class="fas fa-search"></i>
                  </button>
                </div>
              </div>

              <!-- Location Button -->
              <div class="mb-3">
                <button class="btn btn-outline-secondary w-100" id="use-location-btn">
                  <i class="fas fa-map-marker-alt me-1"></i>Use My Location
                </button>
              </div>

              <!-- Search Radius -->
              <div class="mb-3">
                <label for="radius-slider" class="form-label">Search Radius</label>
                <div class="d-flex align-items-center">
                  <input type="range" class="form-range me-2" id="radius-slider" min="0.5" max="25" step="0.5" value="5">
                  <span id="radius-display" class="text-muted small">5.0 mi</span>
                </div>
              </div>

              <!-- Advanced Filters -->
              <div class="mb-3">
                <button class="btn btn-link p-0 text-decoration-none w-100 text-start" type="button" data-bs-toggle="collapse" data-bs-target="#advanced-filters" aria-expanded="false" aria-controls="advanced-filters">
                  <i class="fas fa-filter me-1"></i>Advanced Filters
                  <i class="fas fa-chevron-down ms-1"></i>
                </button>

                <div class="collapse mt-2" id="advanced-filters">
                  <div class="row g-2">
                    <div class="col-12">
                      <label for="cuisine-filter" class="form-label">Cuisine Type</label>
                      <select class="form-select form-select-sm" id="cuisine-filter">
                        <option value="">Any cuisine</option>
                        <option value="italian">Italian</option>
                        <option value="chinese">Chinese</option>
                        <option value="mexican">Mexican</option>
                        <option value="japanese">Japanese</option>
                        <option value="indian">Indian</option>
                        <option value="thai">Thai</option>
                        <option value="american">American</option>
                        <option value="french">French</option>
                        <option value="mediterranean">Mediterranean</option>
                        <option value="korean">Korean</option>
                      </select>
                    </div>

                    <div class="col-6">
                      <label for="min-rating" class="form-label">Min Rating</label>
                      <select class="form-select form-select-sm" id="min-rating">
                        <option value="">Any</option>
                        <option value="4.5">4.5+ ⭐</option>
                        <option value="4.0">4.0+ ⭐</option>
                        <option value="3.5">3.5+ ⭐</option>
                        <option value="3.0">3.0+ ⭐</option>
                      </select>
                    </div>

                    <div class="col-6">
                      <label for="max-price" class="form-label">Max Price</label>
                      <select class="form-select form-select-sm" id="max-price">
                        <option value="">Any</option>
                        <option value="1">$ (Budget)</option>
                        <option value="2">$$ (Moderate)</option>
                        <option value="3">$$$ (Expensive)</option>
                        <option value="4">$$$$ (Very Expensive)</option>
                      </select>
                    </div>


                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Results Section Below -->
        <div class="mt-4">
          <div id="results-header" class="d-flex justify-content-between align-items-center mb-3">
            <h5 class="mb-0">
              <i class="fas fa-utensils me-2"></i>Search Results
            </h5>
            <span id="results-count" class="badge bg-primary fs-6">0 restaurants found</span>
          </div>

          <div id="search-results" class="row g-3">
            <div class="col-12">
              <div class="text-center text-muted py-5">
                <i class="fas fa-search fa-3x mb-3"></i>
                <h6>Find restaurants in your area</h6>
                <p class="mb-0">Click "Search" to discover nearby dining options, or enter specific criteria above</p>
              </div>
            </div>
          </div>
        </div>

        <!-- Location Status -->
        <div id="location-status" class="alert alert-info d-none mt-3">
          <i class="fas fa-info-circle me-2"></i>
          <span id="location-status-text">Getting your location...</span>
        </div>
      </div>
    `;

    this.initMap();
  }

  initMap() {
    const mapElement = this.container.querySelector('#restaurant-map');

    // Default to San Francisco if no location available
    const defaultLocation = { lat: 37.7749, lng: -122.4194 };

    const mapOptions = {
      zoom: 13,
      center: defaultLocation,
      mapTypeControl: true,
      streetViewControl: false,
      fullscreenControl: true,
      zoomControl: true,
      // styles added conditionally below when no mapId is provided
    };

    if (this.options.googleMapsMapId) {
      mapOptions.mapId = this.options.googleMapsMapId;
    } else {
      // Only apply inline styles when not using a cloud-based Map ID style
      mapOptions.styles = [
        {
          featureType: 'poi',
          elementType: 'labels',
          stylers: [{ visibility: 'off' }],
        },
      ];
    }

    this.map = new google.maps.Map(mapElement, mapOptions);

    // Add click listener to map
    this.map.addListener('click', () => {
      this.clearSelection();
    });

    // Add location control button
    this.addLocationControl();
  }

  bindEvents() {
    // Search input
    const searchInput = this.container.querySelector('#search-input');
    const searchBtn = this.container.querySelector('#search-btn');

    searchInput.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') {
        this.performSearch();
      }
    });

    searchBtn.addEventListener('click', () => {
      this.performSearch();
    });

    // Use My Location button
    const useLocationBtn = this.container.querySelector('#use-location-btn');
    useLocationBtn.addEventListener('click', () => {
      this.useMyLocationAndSearch();
    });

    // Radius slider
    const radiusSlider = this.container.querySelector('#radius-slider');
    const radiusDisplay = this.container.querySelector('#radius-display');

    radiusSlider.addEventListener('input', (e) => {
      this.updateRadiusDisplay(radiusDisplay, e.target.value);
    });

    // Event delegation for restaurant cards and buttons
    this.container.addEventListener('click', (e) => {
      // Handle restaurant card clicks
      const restaurantCard = e.target.closest('.restaurant-card');
      if (restaurantCard) {
        const index = parseInt(restaurantCard.dataset.index, 10);
        if (!isNaN(index)) {
          this.selectRestaurant(index);
        }
      }

      // Handle add restaurant button clicks
      const addButton = e.target.closest('[data-action="add-restaurant"]');
      if (addButton) {
        e.stopPropagation(); // Prevent card selection
        const placeId = addButton.dataset.placeId;
        if (placeId && placeId !== 'null' && placeId !== 'undefined') {
          this.addToMyRestaurants(placeId);
        } else {
          console.error('No valid place ID found on button. placeId:', placeId);
        }
      }
    });

    // Add change listeners to filter controls for immediate re-search
    const filterControls = this.container.querySelectorAll('#cuisine-filter, #min-rating, #max-price');
    filterControls.forEach(control => {
      control.addEventListener('change', () => {
        // Re-search when filters change (works with or without search query)
        this.performSearch();
      });
    });
  }

  updateRadiusDisplay(display, value) {
    const miles = parseFloat(value);
    const km = miles * 1.60934;

    if (this.locale.useMiles) {
      display.textContent = `${miles.toFixed(1)} miles`;
    } else {
      display.textContent = `${km.toFixed(1)} km`;
    }
  }

  async useMyLocationAndSearch() {
    const statusDiv = this.container.querySelector('#location-status');
    const statusText = this.container.querySelector('#location-status-text');
    const useLocationBtn = this.container.querySelector('#use-location-btn');

    // Show loading state
    const originalText = useLocationBtn.innerHTML;
    useLocationBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Getting Location...';
    useLocationBtn.disabled = true;

    statusDiv.classList.remove('d-none');
    statusText.textContent = 'Getting your location...';

    try {
      const position = await this.getCurrentPosition();
      this.currentLocation = {
        lat: position.coords.latitude,
        lng: position.coords.longitude
      };

      // Update map center (let fitMapToMarkers handle the zoom)
      this.map.setCenter(this.currentLocation);

      statusDiv.classList.remove('alert-info');
      statusDiv.classList.add('alert-success');
      statusText.innerHTML = '<i class="fas fa-check-circle me-2"></i>Location found! Searching for nearby restaurants...';

      // Perform search automatically
      await this.performSearch();

      // Hide status after 3 seconds
      setTimeout(() => {
        statusDiv.classList.add('d-none');
      }, 3000);

    } catch (error) {
      statusDiv.classList.remove('alert-info');
      statusDiv.classList.add('alert-warning');
      statusText.innerHTML = '<i class="fas fa-exclamation-triangle me-2"></i>Location access denied. You can still search by text.';

      // Hide status after 5 seconds
      setTimeout(() => {
        statusDiv.classList.add('d-none');
      }, 5000);
    } finally {
      // Reset button state
      useLocationBtn.innerHTML = originalText;
      useLocationBtn.disabled = false;
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
        lng: position.coords.longitude
      };

      // Update map center and add location marker
      this.map.setCenter(this.currentLocation);
      this.addCurrentLocationMarker();

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
      statusText.innerHTML = '<i class="fas fa-exclamation-triangle me-2"></i>Location access denied. You can still search by text.';

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
        maximumAge: 300000 // 5 minutes
      });
    });
  }

  async performSearch() {
    if (this.isSearching) return;

    this.isSearching = true;
    const searchBtn = this.container.querySelector('#search-btn');
    const originalText = searchBtn.innerHTML;

    // Show loading state
    searchBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Searching...';
    searchBtn.disabled = true;

    try {
      const searchInput = this.container.querySelector('#search-input');
      const query = searchInput.value.trim();
      const radius = parseFloat(this.container.querySelector('#radius-slider').value);
      const filters = this.getFilters();

      // If no query provided, search for restaurants in the area
      const searchQuery = query || 'restaurants';

      // Always use current map center for search location
      const mapCenter = this.map.getCenter();
      const searchLocation = {
        lat: mapCenter.lat(),
        lng: mapCenter.lng()
      };

      // Build search parameters with proper filter application
      const searchParams = {
        query: searchQuery,
        lat: searchLocation.lat,
        lng: searchLocation.lng,
        radius_miles: radius,
        cuisine: filters.cuisine || '',
        minRating: filters.minRating || '',
        maxPriceLevel: filters.maxPriceLevel || '',
        maxResults: filters.maxResults || 20,
      };

      // Remove empty parameters
      Object.keys(searchParams).forEach(key => {
        if (searchParams[key] === '' || searchParams[key] === undefined) {
          delete searchParams[key];
        }
      });

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
      maxPriceLevel: parseInt(this.container.querySelector('#max-price').value) || undefined,
      maxResults: 20,
    };
  }

  async searchRestaurants(params) {
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
    const resultsCount = this.container.querySelector('#results-count');

    // Store current results for selection
    this.currentResults = results;

    // Clear existing markers
    this.clearMarkers();

    if (!results.results || results.results.length === 0) {
      resultsContainer.innerHTML = `
        <div class="col-12">
          <div class="text-center text-muted py-5">
            <i class="fas fa-search fa-3x mb-3"></i>
            <h6>No restaurants found</h6>
            <p class="mb-0">Try adjusting your search criteria or expanding your search radius</p>
          </div>
        </div>
      `;
      resultsCount.textContent = '0 restaurants found';
      return;
    }

    // Update results count
    const count = results.results.length;
    resultsCount.textContent = `${count} restaurant${count !== 1 ? 's' : ''} found`;

    // Create markers and result cards in grid layout
    const resultsHtml = results.results.map((restaurant, index) => {
      // Create marker
      this.createMarker(restaurant, index);

      // Create result card in grid column
      return `
        <div class="col-lg-4 col-md-6 col-sm-12">
          ${this.createResultCard(restaurant, index)}
        </div>
      `;
    }).join('');

    resultsContainer.innerHTML = resultsHtml;

    // Fit map to show all markers
    this.fitMapToMarkers();
  }

  createMarker(restaurant, index) {
    if (!restaurant.geometry || !restaurant.geometry.location) {
      return;
    }

    const position = {
      lat: restaurant.geometry.location.lat,
      lng: restaurant.geometry.location.lng
    };

    // Use AdvancedMarkerElement with numbered content
    const marker = new google.maps.marker.AdvancedMarkerElement({
      position: position,
      map: this.map,
      title: restaurant.name,
      content: this.createNumberedMarkerContent(index + 1, 'red')
    });

    // Add click listener
    marker.addListener('click', () => {
      this.selectRestaurant(index, restaurant);
    });

    this.markers.push(marker);
  }

  createNumberedMarkerContent(number, color) {
    const markerElement = document.createElement('div');
    markerElement.style.cssText = `
      width: 36px;
      height: 36px;
      background-color: ${color === 'red' ? '#ea4335' : '#4285f4'};
      border: 3px solid white;
      border-radius: 50%;
      box-shadow: 0 3px 6px rgba(0,0,0,0.4);
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: bold;
      font-size: 14px;
      color: white;
      cursor: pointer;
      transition: all 0.2s ease;
    `;

    markerElement.textContent = number;

    // Add hover effect
    markerElement.addEventListener('mouseenter', () => {
      markerElement.style.transform = 'scale(1.1)';
      markerElement.style.boxShadow = '0 4px 8px rgba(0,0,0,0.5)';
    });

    markerElement.addEventListener('mouseleave', () => {
      markerElement.style.transform = 'scale(1)';
      markerElement.style.boxShadow = '0 3px 6px rgba(0,0,0,0.4)';
    });

    return markerElement;
  }

  createMarkerContent(color) {
    const markerElement = document.createElement('div');
    markerElement.style.cssText = `
      width: 32px;
      height: 32px;
      background-color: ${color === 'red' ? '#ea4335' : '#4285f4'};
      border: 2px solid white;
      border-radius: 50%;
      box-shadow: 0 2px 4px rgba(0,0,0,0.3);
      display: flex;
      align-items: center;
      justify-content: center;
    `;

    const icon = document.createElement('i');
    icon.className = 'fas fa-utensils';
    icon.style.cssText = 'color: white; font-size: 12px;';
    markerElement.appendChild(icon);

    return markerElement;
  }

  createResultCard(restaurant, index) {
    const photoUrl = restaurant.photos && restaurant.photos.length > 0
      ? `https://maps.googleapis.com/maps/api/place/photo?maxwidth=300&photoreference=${restaurant.photos[0].photo_reference}&key=${this.options.googleMapsApiKey}`
      : null;

    const rating = restaurant.rating || 0;
    const reviewCount = restaurant.user_ratings_total || 0;
    const priceLevel = restaurant.price_level || 0;

    // Parse address for better display
    const address = this.parseAddress(restaurant);

    // Check opening hours
    const openingStatus = this.getOpeningStatus(restaurant.opening_hours);

    // Contact information
    const phone = restaurant.formatted_phone_number;
    const website = restaurant.website;

    return `
      <div class="card h-100 restaurant-card" data-index="${index}" style="cursor: pointer; position: relative;">
        <!-- Numbered badge to correlate with map markers -->
        <div class="position-absolute top-0 start-0 m-2">
          <span class="badge bg-danger rounded-circle" style="width: 28px; height: 28px; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: bold;">
            ${index + 1}
          </span>
        </div>

        <!-- Open/Closed status badge -->
        ${openingStatus.badge ? `
          <div class="position-absolute top-0 end-0 m-2">
            <span class="badge ${openingStatus.class} small">
              ${openingStatus.text}
            </span>
          </div>
        ` : ''}

        ${photoUrl ? `
          <img src="${photoUrl}" class="card-img-top" alt="${restaurant.name}" style="height: 140px; object-fit: cover;" loading="lazy">
        ` : `
          <div class="card-img-top bg-light d-flex align-items-center justify-content-center" style="height: 140px;">
            <i class="fas fa-utensils fa-2x text-muted"></i>
          </div>
        `}

        <div class="card-body d-flex flex-column p-3">
          <!-- Header with name, price, and rating -->
          <div class="d-flex justify-content-between align-items-start mb-2">
            <div class="flex-grow-1">
              <h6 class="card-title mb-1 d-flex align-items-center gap-2">
                ${restaurant.name}
                ${priceLevel > 0 ? `
                  <span class="price-level text-success fw-bold small">
                    ${'$'.repeat(priceLevel)}
                  </span>
                ` : ''}
              </h6>
            </div>
            ${rating > 0 ? `
              <div class="d-flex align-items-center text-end">
                <i class="fas fa-star text-warning me-1"></i>
                <span class="small fw-bold">${rating.toFixed(1)}</span>
                <span class="text-muted small ms-1">(${reviewCount})</span>
              </div>
            ` : ''}
          </div>

          <!-- Address -->
          <div class="mb-2">
            <div class="d-flex align-items-start text-muted small">
              <i class="fas fa-map-marker-alt me-2 text-secondary mt-1" style="opacity:0.7;"></i>
              <div class="flex-grow-1">
                <div>${address.street}</div>
                ${address.cityStateZip ? `<div>${address.cityStateZip}</div>` : ''}
              </div>
            </div>
          </div>

          <!-- Contact Information -->
          ${phone || website ? `
            <div class="mb-3">
              ${phone ? `
                <div class="d-flex align-items-center text-muted small mb-1">
                  <i class="fas fa-phone me-2 text-secondary" style="opacity:0.7;"></i>
                  <a href="tel:${phone}" class="text-decoration-none text-muted">${phone}</a>
                </div>
              ` : ''}
              ${website ? `
                <div class="d-flex align-items-center text-muted small">
                  <i class="fas fa-globe me-2 text-secondary" style="opacity:0.7;"></i>
                  <a href="${website}" target="_blank" rel="noopener" class="text-decoration-none text-muted">
                    Website <i class="fas fa-external-link-alt ms-1" style="font-size: 10px;"></i>
                  </a>
                </div>
              ` : ''}
            </div>
          ` : ''}

          <!-- Current hours info -->
          ${openingStatus.hoursText ? `
            <div class="mb-3">
              <div class="d-flex align-items-start text-muted small">
                <i class="fas fa-clock me-2 text-secondary mt-1" style="opacity:0.7;"></i>
                <div>${openingStatus.hoursText}</div>
              </div>
            </div>
          ` : ''}

          <!-- Add button -->
          <div class="mt-auto">
            <button class="btn btn-primary btn-sm w-100" data-place-id="${restaurant.place_id}" data-action="add-restaurant">
              <i class="fas fa-plus me-1"></i>Add to My Restaurants
            </button>
          </div>
        </div>
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
        street: street,
        cityStateZip: cityState
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
      const parts = beforeState.split(',').map(p => p.trim());
      if (parts.length > 0) {
        const street = parts[0];
        const city = parts.length > 1 ? parts[parts.length - 1] : '';

        return {
          street: street,
          cityStateZip: city ? `${city}, ${afterState}` : afterState
        };
      }
    }

    // Split by commas and clean up
    const parts = formatted.split(',').map(part => part.trim());

    if (parts.length >= 4) {
      // Format: "Street, City, State ZIP, Country"
      const street = parts[0];
      const city = parts[1];
      const stateZip = parts[2];

      return {
        street: street,
        cityStateZip: `${city}, ${stateZip}`
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
          street: street,
          cityStateZip: `${city}, ${lastPart}`
        };
      } else {
        // Might be country or other info, include it anyway for completeness
        return {
          street: street,
          cityStateZip: `${city}, ${lastPart}`
        };
      }
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
          street: street,
          cityStateZip: `${cityOnly}, ${stateZip}`
        };
      }

      return {
        street: street,
        cityStateZip: cityState
      };
    } else {
      // Single part or fallback - try to extract any state information
      const stateMatch = formatted.match(/\b([A-Z]{2})\b/);
      if (stateMatch) {
        const beforeState = formatted.substring(0, stateMatch.index).trim();
        const afterState = formatted.substring(stateMatch.index).trim();
        return {
          street: beforeState,
          cityStateZip: afterState
        };
      }

      return {
        street: formatted,
        cityStateZip: ''
      };
    }
  }

  getOpeningStatus(openingHours) {
    if (!openingHours) {
      return { badge: false };
    }

    const openNow = openingHours.open_now;
    const weekdayText = openingHours.weekday_text;

    let status = { badge: false, hoursText: '' };

    if (typeof openNow === 'boolean') {
      status.badge = true;
      if (openNow) {
        status.class = 'bg-success';
        status.text = 'Open';
      } else {
        status.class = 'bg-danger';
        status.text = 'Closed';
      }
    }

    // Add today's hours if available
    if (weekdayText && weekdayText.length > 0) {
      const today = new Date().getDay(); // 0 = Sunday, 1 = Monday, etc.
      const todaysHours = weekdayText[today === 0 ? 6 : today - 1]; // Adjust for Monday start

      if (todaysHours) {
        // Extract just the hours part (after the day name and colon)
        const hoursMatch = todaysHours.match(/:\s*(.+)$/);
        if (hoursMatch) {
          status.hoursText = hoursMatch[1];
        }
      }
    }

    return status;
  }

  selectRestaurant(index) {
    // Get restaurant data from the current results
    const restaurant = this.currentResults?.results?.[index];
    if (!restaurant) return;

    // Clear previous selection
    this.clearSelection();

    // Highlight selected restaurant card
    const card = this.container.querySelector(`[data-index="${index}"]`);
    if (card) {
      card.classList.add('border-primary', 'shadow-lg');
      card.style.transform = 'scale(1.02)';
      card.style.transition = 'all 0.2s ease';

      // Scroll to selected card
      card.scrollIntoView({
        behavior: 'smooth',
        block: 'nearest',
        inline: 'nearest'
      });
    }

    // Highlight marker
    if (this.markers[index]) {
      const marker = this.markers[index];
      marker.content = this.createNumberedMarkerContent(index + 1, 'blue');
    }

    // Center map on selected restaurant
    if (restaurant.geometry && restaurant.geometry.location) {
      this.map.setCenter({
        lat: restaurant.geometry.location.lat,
        lng: restaurant.geometry.location.lng
      });
      this.map.setZoom(16);
    }

    this.selectedRestaurant = restaurant;
    this.options.onSelect(restaurant);
  }

  clearSelection() {
    // Clear card selection
    this.container.querySelectorAll('.restaurant-card').forEach(card => {
      card.classList.remove('border-primary', 'shadow-lg');
      card.style.transform = 'scale(1)';
    });

    // Reset all markers to red with numbers
    this.markers.forEach((marker, index) => {
      if (marker.content) {
        // AdvancedMarkerElement
        marker.content = this.createNumberedMarkerContent(index + 1, 'red');
      }
    });

    this.selectedRestaurant = null;
  }

  clearMarkers() {
    this.markers.forEach(marker => {
      marker.setMap(null);
    });
    this.markers = [];
  }

  addCurrentLocationMarker() {
    if (!this.currentLocation) return;

    // Remove existing current location marker
    if (this.currentLocationMarker) {
      this.currentLocationMarker.map = null;
    }

    // Create a blue dot marker for current location
    const currentLocationElement = document.createElement('div');
    currentLocationElement.innerHTML = `
      <div style="
        width: 20px;
        height: 20px;
        background: #4285f4;
        border: 3px solid white;
        border-radius: 50%;
        box-shadow: 0 2px 6px rgba(0,0,0,0.3);
        position: relative;
      ">
        <div style="
          width: 40px;
          height: 40px;
          background: rgba(66, 133, 244, 0.3);
          border-radius: 50%;
          position: absolute;
          top: 50%;
          left: 50%;
          transform: translate(-50%, -50%);
          animation: pulse 2s infinite;
        "></div>
      </div>
      <style>
        @keyframes pulse {
          0% { transform: translate(-50%, -50%) scale(1); opacity: 1; }
          100% { transform: translate(-50%, -50%) scale(2); opacity: 0; }
        }
      </style>
    `;

    this.currentLocationMarker = new google.maps.marker.AdvancedMarkerElement({
      position: this.currentLocation,
      map: this.map,
      content: currentLocationElement,
      title: 'Your Location'
    });
  }

  addLocationControl() {
    // Create custom location control button
    const locationButton = document.createElement('button');
    locationButton.innerHTML = '<i class="fas fa-location-arrow"></i>';
    locationButton.className = 'btn btn-light btn-sm';
    locationButton.style.cssText = `
      margin: 10px;
      box-shadow: 0 2px 6px rgba(0,0,0,0.3);
      border: none;
      width: 40px;
      height: 40px;
      border-radius: 2px;
      cursor: pointer;
      background-color: white;
      color: #666;
    `;
    locationButton.title = 'Go to your location';

    // Add hover effects
    locationButton.addEventListener('mouseenter', () => {
      locationButton.style.backgroundColor = '#f5f5f5';
    });
    locationButton.addEventListener('mouseleave', () => {
      locationButton.style.backgroundColor = 'white';
    });

    // Add click handler
    locationButton.addEventListener('click', () => {
      this.goToCurrentLocation();
    });

    // Add to map
    this.map.controls[google.maps.ControlPosition.RIGHT_BOTTOM].push(locationButton);
  }

  async goToCurrentLocation() {
    try {
      const position = await this.getCurrentPosition();
      this.currentLocation = {
        lat: position.coords.latitude,
        lng: position.coords.longitude
      };

      // Center map on current location
      this.map.setCenter(this.currentLocation);
      this.map.setZoom(15);

      // Add or update current location marker
      this.addCurrentLocationMarker();

      // Show success message
      const statusDiv = this.container.querySelector('#location-status');
      const statusText = this.container.querySelector('#location-status-text');

      if (statusDiv && statusText) {
        statusDiv.classList.remove('d-none', 'alert-warning');
        statusDiv.classList.add('alert-success');
        statusText.innerHTML = '<i class="fas fa-check-circle me-2"></i>Location found!';

        setTimeout(() => {
          statusDiv.classList.add('d-none');
        }, 3000);
      }

    } catch (error) {
      console.warn('Could not get current location:', error);

      // Show error message
      const statusDiv = this.container.querySelector('#location-status');
      const statusText = this.container.querySelector('#location-status-text');

      if (statusDiv && statusText) {
        statusDiv.classList.remove('d-none', 'alert-success');
        statusDiv.classList.add('alert-warning');
        statusText.innerHTML = '<i class="fas fa-exclamation-triangle me-2"></i>Location access denied.';

        setTimeout(() => {
          statusDiv.classList.add('d-none');
        }, 5000);
      }
    }
  }

  fitMapToMarkers() {
    if (this.markers.length === 0) return;

    const bounds = new google.maps.LatLngBounds();
    this.markers.forEach(marker => {
      let position;
      if (marker.getPosition) {
        // Regular Marker
        position = marker.getPosition();
      } else if (marker.position) {
        // AdvancedMarkerElement
        position = marker.position;
      }

      if (position) {
        bounds.extend(position);
      }
    });

    // Get current search radius to determine appropriate zoom
    const radiusSlider = this.container.querySelector('#radius-slider');
    const searchRadius = radiusSlider ? parseFloat(radiusSlider.value) : 5;

    // Calculate appropriate zoom level based on search radius
    let maxZoom = 15;
    if (searchRadius <= 1) maxZoom = 16;
    else if (searchRadius <= 2) maxZoom = 15;
    else if (searchRadius <= 5) maxZoom = 14;
    else if (searchRadius <= 10) maxZoom = 13;
    else if (searchRadius <= 20) maxZoom = 12;
    else maxZoom = 11;

    this.map.fitBounds(bounds);

    // Ensure appropriate zoom level based on search radius
    const listener = google.maps.event.addListener(this.map, 'idle', () => {
      if (this.map.getZoom() > maxZoom) {
        this.map.setZoom(maxZoom);
      }
      google.maps.event.removeListener(listener);
    });
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

  addToMyRestaurants(placeId) {
    // Call the global function defined in the template
    if (window.addToMyRestaurants && typeof window.addToMyRestaurants === 'function') {
      try {
        window.addToMyRestaurants(placeId);
      } catch (error) {
        console.error('Error calling global addToMyRestaurants:', error);
      }
    } else {
      console.error('addToMyRestaurants function not available');
    }
  }
}

// Global functions for restaurant selection and adding
window.selectRestaurant = function(index) {
  // This will be handled by the component instance
  console.log('Selected restaurant index:', index);
};
