/**
 * Map-Based Restaurant Search Component
 *
 * Provides a map-based interface for finding restaurants with photos, ratings, and reviews.
 * Features Google Maps integration with restaurant markers and detailed result cards.
 */

import { initializeRobustFaviconHandling } from '../utils/robust-favicon-handler.js';

// Import security utilities for XSS prevention
let escapeHtml;
if (typeof window !== 'undefined' && window.SecurityUtils) {
  ({ escapeHtml } = window.SecurityUtils);
} else {
  // Fallback escapeHtml implementation
  escapeHtml = function(text) {
    if (text === null || text === undefined) {
      return '';
    }
    const textString = String(text);
    const map = {
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#x27;',
      '/': '&#x2F;',
    };
    return textString.replace(/[&<>"'/]/g, (char) => map[char]);
  };
}

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
    this.markerEntries = [];
    this.currentLocation = null;
    this.currentLocationMarker = null;
    this.searchAreaCircle = null;
    this.searchMode = 'nearby'; // 'nearby', 'text', 'address'
    this.isSearching = false;
    this.locale = this.detectLocale();
    this.selectedRestaurant = null;
    this.selectedResultKey = null;
    this.activeInfoWindow = null;
    this.myRestaurantsLoaded = false;
    this.myRestaurantsByPlaceId = new Map();
    this.myRestaurantsByFallbackKey = new Map();
    this.myRestaurantsCache = [];
    this.currentResults = null;
    this.visibleResults = [];
    this.resultsFilter = 'all';
    this.discoveryScope = 'combined';
    this.includeMine = true;
    this.includeNew = true;
    this.sortMode = 'distance';
    this.requestedMaxResults = 20;
    this.maxResultsStep = 10;
    this.maxResultsCap = 40;
    this.lastSearchContext = null;

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

  async init() {
    await this.loadGoogleMaps();
    await this.waitForGoogleMaps();
    this.render();
    this.bindEvents();
    this.applyInitialDiscoveryMode();
    this.getCurrentLocation();
  }

  applyInitialDiscoveryMode() {
    const mode = this.options.initialDiscoveryMode;
    if (mode === 'my') {
      this.discoveryScope = 'my';
      this.includeMine = true;
      this.includeNew = false;
    } else if (mode === 'nearby') {
      this.discoveryScope = 'combined';
      this.includeMine = true;
      this.includeNew = true;
    } else {
      this.discoveryScope = 'combined';
      this.includeMine = true;
      this.includeNew = true;
    }

    const scopeSelect = this.container.querySelector('#search-scope');
    const includeMine = this.container.querySelector('#include-mine-toggle');
    const includeNew = this.container.querySelector('#include-new-toggle');
    if (scopeSelect) {
      scopeSelect.value = this.discoveryScope;
    }
    if (includeMine instanceof HTMLInputElement) {
      includeMine.checked = this.includeMine;
    }
    if (includeNew instanceof HTMLInputElement) {
      includeNew.checked = this.includeNew;
    }
    this.updateResultToggleButtons();
  }

  // eslint-disable-next-line require-await -- returns Promise for script loading
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

  // eslint-disable-next-line require-await -- returns Promise for polling
  async waitForGoogleMaps() {
    // Wait for Google Maps API to be fully loaded including marker library
    return new Promise((resolve) => {
      const checkGoogleMaps = () => {
        if (
          window.google &&
          window.google.maps &&
          window.google.maps.Map &&
          window.google.maps.marker &&
          window.google.maps.marker.AdvancedMarkerElement
        ) {
          resolve();
        } else {
          setTimeout(checkGoogleMaps, 100);
        }
      };
      checkGoogleMaps();
    });
  }

  render() {
    this.container.innerHTML = `
      <div class="map-restaurant-search discovery-layout">
        <div class="row g-3 align-items-start">
          <div class="col-12 col-xl-8">
            <div class="map-container discovery-map-panel">
              <div class="discovery-map-toolbar">
                <span class="map-toolbar-label"><i class="fas fa-map me-1"></i>Search area</span>
                <button class="btn btn-outline-secondary btn-sm" id="use-location-btn" type="button">
                  <i class="fas fa-location-arrow me-1"></i>Use My Location
                </button>
              </div>
              <div id="restaurant-map" class="discovery-map-canvas"></div>
            </div>
          </div>

          <div class="col-12 col-xl-4">
            <div class="search-panel discovery-control-panel p-3 rounded">
              <h6 class="mb-3"><i class="fas fa-sliders-h me-2"></i>Search Controls</h6>

              <div class="mb-3">
                <label for="search-input" class="form-label">What are you craving?</label>
                <div class="input-group">
                  <input type="text" class="form-control" id="search-input" placeholder="Try tacos, ramen, brunch..." />
                  <button class="btn btn-primary" type="button" id="search-btn">
                    <i class="fas fa-search me-1"></i>Search
                  </button>
                </div>
              </div>

              <div class="mb-3">
                <label for="radius-slider" class="form-label">Search radius</label>
                <div class="d-flex align-items-center gap-2">
                  <input type="range" class="form-range" id="radius-slider" min="0.5" max="25" step="0.5" value="5" />
                  <span id="radius-display" class="text-muted small">5.0 mi</span>
                </div>
              </div>

              <div class="discovery-filters mb-3">
                <div class="row g-2">
                  <div class="col-12">
                    <label for="cuisine-filter" class="form-label">Cuisine</label>
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
                    <label for="min-rating" class="form-label">Min rating</label>
                    <select class="form-select form-select-sm" id="min-rating">
                      <option value="">Any</option>
                      <option value="4.5">4.5+ ⭐</option>
                      <option value="4.0">4.0+ ⭐</option>
                      <option value="3.5">3.5+ ⭐</option>
                      <option value="3.0">3.0+ ⭐</option>
                    </select>
                  </div>

                  <div class="col-6">
                    <label for="max-price" class="form-label">Max price</label>
                    <select class="form-select form-select-sm" id="max-price">
                      <option value="">Any</option>
                      <option value="1">$ (Budget)</option>
                      <option value="2">$$ (Moderate)</option>
                      <option value="3">$$$ (Expensive)</option>
                      <option value="4">$$$$ (Very Expensive)</option>
                    </select>
                  </div>

                  <div class="col-6">
                    <label for="search-scope" class="form-label">Source</label>
                    <select class="form-select form-select-sm" id="search-scope">
                      <option value="combined" selected>Combined</option>
                      <option value="google">Google only</option>
                      <option value="my">My restaurants only</option>
                    </select>
                  </div>

                  <div class="col-6">
                    <label for="sort-by" class="form-label">Sort by</label>
                    <select class="form-select form-select-sm" id="sort-by">
                      <option value="distance" selected>Distance</option>
                      <option value="name">Name (A-Z)</option>
                      <option value="rating">Rating</option>
                    </select>
                  </div>
                </div>
              </div>

              <div class="mb-3">
                <div class="small text-muted mb-1">Include in results</div>
                <div class="d-flex flex-wrap gap-3">
                  <label class="form-check form-switch m-0">
                    <input class="form-check-input" type="checkbox" id="include-mine-toggle" checked />
                    <span class="form-check-label">My restaurants</span>
                  </label>
                  <label class="form-check form-switch m-0">
                    <input class="form-check-input" type="checkbox" id="include-new-toggle" checked />
                    <span class="form-check-label">New places</span>
                  </label>
                </div>
              </div>

              <div class="small text-muted discovery-help-copy">
                Balanced mode returns up to 20 results first. Use <strong>Load More</strong> to fetch 10 more.
              </div>
              <details class="small text-muted mt-2">
                <summary class="cursor-pointer">How search API options work</summary>
                <div class="mt-1">
                  <div><strong>query</strong>: keyword or cuisine text.</div>
                  <div><strong>radius_miles</strong>: strict radius around map center.</div>
                  <div><strong>minRating/maxPriceLevel</strong>: optional quality filters.</div>
                  <div><strong>searchScope</strong>: combined, google only, or my restaurants.</div>
                  <div><strong>maxResults</strong>: balanced starts at 20, then +10 via Load More.</div>
                </div>
              </details>

              <div class="d-grid">
                <button class="btn btn-primary" type="button" id="search-btn-secondary">
                  <i class="fas fa-compass me-1"></i>Search This Area
                </button>
              </div>
            </div>
          </div>
        </div>

        <div class="mt-3">
          <div id="results-header" class="d-flex justify-content-between align-items-center mb-3">
            <h5 class="mb-0">
              <i class="fas fa-utensils me-2"></i>Best Matches Nearby
              <span id="location-indicator" class="badge bg-success ms-2 d-none">
                <i class="fas fa-map-marker-alt me-1"></i>Location-based
              </span>
              <span id="radius-indicator" class="badge bg-info-subtle text-info-emphasis ms-2 d-none"></span>
            </h5>
            <div class="d-flex flex-column flex-sm-row align-items-sm-center gap-2">
              <div class="btn-group btn-group-sm discovery-ownership-filter" role="group" aria-label="Filter results">
                <button type="button" class="btn btn-outline-secondary active" data-result-filter="all">All</button>
                <button type="button" class="btn btn-outline-secondary" data-result-filter="mine">My Restaurants</button>
                <button type="button" class="btn btn-outline-secondary" data-result-filter="new">New To Me</button>
              </div>
              <span id="results-count" class="badge bg-primary fs-6">0 restaurants found</span>
            </div>
          </div>

          <div id="search-diagnostics" class="search-diagnostics text-muted small mb-3"></div>

          <div class="discovery-legend mb-2">
            <span class="legend-item"><i class="fas fa-circle text-primary me-1"></i>My restaurants</span>
            <span class="legend-item"><i class="fas fa-circle text-danger me-1"></i>New places</span>
          </div>

          <div id="search-results" class="discovery-results-list">
            <div class="discovery-empty text-center text-muted py-5">
              <i class="fas fa-search fa-3x mb-3"></i>
              <h6>Find restaurants in your area</h6>
              <p class="mb-2">Move the map, set your filters, then search this area</p>
              <small class="text-muted">Leave the search box empty to discover all nearby restaurants</small>
            </div>
          </div>
          <div class="d-flex justify-content-center mt-3">
            <button class="btn btn-outline-primary d-none" type="button" id="load-more-btn">
              <i class="fas fa-plus-circle me-1"></i>Load More (10)
            </button>
          </div>
        </div>

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
      const mapId = this.options.googleMapsMapId.trim();
      mapOptions.mapId = mapId;
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
    const searchBtnSecondary = this.container.querySelector('#search-btn-secondary');

    searchInput.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') {
        this.performSearch();
      }
    });

    searchBtn.addEventListener('click', () => {
      this.performSearch();
    });

    searchBtnSecondary?.addEventListener('click', () => {
      this.performSearch();
    });

    const loadMoreBtn = this.container.querySelector('#load-more-btn');
    loadMoreBtn?.addEventListener('click', () => {
      if (this.requestedMaxResults >= this.maxResultsCap) return;
      this.requestedMaxResults = Math.min(this.maxResultsCap, this.requestedMaxResults + this.maxResultsStep);
      this.performSearch({ preserveRequestedMax: true });
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
      const targetEl = e.target instanceof Element ? e.target : null;
      if (!targetEl) return;

      // Handle restaurant card clicks
      const restaurantCard = targetEl.closest('.restaurant-card');
      if (restaurantCard && !targetEl.closest('a, button')) {
        const index = parseInt(restaurantCard.dataset.index, 10);
        if (!isNaN(index)) {
          this.selectRestaurant(index);
        }
      }

      // Handle add restaurant button clicks
      const addButton = targetEl.closest('[data-action="add-restaurant"]');
      if (addButton) {
        e.stopPropagation(); // Prevent card selection
        const { placeId } = addButton.dataset;
        if (placeId && placeId !== 'null' && placeId !== 'undefined' && placeId.trim() !== '') {
          this.addToMyRestaurants(placeId);
        } else {
          console.warn(
            'Restaurant cannot be added: missing Google Place ID. This restaurant may need to be added manually.',
          );
          // Note: User-friendly message shown via console.warn above
        }
      }

      const filterButton = targetEl.closest('[data-result-filter]');
      if (filterButton) {
        const { resultFilter } = filterButton.dataset;
        this.setResultsFilter(resultFilter || 'all');
      }
    });

    // Add change listeners to filter controls for immediate re-search
    const filterControls = this.container.querySelectorAll('#cuisine-filter, #min-rating, #max-price, #search-scope');
    filterControls.forEach((control) => {
      control.addEventListener('change', () => {
        if (control.id === 'search-scope') {
          this.discoveryScope = control.value || 'combined';
        }
        this.requestedMaxResults = 20;
        this.performSearch();
      });
    });

    const sortControl = this.container.querySelector('#sort-by');
    sortControl?.addEventListener('change', () => {
      this.sortMode = sortControl.value || 'distance';
      this.renderVisibleResults({ fitMap: false });
    });

    const includeMineToggle = this.container.querySelector('#include-mine-toggle');
    const includeNewToggle = this.container.querySelector('#include-new-toggle');
    const onOwnershipToggle = () => {
      this.includeMine = includeMineToggle instanceof HTMLInputElement ? includeMineToggle.checked : true;
      this.includeNew = includeNewToggle instanceof HTMLInputElement ? includeNewToggle.checked : true;
      this.updateResultToggleButtons();
      this.renderVisibleResults({ fitMap: false });
    };
    includeMineToggle?.addEventListener('change', onOwnershipToggle);
    includeNewToggle?.addEventListener('change', onOwnershipToggle);
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
    statusText.textContent = 'Requesting location permission...';

    try {
      const position = await this.getCurrentPosition();
      this.currentLocation = {
        lat: position.coords.latitude,
        lng: position.coords.longitude,
      };

      // Update map center and show user location
      this.map.setCenter(this.currentLocation);
      this.addCurrentLocationMarker();

      statusDiv.classList.remove('alert-info');
      statusDiv.classList.add('alert-success');
      statusText.innerHTML =
        '<i class="fas fa-check-circle me-2"></i>Location found! Searching for restaurants in your area...';

      // Perform search automatically with location-based results
      await this.performSearch();

      // Hide status after 3 seconds
      setTimeout(() => {
        statusDiv.classList.add('d-none');
      }, 3000);
    } catch {
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
        lng: position.coords.longitude,
      };

      // Update map center and add location marker
      this.map.setCenter(this.currentLocation);
      this.addCurrentLocationMarker();

      statusDiv.classList.remove('alert-info');
      statusDiv.classList.add('alert-success');
      statusText.innerHTML =
        '<i class="fas fa-check-circle me-2"></i>Location found! You can now search for nearby restaurants.';

      // Hide status after 3 seconds
      setTimeout(() => {
        statusDiv.classList.add('d-none');
      }, 3000);
    } catch {}
  }

  getCurrentPosition() {
    return new Promise((resolve, reject) => {
      if (!navigator.geolocation) {
        reject(new Error('Geolocation is not supported'));
        return;
      }

      navigator.geolocation.getCurrentPosition(
        resolve,
        (error) => {
          // Provide more specific error messages for better user feedback
          switch (error.code) {
            case error.PERMISSION_DENIED:
              reject(new Error('User denied geolocation request'));
              break;
            case error.POSITION_UNAVAILABLE:
              reject(new Error('Location information unavailable'));
              break;
            case error.TIMEOUT:
              reject(new Error('Location request timed out'));
              break;
            default:
              reject(new Error(`Geolocation error: ${error.message}`));
              break;
          }
        },
        {
          enableHighAccuracy: true,
          timeout: 15000, // Increased timeout for better success rate
          maximumAge: 300000, // 5 minutes
        },
      );
    });
  }

  async ensureMyRestaurantsLoaded(forceRefresh = false) {
    if (this.myRestaurantsLoaded && !forceRefresh) {
      return;
    }

    const response = await fetch('/api/v1/restaurants', {
      method: 'GET',
      headers: { Accept: 'application/json' },
    });

    if (!response.ok) {
      throw new Error('Failed to load your restaurants for ownership matching.');
    }

    const payload = await response.json();
    const restaurants = payload.data || payload || [];
    this.myRestaurantsCache = Array.isArray(restaurants) ? restaurants : [];

    this.myRestaurantsByPlaceId.clear();
    this.myRestaurantsByFallbackKey.clear();

    restaurants.forEach((restaurant) => {
      const placeId = this.normalizePlaceId(restaurant.google_place_id || restaurant.place_id);
      if (placeId) {
        this.myRestaurantsByPlaceId.set(placeId, restaurant);
      }

      const fallbackKey = this.buildFallbackKey(restaurant);
      if (fallbackKey) {
        this.myRestaurantsByFallbackKey.set(fallbackKey, restaurant);
      }
    });

    this.myRestaurantsLoaded = true;
  }

  mapLocalRestaurantForDiscovery(restaurant) {
    return {
      name: restaurant.name || '',
      formatted_address: [restaurant.address_line_1, restaurant.city, restaurant.state].filter(Boolean).join(', '),
      address_line_1: restaurant.address_line_1 || '',
      city: restaurant.city || '',
      state: restaurant.state || '',
      website: restaurant.website || '',
      google_place_id: restaurant.google_place_id || '',
      place_id: restaurant.google_place_id || '',
      latitude: restaurant.latitude !== null ? Number.parseFloat(restaurant.latitude) : null,
      longitude: restaurant.longitude !== null ? Number.parseFloat(restaurant.longitude) : null,
      rating: Number(restaurant.rating || 0) || 0,
      user_ratings_total: 0,
      price_level: restaurant.price_level || null,
      cuisine_type: restaurant.cuisine || '',
      isMine: true,
      matchedRestaurantId: restaurant.id || null,
      matchedRestaurantWebsite: restaurant.website || '',
      resultKey: this.getResultKey(restaurant),
    };
  }

  searchMyRestaurantsOnly(searchLocation, radiusMiles, query, filters) {
    const lowerQuery = (query || '').trim().toLowerCase();
    const cuisineFilter = (filters.cuisine || '').trim().toLowerCase();

    const mapped = this.myRestaurantsCache
      .map((restaurant) => this.mapLocalRestaurantForDiscovery(restaurant))
      .filter((restaurant) => restaurant.latitude !== null && restaurant.longitude !== null)
      .filter((restaurant) => {
        const distance = this.calculateDistance(
          searchLocation.lat,
          searchLocation.lng,
          restaurant.latitude,
          restaurant.longitude,
        );
        if (distance === null || distance > radiusMiles) {
          return false;
        }

        if (lowerQuery) {
          const haystack = [restaurant.name, restaurant.cuisine_type, restaurant.city].join(' ').toLowerCase();
          if (!haystack.includes(lowerQuery)) {
            return false;
          }
        }

        if (
          cuisineFilter &&
          !String(restaurant.cuisine_type || '')
            .toLowerCase()
            .includes(cuisineFilter)
        ) {
          return false;
        }

        return true;
      });

    return {
      results: mapped.slice(0, this.requestedMaxResults),
      meta: {
        result_count: mapped.length,
        has_more_hint: mapped.length > this.requestedMaxResults,
      },
    };
  }

  normalizePlaceId(placeId) {
    if (!placeId || typeof placeId !== 'string') {
      return '';
    }

    return placeId.trim().toLowerCase();
  }

  normalizeText(value) {
    if (!value) {
      return '';
    }

    return String(value).trim().toLowerCase().replace(/\s+/g, ' ');
  }

  normalizeCoord(value) {
    const parsed = Number.parseFloat(value);
    if (Number.isNaN(parsed)) {
      return '';
    }
    return parsed.toFixed(4);
  }

  buildFallbackKey(restaurant) {
    const nameKey = this.normalizeText(restaurant.name);
    const cityKey = this.normalizeText(restaurant.city);
    const latKey = this.normalizeCoord(restaurant.latitude);
    const lngKey = this.normalizeCoord(restaurant.longitude);

    if (!nameKey || !latKey || !lngKey) {
      return '';
    }

    return `${nameKey}|${cityKey}|${latKey}|${lngKey}`;
  }

  getResultKey(restaurant, index = 0) {
    const placeId = this.normalizePlaceId(restaurant.google_place_id || restaurant.place_id || restaurant.id);
    if (placeId) {
      return `place:${placeId}`;
    }

    const fallbackKey = this.buildFallbackKey(restaurant);
    if (fallbackKey) {
      return `fallback:${fallbackKey}`;
    }

    const nameKey = this.normalizeText(restaurant.name);
    return `idx:${nameKey || 'restaurant'}:${index}`;
  }

  enrichResultsWithOwnership(results) {
    return results.map((restaurant, index) => {
      const placeIdKey = this.normalizePlaceId(restaurant.google_place_id || restaurant.place_id);
      const fallbackKey = this.buildFallbackKey(restaurant);
      const matchedRestaurant =
        (placeIdKey && this.myRestaurantsByPlaceId.get(placeIdKey)) ||
        (fallbackKey && this.myRestaurantsByFallbackKey.get(fallbackKey)) ||
        null;

      return {
        ...restaurant,
        isMine: Boolean(matchedRestaurant),
        matchedRestaurantId: matchedRestaurant?.id || null,
        matchedRestaurantWebsite: matchedRestaurant?.website || '',
        resultKey: this.getResultKey(restaurant, index),
      };
    });
  }

  setResultsFilter(filter) {
    if (!['all', 'mine', 'new'].includes(filter)) {
      return;
    }

    this.resultsFilter = filter;
    this.updateFilterButtonStates();
    this.renderVisibleResults({ fitMap: false });
  }

  updateFilterButtonStates() {
    this.container.querySelectorAll('[data-result-filter]').forEach((button) => {
      const isActive = button.getAttribute('data-result-filter') === this.resultsFilter;
      button.classList.toggle('active', isActive);
      button.classList.toggle('btn-outline-secondary', !isActive);
      button.classList.toggle('btn-primary', isActive);
    });
  }

  async performSearch(options = {}) {
    const { preserveRequestedMax = false } = options;
    if (this.isSearching) return;

    if (!preserveRequestedMax) {
      this.requestedMaxResults = 20;
    }

    this.isSearching = true;
    const searchBtn = this.container.querySelector('#search-btn');
    const searchBtnSecondary = this.container.querySelector('#search-btn-secondary');
    const originalText = searchBtn.innerHTML;
    const originalSecondaryText = searchBtnSecondary ? searchBtnSecondary.innerHTML : '';

    // Show loading state
    searchBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Searching...';
    searchBtn.disabled = true;
    if (searchBtnSecondary) {
      searchBtnSecondary.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Searching...';
      searchBtnSecondary.disabled = true;
    }

    try {
      const searchInput = this.container.querySelector('#search-input');
      const query = searchInput.value.trim();
      const radius = parseFloat(this.container.querySelector('#radius-slider').value);
      const filters = this.getFilters();

      // If no query provided, search for restaurants in the area
      const searchQuery = query || 'restaurants';

      // Update search input placeholder to show it's searching for restaurants
      if (!query) {
        searchInput.placeholder = 'Searching for restaurants in your area...';
        setTimeout(() => {
          searchInput.placeholder = 'Name, cuisine, location...';
        }, 2000);
      }

      // Always use current map center for search location
      const mapCenter = this.map.getCenter();
      const searchLocation = {
        lat: mapCenter.lat(),
        lng: mapCenter.lng(),
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
        searchScope: this.discoveryScope || 'combined',
      };

      this.lastSearchContext = {
        center: searchLocation,
        radiusMiles: radius,
      };

      // Remove empty parameters
      Object.keys(searchParams).forEach((key) => {
        if (searchParams[key] === '' || searchParams[key] === undefined) {
          delete searchParams[key];
        }
      });

      let results;
      if (this.discoveryScope === 'my') {
        await this.ensureMyRestaurantsLoaded();
        results = this.searchMyRestaurantsOnly(searchLocation, radius, query, filters);
      } else {
        results = await this.searchRestaurants(searchParams);
        try {
          await this.ensureMyRestaurantsLoaded();
        } catch (lookupError) {
          console.warn('Failed to load ownership lookup data:', lookupError);
        }
      }

      this.renderSearchArea(searchLocation, radius);

      // Display results
      this.displayResults(results);

      // Call callback
      this.options.onResults(results);
    } catch {
    } finally {
      // Reset button state
      searchBtn.innerHTML = originalText;
      searchBtn.disabled = false;
      if (searchBtnSecondary) {
        searchBtnSecondary.innerHTML = originalSecondaryText;
        searchBtnSecondary.disabled = false;
      }
      this.isSearching = false;
    }
  }

  getFilters() {
    return {
      cuisine: this.container.querySelector('#cuisine-filter').value,
      minRating: parseFloat(this.container.querySelector('#min-rating').value) || undefined,
      maxPriceLevel: parseInt(this.container.querySelector('#max-price').value, 10) || undefined,
      maxResults: this.requestedMaxResults,
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

  sortResultsByDistance(results) {
    if (!results || results.length === 0) {
      return results;
    }

    const center = this.lastSearchContext?.center || this.currentLocation;
    if (!center) {
      return results;
    }

    // Calculate distance for each restaurant and sort by distance
    const resultsWithDistance = results
      .map((restaurant) => {
        const distance = this.calculateDistance(
          center.lat,
          center.lng,
          restaurant.latitude ?? null,
          restaurant.longitude ?? null,
        );

        return {
          ...restaurant,
          distance,
          distanceText: this.formatDistance(distance),
        };
      })
      .filter((restaurant) => restaurant.distance !== null); // Filter out restaurants without valid coordinates

    // Sort by distance (closest first)
    return resultsWithDistance.sort((a, b) => a.distance - b.distance);
  }

  sortResults(results) {
    if (!Array.isArray(results) || !results.length) {
      return [];
    }

    if (this.sortMode === 'name') {
      return [...results].sort((a, b) => (a.name || '').localeCompare(b.name || ''));
    }

    if (this.sortMode === 'rating') {
      return [...results].sort((a, b) => {
        const aRating = Number(a.rating || 0);
        const bRating = Number(b.rating || 0);
        if (aRating !== bRating) {
          return bRating - aRating;
        }
        return (a.name || '').localeCompare(b.name || '');
      });
    }

    return this.sortResultsByDistance(results);
  }

  calculateDistance(lat1, lng1, lat2, lng2) {
    if (!lat2 || !lng2) return null;

    // Haversine formula to calculate distance between two points on Earth
    const R = 3959; // Earth's radius in miles (use 6371 for kilometers)
    const dLat = this.toRadians(lat2 - lat1);
    const dLng = this.toRadians(lng2 - lng1);

    const a =
      Math.sin(dLat / 2) * Math.sin(dLat / 2) +
      Math.cos(this.toRadians(lat1)) * Math.cos(this.toRadians(lat2)) * Math.sin(dLng / 2) * Math.sin(dLng / 2);

    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));

    return R * c; // Distance in miles
  }

  toRadians(degrees) {
    return degrees * (Math.PI / 180);
  }

  formatDistance(distance) {
    if (distance === null) return '';

    if (this.locale.useMiles) {
      if (distance < 0.1) {
        return `${Math.round(distance * 5280)} ft`;
      }
      return `${distance.toFixed(1)} mi`;
    }
    if (distance < 0.1) {
      return `${Math.round(distance * 1000)} m`;
    }
    return `${(distance * 1.60934).toFixed(1)} km`;
  }

  displayResults(results) {
    const resultsContainer = this.container.querySelector('#search-results');
    const locationIndicator = this.container.querySelector('#location-indicator');
    const radiusIndicator = this.container.querySelector('#radius-indicator');

    const withDistance = this.sortResultsByDistance(results.results || []);
    const radiusFilteredResults = this.filterResultsByRadius(withDistance);
    const enrichedResults = this.enrichResultsWithOwnership(radiusFilteredResults);

    // Store current results for selection (use sorted results for consistent ordering)
    this.currentResults = {
      ...results,
      results: enrichedResults,
    };
    this.resultsFilter = 'all';
    this.selectedResultKey = null;
    this.updateFilterButtonStates();
    this.updateResultToggleButtons();

    // Clear existing markers
    this.clearMarkers();

    if (!enrichedResults.length) {
      resultsContainer.innerHTML = `
        <div class="discovery-empty text-center text-muted py-5">
          <i class="fas fa-search fa-3x mb-3"></i>
          <h6>No restaurants found</h6>
          <p class="mb-0">Try widening your radius or removing one of the filters.</p>
        </div>
      `;
      this.updateResultsCount(0, 0);
      this.updateDiagnostics(0, 0);
      this.updateLoadMoreButton(0, false);

      // Hide location indicator if no results
      locationIndicator.classList.add('d-none');
      if (radiusIndicator) {
        radiusIndicator.classList.add('d-none');
      }
      return;
    }

    // Show location indicator if we have location and search was location-based
    if (this.currentLocation) {
      locationIndicator.classList.remove('d-none');
    } else {
      locationIndicator.classList.add('d-none');
    }

    if (radiusIndicator && this.lastSearchContext?.radiusMiles) {
      const radiusText = this.locale.useMiles
        ? `${this.lastSearchContext.radiusMiles.toFixed(1)} mi radius`
        : `${(this.lastSearchContext.radiusMiles * 1.60934).toFixed(1)} km radius`;
      radiusIndicator.textContent = radiusText;
      radiusIndicator.classList.remove('d-none');
    }

    this.renderVisibleResults({ fitMap: false });
  }

  getFilteredResults() {
    const allResults = this.currentResults?.results || [];
    const ownershipFiltered = allResults.filter((restaurant) => {
      if (restaurant.isMine && !this.includeMine) return false;
      if (!restaurant.isMine && !this.includeNew) return false;
      return true;
    });

    let sliced = ownershipFiltered;
    if (this.resultsFilter === 'mine') {
      sliced = ownershipFiltered.filter((restaurant) => restaurant.isMine);
    } else if (this.resultsFilter === 'new') {
      sliced = ownershipFiltered.filter((restaurant) => !restaurant.isMine);
    }

    return this.sortResults(sliced);
  }

  filterResultsByRadius(results) {
    const center = this.lastSearchContext?.center;
    const radiusMiles = this.lastSearchContext?.radiusMiles;
    if (!center || !radiusMiles || !Array.isArray(results)) {
      return results;
    }

    return results.filter((restaurant) => {
      const distance = this.calculateDistance(center.lat, center.lng, restaurant.latitude, restaurant.longitude);
      if (distance === null) {
        return false;
      }
      return distance <= radiusMiles;
    });
  }

  updateResultsCount(visibleCount, totalCount) {
    const resultsCount = this.container.querySelector('#results-count');
    if (!resultsCount) return;

    if (visibleCount === totalCount) {
      resultsCount.textContent = `${visibleCount} restaurant${visibleCount !== 1 ? 's' : ''} found`;
      return;
    }

    resultsCount.textContent = `Showing ${visibleCount} of ${totalCount}`;
  }

  updateDiagnostics(visibleCount, totalCount) {
    const diagnostics = this.container.querySelector('#search-diagnostics');
    if (!diagnostics) return;

    const radius = this.lastSearchContext?.radiusMiles;
    const radiusLabel = radius
      ? this.locale.useMiles
        ? `${radius.toFixed(1)} mi`
        : `${(radius * 1.60934).toFixed(1)} km`
      : 'n/a';

    const scopeMap = {
      combined: 'Combined',
      google: 'Google only',
      my: 'My restaurants only',
    };

    const chips = [
      `Source: ${scopeMap[this.discoveryScope] || 'Combined'}`,
      `Sort: ${this.sortMode === 'distance' ? 'Distance' : this.sortMode === 'name' ? 'Name' : 'Rating'}`,
      `Radius: ${radiusLabel}`,
      `Showing: ${visibleCount}/${totalCount}`,
      `Include mine/new: ${this.includeMine ? 'yes' : 'no'}/${this.includeNew ? 'yes' : 'no'}`,
    ];
    diagnostics.textContent = chips.join(' | ');
  }

  updateLoadMoreButton(totalCount, hasMoreHint = false) {
    const button = this.container.querySelector('#load-more-btn');
    if (!(button instanceof HTMLButtonElement)) return;
    const canLoadMore =
      (hasMoreHint || totalCount >= this.requestedMaxResults) && this.requestedMaxResults < this.maxResultsCap;
    button.classList.toggle('d-none', !canLoadMore);
    button.disabled = this.isSearching;
  }

  updateResultToggleButtons() {
    const mineToggle = this.container.querySelector('#include-mine-toggle');
    const newToggle = this.container.querySelector('#include-new-toggle');
    if (
      mineToggle instanceof HTMLInputElement &&
      !mineToggle.checked &&
      newToggle instanceof HTMLInputElement &&
      !newToggle.checked
    ) {
      newToggle.checked = true;
      this.includeNew = true;
    }
  }

  renderVisibleResults(options = {}) {
    const { fitMap = false } = options;
    const resultsContainer = this.container.querySelector('#search-results');
    const allResults = this.currentResults?.results || [];
    const filteredResults = this.getFilteredResults();

    this.visibleResults = filteredResults;
    this.clearMarkers();

    if (!filteredResults.length) {
      resultsContainer.innerHTML = `
        <div class="discovery-empty text-center text-muted py-5">
          <i class="fas fa-filter fa-3x mb-3"></i>
          <h6>No restaurants in this filter</h6>
          <p class="mb-0">Try switching to All, or run a wider search.</p>
        </div>
      `;
      this.updateResultsCount(0, allResults.length);
      this.updateDiagnostics(0, allResults.length);
      const hasMoreHint = Boolean(this.currentResults?.meta?.has_more_hint);
      this.updateLoadMoreButton(allResults.length, hasMoreHint);
      this.selectedResultKey = null;
      this.closeInfoWindow();
      return;
    }

    filteredResults.forEach((restaurant, index) => {
      this.createMarker(restaurant, index);
    });

    resultsContainer.innerHTML = filteredResults
      .map((restaurant, index) => this.createResultCard(restaurant, index))
      .join('');
    this.initializeDiscoveryFavicons();

    this.updateResultsCount(filteredResults.length, allResults.length);
    this.updateDiagnostics(filteredResults.length, allResults.length);
    const hasMoreHint = Boolean(this.currentResults?.meta?.has_more_hint);
    this.updateLoadMoreButton(allResults.length, hasMoreHint);

    if (this.selectedResultKey) {
      const selectedIndex = filteredResults.findIndex((restaurant) => restaurant.resultKey === this.selectedResultKey);
      if (selectedIndex >= 0) {
        this.selectRestaurant(selectedIndex, { centerMap: false, scrollCard: false, setZoom: false });
      } else {
        this.selectedResultKey = null;
        this.closeInfoWindow();
      }
    }

    if (fitMap) {
      this.fitMapToMarkers();
    }
  }

  initializeDiscoveryFavicons() {
    initializeRobustFaviconHandling('.result-my-favicon');
    initializeRobustFaviconHandling('.result-result-favicon');
  }

  createMarker(restaurant, index) {
    const position =
      restaurant.latitude !== null && restaurant.longitude !== null
        ? { lat: restaurant.latitude, lng: restaurant.longitude }
        : null;

    if (!position) {
      console.warn('No location data found for restaurant:', restaurant.name);
      return;
    }

    // Use AdvancedMarkerElement with numbered content
    const markerType = restaurant.isMine ? 'mine' : 'new';
    const marker = new google.maps.marker.AdvancedMarkerElement({
      position,
      map: this.map,
      title: restaurant.name,
      content: this.createNumberedMarkerContent(index + 1, markerType, false),
    });

    // Add click listener (gmp-click for AdvancedMarkerElement)
    marker.addEventListener('gmp-click', () => {
      this.selectRestaurant(index);
    });

    this.markers.push(marker);
    this.markerEntries[index] = {
      marker,
      markerType,
      restaurant,
    };
  }

  createNumberedMarkerContent(number, markerType, isSelected) {
    const backgroundColor = markerType === 'mine' ? '#0d6efd' : '#dc3545';
    const borderColor = isSelected ? '#ffd166' : '#ffffff';
    const scale = isSelected ? 1.14 : 1;
    const shadow = isSelected ? '0 8px 18px rgba(15,23,42,0.42)' : '0 4px 10px rgba(15,23,42,0.24)';

    const markerElement = document.createElement('div');
    markerElement.style.cssText = `
      width: 36px;
      height: 36px;
      background-color: ${backgroundColor};
      border: 3px solid ${borderColor};
      border-radius: 50%;
      box-shadow: ${shadow};
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: bold;
      font-size: 14px;
      color: white;
      cursor: pointer;
      transition: all 0.2s ease;
      transform: scale(${scale});
    `;

    markerElement.textContent = number;

    // Add hover effect
    markerElement.addEventListener('mouseenter', () => {
      markerElement.style.transform = `scale(${isSelected ? 1.18 : 1.08})`;
      markerElement.style.boxShadow = '0 8px 16px rgba(15,23,42,0.32)';
    });

    markerElement.addEventListener('mouseleave', () => {
      markerElement.style.transform = `scale(${scale})`;
      markerElement.style.boxShadow = shadow;
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
    const rating = restaurant.rating || 0;
    const reviewCount = restaurant.user_ratings_total || 0;
    const priceLevel = restaurant.price_level || 0;

    // Parse address for better display
    const address = this.parseAddress(restaurant);

    // Check opening hours
    const openingStatus = this.getOpeningStatus(restaurant.opening_hours);

    // Contact information (Places API New uses nationalPhoneNumber; we map to phone)
    const phone = restaurant.phone ?? restaurant.nationalPhoneNumber;
    const { website } = restaurant;

    // Escape all user-controlled data to prevent XSS
    const escapedName = escapeHtml(restaurant.name || '');
    const escapedDistanceText = restaurant.distanceText ? escapeHtml(restaurant.distanceText) : '';
    const escapedStreet = escapeHtml(address.street || '');
    const escapedCityStateZip = address.cityStateZip ? escapeHtml(address.cityStateZip) : '';
    const escapedPhone = phone ? escapeHtml(phone) : '';
    const escapedOpeningStatusText = openingStatus.text ? escapeHtml(openingStatus.text) : '';
    const ownershipClass = restaurant.isMine ? 'ownership-mine' : 'ownership-new';
    const ownershipLabel = restaurant.isMine ? 'In My Restaurants' : 'New To Me';
    const rankClass = restaurant.isMine ? 'result-rank-mine' : 'result-rank-new';
    const viewUrl = restaurant.matchedRestaurantId ? `/restaurants/${restaurant.matchedRestaurantId}` : '#';
    const matchedRestaurantWebsite = restaurant.matchedRestaurantWebsite || '';
    const faviconWebsite = matchedRestaurantWebsite || website || '';
    const escapedFaviconWebsite = faviconWebsite ? escapeHtml(faviconWebsite) : '';

    // Validate and sanitize URLs
    let safeWebsiteUrl = '';
    if (website) {
      try {
        const websiteUrlObj = new URL(website);
        // Only allow http/https URLs for websites
        if (websiteUrlObj.protocol === 'http:' || websiteUrlObj.protocol === 'https:') {
          safeWebsiteUrl = websiteUrlObj.href;
        }
      } catch {
        // Invalid URL, skip website link
      }
    }

    return `
      <article class="restaurant-card discovery-result-card ${ownershipClass}" data-index="${index}" data-result-key="${escapeHtml(restaurant.resultKey || '')}">
        <div class="result-rank ${rankClass}">${index + 1}</div>
        <div class="result-media">
          ${
  escapedFaviconWebsite
    ? `
          <img
            src="data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"
            data-website="${escapedFaviconWebsite}"
            data-size="32"
            alt="${escapedName} favicon"
            class="result-result-favicon"
            width="32"
            height="32"
          />`
    : ''
}
          <i class="fas fa-utensils result-media-fallback restaurant-fallback-icon ${escapedFaviconWebsite ? 'd-none' : ''}"></i>
        </div>

        <div class="result-main">
          <div class="d-flex justify-content-between align-items-start gap-2 mb-1">
            <div>
              <h6 class="result-title mb-0">${escapedName}</h6>
              ${
  escapedDistanceText
    ? `<div class="result-distance"><i class="fas fa-location-dot me-1"></i>${escapedDistanceText} away</div>`
    : ''
}
            </div>
            ${
  rating > 0
    ? `
              <div class="d-flex align-items-center text-end small fw-semibold">
                <i class="fas fa-star text-warning me-1"></i>
                <span>${rating.toFixed(1)}</span>
                <span class="text-muted small ms-1">${reviewCount}</span>
              </div>
            `
    : ''
}
          </div>

          <div class="result-meta mb-2">
            <div><i class="fas fa-map-marker-alt me-1"></i>${escapedStreet}</div>
            ${escapedCityStateZip ? `<div>${escapedCityStateZip}</div>` : ''}
          </div>

          <div class="result-badges mb-2">
            <span class="badge result-ownership-badge ${restaurant.isMine ? 'text-bg-primary' : 'text-bg-danger'}">${ownershipLabel}</span>
            ${priceLevel > 0 ? `<span class="badge text-bg-light">${'$'.repeat(priceLevel)}</span>` : ''}
            ${openingStatus.badge ? `<span class="badge ${openingStatus.class}">${escapedOpeningStatusText}</span>` : ''}
            ${openingStatus.hoursText ? `<span class="badge text-bg-light">${escapeHtml(openingStatus.hoursText)}</span>` : ''}
          </div>

          <div class="d-flex flex-wrap gap-2 align-items-center mt-auto">
            ${
  escapedPhone
    ? `
              <a href="tel:${escapedPhone}" class="btn btn-outline-secondary btn-sm">
                <i class="fas fa-phone me-1"></i>Call
              </a>
            `
    : ''
}
            ${
  safeWebsiteUrl
    ? `
              <a href="${safeWebsiteUrl}" target="_blank" rel="noopener" class="btn btn-outline-secondary btn-sm">
                <i class="fas fa-globe me-1"></i>Website
              </a>
            `
    : ''
}
            <div class="ms-auto">
              ${
  restaurant.isMine && restaurant.matchedRestaurantId
    ? `
                <a href="${viewUrl}" class="btn btn-outline-primary btn-sm" data-action="view-restaurant">
                  <i class="fas fa-arrow-up-right-from-square me-1"></i>View in My Restaurants
                </a>
              `
    : (restaurant.google_place_id && restaurant.google_place_id.trim() !== '') ||
                      (restaurant.place_id && restaurant.place_id.trim() !== '')
      ? `
                <button class="btn btn-primary btn-sm" data-place-id="${restaurant.google_place_id || restaurant.place_id}" data-action="add-restaurant">
                  <i class="fas fa-plus me-1"></i>Add
                </button>
              `
      : `
                <button class="btn btn-outline-secondary btn-sm" disabled title="This restaurant is missing a Google Place ID.">
                  <i class="fas fa-ban me-1"></i>Unavailable
                </button>
              `
}
            </div>
          </div>
        </div>
      </article>
    `;
  }

  parseAddress(restaurant) {
    // First, try to use structured address data if available (from details API)
    if (restaurant.address_line_1 && restaurant.city && restaurant.state) {
      const street = restaurant.address_line_1;
      const cityState = restaurant.postal_code
        ? `${restaurant.city}, ${restaurant.state} ${restaurant.postal_code}`
        : `${restaurant.city}, ${restaurant.state}`;

      return {
        street,
        cityStateZip: cityState,
      };
    }

    // Fallback to parsing formatted_address from search results
    const formatted = restaurant.formatted_address || '';

    if (!formatted) {
      return { street: 'Address not available', cityStateZip: '' };
    }

    // Enhanced parsing for search results - handle various formats
    // Try to extract state information from the address string
    const stateRegex = /\b([A-Z]{2})\b/g;
    const states = formatted.match(stateRegex);

    if (states && states.length > 0) {
      // Found state abbreviation, try to parse around it
      const [state] = states;
      const stateIndex = formatted.indexOf(state);

      // Extract everything after the state (should include city)
      const afterState = formatted.substring(stateIndex).trim();
      const beforeState = formatted.substring(0, stateIndex).trim();

      // Try to find city before state
      const parts = beforeState.split(',').map((p) => p.trim());
      if (parts.length > 0) {
        const [street] = parts;
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
      const [street, city, stateZip] = parts;

      return {
        street,
        cityStateZip: `${city}, ${stateZip}`,
      };
    } else if (parts.length === 3) {
      // Format: "Street, City, State ZIP" or "Street, City, Country"
      const [street, city, lastPart] = parts;

      // Check if last part contains state abbreviation or full state name
      const stateRegex =
        /\b[A-Z]{2}\b|\b(Alabama|Alaska|Arizona|Arkansas|California|Colorado|Connecticut|Delaware|Florida|Georgia|Hawaii|Idaho|Illinois|Indiana|Iowa|Kansas|Kentucky|Louisiana|Maine|Maryland|Massachusetts|Michigan|Minnesota|Mississippi|Missouri|Montana|Nebraska|Nevada|New Hampshire|New Jersey|New Mexico|New York|North Carolina|North Dakota|Ohio|Oklahoma|Oregon|Pennsylvania|Rhode Island|South Carolina|South Dakota|Tennessee|Texas|Utah|Vermont|Virginia|Washington|West Virginia|Wisconsin|Wyoming)\b/i;

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
      const [street] = parts;
      const [, cityState] = parts;

      // Try to extract state from cityState if it's in format "City State ZIP"
      const stateMatch = cityState.match(/\b([A-Z]{2})\s+\d{5}(-\d{4})?$/);
      if (stateMatch) {
        const cityOnly = cityState.replace(/\s+[A-Z]{2}\s+\d{5}(-\d{4})?$/, '');
        const [, stateZip] = cityState.match(/\s+([A-Z]{2}\s+\d{5}(-\d{4})?)$/);
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

    const result = {
      street: formatted,
      cityStateZip: '',
    };

    return result;
  }

  getOpeningStatus(openingHours) {
    if (!openingHours) {
      return { badge: false };
    }

    const openNow = openingHours.open_now;
    const weekdayText = openingHours.weekday_text;

    const status = { badge: false, hoursText: '' };

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
          [, status.hoursText] = hoursMatch;
        }
      }
    }

    return status;
  }

  openInfoWindow(restaurant, marker) {
    if (!this.map || !marker) return;

    if (!this.activeInfoWindow) {
      this.activeInfoWindow = new google.maps.InfoWindow();
    }

    const safeName = escapeHtml(restaurant.name || 'Restaurant');
    const safeCity = escapeHtml(restaurant.city || '');
    const safeCuisine = escapeHtml(restaurant.cuisine_type || restaurant.cuisine || '');
    const ownershipText = restaurant.isMine ? 'In My Restaurants' : 'New To Me';
    const ownershipClass = restaurant.isMine ? 'text-bg-primary' : 'text-bg-danger';
    const viewUrl = restaurant.matchedRestaurantId ? `/restaurants/${restaurant.matchedRestaurantId}` : '#';
    const matchedRestaurantWebsite = restaurant.matchedRestaurantWebsite || '';
    const escapedMatchedRestaurantWebsite = matchedRestaurantWebsite ? escapeHtml(matchedRestaurantWebsite) : '';

    this.activeInfoWindow.setContent(`
      <div class="places-map-infowindow">
        <div class="places-map-infowindow-title mb-1">
          <span class="fw-semibold">${safeName}</span>
          ${
  restaurant.isMine && escapedMatchedRestaurantWebsite
    ? `
          <span class="places-map-infowindow-favicon-wrap" title="Saved restaurant favicon">
            <img
              src="data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"
              data-website="${escapedMatchedRestaurantWebsite}"
              data-size="16"
              alt="${safeName} favicon"
              class="places-map-infowindow-favicon"
              width="16"
              height="16"
            />
            <i class="fas fa-utensils restaurant-fallback-icon d-none"></i>
          </span>
          `
    : ''
}
        </div>
        ${safeCity ? `<div class="text-muted small mb-1">${safeCity}</div>` : ''}
        <div class="d-flex flex-wrap align-items-center gap-2 mb-1">
          <span class="badge rounded-pill ${ownershipClass}">${ownershipText}</span>
          ${safeCuisine ? `<span class="badge rounded-pill text-bg-light">${safeCuisine}</span>` : ''}
        </div>
        ${restaurant.isMine && restaurant.matchedRestaurantId ? `<a href="${viewUrl}" class="small text-decoration-none">View in My Restaurants</a>` : '<span class="small text-muted">Add from the list to save</span>'}
      </div>
    `);
    this.activeInfoWindow.open({ map: this.map, anchor: marker });

    google.maps.event.addListenerOnce(this.activeInfoWindow, 'domready', () => {
      initializeRobustFaviconHandling('.places-map-infowindow-favicon');
    });
  }

  closeInfoWindow() {
    if (this.activeInfoWindow) {
      this.activeInfoWindow.close();
    }
  }

  selectRestaurant(index, options = {}) {
    const { centerMap = true, scrollCard = true, setZoom = true } = options;

    // Get restaurant data from visible results
    const restaurant = this.visibleResults?.[index];
    if (!restaurant) return;

    this.selectedResultKey = restaurant.resultKey;

    // Highlight selected restaurant card
    const card = this.container.querySelector(`.restaurant-card[data-index="${index}"]`);
    if (card) {
      // Use requestAnimationFrame to batch DOM writes
      requestAnimationFrame(() => {
        card.classList.add('border-primary', 'shadow-lg');
        card.style.transform = 'scale(1.02)';
        card.style.transition = 'all 0.2s ease';

        // Scroll to selected card
        if (scrollCard) {
          card.scrollIntoView({
            behavior: 'smooth',
            block: 'nearest',
            inline: 'nearest',
          });
        }
      });
    }

    this.container.querySelectorAll('.restaurant-card').forEach((otherCard) => {
      if (otherCard !== card) {
        otherCard.classList.remove('border-primary', 'shadow-lg');
        otherCard.style.transform = 'scale(1)';
      }
    });

    this.markerEntries.forEach((entry, markerIndex) => {
      if (!entry?.marker) {
        return;
      }
      const isSelected = markerIndex === index;
      entry.marker.content = this.createNumberedMarkerContent(markerIndex + 1, entry.markerType, isSelected);
    });

    const markerEntry = this.markerEntries[index];
    if (!markerEntry) {
      return;
    }

    if (centerMap && restaurant.latitude !== null && restaurant.longitude !== null) {
      this.map.panTo({
        lat: restaurant.latitude,
        lng: restaurant.longitude,
      });
      if (setZoom) {
        this.map.setZoom(16);
      }
    }

    this.openInfoWindow(restaurant, markerEntry.marker);

    this.selectedRestaurant = restaurant;
    this.options.onSelect(restaurant);
  }

  clearSelection() {
    // Clear card selection
    this.container.querySelectorAll('.restaurant-card').forEach((card) => {
      card.classList.remove('border-primary', 'shadow-lg');
      card.style.transform = 'scale(1)';
    });

    // Reset all markers to their ownership colors
    this.markerEntries.forEach((entry, index) => {
      if (entry?.marker?.content) {
        entry.marker.content = this.createNumberedMarkerContent(index + 1, entry.markerType, false);
      }
    });

    this.selectedRestaurant = null;
    this.selectedResultKey = null;
    this.closeInfoWindow();
  }

  clearMarkers() {
    this.markers.forEach((marker) => {
      if (typeof marker.setMap === 'function') {
        marker.setMap(null);
      } else {
        marker.map = null;
      }
    });
    this.markers = [];
    this.markerEntries = [];
    this.closeInfoWindow();
  }

  renderSearchArea(searchLocation, radiusMiles) {
    if (!this.map || !searchLocation || Number.isNaN(radiusMiles)) return;

    if (this.searchAreaCircle) {
      this.searchAreaCircle.setMap(null);
    }

    this.searchAreaCircle = new google.maps.Circle({
      strokeColor: '#0d6efd',
      strokeOpacity: 0.65,
      strokeWeight: 1.5,
      fillColor: '#0d6efd',
      fillOpacity: 0.08,
      map: this.map,
      center: searchLocation,
      radius: radiusMiles * 1609.34,
      clickable: false,
    });
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
      title: 'Your Location',
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
        lng: position.coords.longitude,
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
    } catch {}
  }

  fitMapToMarkers() {
    if (this.markers.length === 0) return;

    const bounds = new google.maps.LatLngBounds();
    this.markers.forEach((marker) => {
      let position;
      if (marker.getPosition) {
        // Regular Marker
        position = marker.getPosition();
      } else if (marker.position) {
        // AdvancedMarkerElement
        position = marker.position; // eslint-disable-line prefer-destructuring
      }

      if (position) {
        bounds.extend(position);
      }
    });

    if (this.searchAreaCircle) {
      const circleBounds = this.searchAreaCircle.getBounds();
      if (circleBounds) {
        bounds.union(circleBounds);
      }
    }

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
    // Escape message to prevent XSS
    const escapedMessage = escapeHtml(message || 'An error occurred');
    resultsContainer.innerHTML = `
      <div class="alert alert-danger">
        <i class="fas fa-exclamation-triangle me-2"></i>
        ${escapedMessage}
      </div>
    `;
  }

  applyOptimisticOwnership(placeId) {
    if (!placeId || !this.currentResults?.results?.length) {
      return;
    }

    const normalizedPlaceId = this.normalizePlaceId(placeId);
    const matchedRestaurant = this.myRestaurantsByPlaceId.get(normalizedPlaceId) || null;

    const patched = this.currentResults.results.map((result) => {
      const resultPlaceId = this.normalizePlaceId(result.google_place_id || result.place_id);
      if (resultPlaceId !== normalizedPlaceId) {
        return result;
      }

      return {
        ...result,
        isMine: true,
        matchedRestaurantId: matchedRestaurant?.id || result.matchedRestaurantId || null,
        matchedRestaurantWebsite: matchedRestaurant?.website || result.matchedRestaurantWebsite || '',
      };
    });

    this.currentResults = {
      ...this.currentResults,
      results: patched,
    };
    this.renderVisibleResults({ fitMap: false });
  }

  async addToMyRestaurants(placeId) {
    // Call the global function defined in the template
    if (!window.addToMyRestaurants || typeof window.addToMyRestaurants !== 'function') {
      console.error('addToMyRestaurants function not available');
      return;
    }

    try {
      const addResult = await window.addToMyRestaurants(placeId);
      const wasAdded = Boolean(addResult?.success);
      const alreadyExists = Boolean(addResult?.exists);

      if (wasAdded) {
        this.applyOptimisticOwnership(placeId);
      }

      if (!wasAdded && !alreadyExists) {
        return;
      }

      await this.ensureMyRestaurantsLoaded(true);
      if (this.currentResults?.results?.length) {
        const refreshedResults = this.enrichResultsWithOwnership(this.currentResults.results);
        this.currentResults = {
          ...this.currentResults,
          results: refreshedResults,
        };
        this.renderVisibleResults({ fitMap: false });
      }
    } catch {
      // add handler already surfaced a toast message
    }
  }
}

// Global functions for restaurant selection and adding
window.selectRestaurant = function(index) {
  // This will be handled by the component instance
  console.log('Selected restaurant index:', index);
};
