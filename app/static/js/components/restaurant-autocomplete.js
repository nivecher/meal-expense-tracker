/**
 * Restaurant Autocomplete
 *
 * Simple, clean autocomplete for restaurant search using our backend API
 *
 * Flow: Type restaurant name → Get suggestions → Select restaurant → Populate form
 */

import { cuisineService } from '../services/cuisine-service.js';

// Debug: Check if cuisine service is loaded
console.log('Cuisine service loaded:', cuisineService);

class RestaurantAutocomplete {
  constructor(inputElement) {
    console.log('RestaurantAutocomplete constructor called with:', inputElement);
    this.input = inputElement;
    this.suggestionsContainer = null;
    this.selectedIndex = -1;
    this.suggestions = [];
    this.init();
  }

  init() {
    console.log('RestaurantAutocomplete init() called');
    this.createSuggestionsContainer();
    this.setupEventListeners();
    this.populateCuisineFilter();
    console.log('RestaurantAutocomplete initialization complete');
  }

  async populateCuisineFilter() {
    const cuisineFilter = document.getElementById('cuisine-filter');
    if (!cuisineFilter) {
      // No cuisine filter element found - this is normal for restaurant forms
      return;
    }

    try {
      const cuisineData = await cuisineService.loadCuisineData();
      const cuisineNames = cuisineService.getCuisineNames();

      // Clear existing options except "All Cuisines"
      cuisineFilter.innerHTML = '<option value="">All Cuisines</option>';

      // Add cuisine options
      cuisineNames.forEach(name => {
        const option = document.createElement('option');
        option.value = name.toLowerCase();
        option.textContent = name;
        cuisineFilter.appendChild(option);
      });
    } catch (error) {
      console.error('Failed to populate cuisine filter:', error);
    }
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
      this.showLoading();
      const suggestions = await this.getSuggestions(query);
      console.log('Got suggestions:', suggestions);
      this.showSuggestions(suggestions);
    } catch (error) {
      console.error('Error getting suggestions:', error);
      this.showError('Failed to get suggestions');
    }
  }

  async getSuggestions(query) {
    try {
      // Build query parameters
      const params = new URLSearchParams({
        query: query
      });

      const response = await fetch(`/restaurants/api/places/search?${params.toString()}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();

      if (data.error) {
        throw new Error(data.error);
      }

      // Backend returns { data: { results: [...] } } for places search.
      // Normalize to a lightweight suggestions list expected by the UI.
      const results = (data && data.data && Array.isArray(data.data.results)) ? data.data.results : [];
      const suggestions = results.map((place) => ({
        placeId: place.place_id || place.placeId || '',
        title: place.name || place.title || '',
        description: place.formatted_address || place.vicinity || place.address || '',
      })).filter(s => s.placeId && s.title);

      return suggestions;
    } catch (error) {
      throw new Error(`Search error: ${error.message}`);
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
          <div>
            <div class="fw-medium">${suggestion.title}</div>
            <small class="text-muted">${suggestion.description}</small>
          </div>
        </div>
      </div>
    `).join('');

    this.suggestionsContainer.innerHTML = html;
    this.suggestionsContainer.style.display = 'block';

    // Add click handlers
    this.suggestionsContainer.querySelectorAll('.suggestion-item').forEach(item => {
      item.addEventListener('click', () => {
        const placeId = item.dataset.placeId;
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
    this.suggestionsContainer.querySelectorAll('.suggestion-item').forEach(item => {
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
      const placeId = this.suggestions[this.selectedIndex].placeId;
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
          'Content-Type': 'application/json'
        }
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
        place_id: placeId
      };
    } catch (error) {
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
      'restaurant-is-chain': restaurantData.is_chain,
      'restaurant-rating': restaurantData.rating,
      'restaurant-notes': restaurantData.notes,

      // Restaurant form field IDs (without prefix)
      'name': restaurantData.name,
      'type': restaurantData.type,
      'description': restaurantData.description,
      'address': restaurantData.address,
      'city': restaurantData.city,
      'state': restaurantData.state,
      'postal_code': restaurantData.postal_code,
      'country': restaurantData.country,
      'phone': restaurantData.phone,
      'website': restaurantData.website,
      'email': restaurantData.email,
      'google_place_id': restaurantData.google_place_id,
      'cuisine': restaurantData.cuisine,
      'service_level': restaurantData.service_level,
      'is_chain': restaurantData.is_chain,
      'rating': restaurantData.rating,
      'notes': restaurantData.notes
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

        // Handle different field types
        if (field.type === 'checkbox') {
          field.checked = Boolean(value);
        } else if (field.type === 'select-one') {
          // For select fields, try to find matching option
          const option = Array.from(field.options).find(opt =>
            opt.value === value || opt.text.toLowerCase() === String(value).toLowerCase()
          );
          if (option) {
            field.value = option.value;
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

  showLoading() {
    this.suggestionsContainer.innerHTML = `
      <div class="p-3 text-center">
        <div class="spinner-border spinner-border-sm text-primary" role="status">
          <span class="visually-hidden">Loading...</span>
        </div>
        <span class="ms-2">Loading...</span>
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
