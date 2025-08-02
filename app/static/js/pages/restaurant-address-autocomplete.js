/**
 * Restaurant Address Autocomplete Module
 * Handles address autocomplete functionality using Google Places API
 *
 * @module restaurantAddressAutocomplete
 */

import GoogleMapsLoader from '../utils/google-maps-loader.js';

const restaurantAddressAutocomplete = (() => {
  // Module state
  const state = {
    selectedPlaceId: null,
    autocompleteInput: null,
    suggestionsDiv: null,
    validIndicator: null,
    updateAddressBtn: null,
    formFields: {
      address: null,
      city: null,
      state: null,
      postalCode: null,
      country: null,
    },
  };

  /**
   * Initialize the address autocomplete functionality
   * @public
   */
  async function init () {
    try {
      cacheElements();

      // Only proceed if we have the required elements
      if (!state.autocompleteInput) return;

      // Load Google Maps API first
      try {
        const google = await GoogleMapsLoader.loadApi(window.GOOGLE_MAPS_API_KEY, ['places', 'geocoding']);
        window.google = google;
        setupEventListeners();
        console.log('Restaurant address autocomplete initialized with Google Maps API');
      } catch (error) {
        console.error('Failed to load Google Maps API:', error);
        showError('Failed to load address autocomplete. Please refresh the page and try again.');
      }
    } catch (error) {
      console.error('Error initializing address autocomplete:', error);
      showError('An error occurred while initializing address autocomplete.');
    }
  }

  /**
   * Cache DOM elements
   * @private
   */
  function cacheElements () {
    state.autocompleteInput = document.getElementById('address-autocomplete');
    if (!state.autocompleteInput) return;

    state.suggestionsDiv = document.getElementById('address-suggestions');
    state.validIndicator = document.getElementById('address-valid-indicator');
    state.updateAddressBtn = document.getElementById('update-address-btn');

    // Get field mappings from data attributes
    state.formFields = {
      address: document.getElementById(state.autocompleteInput.dataset.addressField || 'address'),
      city: document.getElementById(state.autocompleteInput.dataset.cityField || 'city'),
      state: document.getElementById(state.autocompleteInput.dataset.stateField || 'state'),
      postalCode: document.getElementById(state.autocompleteInput.dataset.postalCodeField || 'postal_code'),
      country: document.getElementById(state.autocompleteInput.dataset.countryField || 'country'),
    };
  }

  /**
   * Set up event listeners
   * @private
   */
  function setupEventListeners () {
    if (!state.autocompleteInput) return;

    // Input event for address autocomplete
    state.autocompleteInput.addEventListener('input', handleAddressInput);

    // Click event for address suggestions
    if (state.suggestionsDiv) {
      state.suggestionsDiv.addEventListener('click', handleSuggestionClick);
    }

    // Click event for update address button
    if (state.updateAddressBtn) {
      state.updateAddressBtn.addEventListener('click', handleUpdateAddress);
    }
  }

  /**
   * Handle address input for autocomplete
   * @private
   * @param {Event} _event - The input event (unused)
   */
  async function handleAddressInput (_event) {
    const query = state.autocompleteInput.value.trim();
    state.selectedPlaceId = null;

    if (state.updateAddressBtn) {
      state.updateAddressBtn.disabled = true;
    }

    if (state.validIndicator) {
      state.validIndicator.innerHTML = '';
    }

    if (query.length < 3) {
      if (state.suggestionsDiv) {
        state.suggestionsDiv.innerHTML = '';
      }
      return;
    }

    try {
      const response = await fetch(`/api/v1/address-autocomplete?query=${encodeURIComponent(query)}`);
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || 'Failed to fetch address suggestions');
      }

      renderSuggestions(data);
    } catch (error) {
      console.error('Error fetching address suggestions:', error);
      showError(error.message);
    }
  }

  /**
   * Render address suggestions
   * @private
   * @param {Array} suggestions - Array of address suggestions
   */
  function renderSuggestions (suggestions) {
    if (!state.suggestionsDiv) return;

    if (!suggestions || suggestions.length === 0) {
      state.suggestionsDiv.innerHTML = `
        <div class="list-group">
          <div class="list-group-item">No suggestions found</div>
        </div>
      `;
      return;
    }

    const suggestionsHTML = `
      <div class="list-group">
        ${suggestions.map((suggestion) => `
          <div class="list-group-item list-group-item-action"
               data-place-id="${suggestion.place_id}">
            ${escapeHtml(suggestion.description)}
          </div>
        `).join('')}
      </div>
    `;

    state.suggestionsDiv.innerHTML = suggestionsHTML;
  }

  /**
   * Handle click on address suggestion
   * @private
   * @param {Event} event - The click event
   */
  async function handleSuggestionClick (event) {
    try {
      const suggestion = event.target.closest('.suggestion-item');
      if (!suggestion) return;

      const { placeId } = suggestion.dataset;
      const description = suggestion.textContent.trim();

      if (placeId && state.autocompleteInput) {
        state.autocompleteInput.value = description;
        state.selectedPlaceId = placeId;

        // Clear suggestions
        if (state.suggestionsDiv) {
          state.suggestionsDiv.innerHTML = '';
        }

        // Automatically update the address fields
        await handleUpdateAddress();
      }
    } catch (error) {
      console.error('Error handling suggestion click:', error);
      showError(`Failed to load address: ${error.message}`);

      // Re-enable the update button if it exists
      if (state.updateAddressBtn) {
        state.updateAddressBtn.disabled = false;
      }
    }
  }

  /**
   * Handle update address button click
   * @private
   */
  async function handleUpdateAddress () {
    // If no place is selected but we have an input value, try to find a place ID
    if (!state.selectedPlaceId && state.autocompleteInput && state.autocompleteInput.value.trim()) {
      const query = state.autocompleteInput.value.trim();
      const response = await fetch(`/api/v1/address-autocomplete?query=${encodeURIComponent(query)}`);
      const suggestions = await response.json();

      if (suggestions && suggestions.length > 0) {
        state.selectedPlaceId = suggestions[0].place_id;
      }
    }

    if (!state.selectedPlaceId) {
      showError('Please select an address from the suggestions');
      return;
    }

    showLoading('Fetching address details...');

    try {
      const response = await fetch(`/api/v1/place-details?place_id=${encodeURIComponent(state.selectedPlaceId)}`);
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || 'Failed to fetch place details');
      }

      updateFormFields(data);
      showSuccess('Address populated');

      if (state.updateAddressBtn) {
        state.updateAddressBtn.disabled = true;
      }
    } catch (error) {
      console.error('Error fetching place details:', error);
      showError(error.message);
    }
  }

  /**
   * Update form fields with address data from Google Places
   * @private
   * @param {Object} data - Place details data from Google Places API
   */
  function updateFormFields (data) {
    const { address_components: components, name, geometry } = data;
    const address = {
      streetNumber: '',
      route: '',
      city: '',
      state: '',
      postalCode: '',
      country: '',
    };

    // Parse address components
    if (components && Array.isArray(components)) {
      components.forEach((component) => {
        const types = component.types || [];
        if (types.includes('street_number')) {
          address.streetNumber = component.long_name || '';
        } else if (types.includes('route')) {
          address.route = component.long_name || '';
        } else if (types.includes('locality') || types.includes('postal_town')) {
          address.city = component.long_name || '';
        } else if (types.includes('administrative_area_level_1')) {
          address.state = component.short_name || '';
        } else if (types.includes('postal_code')) {
          address.postalCode = component.long_name || '';
        } else if (types.includes('country')) {
          address.country = component.long_name || '';
        }
      });
    }

    // Update restaurant name if empty
    const nameField = document.getElementById('name');
    if (nameField && !nameField.value && name) {
      nameField.value = name;
    }

    // Update address fields
    if (state.formFields.address) {
      state.formFields.address.value = [address.streetNumber, address.route]
        .filter(Boolean)
        .join(' ')
        .trim();
    }

    // Update other address fields
    if (state.formFields.city) state.formFields.city.value = address.city;
    if (state.formFields.state) state.formFields.state.value = address.state;
    if (state.formFields.postalCode) state.formFields.postalCode.value = address.postalCode;
    if (state.formFields.country) state.formFields.country.value = address.country;

    // Update hidden fields for Google Places data
    const googlePlaceIdField = document.getElementById('google_place_id');
    const latitudeField = document.getElementById('latitude');
    const longitudeField = document.getElementById('longitude');

    // Update Google Place ID if available
    if (googlePlaceIdField) {
      googlePlaceIdField.value = data.place_id || '';
    }

    // Update coordinates if available
    if (geometry?.location) {
      if (latitudeField && geometry.location.lat) {
        latitudeField.value = geometry.location.lat;
      }
      if (longitudeField && geometry.location.lng) {
        longitudeField.value = geometry.location.lng;
      }
    }

    // Enable the Update button
    if (state.updateAddressBtn) {
      state.updateAddressBtn.disabled = false;
      state.updateAddressBtn.classList.remove('btn-outline-secondary');
      state.updateAddressBtn.classList.add('btn-outline-success');
    }
  }

  /**
   * Show loading state
   * @private
   * @param {string} message - Loading message
   */
  function showLoading (message) {
    if (!state.validIndicator) return;
    state.validIndicator.innerHTML = `
      <div class="text-info">
        <span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
        ${escapeHtml(message)}
      </div>
    `;
  }

  /**
   * Show success message
   * @private
   * @param {string} message - Success message
   */
  function showSuccess (message) {
    if (!state.validIndicator) return;
    state.validIndicator.innerHTML = `
      <div class="text-success">
        <i class="fas fa-check-circle me-1"></i>
        ${escapeHtml(message)}
      </div>
    `;
  }

  /**
   * Show error message
   * @private
   * @param {string} message - Error message
   */
  function showError (message) {
    if (!state.validIndicator) return;
    state.validIndicator.innerHTML = `
      <div class="alert alert-danger alert-dismissible fade show" role="alert">
        <i class="fas fa-exclamation-circle me-1"></i>
        ${escapeHtml(message)}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
      </div>
    `;
  }

  /**
   * Escape HTML special characters
   * @private
   * @param {string} unsafe - Unsafe string
   * @returns {string} Escaped string
   */
  function escapeHtml (unsafe) {
    if (typeof unsafe !== 'string') return '';
    return unsafe
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  // Public API
  return {
    init,
  };
})();

// Export the public API
export const { init } = restaurantAddressAutocomplete;
