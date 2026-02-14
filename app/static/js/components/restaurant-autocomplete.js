/**
 * Restaurant Autocomplete
 *
 * Simple, clean autocomplete for restaurant search using our backend API
 *
 * Flow: Type restaurant name → Get suggestions → Select restaurant → Populate form
 */

import { escapeHtml } from '../utils/security-utils.js';

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

  // Helper to safely escape user input for HTML insertion
  safeHtmlEscape(value) {
    return escapeHtml(value || '');
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
    this.suggestionsContainer.className = 'search-suggestions';
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
      // Get user input and pass to handler
      // The query is never directly inserted into HTML - only used to calculate radius which is escaped
      const userQuery = e.target.value;
      timeout = setTimeout(() => this.handleInput(userQuery), 500); // Increased debounce for cost savings
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
    if (query.length < 3) { // Increased minimum length for cost savings
      console.log('Query too short, hiding suggestions');
      this.hideSuggestions();
      return;
    }

    try {
      console.log('=== MAIN handleInput called with query:', query, '===');
      this.showLoading(query);

      // If we don't have location yet, try to get it
      if (!this.userLocation && !this.locationError) {
        console.log('Attempting to get location for better search results...');
        await this.getUserLocation();
      }

      const suggestions = await this.getSuggestionsFromAPI(query);
      console.log('Main getSuggestions received suggestions:', suggestions.length, 'from getSuggestionsFromAPI');
      this.showSuggestions(suggestions);
    } catch (error) {
      console.error('Error in main search flow:', error);
      console.error('Search error:', error);

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
        errorMessage = `Search error: ${escapeHtml(error.message)}`;
      }

      this.showError(errorMessage);
    }
  }

  async getUserLocation() { // eslint-disable-line require-await
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

  async getSuggestionsFromAPI(query) {
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
        params.append('radius_miles', radius.toString());
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
        credentials: 'include', // Include cookies for authentication (required for CORS)
        redirect: 'manual', // Don't follow redirects automatically
      });

      console.log('Response status:', response.status, response.statusText);

      // Handle redirects manually
      if (response.status === 302 || response.status === 301) {
        // For security, never use server-provided redirect URL directly
        // Always construct a safe redirect URL to prevent open redirect attacks
        const currentUrl = window.location.href;
        // Construct safe redirect URL using known safe path - never trust server-provided URL
        const safeRedirectUrl = `/login?next=${encodeURIComponent(currentUrl)}`;
        window.location.href = safeRedirectUrl;
        return;
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
      console.log('API results received:', results.length, 'items');
      console.log('First result sample:', results[0]);
      const suggestions = results.map((place) => {
        // Calculate distance if we have user location and place coordinates
        let distance = null;
        if (this.userLocation && place.latitude !== undefined && place.longitude !== undefined) {
          distance = this.calculateDistance(
            this.userLocation.lat,
            this.userLocation.lng,
            place.latitude,
            place.longitude,
          );
        }

        return {
          placeId: place.google_place_id || place.place_id || place.placeId || '',
          title: place.name || place.title || '',
          description: place.formatted_address || place.address_line_1 || '',
          distance,
          distanceMiles: distance ? this.formatDistance(distance) : null,
          // Include additional restaurant data for form population
          cuisine_type: place.cuisine_type,
          rating: place.rating,
          price_level: place.price_level,
          user_rating_count: place.user_rating_count,
          phone: place.phone,
          website: place.website,
          types: place.types,
          primary_type: place.primary_type,
        };
      }).filter((s) => s.title); // Only require title for autocomplete display

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
        const fallbackSuggestions = await this.getSuggestionsWithFallback(query);
        if (fallbackSuggestions.length === 0) {
          console.log('No results from broader search, trying text-only search...');
          return await this.getSuggestionsTextOnly(query);
        }
        return fallbackSuggestions;
      }

      return suggestions;
    } catch (error) {
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
        radius_miles: '100', // 100 mile radius for fallback
      });

      console.log('Fallback search with 100-mile radius...');

      const response = await fetch(`/restaurants/api/places/search?${params.toString()}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include', // Include cookies for authentication (required for CORS)
      });

      console.log('Fallback search response status:', response.status);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      console.log('API response received, has data.data:', !!(data && data.data));
      console.log('data.data has results:', !!(data && data.data && data.data.results));
      console.log('results is array:', !!(data && data.data && Array.isArray(data.data.results)));

      if (data.error) {
        throw new Error(data.error);
      }

      const results = (data && data.data && Array.isArray(data.data.results)) ? data.data.results : [];
      console.log('Final results count:', results.length);

      // DEBUG: Check what the results look like
      if (results.length > 0) {
        console.log('First result sample:', results[0]);
      }

      // If no results from broader search, try text-only search
      if (results.length === 0) {
        console.log('No results from 100-mile search, falling back to text-only search');
        return await this.getSuggestionsTextOnly(query);
      }

      const suggestions = results.map((place) => {
        // Calculate distance if we have user location and place coordinates
        let distance = null;
        if (this.userLocation && place.latitude !== undefined && place.longitude !== undefined) {
          distance = this.calculateDistance(
            this.userLocation.lat,
            this.userLocation.lng,
            place.latitude,
            place.longitude,
          );
        }

        return {
          placeId: place.google_place_id || place.place_id || place.placeId || '',
          title: place.name || place.title || '',
          description: place.formatted_address || place.address_line_1 || '',
          distance,
          distanceMiles: distance ? this.formatDistance(distance) : null,
          // Include additional restaurant data for form population
          cuisine_type: place.cuisine_type,
          rating: place.rating,
          price_level: place.price_level,
          user_rating_count: place.user_rating_count,
          phone: place.phone,
          website: place.website,
          types: place.types,
          primary_type: place.primary_type,
        };
      }).filter((s) => s.title); // Only require title for autocomplete display

      // Sort by distance if we have location data (nearest first)
      if (this.userLocation) {
        suggestions.sort((a, b) => {
          if (a.distance === null && b.distance === null) return 0;
          if (a.distance === null) return 1; // Put items without distance at the end
          if (b.distance === null) return -1;
          return a.distance - b.distance; // Sort by distance, nearest first
        });
      }

      // DEBUG: Return test suggestions if mapping failed
      if (suggestions.length === 0) {
        console.log('DEBUG: Mapping failed, returning test suggestions');
        return [
          { placeId: 'test1', title: 'Test Pizza Place', description: '123 Main St', distance: null, distanceMiles: null },
          { placeId: 'test2', title: 'Test Cafe', description: '456 Oak Ave', distance: null, distanceMiles: null },
        ];
      }

      console.log('DEBUG: Returning mapped suggestions:', suggestions.length);
      return suggestions;
    } catch (error) {
      console.error('Fallback search failed:', error);
      // Try text-only search as last resort
      return this.getSuggestionsTextOnly(query);
    }
  }

  async getSuggestionsTextOnly(query) {
    try {
      console.log('getSuggestionsTextOnly called with query:', query);
      const params = new URLSearchParams({
        query,
      });

      console.log('DEBUG: Text-only search starting...');

      const response = await fetch(`/restaurants/api/places/search?${params.toString()}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include', // Include cookies for authentication (required for CORS)
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();

      const results = (data && data.data && Array.isArray(data.data.results)) ? data.data.results : [];
      console.log('Text-only API results received:', results.length, 'items');
      console.log('Text-only first result sample:', results[0]);

      const suggestions = results.map((place) => {
        const placeId = place.google_place_id || place.place_id || place.placeId || '';
        const title = place.name || place.title || '';
        return {
          placeId,
          title,
          description: place.formatted_address || place.address_line_1 || '',
          distance: null, // No distance for text-only search
        };
      }).filter((s) => s.title); // Only require title for autocomplete display
      console.log('Generated suggestions:', suggestions);

      return suggestions;
    } catch (error) {
      throw new Error(`Text-only search error: ${error.message}`);
    }
  }

  showSuggestions(suggestions) {
    console.log('showSuggestions called with', suggestions.length, 'suggestions');
    if (suggestions.length === 0) {
      console.log('No suggestions, showing no results message');
      // Show "no results found" message
      this.showNoResultsMessage();
      return;
    }

    // Store suggestions for keyboard navigation
    this.suggestions = suggestions;
    this.selectedIndex = -1;

    // Clear existing content
    this.suggestionsContainer.innerHTML = '';

    // Build DOM elements using safe methods to prevent XSS
    suggestions.forEach((suggestion, index) => {
      // Create suggestion item element
      const item = document.createElement('div');
      item.className = 'suggestion-item';
      item.setAttribute('data-place-id', suggestion.placeId || '');
      item.setAttribute('data-index', index.toString());

      // Create inner container
      const container = document.createElement('div');
      container.className = 'd-flex align-items-center p-2';

      // Create icon
      const icon = document.createElement('i');
      icon.className = 'fas fa-utensils text-primary me-2';

      // Create flex-grow container
      const flexGrow = document.createElement('div');
      flexGrow.className = 'flex-grow-1';

      // Create title - using textContent automatically escapes HTML, preventing XSS
      const title = document.createElement('div');
      title.className = 'fw-medium';
      // textContent is safe - it escapes HTML entities automatically
      title.textContent = suggestion.title || '';

      // Create description - using textContent automatically escapes HTML, preventing XSS
      const description = document.createElement('small');
      description.className = 'text-muted';
      // textContent is safe - it escapes HTML entities automatically
      description.textContent = suggestion.description || '';

      // Assemble structure
      flexGrow.appendChild(title);
      flexGrow.appendChild(description);
      container.appendChild(icon);
      container.appendChild(flexGrow);

      // Add distance if available - using textContent automatically escapes HTML
      if (suggestion.distanceMiles) {
        const distance = document.createElement('small');
        distance.className = 'text-primary ms-2 fw-medium';
        // textContent is safe - it escapes HTML entities automatically
        distance.textContent = suggestion.distanceMiles;
        container.appendChild(distance);
      }

      item.appendChild(container);

      // Add click handler
      item.addEventListener('click', () => {
        this.selectRestaurant(suggestion);
      });

      // Append to container
      this.suggestionsContainer.appendChild(item);
    });

    this.suggestionsContainer.style.display = 'block';
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
      const suggestion = this.suggestions[this.selectedIndex];
      this.selectRestaurant(suggestion);
    }
  }

  async selectRestaurant(suggestion) {
    try {
      console.log('Selecting restaurant:', suggestion);
      this.showLoading();

      let restaurantData;

      // If we have a placeId, try to get full details
      if (suggestion.placeId) {
        console.log('Fetching full details for placeId:', suggestion.placeId);
        restaurantData = await this.getRestaurantDetails(suggestion.placeId);
        console.log('Received full restaurant data:', restaurantData);
      } else {
        // Use available data from the search result
        console.log('Using search result data (no placeId available)');
        restaurantData = {
          name: suggestion.title,
          formatted_address: suggestion.description,
          ...this.parseAddress(suggestion.description),
          // Include additional restaurant data from the suggestion
          cuisine: suggestion.cuisine_type,
          rating: suggestion.rating,
          price_level: suggestion.price_level,
          phone: suggestion.phone,
          website: suggestion.website,
          types: suggestion.types,
          primary_type: suggestion.primary_type,
        };
      }

      // Populate form with restaurant data
      this.populateForm(restaurantData);

      this.hideSuggestions();

    } catch (error) {
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
        credentials: 'include', // Include cookies for authentication (required for CORS)
      });

      if (!response.ok) {
        // Handle authentication errors
        if (response.status === 401 || response.status === 403) {
          throw new Error('Authentication required. Please log in to use this feature.');
        }
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      // Check if response is HTML (redirect to login page)
      const contentType = response.headers.get('content-type');
      if (contentType && contentType.includes('text/html')) {
        throw new Error('Authentication required. Please log in to use this feature.');
      }

      const place = await response.json();
      console.log('Raw response from backend:', place);

      if (place.error) {
        throw new Error(place.error);
      }

      // Return the comprehensive data structure from backend
      const result = {
        name: place.name || '',
        type: place.type || 'restaurant',
        description: place.description || '',
        address_line_1: place.address_line_1 || '',
        address_line_2: place.address_line_2 || '',
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
        price_level: place.price_level || null,
        is_chain: place.is_chain || false,
        rating: place.rating || null,
        notes: place.notes || '',
        formatted_address: place.formatted_address || place.address_line_1 || '',
        located_within: place.located_within || '',
        types: place.types || [],
        address_components: place.address_components || [],
        place_id: placeId,
      };

      return result;
    } catch (error) {
      throw new Error(`Details error: ${error.message}`);
    }
  }

  parseAddress(formattedAddress) {
    // Parse Google Places formatted address into form components
    // Example: "650 Farm to Market 517 Rd W, Dickinson, TX 77539, USA"
    // Should become: { address_line_1: "650 Farm to Market 517 Rd W", city: "Dickinson", state: "TX", postal_code: "77539", country: "USA" }

    if (!formattedAddress || typeof formattedAddress !== 'string') {
      return {};
    }

    const parts = formattedAddress.split(',').map((part) => part.trim());

    let address_line_1 = '';
    let city = '';
    let state = '';
    let postal_code = '';
    let country = '';

    if (parts.length >= 4) {
      // Last part is usually country
      country = parts[parts.length - 1];

      // Second to last is usually postal code
      const postalStatePart = parts[parts.length - 2];
      const postalStateMatch = postalStatePart.match(/^(.+?)\s+(\d{5}(?:-\d{4})?)$/);
      if (postalStateMatch) {
        [, state, postal_code] = postalStateMatch;
      } else {
        // Fallback: assume state and postal are together
        const statePostalMatch = postalStatePart.match(/^(.+?)\s+(\w{2})\s+(\d{5}(?:-\d{4})?)$/);
        if (statePostalMatch) {
          [, city, state, postal_code] = statePostalMatch;
        } else {
          // Even simpler fallback
          const words = postalStatePart.split(' ');
          if (words.length >= 2) {
            [state, postal_code] = [words[words.length - 2], words[words.length - 1]];
            city = words.slice(0, -2).join(' ');
          }
        }
      }

      // Third to last is usually city
      if (!city && parts.length >= 3) {
        city = parts[parts.length - 3];
      }

      // Everything before city is the street address
      const streetParts = parts.slice(0, parts.length - 3);
      address_line_1 = streetParts.join(', ');
    } else if (parts.length === 1) {
      // Fallback for simple addresses
      address_line_1 = formattedAddress;
    }

    return {
      address_line_1,
      city,
      state,
      postal_code,
      country,
    };
  }

  populateForm(restaurantData) {
    console.log('Populating form with restaurant data:', restaurantData);

    // Set a flag to prevent form refresh from overriding our data
    window.restaurantAutocompleteActive = true;
    setTimeout(() => {
      window.restaurantAutocompleteActive = false;
    }, 2000); // Clear flag after 2 seconds

    // Define field mappings for both places_search.html and form.html
    const fieldMappings = {
      // Places search page field IDs (with restaurant- prefix)
      'restaurant-name': restaurantData.name,
      'restaurant-type': restaurantData.type,
      'restaurant-description': restaurantData.description,
      'restaurant-address_line_1': restaurantData.address_line_1,
      'restaurant-address_line_2': restaurantData.address_line_2,
      'restaurant-located_within': restaurantData.located_within,
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
      address_line_1: restaurantData.address_line_1,
      address_line_2: restaurantData.address_line_2,
      located_within: restaurantData.located_within,
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
    // Escape cuisine to prevent XSS
    const cuisineText = restaurantData.cuisine ? `(${this.safeHtmlEscape(restaurantData.cuisine)})` : '';
    const message = `Restaurant data loaded from Google Places! ${cuisineText}`;
    this.showSuccess(message);
  }

  showLoading(query = '') {
    // query is only used to calculate radius, never directly inserted into HTML
    // The query parameter itself is never used in any HTML context
    let locationStatus;
    if (this.userLocation) {
      // Query is only used to calculate radius (returns a number)
      const radius = this.getDynamicRadius(query);
      // radius is a number, but escape it for safety using helper method
      const escapedRadius = this.safeHtmlEscape(radius.toString());
      // Only the escaped radius (not the query) is inserted into HTML
      locationStatus = `<small class="text-success d-block mt-1"><i class="fas fa-map-marker-alt me-1"></i>Searching within ${escapedRadius} miles</small>`;
    } else if (this.locationError) {
      locationStatus = '<small class="text-muted d-block mt-1"><i class="fas fa-info-circle me-1"></i>Searching all restaurants</small>';
    } else {
      locationStatus = '<small class="text-info d-block mt-1"><i class="fas fa-spinner fa-spin me-1"></i>Getting your location...</small>';
    }

    // locationStatus is built from escaped values (radius is escaped) - safe to set innerHTML
    // Note: query parameter is never used in locationStatus
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
    // Use DOM methods to prevent XSS - createTextNode automatically escapes HTML
    const container = document.createElement('div');
    container.className = 'p-3 text-center text-danger';

    // Create icon
    const icon = document.createElement('i');
    icon.className = 'fas fa-exclamation-triangle me-2';

    // Create message text - using createTextNode automatically escapes HTML
    const messageText = document.createTextNode(message);

    // Assemble the error message
    container.appendChild(icon);
    container.appendChild(messageText);

    // Clear existing content and add error message
    this.suggestionsContainer.innerHTML = '';
    this.suggestionsContainer.appendChild(container);
    this.suggestionsContainer.style.display = 'block';
    setTimeout(() => this.hideSuggestions(), 3000);
  }

  showSuccess(message) {
    // Create a temporary success message using DOM methods to prevent XSS
    const successDiv = document.createElement('div');
    successDiv.className = 'alert alert-success alert-dismissible fade show';

    // Create icon
    const icon = document.createElement('i');
    icon.className = 'fas fa-check-circle me-2';

    // Create message text - using textContent automatically escapes HTML
    const messageText = document.createTextNode(message);

    // Create close button
    const closeButton = document.createElement('button');
    closeButton.type = 'button';
    closeButton.className = 'btn-close';
    closeButton.setAttribute('data-bs-dismiss', 'alert');
    closeButton.setAttribute('aria-label', 'Close');

    // Assemble the alert
    successDiv.appendChild(icon);
    successDiv.appendChild(messageText);
    successDiv.appendChild(closeButton);

    // Insert after the input
    this.input.parentNode.insertBefore(successDiv, this.input.nextSibling);

    // Auto-dismiss after 3 seconds
    setTimeout(() => {
      if (successDiv.parentNode) {
        successDiv.remove();
      }
    }, 3000);
  }

  showNoResultsMessage() {
    const html = `
      <div class="suggestion-item no-results">
        <div class="d-flex align-items-center p-2 text-muted">
          <i class="fas fa-search text-muted me-2"></i>
          <div class="flex-grow-1">
            <div class="fw-medium">No restaurants found</div>
            <small class="text-muted">Try a different search term or check your location permissions</small>
          </div>
        </div>
      </div>
    `;

    this.suggestionsContainer.innerHTML = html;
    this.suggestionsContainer.style.display = 'block';

    // Auto-hide after 5 seconds
    setTimeout(() => this.hideSuggestions(), 5000);
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
      new RestaurantAutocomplete(input); // eslint-disable-line no-new
      console.log('Successfully initialized autocomplete for input', index);
    } catch (error) {
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
