/**
 * Restaurant Autocomplete
 *
 * Simple, clean autocomplete for restaurant search using our backend API
 *
 * Flow: Type restaurant name → Get suggestions → Select restaurant → Populate form
 */

// Cuisine service removed - not needed for basic autocomplete functionality

class RestaurantAutocomplete {
  constructor(inputElement) {
    console.log('RestaurantAutocomplete constructor called with:', inputElement);
    this.input = inputElement;
    this.suggestionsContainer = null;
    this.selectedIndex = -1;
    this.suggestions = [];
    this.userLocation = null;
    this.locationError = null;
    this.init();
  }

  init() {
    console.log('RestaurantAutocomplete init() called');
    this.createSuggestionsContainer();
    this.setupEventListeners();
    this.getUserLocation();
    console.log('RestaurantAutocomplete initialization complete');
  }

  createSuggestionsContainer() {
    this.suggestionsContainer = document.createElement('div');
    this.suggestionsContainer.className = 'restaurant-suggestions';
    this.suggestionsContainer.setAttribute('data-dynamic', 'true');
    this.suggestionsContainer.dataset.createdTime = Date.now().toString();
    this.suggestionsContainer.style.cssText = `
      position: absolute;
      top: 100%;
      left: 0;
      right: 0;
      background: white;
      border: 1px solid #ddd;
      border-top: none;
      border-radius: 0 0 4px 4px;
      box-shadow: 0 2px 4px rgba(0,0,0,0.1);
      max-height: 200px;
      overflow-y: auto;
      z-index: 1000;
      display: none;
    `;

    // Add CSS for suggestion items
    const style = document.createElement('style');
    style.textContent = `
      .restaurant-suggestions .suggestion-item {
        cursor: pointer;
        transition: background-color 0.15s ease;
      }
      .restaurant-suggestions .suggestion-item:hover {
        background-color: #f8f9fa;
      }
      .restaurant-suggestions .suggestion-item.selected {
        background-color: #f8f9fa;
      }
    `;
    document.head.appendChild(style);

    this.input.parentNode.style.position = 'relative';
    this.input.parentNode.appendChild(this.suggestionsContainer);
  }

  setupEventListeners() {
    console.log('Setting up event listeners for input:', this.input);
    // Debounced input
    let timeout;
    this.input.addEventListener('input', (e) => {
      console.log('Input event triggered, value:', e.target.value);
      clearTimeout(timeout);
      timeout = setTimeout(() => this.handleInput(e.target.value), 300);
    });

    // Click outside to close
    document.addEventListener('click', (e) => {
      if (!this.input.contains(e.target) && !this.suggestionsContainer.contains(e.target)) {
        this.hideSuggestions();
      }
    });

    // Keyboard navigation
    this.input.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        this.hideSuggestions();
      } else if (e.key === 'ArrowDown') {
        e.preventDefault();
        this.navigateSuggestions(1);
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        this.navigateSuggestions(-1);
      } else if (e.key === 'Enter') {
        e.preventDefault();
        this.selectCurrentSuggestion();
      }
    });
  }

  async handleInput(query) {
    console.log('handleInput called with query:', query);
    if (query.length < 2) {
      console.log('Query too short, hiding suggestions');
      this.hideSuggestions();
      return;
    }

    try {
      console.log('Showing loading and getting suggestions for:', query);
      this.showLoading(query);

      // If we don't have location yet, try to get it
      if (!this.userLocation && !this.locationError) {
        console.log('Attempting to get location for better search results...');
        await this.getUserLocation();
      }

      const suggestions = await this.getSuggestions(query);
      console.log('Got suggestions:', suggestions);
      this.showSuggestions(suggestions);
    } catch {
      console.error('Error getting suggestions:', error);

      // Provide more specific error messages based on the error type
      let errorMessage = 'Failed to get suggestions';

      if (error.message.includes('Failed to fetch')) {
        // This could be a network error or authentication redirect
        // Let the server handle authentication redirects naturally
        errorMessage = 'Unable to connect to server. Please check your connection and try again.';
      } else if (error.message.includes('HTTP 401')) {
        // Don't show error for 401 - redirect to login
        console.log('Authentication required - redirecting to login');
        const currentUrl = window.location.href;
        window.location.href = `/login?next=${encodeURIComponent(currentUrl)}`;
        return;
      } else if (error.message.includes('HTTP 403')) {
        errorMessage = 'Access denied: You do not have permission to search for restaurants.';
      } else if (error.message.includes('HTTP 500')) {
        errorMessage = 'Server error: Google Maps API is not configured. Please contact support.';
      } else if (error.message.includes('Google Maps API key not configured')) {
        errorMessage = 'Google Maps integration is not available. Please contact support.';
      } else if (error.message) {
        errorMessage = `Search error: ${error.message}`;
      }

      this.showError(errorMessage);
    }
  }

  async getUserLocation() {
    return new Promise((resolve) => {
      if (!navigator.geolocation) {
        console.log('Geolocation not supported');
        this.locationError = 'Geolocation not supported';
        resolve(null);
        return;
      }

      console.log('Requesting user location...');
      navigator.geolocation.getCurrentPosition(
        (position) => {
          this.userLocation = {
            lat: position.coords.latitude,
            lng: position.coords.longitude,
          };
          console.log('User location obtained:', this.userLocation);
          resolve(this.userLocation);
        },
        (error) => {
          console.log('Geolocation error:', error.message);
          this.locationError = error.message;
          resolve(null);
        },
        {
          enableHighAccuracy: true,
          timeout: 10000,
          maximumAge: 300000, // 5 minutes
        },
      );
    });
  }

  async getSuggestions(query) {
    try {
      // Build query parameters with location if available
      const params = new URLSearchParams({
        query,
      });

      // Add location parameters if we have user location
      if (this.userLocation) {
        params.append('lat', this.userLocation.lat);
        params.append('lng', this.userLocation.lng);

        // Use dynamic radius based on search context
        const radius = this.getDynamicRadius(query);
        params.append('radiusMiles', radius.toString());
        console.log(`Searching with location: ${this.userLocation.lat}, ${this.userLocation.lng}, radius: ${radius} miles`);
      } else {
        console.log('Searching without location (fallback to text-only search)');
      }

      const url = `/restaurants/api/places/search?${params.toString()}`;
      console.log('Making request to:', url);

      const response = await fetch(url, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'same-origin', // Include cookies for authentication
        redirect: 'manual', // Don't follow redirects automatically
      });

      console.log('Response status:', response.status, response.statusText);

      // Handle redirects manually
      if (response.status === 302 || response.status === 301) {
        const redirectUrl = response.headers.get('Location');
        console.log('Redirect detected to:', redirectUrl);
        if (redirectUrl && redirectUrl.includes('/login')) {
          // Redirect to login page
          window.location.href = redirectUrl;
          return;
        }
      }

      // Handle authentication errors
      if (response.status === 401) {
        console.log('Authentication required - redirecting to login');
        // Redirect to login page with current URL as next parameter
        const currentUrl = window.location.href;
        window.location.href = `/login?next=${encodeURIComponent(currentUrl)}`;
        return;
      }

      if (!response.ok) {
        const errorText = await response.text();
        console.error('Response error:', errorText);
        throw new Error(`HTTP ${response.status}: ${response.statusText} - ${errorText}`);
      }

      const data = await response.json();
      console.log('Response data:', data);

      if (data.error) {
        // Handle specific API errors
        if (data.error.includes('Google Maps API key not configured')) {
          throw new Error('Google Maps integration is not available. Please contact support.');
        }
        throw new Error(data.error);
      }

      // Backend returns { data: { results: [...] } } for places search.
      // Normalize to a lightweight suggestions list expected by the UI.
      const results = (data && data.data && Array.isArray(data.data.results)) ? data.data.results : [];
      const suggestions = results.map((place) => {
        // Calculate distance if we have user location and place coordinates
        let distance = null;
        if (this.userLocation && place.geometry && place.geometry.location) {
          distance = this.calculateDistance(
            this.userLocation.lat,
            this.userLocation.lng,
            place.geometry.location.lat,
            place.geometry.location.lng,
          );
        }

        return {
          placeId: place.place_id || place.placeId || '',
          title: place.name || place.title || '',
          description: place.formatted_address || place.vicinity || place.address || '',
          distance,
          distanceMiles: distance ? this.formatDistance(distance) : null,
        };
      }).filter((s) => s.placeId && s.title);

      // Sort by distance if we have location data (nearest first)
      if (this.userLocation) {
        suggestions.sort((a, b) => {
          if (a.distance === null && b.distance === null) return 0;
          if (a.distance === null) return 1; // Put items without distance at the end
          if (b.distance === null) return -1;
          return a.distance - b.distance; // Sort by distance, nearest first
        });
      }

      // If we have location but no results, try a broader search
      if (this.userLocation && suggestions.length === 0) {
        console.log('No nearby results found, trying broader search...');
        return await this.getSuggestionsWithFallback(query);
      }

      return suggestions;
    } catch {
      throw new Error(`Search error: ${error.message}`);
    }
  }

  getDynamicRadius(query) {
    const lowerQuery = query.toLowerCase();

    // Chain restaurants - search wider since they're more common
    const chainRestaurants = ['mcdonald', 'burger king', 'kfc', 'subway', 'taco bell', 'pizza hut', 'domino', 'starbucks', 'dunkin'];
    const isChain = chainRestaurants.some((chain) => lowerQuery.includes(chain));

    // Fine dining or specific restaurants - search wider
    const fineDining = ['michelin', 'fine dining', 'upscale', 'gourmet', 'chef', 'restaurant'];
    const isFineDining = fineDining.some((term) => lowerQuery.includes(term));

    // Generic terms - search wider
    const genericTerms = ['restaurant', 'food', 'dining', 'eat', 'lunch', 'dinner'];
    const isGeneric = genericTerms.some((term) => lowerQuery.includes(term));

    if (isChain) {
      return 25; // 25 miles for chains
    } else if (isFineDining) {
      return 50; // 50 miles for fine dining
    } else if (isGeneric) {
      return 15; // 15 miles for generic searches
    }
    return 20; // 20 miles for specific restaurant names

  }

  calculateDistance(lat1, lng1, lat2, lng2) {
    // Haversine formula to calculate distance between two points
    const R = 3959; // Earth's radius in miles
    const dLat = this.toRadians(lat2 - lat1);
    const dLng = this.toRadians(lng2 - lng1);
    const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
              Math.cos(this.toRadians(lat1)) * Math.cos(this.toRadians(lat2)) *
              Math.sin(dLng / 2) * Math.sin(dLng / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    return R * c;
  }

  toRadians(degrees) {
    return degrees * (Math.PI / 180);
  }

  formatDistance(distanceMiles) {
    if (distanceMiles < 0.1) {
      return '< 0.1 mi';
    } else if (distanceMiles < 1) {
      return `${distanceMiles.toFixed(1)} mi`;
    }
    return `${Math.round(distanceMiles)} mi`;

  }

  async getSuggestionsWithFallback(query) {
    try {
      // Try with a much larger radius (100 miles)
      const params = new URLSearchParams({
        query,
        lat: this.userLocation.lat,
        lng: this.userLocation.lng,
        radiusMiles: '100', // 100 mile radius for fallback
      });

      console.log('Fallback search with 100-mile radius...');

      const response = await fetch(`/restaurants/api/places/search?${params.toString()}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();

      if (data.error) {
        throw new Error(data.error);
      }

      const results = (data && data.data && Array.isArray(data.data.results)) ? data.data.results : [];
      const suggestions = results.map((place) => {
        // Calculate distance if we have user location and place coordinates
        let distance = null;
        if (this.userLocation && place.geometry && place.geometry.location) {
          distance = this.calculateDistance(
            this.userLocation.lat,
            this.userLocation.lng,
            place.geometry.location.lat,
            place.geometry.location.lng,
          );
        }

        return {
          placeId: place.place_id || place.placeId || '',
          title: place.name || place.title || '',
          description: place.formatted_address || place.vicinity || place.address || '',
          distance,
          distanceMiles: distance ? this.formatDistance(distance) : null,
        };
      }).filter((s) => s.placeId && s.title);

      // Sort by distance if we have location data (nearest first)
      if (this.userLocation) {
        suggestions.sort((a, b) => {
          if (a.distance === null && b.distance === null) return 0;
          if (a.distance === null) return 1; // Put items without distance at the end
          if (b.distance === null) return -1;
          return a.distance - b.distance; // Sort by distance, nearest first
        });
      }

      // If still no results, try without location
      if (suggestions.length === 0) {
        console.log('No results with location, trying text-only search...');
        return await this.getSuggestionsTextOnly(query);
      }

      return suggestions;
    } catch {
      console.error('Fallback search failed:', error);
      // Try text-only search as last resort
      return this.getSuggestionsTextOnly(query);
    }
  }

  async getSuggestionsTextOnly(query) {
    try {
      const params = new URLSearchParams({
        query,
      });

      console.log('Text-only search (no location)...');

      const response = await fetch(`/restaurants/api/places/search?${params.toString()}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();

      if (data.error) {
        throw new Error(data.error);
      }

      const results = (data && data.data && Array.isArray(data.data.results)) ? data.data.results : [];
      const suggestions = results.map((place) => ({
        placeId: place.place_id || place.placeId || '',
        title: place.name || place.title || '',
        description: place.formatted_address || place.vicinity || place.address || '',
        distance: null, // No distance for text-only search
      })).filter((s) => s.placeId && s.title);

      return suggestions;
    } catch {
      throw new Error(`Text-only search error: ${error.message}`);
    }
  }

  showSuggestions(suggestions) {
    if (suggestions.length === 0) {
      this.hideSuggestions();
      return;
    }

    // Store suggestions for keyboard navigation
    this.suggestions = suggestions;
    this.selectedIndex = -1;

    const html = suggestions.map((suggestion, index) => `
      <div class="suggestion-item" data-place-id="${suggestion.placeId}" data-index="${index}">
        <div class="d-flex align-items-center p-2">
          <i class="fas fa-utensils text-primary me-2"></i>
          <div class="flex-grow-1">
            <div class="fw-medium">${suggestion.title}</div>
            <small class="text-muted">${suggestion.description}</small>
          </div>
          ${suggestion.distanceMiles ? `<small class="text-primary ms-2 fw-medium">${suggestion.distanceMiles}</small>` : ''}
        </div>
      </div>
    `).join('');

    this.suggestionsContainer.innerHTML = html;
    this.suggestionsContainer.style.display = 'block';

    // Add click handlers
    this.suggestionsContainer.querySelectorAll('.suggestion-item').forEach((item) => {
      item.addEventListener('click', () => {
        const { placeId } = item.dataset;
        this.selectRestaurant(placeId);
      });
    });
  }

  navigateSuggestions(direction) {
    if (this.suggestions.length === 0) return;

    // Remove current selection
    this.clearSelection();

    // Update selected index
    if (direction > 0) {
      this.selectedIndex = Math.min(this.selectedIndex + 1, this.suggestions.length - 1);
    } else {
      this.selectedIndex = Math.max(this.selectedIndex - 1, 0);
    }

    // Highlight selected item
    this.highlightSelection();
  }

  clearSelection() {
    this.suggestionsContainer.querySelectorAll('.suggestion-item').forEach((item) => {
      item.classList.remove('selected');
    });
  }

  highlightSelection() {
    if (this.selectedIndex >= 0 && this.selectedIndex < this.suggestions.length) {
      const selectedItem = this.suggestionsContainer.querySelector(`[data-index="${this.selectedIndex}"]`);
      if (selectedItem) {
        selectedItem.classList.add('selected');
      }
    }
  }

  selectCurrentSuggestion() {
    if (this.selectedIndex >= 0 && this.selectedIndex < this.suggestions.length) {
      const { placeId } = this.suggestions[this.selectedIndex];
      this.selectRestaurant(placeId);
    }
  }

  async selectRestaurant(placeId) {
    try {
      console.log('Selecting restaurant with placeId:', placeId);
      this.showLoading();

      // Get restaurant details from our backend
      const restaurantData = await this.getRestaurantDetails(placeId);
      console.log('Received restaurant data:', restaurantData);

      // Populate form with restaurant data
      this.populateForm(restaurantData);

      this.hideSuggestions();

    } catch {
      console.error('Error getting restaurant details:', error);
      this.showError('Failed to load restaurant details');
    }
  }

  async getRestaurantDetails(placeId) {
    try {
      console.log('Fetching restaurant details for placeId:', placeId);
      const response = await fetch(`/restaurants/api/places/details/${placeId}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const place = await response.json();
      console.log('Raw response from backend:', place);

      if (place.error) {
        throw new Error(place.error);
      }

      // Return the comprehensive data structure from backend
      return {
        name: place.name || '',
        type: place.type || 'restaurant',
        description: place.description || '',
        address: place.address || '',
        city: place.city || '',
        state: place.state || '',
        postal_code: place.postal_code || '',
        country: place.country || '',
        phone: place.phone || '',
        website: place.website || '',
        email: place.email || '',
        google_place_id: place.google_place_id || placeId,
        cuisine: place.cuisine || '',
        service_level: place.service_level || '',
        is_chain: place.is_chain || false,
        rating: place.rating || null,
        notes: place.notes || '',
        // Keep the original fields for backward compatibility
        formatted_address: place.formatted_address || place.address || '',
        formatted_phone_number: place.phone || '',
        types: place.types || [],
        address_components: place.address_components || [],
        place_id: placeId,
      };
    } catch {
      throw new Error(`Details error: ${error.message}`);
    }
  }

  populateForm(restaurantData) {
    console.log('Populating form with restaurant data:', restaurantData);

    // Define field mappings for both places_search.html and form.html
    const fieldMappings = {
      // Places search page field IDs (with restaurant- prefix)
      'restaurant-name': restaurantData.name,
      'restaurant-type': restaurantData.type,
      'restaurant-description': restaurantData.description,
      'restaurant-address': restaurantData.address,
      'restaurant-city': restaurantData.city,
      'restaurant-state': restaurantData.state,
      'restaurant-postal-code': restaurantData.postal_code,
      'restaurant-country': restaurantData.country,
      'restaurant-phone': restaurantData.phone,
      'restaurant-website': restaurantData.website,
      'restaurant-email': restaurantData.email,
      'restaurant-google-place-id': restaurantData.google_place_id,
      'restaurant-cuisine': restaurantData.cuisine,
      'restaurant-service-level': restaurantData.service_level,
      'restaurant-price-level': restaurantData.price_level,
      'restaurant-is-chain': restaurantData.is_chain,
      'restaurant-rating': restaurantData.rating,
      'restaurant-notes': restaurantData.notes,

      // Restaurant form field IDs (without prefix)
      name: restaurantData.name,
      type: restaurantData.type,
      description: restaurantData.description,
      address: restaurantData.address,
      city: restaurantData.city,
      state: restaurantData.state,
      postal_code: restaurantData.postal_code,
      country: restaurantData.country,
      phone: restaurantData.phone,
      website: restaurantData.website,
      email: restaurantData.email,
      google_place_id: restaurantData.google_place_id,
      cuisine: restaurantData.cuisine,
      service_level: restaurantData.service_level,
      price_level: restaurantData.price_level,
      is_chain: restaurantData.is_chain,
      rating: restaurantData.rating,
      notes: restaurantData.notes,
    };

    console.log('Field mappings:', fieldMappings);

    // Populate form fields
    Object.entries(fieldMappings).forEach(([fieldId, value]) => {
      const field = document.getElementById(fieldId);
      if (field && value !== null && value !== undefined) {
        console.log(`Setting field ${fieldId} to:`, value);

        // Special debugging for cuisine field
        if (fieldId === 'restaurant-cuisine' || fieldId === 'cuisine') {
          console.log('Cuisine field found:', field);
          console.log('Cuisine value:', value);
          console.log('Field type:', field.type);
        }

        // Special debugging for price_level field
        if (fieldId === 'restaurant-price-level' || fieldId === 'price_level') {
          console.log('Price level field found:', field);
          console.log('Price level value:', value);
          console.log('Field type:', field.type);
          console.log('Field options:', Array.from(field.options).map((opt) => ({ value: opt.value, text: opt.text })));
        }

        // Handle different field types
        if (field.type === 'checkbox') {
          field.checked = Boolean(value);
        } else if (field.type === 'select-one') {
          // For select fields, try to find matching option
          const option = Array.from(field.options).find((opt) =>
            opt.value === String(value) || opt.value === value || opt.text.toLowerCase() === String(value).toLowerCase(),
          );
          if (option) {
            field.value = option.value;
            console.log(`Set select field ${fieldId} to option:`, { value: option.value, text: option.text });
          } else {
            console.log(`No matching option found for ${fieldId} with value:`, value);
          }
        } else {
          field.value = value;
        }
      } else if (value !== null && value !== undefined) {
        console.log(`Field ${fieldId} not found in DOM`);
      } else {
        console.log(`Field ${fieldId} has null/undefined value:`, value);
      }
    });

    this.input.value = restaurantData.name || '';

    // Show success message with details
    const message = `Restaurant data loaded from Google Places! ${restaurantData.cuisine ? `(${restaurantData.cuisine})` : ''}`;
    this.showSuccess(message);
  }

  showLoading(query = '') {
    let locationStatus;
    if (this.userLocation) {
      const radius = this.getDynamicRadius(query);
      locationStatus = `<small class="text-success d-block mt-1"><i class="fas fa-map-marker-alt me-1"></i>Searching within ${radius} miles</small>`;
    } else if (this.locationError) {
      locationStatus = '<small class="text-muted d-block mt-1"><i class="fas fa-info-circle me-1"></i>Searching all restaurants</small>';
    } else {
      locationStatus = '<small class="text-info d-block mt-1"><i class="fas fa-spinner fa-spin me-1"></i>Getting your location...</small>';
    }

    this.suggestionsContainer.innerHTML = `
      <div class="p-3 text-center">
        <div class="spinner-border spinner-border-sm text-primary" role="status">
          <span class="visually-hidden">Loading...</span>
        </div>
        <span class="ms-2">Loading...</span>
        ${locationStatus}
      </div>
    `;
    this.suggestionsContainer.style.display = 'block';
  }

  showError(message) {
    this.suggestionsContainer.innerHTML = `
      <div class="p-3 text-center text-danger">
        <i class="fas fa-exclamation-triangle me-2"></i>
        ${message}
      </div>
    `;
    this.suggestionsContainer.style.display = 'block';
    setTimeout(() => this.hideSuggestions(), 3000);
  }

  showSuccess(message) {
    // Create a temporary success message
    const successDiv = document.createElement('div');
    successDiv.className = 'alert alert-success alert-dismissible fade show';
    successDiv.innerHTML = `
      <i class="fas fa-check-circle me-2"></i>
      ${message}
      <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;

    // Insert after the input
    this.input.parentNode.insertBefore(successDiv, this.input.nextSibling);

    // Auto-dismiss after 3 seconds
    setTimeout(() => {
      if (successDiv.parentNode) {
        successDiv.remove();
      }
    }, 3000);
  }

  hideSuggestions() {
    this.suggestionsContainer.style.display = 'none';
  }

}

// Auto-initialize when DOM is ready
function initRestaurantAutocomplete() {
  console.log('initRestaurantAutocomplete called');
  const inputs = document.querySelectorAll('[data-restaurant-autocomplete]');
  console.log('Found', inputs.length, 'restaurant autocomplete inputs');

  if (inputs.length === 0) {
    console.warn('No restaurant autocomplete inputs found');
    return;
  }

  inputs.forEach((input, index) => {
    console.log('Initializing restaurant autocomplete for input', index, input);
    try {
      new RestaurantAutocomplete(input);
      console.log('Successfully initialized autocomplete for input', index);
    } catch {
      console.error('Failed to initialize autocomplete for input', index, error);
    }
  });
}

// Initialize when DOM is ready
console.log('Document ready state:', document.readyState);
if (document.readyState === 'loading') {
  console.log('Adding DOMContentLoaded listener');
  document.addEventListener('DOMContentLoaded', initRestaurantAutocomplete);
} else {
  console.log('DOM already ready, initializing immediately');
  initRestaurantAutocomplete();
}

// Export for manual initialization
window.RestaurantAutocomplete = RestaurantAutocomplete;
