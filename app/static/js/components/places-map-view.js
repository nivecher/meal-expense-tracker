/**
 * Places Map View Component
 *
 * Unified map view for the Places tab with three modes:
 * - My Restaurants: Display user's restaurants on the map
 * - Nearby: Show user's restaurants within radius of location
 * - Find New: Embed MapRestaurantSearch for Google Places discovery
 */

import { initializeRobustFaviconHandling } from '../utils/robust-favicon-handler.js';

let escapeHtml;
if (typeof window !== 'undefined' && window.SecurityUtils) {
  ({ escapeHtml } = window.SecurityUtils);
} else {
  escapeHtml = function(text) {
    if (text === null || text === undefined) return '';
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

const DEFAULT_CENTER = { lat: 37.7749, lng: -122.4194 };
let googleMapsLoaderPromise = null;

export class PlacesMapView {
  constructor(container, options = {}) {
    this.container = container;
    this.options = {
      googleMapsApiKey: options.googleMapsApiKey || window.GOOGLE_MAPS_API_KEY || '',
      googleMapsMapId: options.googleMapsMapId || '',
      csrfToken: options.csrfToken || '',
      addRestaurantUrl: options.addRestaurantUrl || '',
      findPlacesUrl: options.findPlacesUrl || '',
      onError: options.onError || (() => {}),
      ...options,
    };

    this.map = null;
    this.markers = [];
    this.currentLocation = null;
    this.currentMode = 'find';
    this.mapSearchInstance = null;
    this.findNewContainer = null;
    this.initialized = false;
    this.myRestaurants = [];
    this.filteredMyRestaurants = [];
    this.myRestaurantsWithoutCoords = 0;
    this.myRestaurantsSearchTerm = '';
    this.selectedRestaurantKey = null;
    this.myRestaurantMarkers = new Map();
    this.activeInfoWindow = null;
    this.userLocationMarker = null;
    this.selectedNearbyIndex = null;

    this.init();
  }

  async init() {
    try {
      await this.loadConfig();
      if (!this.options.googleMapsApiKey || !this.options.googleMapsApiKey.trim()) {
        this.showSidebarError('Google Maps is not configured. Add GOOGLE_MAPS_API_KEY to enable the map.');
        return;
      }
      await this.loadGoogleMaps();
      await this.waitForGoogleMaps();
      this.initMap();
      if (!this.map) {
        this.showSidebarError('Could not create map. Check the browser console for errors.');
        return;
      }
      this.triggerMapResizeWhenVisible();
      this.bindEvents();
      this.setInitialModeFromUI();
      this.initialized = true;
      this.loadModeData();
    } catch (err) {
      this.showSidebarError(err?.message || 'Failed to load map.');
      this.options.onError(err);
    }
  }

  showSidebarError(message) {
    const sidebar = this.container?.querySelector('#places-sidebar-content');
    if (sidebar) {
      const safeMsg = typeof escapeHtml === 'function' ? escapeHtml(String(message)) : String(message);
      sidebar.innerHTML = `
        <div class="alert alert-warning mb-0">
          <i class="fas fa-exclamation-triangle me-2"></i>${safeMsg}
        </div>
      `;
    }
  }

  loadConfig() {
    const configEl = document.getElementById('places-map-config');
    if (!configEl) return Promise.resolve();

    try {
      const config = JSON.parse(configEl.textContent);
      this.options.googleMapsApiKey = config.googleMapsApiKey || this.options.googleMapsApiKey;
      this.options.googleMapsMapId = config.googleMapsMapId || this.options.googleMapsMapId;
      this.options.csrfToken = config.csrfToken || this.options.csrfToken;
      this.options.addRestaurantUrl = config.addRestaurantUrl || this.options.addRestaurantUrl;
      this.options.findPlacesUrl = config.findPlacesUrl || this.options.findPlacesUrl;
    } catch {}
    return Promise.resolve();
  }

  // eslint-disable-next-line require-await -- returns Promise for script loading
  async loadGoogleMaps() {
    if (window.google && window.google.maps) return Promise.resolve();

    if (googleMapsLoaderPromise) return googleMapsLoaderPromise;

    const apiKey = (this.options.googleMapsApiKey || '').trim();
    if (!apiKey) {
      return Promise.reject(new Error('Google Maps API key is required'));
    }

    googleMapsLoaderPromise = new Promise((resolve, reject) => {
      const existing = document.querySelector('script[data-google-maps="true"]');
      if (existing) {
        resolve();
        return;
      }

      const script = document.createElement('script');
      script.dataset.googleMaps = 'true';
      script.src = `https://maps.googleapis.com/maps/api/js?key=${apiKey}&libraries=places,marker&loading=async`;
      script.async = true;
      script.onload = resolve;
      script.onerror = () =>
        reject(new Error('Failed to load Google Maps script. Check your API key and restrictions.'));
      document.head.appendChild(script);
    });

    return googleMapsLoaderPromise;
  }

  // eslint-disable-next-line require-await -- returns Promise for polling
  async waitForGoogleMaps() {
    return new Promise((resolve) => {
      const check = () => {
        if (window.google && window.google.maps && window.google.maps.Map && window.google.maps.places) {
          resolve();
        } else {
          setTimeout(check, 100);
        }
      };
      check();
    });
  }

  initMap() {
    const mapEl = this.container.querySelector('#places-map');
    if (!mapEl) return;

    const mapOptions = {
      zoom: 10,
      center: DEFAULT_CENTER,
      mapTypeControl: true,
      streetViewControl: false,
      fullscreenControl: true,
      zoomControl: true,
    };

    if (this.options.googleMapsMapId?.trim()) {
      mapOptions.mapId = this.options.googleMapsMapId.trim();
    } else {
      mapOptions.styles = [
        {
          featureType: 'poi',
          elementType: 'labels',
          stylers: [{ visibility: 'off' }],
        },
      ];
    }

    this.map = new google.maps.Map(mapEl, mapOptions);
  }

  /**
   * Trigger map resize after the next layout pass so the map gets correct
   * dimensions when built inside a tab that was just shown.
   */
  triggerMapResizeWhenVisible() {
    if (!this.map) return;
    const triggerResize = () => {
      if (window.google?.maps?.event && this.map) {
        window.google.maps.event.trigger(this.map, 'resize');
      }
    };
    requestAnimationFrame(() => {
      requestAnimationFrame(triggerResize);
    });
  }

  bindEvents() {
    const modeInputs = this.container.querySelectorAll('input[name="places-mode"]');
    modeInputs.forEach((input) => {
      input.addEventListener('change', (e) => {
        this.setMode(e.target.value, { updateUrl: true });
      });
    });
  }

  setInitialModeFromUI() {
    const selected = this.container.querySelector('input[name="places-mode"]:checked');
    const hiddenModeInput = this.container.querySelector('input[type="hidden"][name="places-mode"]');
    const modeFromUrl = new URLSearchParams(window.location.search).get('places_mode');
    const mode = [
      selected?.value,
      hiddenModeInput?.value,
      modeFromUrl,
      this.options.initialMode,
      this.currentMode,
    ].find((candidate) => ['my', 'nearby', 'find'].includes(candidate));
    this.currentMode = mode || 'my';

    const input = this.container.querySelector(`input[name="places-mode"][value="${this.currentMode}"]`);
    if (input) input.checked = true;
  }

  setMode(mode, options = {}) {
    const { updateUrl = false } = options;
    if (!['my', 'nearby', 'find'].includes(mode)) {
      return;
    }

    this.currentMode = mode;
    if (updateUrl) {
      this.syncPlacesModeToUrl(mode);
    }

    const mapCol = this.container.querySelector('.col-lg-8');
    const sidebarCol = this.container.querySelector('.col-lg-4');
    this.showFindNewMode(mapCol, sidebarCol, mode);
  }

  syncPlacesModeToUrl(mode) {
    const url = new URL(window.location.href);
    url.searchParams.set('tab', 'places');
    url.searchParams.set('places_mode', mode);
    window.history.replaceState({}, '', url);
  }

  showFindNewMode(mapCol, sidebarCol, mode = 'find') {
    this.clearMarkers();
    if (mapCol) mapCol.classList.add('d-none');
    if (sidebarCol) sidebarCol.classList.add('d-none');

    let findContainer = this.container.querySelector('#places-find-new-container');
    if (!findContainer) {
      findContainer = document.createElement('div');
      findContainer.id = 'places-find-new-container';
      findContainer.className = 'col-12';
      this.container.querySelector('.row.g-4')?.appendChild(findContainer);
    }
    findContainer.classList.remove('d-none');
    findContainer.innerHTML = '';

    this.findNewContainer = findContainer;

    window.PLACES_SEARCH_CONFIG = {
      csrfToken: this.options.csrfToken,
      addRestaurantUrl: this.options.addRestaurantUrl,
      googleMapsMapId: this.options.googleMapsMapId,
    };

    import('./map-restaurant-search.js').then(({ MapRestaurantSearch }) => {
      const scopedMode = ['my', 'nearby', 'find'].includes(mode) ? mode : 'find';
      this.mapSearchInstance = new MapRestaurantSearch(findContainer, {
        googleMapsApiKey: this.options.googleMapsApiKey,
        googleMapsMapId: this.options.googleMapsMapId,
        initialDiscoveryMode: scopedMode,
        onError: (err) => this.options.onError(err),
      });
    });
  }

  showMapMode(mapCol, sidebarCol) {
    const findContainer = this.container.querySelector('#places-find-new-container');
    if (findContainer) {
      findContainer.classList.add('d-none');
      findContainer.innerHTML = '';
    }
    this.mapSearchInstance = null;

    if (mapCol) mapCol.classList.remove('d-none');
    if (sidebarCol) sidebarCol.classList.remove('d-none');

    if (this.map) {
      this.triggerMapResizeWhenVisible();
    }
  }

  loadModeData() {
    const mapCol = this.container.querySelector('.col-lg-8');
    const sidebarCol = this.container.querySelector('.col-lg-4');
    this.showFindNewMode(mapCol, sidebarCol, this.currentMode);
  }

  async loadMyRestaurants() {
    const sidebar = this.container.querySelector('#places-sidebar-content');
    if (!sidebar) return;

    try {
      const response = await fetch('/api/v1/restaurants', {
        headers: { Accept: 'application/json' },
      });
      if (!response.ok) throw new Error('Failed to fetch restaurants');

      const data = await response.json();
      const restaurants = data.data || data || [];
      const withCoords = restaurants.filter(
        (r) =>
          r.latitude !== null &&
          r.longitude !== null &&
          !Number.isNaN(parseFloat(r.latitude)) &&
          !Number.isNaN(parseFloat(r.longitude)),
      );

      const withoutCoords = restaurants.length - withCoords.length;

      this.myRestaurants = withCoords;
      this.filteredMyRestaurants = withCoords;
      this.myRestaurantsWithoutCoords = withoutCoords;
      this.selectedRestaurantKey = null;
      this.myRestaurantsSearchTerm = '';

      this.renderMyRestaurantsSidebar(withoutCoords, withCoords.length);
      this.applyMyRestaurantsFilter({ fitMap: true, preserveSelection: false });
    } catch {}
  }

  setupNearbyMode() {
    const sidebar = this.container.querySelector('#places-sidebar-content');
    if (!sidebar) return;

    sidebar.innerHTML = `
      <h6 class="mb-3"><i class="fas fa-map-marker-alt me-2"></i>Nearby</h6>
      <button class="btn btn-outline-secondary w-100 mb-3" type="button" id="places-use-location-btn">
        <i class="fas fa-location-arrow me-1"></i>Use My Location
      </button>
      <div class="mb-3">
        <label for="places-radius-slider" class="form-label">Radius (km)</label>
        <input type="range" class="form-range" id="places-radius-slider" min="1" max="50" step="1" value="10">
        <span id="places-radius-display" class="text-muted small">10 km</span>
      </div>
      <button class="btn btn-primary w-100" type="button" id="places-search-nearby-btn">
        <i class="fas fa-search me-1"></i>Search Nearby
      </button>
      <div id="places-nearby-results" class="mt-3"></div>
    `;

    const radiusSlider = sidebar.querySelector('#places-radius-slider');
    const radiusDisplay = sidebar.querySelector('#places-radius-display');
    if (radiusSlider && radiusDisplay) {
      radiusSlider.addEventListener('input', () => {
        radiusDisplay.textContent = `${radiusSlider.value} km`;
      });
    }

    sidebar.querySelector('#places-use-location-btn')?.addEventListener('click', () => {
      this.getCurrentLocation().then((loc) => {
        if (loc && this.map) {
          this.map.setCenter(loc);
          this.map.setZoom(14);
          this.currentLocation = loc;
          this.searchNearby();
        }
      });
    });

    sidebar.querySelector('#places-search-nearby-btn')?.addEventListener('click', () => {
      this.searchNearby();
    });
  }

  async searchNearby() {
    const resultsEl = this.container.querySelector('#places-nearby-results');
    if (!resultsEl) return;

    let center = this.currentLocation;
    if (!center && this.map) {
      const c = this.map.getCenter();
      center = { lat: c.lat(), lng: c.lng() };
    }
    if (!center) {
      resultsEl.innerHTML =
        '<p class="text-muted small">Use "Use My Location" or pan the map, then click Search Nearby.</p>';
      return;
    }

    const radiusSlider = this.container.querySelector('#places-radius-slider');
    const radiusKm = radiusSlider ? parseFloat(radiusSlider.value, 10) : 10;

    resultsEl.innerHTML = '<p class="text-muted small"><i class="fas fa-spinner fa-spin me-1"></i>Searching...</p>';

    try {
      const params = new URLSearchParams({
        latitude: center.lat,
        longitude: center.lng,
        radius_km: radiusKm,
        limit: '50',
      });
      const response = await fetch(`/restaurants/api/search/location?${params}`);
      if (!response.ok) throw new Error('Search failed');

      const data = await response.json();
      const results = data.results || [];

      this.clearMarkers();
      results.forEach((restaurant, index) => {
        this.createMarker(
          {
            ...restaurant,
            latitude: restaurant.latitude,
            longitude: restaurant.longitude,
          },
          index,
        );
      });

      this.fitMapToMarkers(results);
      this.renderNearbyResultsSidebar(results);
    } catch {}
  }

  renderMyRestaurantsSidebar(withoutCoords, totalWithCoords) {
    const sidebar = this.container.querySelector('#places-sidebar-content');
    if (!sidebar) return;

    let html = '<h6 class="mb-3"><i class="fas fa-utensils me-2"></i>My Restaurants</h6>';
    if (withoutCoords > 0) {
      html += `
        <p class="text-muted small mb-3">
          <i class="fas fa-info-circle me-1"></i>${withoutCoords} restaurant(s) without coordinates (not shown on map).
          <a href="${this.options.findPlacesUrl || '/restaurants/find-places'}">Add coordinates</a> via Find Places.
        </p>
      `;
    }
    html += `
      <div class="places-my-toolbar mb-3">
        <div class="input-group input-group-sm mb-2">
          <span class="input-group-text bg-white"><i class="fas fa-search text-muted"></i></span>
          <input
            type="search"
            id="places-my-search"
            class="form-control"
            placeholder="Filter by name, city, cuisine"
            value="${escapeHtml(this.myRestaurantsSearchTerm)}"
            autocomplete="off"
          />
          <button class="btn btn-outline-secondary" type="button" id="places-my-clear" aria-label="Clear search">
            <i class="fas fa-times"></i>
          </button>
        </div>
        <div class="d-flex justify-content-between align-items-center">
          <span class="text-muted small" id="places-my-count">Showing 0 of ${totalWithCoords}</span>
          <div class="d-flex align-items-center gap-2">
            <button class="btn btn-outline-secondary btn-sm" type="button" id="places-my-location">
              <i class="fas fa-location-arrow me-1"></i>My Location
            </button>
            <button class="btn btn-outline-primary btn-sm" type="button" id="places-my-fit">
              <i class="fas fa-expand-arrows-alt me-1"></i>Fit Map
            </button>
          </div>
        </div>
      </div>
      <div class="results-container places-my-results">
        <div class="results-list" id="places-my-list"></div>
      </div>
    `;
    sidebar.innerHTML = html;

    this.bindMyRestaurantsSidebarEvents();
  }

  bindMyRestaurantsSidebarEvents() {
    const sidebar = this.container.querySelector('#places-sidebar-content');
    if (!sidebar) return;

    const searchInput = sidebar.querySelector('#places-my-search');
    const clearButton = sidebar.querySelector('#places-my-clear');
    const fitButton = sidebar.querySelector('#places-my-fit');
    const locationButton = sidebar.querySelector('#places-my-location');

    searchInput?.addEventListener('input', () => {
      this.myRestaurantsSearchTerm = searchInput.value || '';
      this.applyMyRestaurantsFilter({ preserveSelection: true });
    });

    clearButton?.addEventListener('click', () => {
      this.myRestaurantsSearchTerm = '';
      if (searchInput) searchInput.value = '';
      this.applyMyRestaurantsFilter({ fitMap: true, preserveSelection: true });
      searchInput?.focus();
    });

    fitButton?.addEventListener('click', () => {
      this.fitMapToMarkers(this.filteredMyRestaurants);
    });

    locationButton?.addEventListener('click', async() => {
      const loc = await this.getCurrentLocation();
      if (!loc || !this.map) return;
      this.currentLocation = loc;
      this.map.panTo(loc);
      this.map.setZoom(13);
      this.showUserLocationMarker(loc);
    });

    sidebar.addEventListener('click', (e) => {
      const viewButton = e.target.closest('[data-action="view-restaurant"]');
      if (viewButton) {
        const { viewUrl } = viewButton.dataset;
        if (viewUrl) {
          window.location.href = viewUrl;
        }
        return;
      }

      const restaurantItem = e.target.closest('.places-restaurant-item[data-restaurant-key]');
      if (restaurantItem) {
        const key = restaurantItem.getAttribute('data-restaurant-key');
        this.setSelectedRestaurant(key, { centerMap: true, zoomLevel: 15, scrollCard: true });
      }
    });
  }

  applyMyRestaurantsFilter(options = {}) {
    const { fitMap = false, preserveSelection = true } = options;
    const query = this.myRestaurantsSearchTerm.trim().toLowerCase();

    this.filteredMyRestaurants = this.myRestaurants.filter((restaurant) => {
      if (!query) return true;
      const searchable = [restaurant.name, restaurant.city, restaurant.state, restaurant.cuisine]
        .filter(Boolean)
        .join(' ')
        .toLowerCase();
      return searchable.includes(query);
    });

    this.updateMyRestaurantsList(this.filteredMyRestaurants, this.myRestaurants.length);
    this.renderMyRestaurantMarkers(this.filteredMyRestaurants);

    if (fitMap) {
      this.fitMapToMarkers(this.filteredMyRestaurants);
    }

    if (!preserveSelection || !this.selectedRestaurantKey) {
      this.selectedRestaurantKey = null;
      this.closeInfoWindow();
      return;
    }

    const stillVisible = this.filteredMyRestaurants.some(
      (r) => this.getRestaurantKey(r) === this.selectedRestaurantKey,
    );
    if (stillVisible) {
      this.setSelectedRestaurant(this.selectedRestaurantKey, {
        centerMap: false,
        zoomLevel: null,
        scrollCard: false,
      });
    } else {
      this.selectedRestaurantKey = null;
      this.closeInfoWindow();
    }
  }

  updateMyRestaurantsList(restaurants, totalWithCoords) {
    const list = this.container.querySelector('#places-my-list');
    const count = this.container.querySelector('#places-my-count');
    if (!list || !count) return;

    count.textContent = `Showing ${restaurants.length} of ${totalWithCoords}`;

    if (restaurants.length === 0) {
      list.innerHTML = this.myRestaurants.length
        ? '<p class="text-muted small mb-0">No matches for your filter. Try a different search.</p>'
        : "<p class='text-muted small mb-0'>No restaurants with coordinates. Add restaurants from Find Places.</p>";
      return;
    }

    let html = '';
    restaurants.forEach((restaurant, index) => {
      const name = escapeHtml(restaurant.name || '');
      const city = escapeHtml(this.formatCityState(restaurant));
      const cuisine = escapeHtml(restaurant.cuisine || '');
      const viewUrl = restaurant.id ? `/restaurants/${restaurant.id}` : '#';
      const key = this.getRestaurantKey(restaurant);
      const isActive = this.selectedRestaurantKey && this.selectedRestaurantKey === key;

      html += `
        <div class="places-restaurant-item${isActive ? ' is-active' : ''}" data-restaurant-key="${escapeHtml(key)}">
          <div class="places-restaurant-badge">${index + 1}</div>
          <div class="places-restaurant-content">
            <div class="d-flex justify-content-between align-items-start gap-2">
              <span class="fw-semibold text-dark">${name}</span>
              ${cuisine ? `<span class="badge rounded-pill text-bg-light">${cuisine}</span>` : ''}
            </div>
            <div class="d-flex justify-content-between align-items-center mt-1 gap-2">
              ${city ? `<div class="text-muted small">${city}</div>` : '<div></div>'}
              ${restaurant.id ? `<button type="button" class="btn btn-link btn-sm p-0 text-decoration-none" data-action="view-restaurant" data-view-url="${viewUrl}">View</button>` : ''}
            </div>
          </div>
        </div>
      `;
    });
    list.innerHTML = html;
  }

  renderMyRestaurantMarkers(restaurants) {
    this.clearMarkers();
    this.myRestaurantMarkers.clear();

    restaurants.forEach((restaurant, index) => {
      const markerEntry = this.createMyRestaurantMarker(restaurant, index);
      if (markerEntry) {
        this.myRestaurantMarkers.set(markerEntry.key, markerEntry);
      }
    });
  }

  createMyRestaurantMarker(restaurant, index) {
    if (!this.map) return null;

    const lat = parseFloat(restaurant.latitude, 10);
    const lng = parseFloat(restaurant.longitude, 10);
    if (Number.isNaN(lat) || Number.isNaN(lng)) return null;

    const position = { lat, lng };
    const key = this.getRestaurantKey(restaurant);
    const labelNumber = index + 1;
    let marker;

    if (window.google.maps.marker?.AdvancedMarkerElement && this.options.googleMapsMapId?.trim()) {
      marker = new google.maps.marker.AdvancedMarkerElement({
        position,
        map: this.map,
        title: restaurant.name,
        content: this.createNumberedMarkerContent(labelNumber, false),
      });
      marker.addEventListener('gmp-click', () => {
        this.setSelectedRestaurant(key, { centerMap: true, zoomLevel: 15, scrollCard: true });
      });
    } else {
      marker = new google.maps.Marker({
        position,
        map: this.map,
        title: restaurant.name,
        ...this.getClassicMarkerOptions(labelNumber, false),
      });
      marker.addListener('click', () => {
        this.setSelectedRestaurant(key, { centerMap: true, zoomLevel: 15, scrollCard: true });
      });
    }

    this.markers.push(marker);
    return { key, marker, position, index, restaurant };
  }

  setSelectedRestaurant(key, options = {}) {
    const { centerMap = true, zoomLevel = 15, scrollCard = true } = options;
    if (!key) return;

    const markerEntry = this.myRestaurantMarkers.get(key);
    if (!markerEntry) return;

    this.selectedRestaurantKey = key;

    this.container.querySelectorAll('.places-restaurant-item[data-restaurant-key]').forEach((item) => {
      item.classList.toggle('is-active', item.getAttribute('data-restaurant-key') === key);
    });

    if (scrollCard) {
      const escapedKey =
        typeof CSS !== 'undefined' && typeof CSS.escape === 'function'
          ? CSS.escape(key)
          : key.replace(/["\\]/g, '\\$&');
      const card = this.container.querySelector(`.places-restaurant-item[data-restaurant-key="${escapedKey}"]`);
      card?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

    this.myRestaurantMarkers.forEach((entry) => {
      const isActive = entry.key === key;
      this.updateMarkerStyle(entry, isActive);
    });

    if (centerMap && this.map) {
      this.map.panTo(markerEntry.position);
      if (typeof zoomLevel === 'number') {
        this.map.setZoom(zoomLevel);
      }
    }

    this.openRestaurantInfo(markerEntry);
  }

  updateMarkerStyle(markerEntry, isActive) {
    if (!markerEntry) return;
    const markerNumber = markerEntry.index + 1;
    if (markerEntry.marker.content) {
      markerEntry.marker.content = this.createNumberedMarkerContent(markerNumber, isActive);
    } else if (typeof markerEntry.marker.setIcon === 'function') {
      const iconOptions = this.getClassicMarkerOptions(markerNumber, isActive);
      markerEntry.marker.setIcon(iconOptions.icon);
      markerEntry.marker.setLabel(iconOptions.label);
    }
  }

  openRestaurantInfo(markerEntry) {
    if (!this.map || !markerEntry) return;

    if (!this.activeInfoWindow) {
      this.activeInfoWindow = new google.maps.InfoWindow();
    }

    const { restaurant } = markerEntry;
    const safeName = escapeHtml(restaurant.name || 'Restaurant');
    const safeCity = escapeHtml(this.formatCityState(restaurant));
    const safeCuisine = escapeHtml(restaurant.cuisine || '');
    const viewUrl = restaurant.id ? `/restaurants/${restaurant.id}` : '#';

    this.activeInfoWindow.setContent(`
      <div class="places-map-infowindow">
        <div class="fw-semibold mb-1">${safeName}</div>
        ${safeCity ? `<div class="text-muted small mb-1">${safeCity}</div>` : ''}
        <div class="d-flex align-items-center gap-2">
          ${safeCuisine ? `<span class="badge rounded-pill text-bg-light">${safeCuisine}</span>` : ''}
          <a href="${viewUrl}" class="small text-decoration-none">View details</a>
        </div>
      </div>
    `);
    this.activeInfoWindow.setPosition(markerEntry.position);
    this.activeInfoWindow.open({ map: this.map, anchor: markerEntry.marker });
  }

  closeInfoWindow() {
    if (this.activeInfoWindow) {
      this.activeInfoWindow.close();
    }
  }

  getRestaurantKey(restaurant) {
    if (restaurant.id !== null && restaurant.id !== undefined) {
      return `id:${restaurant.id}`;
    }

    const lat = Number.parseFloat(restaurant.latitude);
    const lng = Number.parseFloat(restaurant.longitude);
    return `coord:${lat},${lng}:${restaurant.name || ''}`;
  }

  formatCityState(restaurant) {
    const city = String(restaurant?.city || '').trim();
    const state = String(restaurant?.state || '').trim();
    if (city && state) {
      return `${city}, ${state}`;
    }
    return city || state;
  }

  renderNearbyResultsSidebar(results) {
    const resultsEl = this.container.querySelector('#places-nearby-results');
    if (!resultsEl) return;

    if (results.length === 0) {
      resultsEl.innerHTML = '<p class="text-muted small">No restaurants found in this area.</p>';
      return;
    }

    let html = '<div class="results-container"><div class="results-list">';
    results.forEach((r, i) => {
      const name = escapeHtml(r.name || '');
      const cityState = escapeHtml(this.formatCityState(r));
      const dist = typeof r.distance_km === 'number' ? `${r.distance_km.toFixed(1)} km` : '';
      const viewUrl = r.id ? `/restaurants/${r.id}` : '#';
      const faviconWebsite = escapeHtml(r.website || '');
      html += `
        <div class="card restaurant-card mb-2" data-index="${i}" style="cursor: pointer;">
          <div class="card-body py-2">
            <div class="d-flex justify-content-between align-items-start gap-2">
              <div class="d-flex align-items-start gap-2 min-w-0">
                <span class="places-nearby-favicon-wrap" title="Restaurant favicon">
                  ${
  faviconWebsite
    ? `<img
                    src="data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"
                    data-website="${faviconWebsite}"
                    data-size="18"
                    alt="${name} favicon"
                    class="places-nearby-favicon"
                    width="18"
                    height="18"
                  />`
    : ''
}
                  <i class="fas fa-utensils restaurant-fallback-icon ${faviconWebsite ? 'd-none' : ''}"></i>
                </span>
                <span class="text-dark fw-semibold text-truncate">${name}</span>
              </div>
              ${
  r.id
    ? `<button type="button" class="btn btn-link btn-sm p-0 text-decoration-none" data-action="view-restaurant" data-view-url="${viewUrl}">View</button>`
    : ''
}
            </div>
            ${cityState ? `<div class="text-muted small">${cityState}</div>` : ''}
            ${dist ? `<span class="badge bg-primary small">${dist}</span>` : ''}
          </div>
        </div>
      `;
    });
    html += '</div></div>';
    resultsEl.innerHTML = html;

    initializeRobustFaviconHandling('.places-nearby-favicon');

    this.bindSidebarCardClicks(results);
  }

  bindSidebarCardClicks(restaurants) {
    this.container.querySelectorAll('.restaurant-card[data-index]').forEach((card) => {
      card.addEventListener('click', (e) => {
        const viewButton = e.target.closest('[data-action="view-restaurant"]');
        if (viewButton) {
          const { viewUrl } = viewButton.dataset;
          if (viewUrl) {
            window.location.href = viewUrl;
          }
          return;
        }

        const index = parseInt(card.getAttribute('data-index'), 10);
        const r = restaurants[index];
        if (r && r.latitude !== null && r.longitude !== null && this.map) {
          this.map.setCenter({ lat: r.latitude, lng: r.longitude });
          this.map.setZoom(15);
          this.selectedNearbyIndex = index;
          this.updateNearbySelectionUI(index, { scrollCard: false });
        }
      });
    });
  }

  updateNearbySelectionUI(index, options = {}) {
    const { scrollCard = false } = options;
    this.container.querySelectorAll('#places-nearby-results .restaurant-card[data-index]').forEach((card) => {
      const cardIndex = Number.parseInt(card.getAttribute('data-index'), 10);
      const isActive = cardIndex === index;
      card.classList.toggle('border-primary', isActive);
      card.classList.toggle('shadow', isActive);
      if (isActive && scrollCard) {
        card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      }
    });

    this.markers.forEach((marker, markerIndex) => {
      const isActive = markerIndex === index;
      if (marker.content) {
        marker.content = this.createNumberedMarkerContent(markerIndex + 1, isActive);
      } else if (typeof marker.setIcon === 'function') {
        const iconOptions = this.getClassicMarkerOptions(markerIndex + 1, isActive);
        marker.setIcon(iconOptions.icon);
        marker.setLabel(iconOptions.label);
      }
    });
  }

  createMarker(restaurant, index) {
    if (!this.map) return;

    const lat = parseFloat(restaurant.latitude, 10);
    const lng = parseFloat(restaurant.longitude, 10);
    if (Number.isNaN(lat) || Number.isNaN(lng)) return;

    const position = { lat, lng };
    let marker;
    if (window.google.maps.marker?.AdvancedMarkerElement && this.options.googleMapsMapId?.trim()) {
      marker = new google.maps.marker.AdvancedMarkerElement({
        position,
        map: this.map,
        title: restaurant.name,
        content: this.createMarkerContent(index + 1),
      });
      marker.addEventListener('gmp-click', () => {
        this.map.panTo(position);
        this.map.setZoom(15);
        if (this.currentMode === 'nearby') {
          this.selectedNearbyIndex = index;
          this.updateNearbySelectionUI(index, { scrollCard: true });
        }
      });
    } else {
      marker = new google.maps.Marker({
        position,
        map: this.map,
        title: restaurant.name,
      });
      marker.addListener('click', () => {
        this.map.panTo(position);
        this.map.setZoom(15);
        if (this.currentMode === 'nearby') {
          this.selectedNearbyIndex = index;
          this.updateNearbySelectionUI(index, { scrollCard: true });
        }
      });
    }

    this.markers.push(marker);
  }

  createMarkerContent(number) {
    const el = document.createElement('div');
    el.style.cssText = `
      width: 32px;
      height: 32px;
      border-radius: 999px;
      border: 2px solid #fff;
      box-shadow: 0 4px 14px rgba(15, 23, 42, 0.22);
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 700;
      font-size: 12px;
      color: #fff;
      cursor: pointer;
      transition: transform 0.18s ease, background-color 0.18s ease;
      background-color: #0d6efd;
    `;
    el.textContent = number;
    return el;
  }

  createNumberedMarkerContent(number, isActive) {
    const el = this.createMarkerContent(number);
    if (isActive) {
      el.style.backgroundColor = '#198754';
      el.style.transform = 'scale(1.14)';
    }
    return el;
  }

  getClassicMarkerOptions(number, isActive) {
    return {
      icon: {
        path: google.maps.SymbolPath.CIRCLE,
        fillColor: isActive ? '#198754' : '#0d6efd',
        fillOpacity: 1,
        strokeColor: '#ffffff',
        strokeWeight: 2,
        scale: isActive ? 13 : 11,
      },
      label: {
        text: String(number),
        color: '#ffffff',
        fontSize: '12px',
        fontWeight: '700',
      },
    };
  }

  clearMarkers() {
    this.markers.forEach((m) => {
      if (typeof m.setMap === 'function') {
        m.setMap(null);
      } else {
        m.map = null;
      }
    });
    this.markers = [];
    this.myRestaurantMarkers.clear();
    this.closeInfoWindow();
    this.selectedNearbyIndex = null;
  }

  showUserLocationMarker(location) {
    if (!this.map || !location) return;

    if (this.userLocationMarker) {
      if (typeof this.userLocationMarker.setMap === 'function') {
        this.userLocationMarker.setMap(null);
      } else {
        this.userLocationMarker.map = null;
      }
    }

    if (window.google.maps.marker?.AdvancedMarkerElement) {
      const markerEl = document.createElement('div');
      markerEl.style.cssText = `
        width: 18px;
        height: 18px;
        background: #2563eb;
        border: 3px solid #ffffff;
        border-radius: 999px;
        box-shadow: 0 0 0 6px rgba(37, 99, 235, 0.22);
      `;
      this.userLocationMarker = new google.maps.marker.AdvancedMarkerElement({
        map: this.map,
        position: location,
        title: 'Your current location',
        content: markerEl,
      });
    } else {
      this.userLocationMarker = new google.maps.Marker({
        map: this.map,
        position: location,
        title: 'Your current location',
        icon: {
          path: google.maps.SymbolPath.CIRCLE,
          fillColor: '#2563eb',
          fillOpacity: 1,
          strokeColor: '#ffffff',
          strokeWeight: 3,
          scale: 8,
        },
      });
    }
  }

  fitMapToMarkers(restaurants) {
    if (!this.map || !restaurants?.length) return;

    const bounds = new google.maps.LatLngBounds();
    restaurants.forEach((r) => {
      if (r.latitude !== null && r.longitude !== null) {
        bounds.extend({ lat: parseFloat(r.latitude, 10), lng: parseFloat(r.longitude, 10) });
      }
    });
    if (bounds.isEmpty()) return;

    this.map.fitBounds(bounds, 50);
    const listener = google.maps.event.addListener(this.map, 'idle', () => {
      google.maps.event.removeListener(listener);
      const zoom = this.map.getZoom();
      if (zoom > 14) this.map.setZoom(14);
    });
  }

  getCurrentLocation() {
    return new Promise((resolve) => {
      if (!navigator.geolocation) {
        resolve(null);
        return;
      }
      navigator.geolocation.getCurrentPosition(
        (pos) => resolve({ lat: pos.coords.latitude, lng: pos.coords.longitude }),
        () => resolve(null),
        { enableHighAccuracy: true, timeout: 10000, maximumAge: 300000 },
      );
    });
  }
}
