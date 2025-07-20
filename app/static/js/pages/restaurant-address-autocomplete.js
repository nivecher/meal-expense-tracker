/**
 * Restaurant Address Autocomplete Module
 * Handles address autocomplete functionality using Google Places API
 *
 * @module restaurantAddressAutocomplete
 */

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
      country: null
    }
  };

  /**
   * Initialize the address autocomplete functionality
   * @public
   */
  function init() {
    try {
      cacheElements();
      setupEventListeners();
      console.log('Restaurant address autocomplete initialized');
    } catch (error) {
      console.error('Error initializing address autocomplete:', error);
    }
  }

  /**
   * Cache DOM elements
   * @private
   */
  function cacheElements() {
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
      country: document.getElementById(state.autocompleteInput.dataset.countryField || 'country')
    };
  }

  /**
   * Set up event listeners
   * @private
   */
  function setupEventListeners() {
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
   * @param {Event} event - The input event
   */
  async function handleAddressInput(event) {
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
  function renderSuggestions(suggestions) {
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
        ${suggestions.map(suggestion => `
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
  function handleSuggestionClick(event) {
    const suggestionItem = event.target.closest('.list-group-item-action');
    if (!suggestionItem) return;

    state.selectedPlaceId = suggestionItem.dataset.placeId;
    const description = suggestionItem.textContent.trim();

    if (state.autocompleteInput) {
      state.autocompleteInput.value = description;
    }

    if (state.suggestionsDiv) {
      state.suggestionsDiv.innerHTML = '';
    }

    if (state.updateAddressBtn) {
      state.updateAddressBtn.disabled = false;
    }

    showSuccess('Address selected');
  }

  /**
   * Handle update address button click
   * @private
   */
  async function handleUpdateAddress() {
    if (!state.selectedPlaceId) return;

    showLoading('Validating address...');

    try {
      const response = await fetch(`/api/place-details?place_id=${encodeURIComponent(state.selectedPlaceId)}`);
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || 'Failed to fetch place details');
      }

      updateFormFields(data);
      showSuccess('Address populated');

      if (state.updateAddressBtn) {
        state.updateAddressBtn.disabled = true;
      }

      state.selectedPlaceId = null;
    } catch (error) {
      console.error('Error fetching place details:', error);
      showError(error.message);
    }
  }

  /**
   * Update form fields with address data
   * @private
   * @param {Object} data - Place details data
   */
  function updateFormFields(data) {
    const { address_components: components } = data;
    const address = {
      streetNumber: '',
      route: '',
      city: '',
      state: '',
      postalCode: '',
      country: ''
    };

    // Parse address components
    components.forEach(component => {
      const types = component.types;
      if (types.includes('street_number')) {
        address.streetNumber = component.long_name;
      } else if (types.includes('route')) {
        address.route = component.long_name;
      } else if (types.includes('locality') || types.includes('postal_town')) {
        address.city = component.long_name;
      } else if (types.includes('administrative_area_level_1')) {
        address.state = component.short_name;
      } else if (types.includes('postal_code')) {
        address.postalCode = component.long_name;
      } else if (types.includes('country')) {
        address.country = component.long_name;
      }
    });

    // Update form fields
    if (state.formFields.address) {
      state.formFields.address.value = [address.streetNumber, address.route]
        .filter(Boolean)
        .join(' ')
        .trim();
    }
    if (state.formFields.city) state.formFields.city.value = address.city;
    if (state.formFields.state) state.formFields.state.value = address.state;
    if (state.formFields.postalCode) state.formFields.postalCode.value = address.postalCode;
    if (state.formFields.country) state.formFields.country.value = address.country;
  }

  /**
   * Show loading state
   * @private
   * @param {string} message - Loading message
   */
  function showLoading(message) {
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
  function showSuccess(message) {
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
  function showError(message) {
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
  function escapeHtml(unsafe) {
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
    init
  };
})();

// Initialize when DOM is loaded
if (typeof document !== 'undefined') {
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      restaurantAddressAutocomplete.init();
    });
  } else {
    restaurantAddressAutocomplete.init();
  }
}
