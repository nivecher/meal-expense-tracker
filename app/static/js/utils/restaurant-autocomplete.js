/**
 * Restaurant Autocomplete - Clean TIGER-compliant version
 * Simple, focused autocomplete for restaurant search field
 */

// Import cuisine formatting utilities
import { mapPlaceTypesToRestaurant } from './cuisine-formatter.js';

// Global state
let search_input = null;
let suggestions_container = null;
let search_timeout = null;
let current_request_id = 0;
let autocomplete_disabled = false;

// Standard initialization function
function init() {
  search_input = document.getElementById('restaurant-search');
  suggestions_container = document.getElementById('restaurant-suggestions');

  if (!search_input || !suggestions_container) return;
  if (!is_google_maps_ready()) {
    setTimeout(init, 500);
    return;
  }

  setup_search_listener();
  setup_click_outside_handler();
}

function is_google_maps_ready() {
  return window.google && window.google.maps && window.google.maps.places;
}

function setup_search_listener() {
  search_input.addEventListener('input', function() {
    clearTimeout(search_timeout);
    search_timeout = setTimeout(() => handle_search_input(this.value), 300);
  });
}

async function handle_search_input(query) {
  if (!should_process_query(query)) return;

  const request_id = generate_request_id(query);

  try {
    show_loading_state();
    const suggestions = await fetch_suggestions(query, request_id);
    handle_success_result(suggestions, request_id);
  } catch (error) {
    handle_error_result(error, request_id);
  }
}

function should_process_query(query) {
  if (query.length < 2) {
    hide_suggestions();
    return false;
  }

  if (autocomplete_disabled) {
    if (window.showErrorToast) {
      window.showErrorToast('Restaurant search disabled due to technical issues.');
    }
    return false;
  }

  return true;
}

function generate_request_id(query) {
  const request_id = ++current_request_id;
  console.log(`Autocomplete request ${request_id}: "${query}"`);
  return request_id;
}

async function fetch_suggestions(query, request_id) {
  const request = { input: query };

  // Add timeout for reliability
  const timeout_promise = new Promise((_, reject) => {
    setTimeout(() => reject(new Error('Request timeout')), 5000);
  });

  const { suggestions } = await Promise.race([
    google.maps.places.AutocompleteSuggestion.fetchAutocompleteSuggestions(request),
    timeout_promise,
  ]);

  // Check if still latest request
  if (request_id !== current_request_id) {
    throw new Error('Outdated request');
  }

  return suggestions;
}

function handle_success_result(suggestions, request_id) {
  if (suggestions && suggestions.length > 0) {
    show_suggestions(suggestions);
  } else {
    show_no_results_message();
  }
}

function handle_error_result(error, request_id) {
  console.error(`Request ${request_id} failed:`, error);

  if (error.message === 'Outdated request') return;

  if (should_disable_autocomplete(error, request_id)) {
    disable_autocomplete_for_session();
  }

  show_user_friendly_error(error);
}

function should_disable_autocomplete(error, request_id) {
  return (request_id <= 3) && (
    error.message.includes('InvalidValueError') ||
    error.message.includes('locationRestriction')
  );
}

function show_user_friendly_error(error) {
  if (error.message.includes('InvalidValueError')) {
    if (window.showErrorToast) {
      window.showErrorToast('Restaurant search temporarily unavailable due to technical issue.');
    }
  } else {
    if (window.showErrorToast) {
      window.showErrorToast('Unable to search restaurants. Please check your connection and try again.');
    }
  }
}

// UI Functions
function hide_suggestions() {
  suggestions_container.style.display = 'none';
  suggestions_container.innerHTML = '';
}

function show_loading_state() {
  suggestions_container.innerHTML = `
    <div class="dropdown-item">
      <div class="d-flex align-items-center">
        <div class="spinner-border spinner-border-sm me-2" role="status">
          <span class="visually-hidden">Loading...</span>
        </div>
        <div>Searching restaurants...</div>
      </div>
    </div>
  `;
  suggestions_container.style.display = 'block';
}

function show_suggestions(suggestions) {
  const html = suggestions.map((suggestion) => {
    const { place_id, main_text, secondary_text } = extract_suggestion_data(suggestion);
    return create_suggestion_html(place_id, main_text, secondary_text);
  }).join('');

  suggestions_container.innerHTML = html;
  suggestions_container.style.display = 'block';
  setup_suggestion_handlers();
}

function extract_suggestion_data(suggestion) {
  const place_prediction = suggestion.placePrediction || suggestion;
  const place_id = place_prediction.placeId || place_prediction.id || '';

  let main_text = '';
  let secondary_text = '';

  if (place_prediction.structuredFormat) {
    main_text = place_prediction.structuredFormat.mainText?.text || place_prediction.structuredFormat.mainText || '';
    secondary_text = place_prediction.structuredFormat.secondaryText?.text || place_prediction.structuredFormat.secondaryText || '';
  } else if (place_prediction.structured_formatting) {
    main_text = place_prediction.structured_formatting.main_text || '';
    secondary_text = place_prediction.structured_formatting.secondary_text || '';
  } else {
    main_text = place_prediction.description || place_prediction.text || '';
  }

  return { place_id, main_text, secondary_text };
}

function create_suggestion_html(place_id, main_text, secondary_text) {
  return `
    <a href="#" class="dropdown-item" data-place-id="${place_id}">
      <div class="d-flex align-items-center">
        <i class="fas fa-utensils me-2 text-muted"></i>
        <div>
          <div class="fw-bold">${main_text}</div>
          <small class="text-muted">${secondary_text}</small>
        </div>
      </div>
    </a>
  `;
}

function setup_suggestion_handlers() {
  suggestions_container.querySelectorAll('.dropdown-item').forEach((item) => {
    item.addEventListener('click', function(e) {
      e.preventDefault();
      select_restaurant(this.dataset.placeId);
    });
  });
}

async function select_restaurant(place_id) {
  try {
    const place = new google.maps.places.Place({
      id: place_id,
      requestedLanguage: 'en',
    });

    await place.fetchFields({
      fields: ['id', 'displayName', 'formattedAddress', 'websiteURI', 'nationalPhoneNumber', 'addressComponents', 'types', 'primaryType'],
    });

    populate_form(place);
    hide_suggestions();
    search_input.value = place.displayName;
    show_success_feedback(`Restaurant "${place.displayName}" selected!`);

  } catch (error) {
    console.error('Error fetching place details:', error);
    if (window.showErrorToast) {
      window.showErrorToast('Failed to load restaurant details.');
    }
  }
}

function parse_address_components(addressComponents) {
  const address_components = {
    street: '',
    city: '',
    state: '',
    postalCode: '',
    country: '',
  };

  if (!addressComponents || !Array.isArray(addressComponents)) {
    console.warn('Restaurant Autocomplete: No valid address components array provided');
    return address_components;
  }

  if (addressComponents.length === 0) {
    console.warn('Restaurant Autocomplete: Address components array is empty');
    return address_components;
  }

  let streetNumber = '';
  let route = '';

  addressComponents.forEach((component) => {
    const types = component.types || [];
    const longText = component.longText || component.long_name || '';
    const shortText = component.shortText || component.short_name || '';

    console.log('Restaurant Autocomplete: Processing address component:', longText, 'Types:', types);

    if (types.includes('street_number')) {
      streetNumber = longText;
    } else if (types.includes('route')) {
      route = longText;
    } else if (types.includes('locality') || types.includes('sublocality_level_1')) {
      address_components.city = longText;
    } else if (types.includes('administrative_area_level_1')) {
      address_components.state = shortText || longText;
    } else if (types.includes('postal_code') || types.includes('postal_code_prefix')) {
      address_components.postalCode = longText;
    } else if (types.includes('country')) {
      address_components.country = longText;
    }
  });

  // Build street address from components
  address_components.street = [streetNumber, route].filter(Boolean).join(' ');

  console.log('Restaurant Autocomplete: Extracted address components:', address_components);
  return address_components;
}

// Use centralized cuisine formatting utility
function mapPlaceTypesToForm(types, primaryType) {
  return mapPlaceTypesToRestaurant(types, primaryType);
}

function populate_form(place) {
  console.log('Restaurant Autocomplete: Populating form with place:', place);
  console.log('Restaurant Autocomplete: Available place properties:', Object.keys(place));

  // Parse address components
  const address_components = parse_address_components(place.addressComponents || []);

  // Map Google Places types to restaurant type and cuisine
  const typeAndCuisine = mapPlaceTypesToForm(place.types, place.primaryType);

  // Handle different Google Places API formats for various fields
  const name = place.displayName?.text || place.displayName || '';
  const phone = place.nationalPhoneNumber || place.formatted_phone_number || '';
  const website = place.websiteURI || place.website || '';
  const google_place_id = place.id || place.placeId || place.place_id || '';

  const fields = {
    name,
    type: typeAndCuisine.type || '',
    cuisine: typeAndCuisine.cuisine || '',
    address: address_components.street || place.formattedAddress || '',
    city: address_components.city || '',
    state: address_components.state || '',
    postal_code: address_components.postalCode || '',
    country: address_components.country || '',
    phone,
    website,
    google_place_id,
    // Note: rating would be user's personal rating, not Google's
    // Google's rating, coordinates, price_level would be looked up dynamically
  };

  console.log('Restaurant Autocomplete: Field mappings:', fields);

  Object.entries(fields).forEach(([field_id, value]) => {
    const field = document.getElementById(field_id);
    if (field && value) {
      field.value = value;
      console.log(`Restaurant Autocomplete: Set ${field_id} = ${value}`);
    } else if (field) {
      console.log(`Restaurant Autocomplete: Field ${field_id} found but no value to set`);
    } else if (value) {
      console.warn(`Restaurant Autocomplete: Field ${field_id} not found in DOM`);
    }
  });

  // Show success feedback with type and cuisine info
  let successMessage = `Restaurant "${name}" selected and form populated!`;
  if (typeAndCuisine.type) {
    successMessage += ` Type: ${typeAndCuisine.type}`;
  }
  if (typeAndCuisine.cuisine) {
    successMessage += `, Cuisine: ${typeAndCuisine.cuisine}`;
  }
  show_success_feedback(successMessage);
}

function show_no_results_message() {
  suggestions_container.innerHTML = `
    <div class="alert alert-info mt-2 mb-0">
      <i class="fas fa-search me-2"></i>
      <strong>No restaurants found</strong>
      <div class="mt-1">Try different keywords or add manually below.</div>
    </div>
  `;
  suggestions_container.style.display = 'block';
}

function show_success_feedback(message) {
  suggestions_container.innerHTML = `
    <div class="alert alert-success mt-2 mb-0">
      <i class="fas fa-check-circle me-2"></i>
      <strong>Success!</strong> ${message}
    </div>
  `;
  suggestions_container.style.display = 'block';

  setTimeout(() => hide_suggestions(), 3000);
}

function show_error_message(message) {
  // Show in UI suggestions area
  suggestions_container.innerHTML = `
    <div class="alert alert-warning mt-2 mb-0">
      <i class="fas fa-info-circle me-2"></i>
      <strong>Search Issue:</strong> ${message}
      <div class="mt-1">
        <small class="text-muted">💡 You can add the restaurant manually below.</small>
      </div>
    </div>
  `;
  suggestions_container.style.display = 'block';

  // Also show as toast for better visibility
  if (window.showWarningToast) {
    window.showWarningToast(message);
  }
}

function disable_autocomplete_for_session() {
  autocomplete_disabled = true;
  if (search_input) {
    search_input.placeholder = 'Type restaurant name manually';
    search_input.disabled = true;
    setTimeout(() => {
      search_input.disabled = false;
    }, 2000);
  }
}

function setup_click_outside_handler() {
  document.addEventListener('click', (e) => {
    if (!search_input.contains(e.target) && !suggestions_container.contains(e.target)) {
      hide_suggestions();
    }
  });
}

// Auto-initialize
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}

// Export for manual triggering
window.initRestaurantSearchAutocomplete = init;
