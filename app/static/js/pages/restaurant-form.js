/**
 * Restaurant Form - Enhanced with Google Place ID validation
 * Handles restaurant form submission and Google Places integration
 */

// Removed complex imports to avoid Chrome extension runtime conflicts
// Google Maps will be loaded directly via template script tag

// Simple state tracking
let isInitialized = false;
let addressAutocomplete = null;
let addressAutocompleteInitialized = false;

// Enhanced error recovery state
let error_recovery_initialized = false;
let google_maps_fallback_enabled = false;
const form_auto_save_enabled = true;

// DOM elements
const elements = {
  form: null,
  restaurantSearch: null,
  searchBtn: null,
  suggestions: null,
  address: null,
  googlePlaceId: null,
};

// Initialize the form
function init() {
  if (isInitialized) return;

  // Cache elements
  elements.form = document.getElementById('restaurantForm');
  elements.restaurantSearch = document.getElementById('restaurant-search');
  elements.searchBtn = document.getElementById('search-restaurant-btn');
  elements.suggestions = document.getElementById('restaurant-suggestions');
  elements.address = document.getElementById('address');
  elements.googlePlaceId = document.getElementById('google_place_id');

  if (!elements.form) return;

  // Set up event listeners
  elements.form.addEventListener('submit', handleFormSubmit);

  // Restaurant search autocomplete is now handled by restaurant-autocomplete.js
  // if (elements.restaurantSearch) {
  //   setupRestaurantAutocomplete();
  // }

  // Clear Google Place ID on manual address edit
  elements.address?.addEventListener('input', () => {
    if (elements.googlePlaceId) elements.googlePlaceId.value = '';
  });

  // Make functions available to Google Maps initialization
  console.log('Setting up restaurantFormModule...');
  window.restaurantFormModule = {
    initAddressAutocomplete: initAddressAutocompleteWithClass,
    showError,
  };
  console.log('restaurantFormModule set up and ready for Google Maps initialization');

  // Check if Google Maps is already ready and try to initialize
  if (window.googleMapsReady && window.tryInitRestaurantAutocomplete) {
    console.log('Google Maps was already ready, attempting delayed initialization...');
    if (typeof window.attemptRestaurantAutocompleteInit === 'function') {
      window.attemptRestaurantAutocompleteInit();
    }
  }

  // Set up enhanced error handling
  initialize_error_recovery_for_restaurant_form();

  // Set up global error handler for Google Maps
  window.gm_authFailure = () => {
    console.error('Google Maps authentication failed');
    handle_google_maps_auth_failure();
  };

  // Check for URL parameters and pre-fill form if coming from search
  handleUrlParameters();

  // Check for Google Places data from conflict resolution
  handleGooglePlacesDataFromConflict();

  isInitialized = true;
}

// Google Maps is now loaded with modern async pattern
// This avoids Chrome extension runtime conflicts and improves performance

// Modern async initialization with provided Autocomplete class
function initAddressAutocompleteWithClass(AutocompleteClass = null) {
  console.log('initAddressAutocompleteWithClass called with:', AutocompleteClass ? 'Provided class' : 'No class provided');
  console.log('Elements available - address:', !!elements.address, 'restaurant search:', !!elements.restaurantSearch);

  // Use provided class or fallback to global
  const AutocompleteToUse = AutocompleteClass || window.google?.maps?.places?.Autocomplete;

  if (!AutocompleteToUse) {
    console.error('No Autocomplete class available');
    showError('Google Maps Autocomplete is not available');
    return;
  }

  console.log('Using Autocomplete class:', AutocompleteToUse);

  // Initialize address autocomplete
  if (elements.address) {
    initAddressAutocompleteWithProvidedClass(AutocompleteToUse);
  }

  // Restaurant search autocomplete is now handled by restaurant-autocomplete.js
  // if (elements.restaurantSearch) {
  //   setupRestaurantAutocompleteWithProvidedClass(AutocompleteToUse);
  // }
}

// Initialize address autocomplete with provided class
function initAddressAutocompleteWithProvidedClass(AutocompleteClass) {
  console.log('Initializing address autocomplete with provided class');

  if (addressAutocompleteInitialized) {
    console.log('Address autocomplete already initialized');
    return;
  }

  addLoadingIndicator(elements.address, 'Setting up address autocomplete...');

  try {
    addressAutocomplete = new AutocompleteClass(elements.address, {
      types: ['establishment', 'geocode'],
      fields: ['place_id', 'name', 'formatted_address', 'address_components', 'geometry', 'formatted_phone_number', 'website'],
    });

    addressAutocomplete.addListener('place_changed', () => {
      const place = addressAutocomplete.getPlace();

      showAutocompleteFeedback(elements.address, 'Loading restaurant details...', 'info');

      if (!place.place_id) {
        console.warn('No place ID returned from autocomplete');
        showAutocompleteFeedback(elements.address, 'Please select a place from the suggestions', 'error');
        return;
      }

      console.log('Place selected from address autocomplete:', place);

      try {
        fillFormWithPlace(place);
        showAutocompleteFeedback(elements.address, 'Restaurant details loaded successfully!', 'success');
      } catch (error) {
        console.error('Error filling form with place data:', error);
        showAutocompleteFeedback(elements.address, 'Error loading restaurant details', 'error');
      }
    });

    removeLoadingIndicator(elements.address);
    showAutocompleteFeedback(elements.address, 'Address autocomplete ready!', 'success');
    addressAutocompleteInitialized = true;
    console.log('Address autocomplete initialized successfully');

  } catch (error) {
    console.error('Error initializing address autocomplete:', error);
    removeLoadingIndicator(elements.address);
    showAutocompleteFeedback(elements.address, 'Failed to initialize address autocomplete', 'error');
  }
}

// Old restaurant autocomplete function removed - handled by restaurant-autocomplete.js

// Initialize address autocomplete with proper error handling
function initAddressAutocomplete(AutocompleteClass = null) {
  if (addressAutocompleteInitialized) {
    console.log('Restaurant Form: Address autocomplete already initialized, skipping...');
    return;
  }

  const AutocompleteConstructor = get_autocomplete_constructor(AutocompleteClass);
  if (!AutocompleteConstructor || !elements.address) return;

  create_address_autocomplete(AutocompleteConstructor);
}

function get_autocomplete_constructor(AutocompleteClass) {
  const AutocompleteConstructor = AutocompleteClass || window.google?.maps?.places?.Autocomplete;

  if (!AutocompleteConstructor) {
    console.warn('Autocomplete class not available');
    return null;
  }

  if (!elements.address) {
    console.warn('Address input element not found');
    return null;
  }

  return AutocompleteConstructor;
}

function create_address_autocomplete(AutocompleteConstructor) {
  try {
    console.log('Initializing autocomplete for address input');

    // Add loading indicator
    addLoadingIndicator(elements.address, 'Setting up address autocomplete...');

    // Create autocomplete with minimal configuration to avoid runtime errors
    const autocomplete = new AutocompleteConstructor(elements.address, {
      types: ['establishment'],
      fields: ['place_id', 'name', 'formatted_address', 'formatted_phone_number', 'website', 'geometry', 'address_components'],
    });

    setup_address_autocomplete_listeners(autocomplete);
    finalize_address_autocomplete_setup();

  } catch (error) {
    console.error('Error initializing address autocomplete:', error);
    showError('Failed to initialize address autocomplete');
  }
}

function setup_address_autocomplete_listeners(autocomplete) {
  // Disable the default Enter key behavior
  google.maps.event.addDomListener(elements.address, 'keydown', (e) => {
    if (e.keyCode === 13) {
      e.preventDefault();
    }
  });

  // Handle place selection with error boundary
  autocomplete.addListener('place_changed', () => {
    handle_address_place_changed(autocomplete);
  });
}

function handle_address_place_changed(autocomplete) {
  try {
    const place = autocomplete.getPlace();
    console.log('Place selected:', place?.name || 'Unknown place');

    // Validate place has required data
    if (!place || !place.geometry || !place.place_id) {
      console.log('Invalid place selected - missing geometry or place_id', place);
      return;
    }

    console.log('Valid place selected, filling form...');

    // Show loading feedback
    showAutocompleteFeedback(elements.address, 'Loading restaurant details...', 'info');

    // Fill form with place data
    fillFormWithPlace(place).then(() => {
      showAutocompleteFeedback(elements.address, 'Restaurant details loaded successfully!', 'success');
    }).catch((error) => {
      console.error('Error filling form with place:', error);
      showAutocompleteFeedback(elements.address, 'Failed to load restaurant details', 'error');
    });

  } catch (error) {
    console.error('Error in place_changed listener:', error);
  }
}

function finalize_address_autocomplete_setup() {
  console.log('Address autocomplete initialized successfully');
  addressAutocompleteInitialized = true;

  // Remove loading indicator and show success
  removeLoadingIndicator(elements.address);
  showAutocompleteFeedback(elements.address, 'Address autocomplete ready! Start typing a restaurant name.', 'success');
}

// Restaurant search autocomplete is now handled by restaurant-autocomplete.js

// Handle form submission with Google Place ID validation
function handleFormSubmit(event) {
  event.preventDefault();

  const formData = new FormData(elements.form);
  const submitButton = elements.form.querySelector('button[type="submit"]');
  const originalText = submitButton.innerHTML;

  // Show loading state
  submitButton.disabled = true;
  submitButton.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Saving...';

  // Submit form
  fetch(elements.form.action, {
    method: elements.form.method || 'POST',
    body: formData,
    headers: {
      'X-Requested-With': 'XMLHttpRequest',
      'X-CSRFToken': getCSRFToken(),
    },
  })
    .then((response) => {
      if (!response.ok) {
        return response.json().then((err) => Promise.reject(err));
      }
      return response.json();
    })
    .then((data) => {
      showSuccess('Restaurant saved successfully!');
      if (data.redirect_url) {
        window.location.href = data.redirect_url;
      }
    })
    .catch((error) => {
      console.error('Error saving restaurant:', error);

      // Handle structured error responses (already parsed by .then())
      if (error && error.error) {
        if (error.error.code === 'DUPLICATE_GOOGLE_PLACE_ID') {
          handleDuplicateGooglePlaceIdError(error.error);
          return;
        } else if (error.error.code === 'DUPLICATE_RESTAURANT') {
          handleDuplicateRestaurantError(error.error);
          return;
        }
      }

      // Enhanced error message parsing
      let userMessage = error.message || error.error?.message || 'Failed to save restaurant';

      if (userMessage.includes('Google Place ID')) {
        userMessage = 'This restaurant already exists in your list. Please search for the existing restaurant or choose a different one.';
      } else if (userMessage.includes('already exists')) {
        userMessage = 'A similar restaurant already exists. Please check your existing restaurants or modify the details to make it unique.';
      }

      showError(userMessage);
    })
    .finally(() => {
      submitButton.disabled = false;
      submitButton.innerHTML = originalText;
    });
}

// Enhanced error handling functions

/**
 * Handle duplicate Google Place ID error with user-friendly modal
 */
function handleDuplicateGooglePlaceIdError(error) {
  const { existing_restaurant, google_place_id } = error;

  showDuplicateRestaurantModal({
    title: 'Restaurant Already Exists',
    message: `You already have "${existing_restaurant.full_name}" in your restaurants.`,
    details: 'This restaurant has the same Google Place ID and cannot be added again.',
    existing_restaurant,
    primaryAction: {
      label: 'View Existing Restaurant',
      url: `/restaurants/${existing_restaurant.id}`,
    },
    secondaryAction: {
      label: 'Add Expense',
      url: `/expenses/add?restaurant_id=${existing_restaurant.id}`,
    },
  });
}

/**
 * Handle duplicate restaurant (name/city) error
 */
function handleDuplicateRestaurantError(error) {
  const { existing_restaurant, name, city } = error;

  showDuplicateRestaurantModal({
    title: 'Similar Restaurant Found',
    message: `You already have a restaurant named "${name}"${city ? ` in ${city}` : ''}.`,
    details: 'This might be the same restaurant. You can view the existing one or modify your input to make it unique.',
    existing_restaurant,
    primaryAction: {
      label: 'View Existing Restaurant',
      url: `/restaurants/${existing_restaurant.id}`,
    },
    secondaryAction: {
      label: 'Continue Adding',
      action: () => showWarning('Please modify the restaurant name or location to make it unique.'),
    },
  });
}

/**
 * Show modal for duplicate restaurant conflicts
 */
function showDuplicateRestaurantModal(options) {
  const {
    title,
    message,
    details,
    existing_restaurant,
    primaryAction,
    secondaryAction,
  } = options;

  const modalHtml = `
    <div class="modal fade" id="duplicateRestaurantModal" tabindex="-1" aria-labelledby="duplicateRestaurantModalLabel" aria-hidden="true">
      <div class="modal-dialog modal-dialog-centered">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title" id="duplicateRestaurantModalLabel">
              <i class="fas fa-exclamation-triangle text-warning me-2"></i>
              ${title}
            </h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
          </div>
          <div class="modal-body">
            <div class="alert alert-warning" role="alert">
              <strong>${message}</strong>
              <br><small class="text-muted">${details}</small>
            </div>

            <div class="card mt-3">
              <div class="card-body">
                <h6 class="card-title">
                  <i class="fas fa-utensils me-2"></i>
                  ${existing_restaurant.full_name}
                </h6>
                <div class="d-flex gap-2 mt-2">
                  <a href="/restaurants/${existing_restaurant.id}" class="btn btn-sm btn-outline-primary">
                    <i class="fas fa-eye me-1"></i>
                    View Details
                  </a>
                  <a href="/expenses/add?restaurant_id=${existing_restaurant.id}" class="btn btn-sm btn-outline-success">
                    <i class="fas fa-plus me-1"></i>
                    Add Expense
                  </a>
                </div>
              </div>
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
            ${secondaryAction ? `
              <button type="button" class="btn btn-warning" id="secondaryActionBtn">
                ${secondaryAction.label}
              </button>
            ` : ''}
            <button type="button" class="btn btn-primary" id="primaryActionBtn">
              ${primaryAction.label}
            </button>
          </div>
        </div>
      </div>
    </div>
  `;

  // Remove existing modal if any
  const existingModal = document.getElementById('duplicateRestaurantModal');
  if (existingModal) {
    existingModal.remove();
  }

  // Add modal to DOM
  document.body.insertAdjacentHTML('beforeend', modalHtml);

  const modalElement = document.getElementById('duplicateRestaurantModal');

  // Add event listeners
  const primaryBtn = modalElement.querySelector('#primaryActionBtn');
  const secondaryBtn = modalElement.querySelector('#secondaryActionBtn');

  if (primaryBtn) {
    primaryBtn.addEventListener('click', () => {
      if (primaryAction.url) {
        window.location.href = primaryAction.url;
      } else if (primaryAction.action) {
        primaryAction.action();
      }
    });
  }

  if (secondaryBtn && secondaryAction) {
    secondaryBtn.addEventListener('click', () => {
      if (secondaryAction.url) {
        window.location.href = secondaryAction.url;
      } else if (secondaryAction.action) {
        secondaryAction.action();
        const bsModal = bootstrap.Modal.getInstance(modalElement);
        if (bsModal) bsModal.hide();
      }
    });
  }

  // Show modal
  const bsModal = new bootstrap.Modal(modalElement);
  bsModal.show();

  // Clean up modal after hiding
  modalElement.addEventListener('hidden.bs.modal', () => {
    modalElement.remove();
  });
}

// Legacy restaurant search functions removed - now handled by restaurant-autocomplete.js

// Fill form with place details with validation
async function fillFormWithPlace(place) {
  // Check if restaurant already exists before filling form
  const exists = await check_restaurant_exists(place.place_id);
  if (exists) return;

  const fields = extract_place_fields(place);
  populate_form_fields(fields);
  showSuccess('Restaurant details filled in from Google Places. Please review and submit.');
}

async function check_restaurant_exists(place_id) {
  if (!place_id) return false;

  try {
    const response = await fetch('/restaurants/check-restaurant-exists', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Requested-With': 'XMLHttpRequest',
        'X-CSRFToken': getCSRFToken(),
      },
      body: JSON.stringify({ google_place_id: place_id }),
    });

    if (response.ok) {
      const data = await response.json();
      if (data.exists) {
        showExistingRestaurantModal(data);
        return true;
      }
    }
  } catch (error) {
    console.error('Error checking if restaurant exists:', error);
    // Continue with form filling even if check fails
  }

  return false;
}

function extract_place_fields(place) {
  const fields = {
    name: place.name || '',
    google_place_id: place.place_id || '',
    phone: place.formatted_phone_number || '',
    website: place.website || '',
  };

  // Set coordinates
  // Note: coordinates would be looked up dynamically from Google Places API

  // Parse address components
  const address_parts = parse_address_components(place.address_components || []);
  Object.assign(fields, address_parts);

  console.log('Restaurant Form: Final fields object:', fields);
  return fields;
}

function parse_address_components(components) {
  let streetNumber = '', route = '';
  const fields = {};

  console.log('Restaurant Form: Address components received:', components);

  components.forEach((component) => {
    const { types } = component;
    console.log('Restaurant Form: Processing component:', component.long_name, 'Types:', types);

    if (types.includes('street_number')) {
      streetNumber = component.long_name;
    } else if (types.includes('route')) {
      route = component.long_name;
    } else if (types.includes('locality') || types.includes('sublocality_level_1')) {
      fields.city = component.long_name;
      console.log('Restaurant Form: Set city to:', fields.city);
    } else if (types.includes('administrative_area_level_1')) {
      fields.state = component.short_name || component.long_name;
      console.log('Restaurant Form: Set state to:', fields.state);
    } else if (types.includes('postal_code') || types.includes('postal_code_prefix')) {
      fields.postal_code = component.long_name;
      console.log('Restaurant Form: Set postal_code to:', fields.postal_code);
    } else if (types.includes('country')) {
      fields.country = component.long_name;
      console.log('Restaurant Form: Set country to:', fields.country);
    }
  });

  fields.address = [streetNumber, route].filter(Boolean).join(' ');
  return fields;
}

function populate_form_fields(fields) {
  Object.entries(fields).forEach(([id, value]) => {
    const element = document.getElementById(id);
    if (element && value) {
      element.value = value;
      // Trigger change event for any listeners
      element.dispatchEvent(new Event('change', { bubbles: true }));
    }
  });
}

// Show modal for existing restaurant
function showExistingRestaurantModal(existsData) {
  const modalHtml = `
    <div class="modal fade" id="existingRestaurantModal" tabindex="-1">
      <div class="modal-dialog">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">
              <i class="fas fa-exclamation-triangle text-warning me-2"></i>
              Restaurant Already Exists
            </h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
          </div>
          <div class="modal-body">
            <p>The restaurant "<strong>${existsData.restaurant_name}</strong>" already exists in your collection.</p>
            <p>What would you like to do?</p>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
            <a href="/restaurants/${existsData.restaurant_id}" class="btn btn-primary">
              <i class="fas fa-eye me-1"></i>View Restaurant
            </a>
            <a href="/restaurants/${existsData.restaurant_id}/edit" class="btn btn-outline-primary">
              <i class="fas fa-edit me-1"></i>Edit Restaurant
            </a>
          </div>
        </div>
      </div>
    </div>
  `;

  // Remove any existing modal
  const existingModal = document.getElementById('existingRestaurantModal');
  if (existingModal) {
    existingModal.remove();
  }

  // Add modal to body
  document.body.insertAdjacentHTML('beforeend', modalHtml);

  // Show modal
  const modal = new bootstrap.Modal(document.getElementById('existingRestaurantModal'));
  modal.show();

  // Clean up modal after hiding
  document.getElementById('existingRestaurantModal').addEventListener('hidden.bs.modal', () => {
    document.getElementById('existingRestaurantModal').remove();
  });
}

// Utility functions
function getCSRFToken() {
  return document.querySelector('meta[name="csrf-token"]')?.content || '';
}

function showSuccess(message) {
  showAlert('success', message);
}

function showError(message) {
  showAlert('danger', message);
}

function showAlert(type, message) {
  // Remove existing alerts
  document.querySelectorAll('.alert-dismissible').forEach((alert) => alert.remove());

  // Create new alert
  const alert = document.createElement('div');
  alert.className = `alert alert-${type} alert-dismissible fade show`;
  alert.innerHTML = `
    ${message}
    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
  `;

  // Insert at top of form
  const header = elements.form.querySelector('.card-header');
  if (header) {
    header.insertAdjacentElement('afterend', alert);
  } else {
    elements.form.prepend(alert);
  }
}

// Handle Google Places data from conflict resolution (stored in session storage)
function handleGooglePlacesDataFromConflict() {
  try {
    const storedData = sessionStorage.getItem('restaurantEditGooglePlacesData');
    if (!storedData) return;

    const parsedData = JSON.parse(storedData);

    // Safety: Validate data structure and expiry (5 minutes)
    if (!parsedData.googlePlacesData || !parsedData.timestamp) {
      sessionStorage.removeItem('restaurantEditGooglePlacesData');
      return;
    }

    // Check if data is expired (5 minutes)
    const dataAge = Date.now() - parsedData.timestamp;
    if (dataAge > 5 * 60 * 1000) {
      sessionStorage.removeItem('restaurantEditGooglePlacesData');
      console.log('Google Places data expired, removed from session storage');
      return;
    }

    // Check if this is the correct restaurant
    const currentUrl = window.location.pathname;
    const restaurantIdMatch = currentUrl.match(/\/restaurants\/(\d+)\/edit/);

    if (!restaurantIdMatch || parseInt(restaurantIdMatch[1]) !== parsedData.restaurantId) {
      console.log('Restaurant ID mismatch, ignoring stored Google Places data');
      return;
    }

    console.log('Found Google Places data from conflict resolution:', parsedData.googlePlacesData);

    // Populate form with Google Places data
    populateFormWithGooglePlacesData(parsedData.googlePlacesData);

    // Clear the session storage data after use
    sessionStorage.removeItem('restaurantEditGooglePlacesData');

  } catch (error) {
    console.error('Error handling Google Places data from conflict:', error);
    sessionStorage.removeItem('restaurantEditGooglePlacesData');
  }
}

/**
 * Populate form fields with Google Places data
 * @param {Object} googlePlacesData - Google Places data from conflict resolution
 */
function populateFormWithGooglePlacesData(googlePlacesData) {
  try {
    // Extract address components from Google Places data
    const addressComponents = extractAddressComponents(googlePlacesData.address_components || googlePlacesData.addressComponents || []);

    // Build form field data
    const formFields = {
      name: googlePlacesData.name || googlePlacesData.displayName?.text || '',
      google_place_id: googlePlacesData.placeId || googlePlacesData.place_id || googlePlacesData.id || '',
      phone: googlePlacesData.formatted_phone_number || googlePlacesData.nationalPhoneNumber || '',
      website: googlePlacesData.website || googlePlacesData.websiteURI || '',
      address: addressComponents.street || googlePlacesData.formatted_address || '',
      city: addressComponents.city || '',
      state: addressComponents.state || '',
      postal_code: addressComponents.postalCode || '',
      country: addressComponents.country || '',
    };

    console.log('Populating form with Google Places data:', formFields);

    // Populate form fields
    Object.entries(formFields).forEach(([fieldId, value]) => {
      if (value) {
        const element = document.getElementById(fieldId);
        if (element) {
          element.value = value;
          // Trigger change event for any listeners
          element.dispatchEvent(new Event('change', { bubbles: true }));
          console.log(`Populated ${fieldId} with: ${value}`);
        }
      }
    });

    // Show success message
    showSuccess('Form updated with Google Places data. Google Place ID and associated fields have been populated. Please review and save the changes.');

  } catch (error) {
    console.error('Error populating form with Google Places data:', error);
    showError('Error updating form with Google Places data. Please fill fields manually.');
  }
}

/**
 * Extract address components from Google Places address components array
 * @param {Array} addressComponentsArray - Array of address components from Google Places
 * @returns {Object} Extracted address components
 */
function extractAddressComponents(addressComponentsArray) {
  const addressComponents = {
    street: '',
    city: '',
    state: '',
    postalCode: '',
    country: '',
  };

  if (!Array.isArray(addressComponentsArray)) {
    return addressComponents;
  }

  let streetNumber = '';
  let route = '';

  addressComponentsArray.forEach((component) => {
    const types = component.types || [];
    const longText = component.long_name || component.longText || '';
    const shortText = component.short_name || component.shortText || '';

    if (types.includes('street_number')) {
      streetNumber = longText;
    } else if (types.includes('route')) {
      route = longText;
    } else if (types.includes('locality') || types.includes('sublocality_level_1')) {
      addressComponents.city = longText;
    } else if (types.includes('administrative_area_level_1')) {
      addressComponents.state = shortText || longText;
    } else if (types.includes('postal_code') || types.includes('postal_code_prefix')) {
      addressComponents.postalCode = longText;
    } else if (types.includes('country')) {
      addressComponents.country = longText;
    }
  });

  // Build street address from components
  addressComponents.street = [streetNumber, route].filter(Boolean).join(' ');

  return addressComponents;
}

// Handle URL parameters when redirected from search results
function handleUrlParameters() {
  const urlParams = new URLSearchParams(window.location.search);

  // Check if we have Google Place data in URL parameters
  const googlePlaceId = urlParams.get('google_place_id');
  if (googlePlaceId) {
    // Pre-fill form with URL parameters
    const fields = {
      google_place_id: googlePlaceId,
      name: urlParams.get('name') || '',
      phone: urlParams.get('phone') || '',
      website: urlParams.get('website') || '',
    };

    // Handle coordinates
    const lat = urlParams.get('lat');
    // Note: coordinates would be looked up dynamically from Google Places API

    // Handle address - if we have a formatted address, use it
    const address = urlParams.get('address');
    if (address) {
      fields.address = address;
    }

    // Update form fields
    Object.entries(fields).forEach(([id, value]) => {
      const element = document.getElementById(id);
      if (element && value) {
        element.value = value;
        // Trigger change event for any listeners
        element.dispatchEvent(new Event('change', { bubbles: true }));
      }
    });

    // Show info message that form was pre-filled
    if (Object.values(fields).some((value) => value)) {
      showSuccess('Form pre-filled with restaurant details from Google Places. Please review and complete any missing information.');

      // Clear URL parameters to keep URL clean
      window.history.replaceState({}, document.title, window.location.pathname);
    }
  }
}

// Visual feedback helper functions for autocomplete
function addLoadingIndicator(inputElement, message) {
  if (!inputElement) return;

  // Create loading indicator
  const loadingDiv = document.createElement('div');
  loadingDiv.className = 'autocomplete-loading d-flex align-items-center mt-2';
  loadingDiv.innerHTML = `
    <div class="spinner-border spinner-border-sm text-primary me-2" role="status">
      <span class="visually-hidden">Loading...</span>
    </div>
    <small class="text-muted">${message}</small>
  `;

  // Remove any existing loading indicators
  removeLoadingIndicator(inputElement);

  // Add after the input element
  inputElement.parentNode.insertBefore(loadingDiv, inputElement.nextSibling);
  inputElement._loadingIndicator = loadingDiv;
}

function removeLoadingIndicator(inputElement) {
  if (inputElement && inputElement._loadingIndicator) {
    inputElement._loadingIndicator.remove();
    inputElement._loadingIndicator = null;
  }
}

function showAutocompleteFeedback(inputElement, message, type = 'info') {
  if (!inputElement) return;

  const feedbackDiv = document.createElement('div');
  const alertClass = type === 'success' ? 'alert-success' : type === 'error' ? 'alert-danger' : 'alert-info';
  feedbackDiv.className = `alert ${alertClass} alert-dismissible fade show mt-2`;
  feedbackDiv.innerHTML = `
    <small>${message}</small>
    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
  `;

  // Remove any existing feedback
  removeAutocompleteFeedback(inputElement);

  // Add after the input element
  inputElement.parentNode.insertBefore(feedbackDiv, inputElement.nextSibling);
  inputElement._feedbackIndicator = feedbackDiv;

  // Auto-hide success messages after 3 seconds
  if (type === 'success') {
    setTimeout(() => {
      removeAutocompleteFeedback(inputElement);
    }, 3000);
  }
}

function removeAutocompleteFeedback(inputElement) {
  if (inputElement && inputElement._feedbackIndicator) {
    inputElement._feedbackIndicator.remove();
    inputElement._feedbackIndicator = null;
  }
}

// Enhanced Error Recovery Functions
function initialize_error_recovery_for_restaurant_form() {
  if (error_recovery_initialized) return;

  console.log('Initializing enhanced error recovery for restaurant form');

  // Set up form auto-save
  if (form_auto_save_enabled && elements.form) {
    setup_form_auto_save();
  }

  // Set up connection monitoring
  setup_connection_monitoring();

  // Set up Google Maps fallback detection
  setup_google_maps_fallback();

  error_recovery_initialized = true;
}

function setup_form_auto_save() {
  const AUTOSAVE_INTERVAL_MS = 30000; // 30 seconds
  const AUTOSAVE_KEY = 'restaurant_form_autosave';

  // Load saved data on page load
  try {
    const saved_data = localStorage.getItem(AUTOSAVE_KEY);
    if (saved_data) {
      const parsed_data = JSON.parse(saved_data);
      if (Date.now() - parsed_data.timestamp < 24 * 60 * 60 * 1000) { // 24 hours
        restore_form_data(parsed_data.data);
        showSuccess('Restored previously saved form data');
      }
    }
  } catch (error) {
    console.warn('Failed to load autosaved form data:', error);
  }

  // Auto-save form data periodically
  setInterval(() => {
    if (elements.form && has_form_data()) {
      try {
        const form_data = get_form_data();
        const save_data = {
          data: form_data,
          timestamp: Date.now(),
        };
        localStorage.setItem(AUTOSAVE_KEY, JSON.stringify(save_data));
        console.log('Form data auto-saved');
      } catch (error) {
        console.warn('Failed to auto-save form data:', error);
      }
    }
  }, AUTOSAVE_INTERVAL_MS);

  // Clear auto-save on successful submission
  elements.form.addEventListener('submit', () => {
    try {
      localStorage.removeItem(AUTOSAVE_KEY);
    } catch (error) {
      console.warn('Failed to clear auto-save data:', error);
    }
  });
}

function setup_connection_monitoring() {
  // Monitor online/offline status
  window.addEventListener('online', () => {
    console.log('Connection restored');
    showSuccess('Connection restored! You can now submit the form.');

    // Re-enable form submission
    if (elements.form) {
      const submit_button = elements.form.querySelector('button[type="submit"]');
      if (submit_button) {
        submit_button.disabled = false;
        submit_button.textContent = 'Save Restaurant';
      }
    }

    // Retry any offline submissions
    retry_offline_submissions();
  });

  window.addEventListener('offline', () => {
    console.log('Connection lost');
    showWarning('Connection lost. Form data will be saved automatically.');

    // Disable form submission but keep form functional
    if (elements.form) {
      const submit_button = elements.form.querySelector('button[type="submit"]');
      if (submit_button) {
        submit_button.disabled = true;
        submit_button.textContent = 'Offline - Data Saved';
      }
    }
  });
}

function setup_google_maps_fallback() {
  // Monitor for Google Maps failures and provide fallbacks
  let maps_load_timeout;

  const MAPS_LOAD_TIMEOUT_MS = 15000; // 15 seconds

  // Set timeout for Google Maps loading
  maps_load_timeout = setTimeout(() => {
    if (!window.google?.maps?.places) {
      console.warn('Google Maps failed to load within timeout, enabling fallback');
      enable_google_maps_fallback();
    }
  }, MAPS_LOAD_TIMEOUT_MS);

  // Clear timeout if Google Maps loads successfully
  const check_maps_loaded = () => {
    if (window.google?.maps?.places) {
      clearTimeout(maps_load_timeout);
      console.log('Google Maps loaded successfully');
    }
  };

  // Check periodically
  const check_interval = setInterval(() => {
    check_maps_loaded();
    if (window.google?.maps?.places || google_maps_fallback_enabled) {
      clearInterval(check_interval);
    }
  }, 1000);
}

function enable_google_maps_fallback() {
  if (google_maps_fallback_enabled) return;

  google_maps_fallback_enabled = true;

  showWarning('Map services are unavailable. You can still add restaurants manually.');

  // Enable manual address entry with enhanced UX
  if (elements.address) {
    elements.address.placeholder = 'Enter address manually (autocomplete unavailable)';
    elements.address.style.borderColor = '#ffc107'; // Warning color

    // Add helpful text
    const help_text = document.createElement('small');
    help_text.className = 'form-text text-warning';
    help_text.textContent = 'Autocomplete is unavailable. Please enter the address manually.';
    elements.address.parentNode.appendChild(help_text);
  }

  // Hide restaurant search if it depends on Google Maps
  if (elements.restaurantSearch) {
    const search_section = elements.restaurantSearch.closest('.form-section');
    if (search_section) {
      search_section.style.opacity = '0.5';
      search_section.style.pointerEvents = 'none';

      const fallback_text = document.createElement('div');
      fallback_text.className = 'alert alert-warning mt-2';
      fallback_text.innerHTML = '<i class="fas fa-exclamation-triangle me-2"></i>Restaurant search is temporarily unavailable. Please fill in details manually.';
      search_section.appendChild(fallback_text);
    }
  }

  // Provide alternative geocoding hint
  add_manual_geocoding_help();
}

function add_manual_geocoding_help() {
  if (!elements.form) return;

  const coordinate_help = document.createElement('div');
  coordinate_help.className = 'alert alert-info mt-3';
  // Note: coordinate help removed - coordinates are looked up dynamically from Google Places API

  // Insert before form buttons
  const form_actions = elements.form.querySelector('.d-flex.justify-content-between');
  if (form_actions) {
    form_actions.parentNode.insertBefore(coordinate_help, form_actions);
  }
}

function handle_google_maps_auth_failure() {
  console.error('Google Maps authentication failed');

  showError('Map services authentication failed. Please contact support if this persists.');

  // Enable fallback immediately
  enable_google_maps_fallback();

  // Report the issue (if analytics available)
  if (window.gtag) {
    window.gtag('event', 'google_maps_auth_failure', {
      event_category: 'error',
      event_label: 'google_maps_api_key_invalid',
    });
  }
}

function has_form_data() {
  if (!elements.form) return false;

  const inputs = elements.form.querySelectorAll('input[type="text"], input[type="tel"], input[type="url"], textarea, select');

  for (const input of inputs) {
    if (input.value && input.value.trim().length > 0) {
      return true;
    }
  }

  return false;
}

function get_form_data() {
  if (!elements.form) return {};

  const form_data = {};
  const inputs = elements.form.querySelectorAll('input, textarea, select');

  inputs.forEach((input) => {
    if (input.name) {
      form_data[input.name] = input.value;
    }
  });

  return form_data;
}

function restore_form_data(saved_data) {
  if (!elements.form || !saved_data) return;

  Object.entries(saved_data).forEach(([name, value]) => {
    const input = elements.form.querySelector(`[name="${name}"]`);
    if (input && !input.value) { // Only restore if field is empty
      input.value = value;
    }
  });
}

function getCsrfToken() {
  return document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';
}

// Enhanced form submission with retry and offline support
async function submit_form_with_enhanced_recovery(form_data) {
  const MAX_RETRY_ATTEMPTS = 3;
  const RETRY_DELAY_MS = 2000;

  for (let attempt = 1; attempt <= MAX_RETRY_ATTEMPTS; attempt++) {
    try {
      console.log(`Form submission attempt ${attempt}/${MAX_RETRY_ATTEMPTS}`);

      // Check if online
      if (!navigator.onLine) {
        // Save for later submission
        save_form_for_offline_submission(form_data);
        return { offline_saved: true };
      }

      // Create timeout controller
      const controller = new AbortController();
      const timeout_id = setTimeout(() => controller.abort(), 15000); // 15 second timeout

      const response = await fetch(elements.form.action, {
        method: elements.form.method || 'POST',
        body: form_data,
        headers: {
          'X-Requested-With': 'XMLHttpRequest',
          'X-CSRFToken': getCsrfToken(),
        },
        signal: controller.signal,
      });

      clearTimeout(timeout_id);

      if (!response.ok) {
        const error_data = await response.json().catch(() => ({}));
        throw new Error(error_data.message || `Server error: ${response.status}`);
      }

      const result = await response.json();
      console.log('Form submitted successfully');

      // Clear any saved offline data on successful submission
      try {
        localStorage.removeItem('restaurant_form_autosave');
        localStorage.removeItem('restaurant_form_offline_submissions');
      } catch (error) {
        console.warn('Failed to clear saved form data:', error);
      }

      return result;

    } catch (error) {
      console.warn(`Submission attempt ${attempt} failed:`, error.message);

      if (attempt === MAX_RETRY_ATTEMPTS) {
        // Final attempt failed
        if (error.name === 'AbortError') {
          showError('Request timed out. Your data has been saved and you can try again.');
          save_form_for_offline_submission(form_data);
        } else if (error.message.includes('NetworkError') || error.message.includes('fetch')) {
          showError('Network error. Your data has been saved for when connection is restored.');
          save_form_for_offline_submission(form_data);
        } else {
          showError(`Submission failed: ${error.message}`);
        }

        throw error;
      } else {
        // Wait before retrying with exponential backoff
        await new Promise((resolve) => setTimeout(resolve, RETRY_DELAY_MS * attempt));
      }
    }
  }
}

function save_form_for_offline_submission(form_data) {
  try {
    const offline_key = 'restaurant_form_offline_submissions';
    const stored_submissions = JSON.parse(localStorage.getItem(offline_key) || '[]');

    // Convert FormData to object for storage
    let data_object = {};
    if (form_data instanceof FormData) {
      for (const [key, value] of form_data.entries()) {
        data_object[key] = value;
      }
    } else {
      data_object = form_data;
    }

    stored_submissions.push({
      data: data_object,
      timestamp: Date.now(),
      endpoint: elements.form?.action || window.location.pathname,
    });

    localStorage.setItem(offline_key, JSON.stringify(stored_submissions));
    console.log('Form saved for offline submission');
  } catch (error) {
    console.error('Failed to save form for offline submission:', error);
  }
}

// Function to retry offline submissions when connection is restored
async function retry_offline_submissions() {
  if (!navigator.onLine) return;

  try {
    const offline_key = 'restaurant_form_offline_submissions';
    const stored_submissions = JSON.parse(localStorage.getItem(offline_key) || '[]');

    if (stored_submissions.length === 0) return;

    console.log(`Retrying ${stored_submissions.length} offline submissions`);

    for (let i = 0; i < stored_submissions.length; i++) {
      const submission = stored_submissions[i];

      try {
        // Convert back to FormData
        const form_data = new FormData();
        Object.entries(submission.data).forEach(([key, value]) => {
          form_data.append(key, value);
        });

        const response = await fetch(submission.endpoint, {
          method: 'POST',
          body: form_data,
          headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': getCsrfToken(),
          },
        });

        if (response.ok) {
          console.log(`Successfully submitted offline form ${i + 1}`);
          showSuccess('Offline form submitted successfully!');
        } else {
          console.warn(`Failed to submit offline form ${i + 1}: ${response.status}`);
        }

      } catch (error) {
        console.warn(`Error submitting offline form ${i + 1}:`, error);
        // Keep this submission for next retry
        continue;
      }
    }

    // Clear successfully submitted forms
    localStorage.removeItem(offline_key);

  } catch (error) {
    console.error('Error retrying offline submissions:', error);
  }
}

// Export
export { init };
export default { init };
