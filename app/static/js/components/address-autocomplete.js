/**
 * Address Autocomplete Component
 *
 * Provides Google Places Autocomplete functionality for address fields
 * Automatically populates related fields when an address is selected
 */

export class AddressAutocomplete {
  constructor(options = {}) {
    this.options = {
      inputId: 'address',
      streetNumberId: 'street_number',
      streetNameId: 'route',
      cityId: 'city',
      stateId: 'state',
      postalCodeId: 'postal_code',
      countryId: 'country',
      placeId: 'google_place_id',
      latId: 'latitude',
      lngId: 'longitude',
      ...options
    };

    this.autocomplete = null;
    this.place = null;
    this.initialized = false;
  }

  /**
   * Initialize the address autocomplete
   * @param {google.maps.places.Autocomplete} autocompleteService - Google Maps Autocomplete service
   */
  init(autocompleteService) {
    if (this.initialized) return;

    const input = document.getElementById(this.options.inputId);
    if (!input) {
      console.error('Address input element not found');
      return;
    }

    // Create the autocomplete object
    this.autocomplete = new google.maps.places.Autocomplete(input, {
      types: ['address'],
      componentRestrictions: { country: 'us' },
      fields: ['address_components', 'geometry', 'name', 'place_id', 'formatted_address']
    });

    // When a place is selected
    this.autocomplete.addListener('place_changed', () => {
      this.onPlaceChanged();
    });

    // Handle form submission to prevent submission on Enter in the autocomplete
    const form = input.closest('form');
    if (form) {
      form.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && document.activeElement === input) {
          e.preventDefault();
          return false;
        }
      });
    }

    this.initialized = true;
  }

  /**
   * Handle place selection
   */
  onPlaceChanged() {
    this.place = this.autocomplete.getPlace();

    if (!this.place.geometry) {
      // User entered the name of a Place that was not suggested and
      // pressed the Enter key, or the Place Details request failed.
      console.log("No details available for input: '" + this.place.name + "'");
      return;
    }

    // Fill in the form fields
    this.fillInAddress();
  }

  /**
   * Fill in the address fields based on the place details
   */
  fillInAddress() {
    if (!this.place) return;

    // Get the address components
    const addressComponents = {
      street_number: '',
      route: '',
      locality: '', // city
      administrative_area_level_1: '', // state
      country: '',
      postal_code: ''
    };

    // Extract address components
    for (const component of this.place.address_components) {
      const addressType = component.types[0];
      if (addressComponents.hasOwnProperty(addressType)) {
        addressComponents[addressType] = component.long_name;
      }
    }

    // Update form fields
    this.setValue(this.options.streetNumberId, addressComponents.street_number || '');
    this.setValue(this.options.streetNameId, addressComponents.route || '');
    this.setValue(this.options.cityId, addressComponents.locality || '');
    this.setValue(this.options.stateId, addressComponents.administrative_area_level_1 || '');
    this.setValue(this.options.countryId, addressComponents.country || '');
    this.setValue(this.options.postalCodeId, addressComponents.postal_code || '');

    // Set the place ID and coordinates
    this.setValue(this.options.placeId, this.place.place_id || '');

    if (this.place.geometry?.location) {
      this.setValue(this.options.latId, this.place.geometry.location.lat() || '');
      this.setValue(this.options.lngId, this.place.geometry.location.lng() || '');
    }

    // If this is a restaurant form, try to set the name
    const nameInput = document.getElementById('name');
    if (nameInput && this.place.name && !nameInput.value) {
      nameInput.value = this.place.name;
    }
  }

  /**
   * Helper function to set a form field value
   * @param {string} id - The ID of the form field
   * @param {string} value - The value to set
   */
  setValue(id, value) {
    const element = document.getElementById(id);
    if (element) {
      element.value = value;
      // Trigger change event for any listeners
      const event = new Event('change', { bubbles: true });
      element.dispatchEvent(event);
    }
  }
}
