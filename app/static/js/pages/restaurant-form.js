/**
 * Restaurant Form Page
 *
 * Handles restaurant form functionality including website opening, place ID management,
 * and restaurant validation. This replaces the inline JavaScript in the restaurants/form.html template.
 */

// Global variables to store validation results

let validationData = null;
// eslint-disable-next-line no-unused-vars
let currentValidationStatus = null;

// Define all functions first
function getCSRFToken() {
  const token = document.querySelector('meta[name="csrf-token"]');
  return token ? token.getAttribute('content') : '';
}

// Import toast functions
import { toast } from '../utils/notifications.js';

function updateWebsiteButton() {
  const websiteField = document.getElementById('website');
  const websiteBtn = document.getElementById('website-btn');

  if (websiteField && websiteBtn) {
    const hasWebsite = websiteField.value.trim().length > 0;
    websiteBtn.style.display = hasWebsite ? 'inline-block' : 'none';
  }
}

function updateValidateButton() {
  const placeIdField = document.getElementById('google_place_id');
  const validateBtn = document.getElementById('validate-restaurant-btn');

  if (placeIdField && validateBtn) {
    const hasPlaceId = placeIdField.value.trim().length > 0;
    validateBtn.disabled = !hasPlaceId;
  }
}

function showValidationLoading() {
  // Show loading toast instead of modal
  toast.info('Validating restaurant information with Google Places...', 0);
}

function showValidationError(message) {
  // Use toast notification instead of modal for better UX
  toast.error(message, 0); // No auto-hide for errors
}

// Validation UI functions
function updateValidationIndicator(fieldName, status, message, tooltip, providedIconClass = null) {
  const indicator = document.getElementById(`${fieldName}-validation-indicator`);
  if (!indicator) return;

  // Use provided iconClass or fall back to default mapping
  let finalIconClass = providedIconClass;
  if (!finalIconClass) {
    const iconMap = {
      match: 'fa-check-circle',
      mismatch: 'fa-exclamation-triangle',
      'no-data': 'fa-question-circle',
      'not-validated': 'fa-question-circle',
    };
    const colorMap = {
      match: 'text-success',
      mismatch: 'text-warning',
      'no-data': 'text-muted',
      'not-validated': 'text-secondary',
    };
    finalIconClass = `${colorMap[status] || 'text-secondary'} fas ${iconMap[status] || 'fa-question-circle'}`;
  }

  indicator.innerHTML = `
    <small ${tooltip ? `title="${tooltip}"` : ''}>
      <i class="${finalIconClass} me-1"></i>
      ${message}
    </small>
  `;

  // Update form field styling
  const field = document.querySelector(`[data-field="${fieldName}"]`);
  if (field) {
    // Remove existing validation classes
    field.classList.remove('validation-match', 'validation-mismatch', 'validation-no-data');

    // Add new validation class
    if (status !== 'not-validated') {
      field.classList.add(`validation-${status}`);
    }
  }
}

function resetAllValidationIndicators() {
  const fields = ['name', 'address_line_1', 'cuisine', 'service_level', 'price_level', 'phone', 'website'];
  fields.forEach((field) => {
    updateValidationIndicator(field, 'not-validated', 'Not validated', '', null);
  });

  // Reset validation status badges
  document.getElementById('validation-status').classList.add('d-none');
  document.getElementById('validation-status-good').classList.add('d-none');
  document.getElementById('validation-status-warnings').classList.add('d-none');
  document.getElementById('validation-status-errors').classList.add('d-none');

  // Clear stored validation data
  validationData = null;
  currentValidationStatus = null;
}

function updateFieldValidationIndicators(data) {
  // Reset all field indicators to "not validated"
  const fields = [
    'name', 'address_line_1', 'address_line_2', 'city', 'state', 'postal_code', 'country',
    'cuisine', 'service_level', 'price_level', 'rating', 'phone', 'website', 'type',
  ];
  fields.forEach((field) => {
    updateValidationIndicator(field, 'not-validated', 'Not validated', '', null);
  });

  // Parse mismatches to determine field status
  const mismatches = data.mismatches || [];

  // Create a map of field statuses
  const fieldStatuses = {};

  // Check which fields have Google data available and set appropriate status
  const googleDataMapping = {
    name: data.google_name,
    address_line_1: data.google_address_line_1,
    address_line_2: data.google_address_line_2,
    city: data.google_city,
    state: data.google_state,
    postal_code: data.google_postal_code,
    country: data.google_country,
    type: data.primary_type,
    cuisine: data.google_cuisine,
    service_level: data.google_service_level,
    price_level: data.google_price_level,
    rating: data.google_rating,
    phone: data.google_phone,
    website: data.google_website,
  };

  fields.forEach((field) => {
    if (googleDataMapping[field] !== undefined && googleDataMapping[field] !== null) {
      fieldStatuses[field] = 'match'; // Google has data for this field
    } else {
      fieldStatuses[field] = 'no-data'; // Google doesn't have data for this field
    }
  });

  // Check mismatches to mark fields with issues
  mismatches.forEach((mismatch) => {
    // Parse mismatch strings like "Name: 'value' vs Google: 'value'"
    const fieldNameMatch = mismatch.match(/^([^:]+):\s/);
    if (fieldNameMatch) {
      const fieldName = fieldNameMatch[1].toLowerCase();

      // Map mismatch field names to form field names
      const fieldMapping = {
        name: 'name',
        address: 'address_line_1',
        'address line 2': 'address_line_2',
        city: 'city',
        state: 'state',
        'postal code': 'postal_code',
        country: 'country',
        type: 'type',
        cuisine: 'cuisine',
        'service level': 'service_level',
        'price level': 'price_level',
        rating: 'rating',
        phone: 'phone',
        website: 'website',
      };

      const formField = fieldMapping[fieldName];
      if (formField) {
        fieldStatuses[formField] = 'mismatch';
      }
    }
  });

  // Update field indicators with improved messaging
  Object.entries(fieldStatuses).forEach(([fieldName, status]) => {
    let statusText, tooltipText, iconClass;

    if (status === 'match') {
      statusText = 'Match';
      tooltipText = 'Matches Google data';
      iconClass = 'fas fa-check-circle text-success';
    } else if (status === 'mismatch') {
      statusText = 'Mismatch';
      tooltipText = 'Click to apply Google data';
      iconClass = 'fas fa-exclamation-triangle text-warning';
    } else if (status === 'no-data') {
      statusText = 'No data';
      tooltipText = 'Google has no data for this field';
      iconClass = 'fas fa-question-circle text-muted';
    } else {
      statusText = '?';
      tooltipText = 'Not validated';
      iconClass = 'fas fa-question-circle text-secondary';
    }

    updateValidationIndicator(fieldName, status, statusText, tooltipText, iconClass);
  });
}

function updateValidationStatus(status, mismatchCount = 0) {
  const statusContainer = document.getElementById('validation-status');
  const goodBadge = document.getElementById('validation-status-good');
  const warningsBadge = document.getElementById('validation-status-warnings');
  const errorsBadge = document.getElementById('validation-status-errors');

  // Hide all badges first
  goodBadge.classList.add('d-none');
  warningsBadge.classList.add('d-none');
  errorsBadge.classList.add('d-none');

  // Show status container
  statusContainer.classList.remove('d-none');

  // Update badges based on status
  if (status === 'valid' && mismatchCount === 0) {
    goodBadge.classList.remove('d-none');
  } else if (mismatchCount > 0) {
    warningsBadge.classList.remove('d-none');
    warningsBadge.innerHTML = `<i class="fas fa-exclamation-triangle me-1"></i> ${mismatchCount} Issue${mismatchCount !== 1 ? 's' : ''}`;
  } else if (status === 'error') {
    errorsBadge.classList.remove('d-none');
  }

  currentValidationStatus = { status, mismatchCount };
}

function applyAllFixes() {
  if (!validationData || !validationData.fixes) {
    toast.error('No validation data available for fixes');
    return;
  }

  let appliedCount = 0;

  // Apply all fixes from the stored validation data
  Object.entries(validationData.fixes).forEach(([fieldName, value]) => {
    const field = document.querySelector(`[data-field="${fieldName}"]`);
    if (field && value !== undefined && value !== null) {
      try {
        // Update the form field
        if (field.tagName === 'SELECT') {
          field.value = value;
        } else {
          field.value = value;
        }

        // Trigger change event for any dependent functionality
        field.dispatchEvent(new Event('change', { bubbles: true }));

        // Update the validation indicator
        updateValidationIndicator(fieldName, 'match', 'Fixed - matches Google', 'Fixed with Google data', null);

        appliedCount++;
      } catch (error) {
        console.error(`Error applying fix for ${fieldName}:`, error);
      }
    }
  });

  if (appliedCount > 0) {
    toast.success(`Applied ${appliedCount} fix${appliedCount !== 1 ? 'es' : ''}`);

    // Update validation status to reflect that issues are resolved
    updateValidationStatus('valid', 0);
  } else {
    toast.warning('No fixes could be applied');
  }
}

async function applyFixes(_fixes) {
  const placeIdField = document.getElementById('google_place_id');
  const placeId = placeIdField ? placeIdField.value.trim() : '';
  const restaurantIdField = document.querySelector('[data-restaurant-id]');
  const restaurantId = restaurantIdField ? restaurantIdField.getAttribute('data-restaurant-id') : '';

  if (!placeId || !restaurantId) {
    toast.error('Missing required data for applying fixes.');
    return;
  }

  try {
    const response = await fetch('/api/v1/restaurants/validate', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCSRFToken(),
      },
      body: JSON.stringify({
        restaurant_id: parseInt(restaurantId, 10),
        google_place_id: placeId,
        fix_mismatches: true,
      }),
    });

    const result = await response.json();

    if (result.status === 'success') {
      if (result.data.restaurant_updated) {
        toast.success('Restaurant information updated successfully!');
      } else {
        toast.success('No changes were needed - restaurant information is already up to date.');
      }

      // Show success message for applied fixes
      toast.success('Restaurant information has been updated with Google Places data.');
    } else {
      toast.error(`Failed to apply fixes: ${result.message || 'Unknown error'}`);
    }

  } catch {
    toast.error('Network error occurred while applying fixes. Please try again.');
  }
}

function showValidationResults(results) {
  if (results.status === 'success' && results.data) {
    const { data } = results;
    validationData = data; // Store for later use

    // Update validation status
    const mismatchCount = data.mismatches ? data.mismatches.length : 0;
    updateValidationStatus('valid', mismatchCount);

    // Update individual field validation indicators
    updateFieldValidationIndicators(data);

    if (mismatchCount > 0) {
      // Show detailed mismatch information
      const mismatchDetails = data.mismatches.map((mismatch) => `• ${mismatch}`).join('\n');
      toast.warning(`Found ${mismatchCount} mismatch(es) with Google Places data:\n${mismatchDetails}`, 0);
    } else {
      toast.success('Restaurant information validated successfully! All data matches Google Places.');
    }
  } else {
    updateValidationStatus('error');
    showValidationError(results.message || 'Validation failed');
  }
}

// Function to open website in new tab
function openWebsite() {
  const websiteField = document.getElementById('website');
  const websiteUrl = websiteField.value.trim();

  if (websiteUrl) {
    // Ensure URL has protocol
    let url = websiteUrl;
    if (!url.startsWith('http://') && !url.startsWith('https://')) {
      url = `https://${url}`;
    }
    window.open(url, '_blank', 'noopener,noreferrer');
  }
}

// Function to collect current form data for validation
function collectCurrentFormData() {
  const formData = {};

  // Collect values from all relevant form fields
  const fields = [
    'name', 'type', 'located_within', 'description',
    'address_line_1', 'address_line_2', 'city', 'state', 'postal_code', 'country',
    'phone', 'email', 'website',
    'cuisine', 'service_level', 'rating', 'price_level',
  ];

  fields.forEach((fieldName) => {
    const element = document.getElementById(fieldName) || document.querySelector(`[name="${fieldName}"]`);
    if (element) {
      let { value } = element;
      // Convert numeric fields
      if (fieldName === 'rating' && value) {
        value = parseFloat(value);
      } else if (fieldName === 'price_level' && value) {
        value = parseInt(value, 10);
      }
      // Only include non-empty values
      if (value !== '' && value !== null && value !== undefined) {
        formData[fieldName] = value;
      }
    }
  });

  return formData;
}

// Function to clear Google Place ID
function clearPlaceId() {
  if (confirm('Are you sure you want to clear the Google Place ID? This will remove the connection to Google Places.')) {
    // Clear the hidden field
    const hiddenField = document.getElementById('google_place_id');
    if (hiddenField) {
      hiddenField.value = '';
    }

    // Clear the search input
    const searchInput = document.getElementById('restaurant_search');
    if (searchInput) {
      searchInput.value = '';
    }

    // Show success message
    toast.success('Google Place ID cleared successfully');
  }
}

// Function to validate restaurant data
async function validateRestaurantData() {
  const placeIdField = document.getElementById('google_place_id');
  const placeId = placeIdField ? placeIdField.value.trim() : '';
  const restaurantIdField = document.querySelector('[data-restaurant-id]');
  const restaurantId = restaurantIdField ? restaurantIdField.getAttribute('data-restaurant-id') : '';

  if (!placeId) {
    toast.error('No Google Place ID found. Please search for a restaurant first.');
    return;
  }

  if (!restaurantId) {
    toast.error('Restaurant ID not found. Please refresh the page and try again.');
    return;
  }

  // Reset validation indicators before starting
  resetAllValidationIndicators();

  try {
    showValidationLoading();

    // Collect current form values for validation
    const formData = collectCurrentFormData();

    const response = await fetch('/api/v1/restaurants/validate', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCSRFToken(),
      },
      body: JSON.stringify({
        restaurant_id: parseInt(restaurantId, 10),
        google_place_id: placeId,
        fix_mismatches: false,
        form_data: formData, // Include current form values
      }),
    });

    const result = await response.json();
    showValidationResults(result);

  } catch {
    showValidationError('Network error occurred during validation. Please try again.');
  }
}

// Cuisine dropdown is now handled by WTForms SelectField
// No need for manual population - options are rendered server-side

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {

  // Set up website field monitoring
  const websiteField = document.getElementById('website');
  if (websiteField) {
    websiteField.addEventListener('input', updateWebsiteButton);
    updateWebsiteButton(); // Initial check
  }

  // Set up place ID field monitoring
  const placeIdField = document.getElementById('google_place_id');
  if (placeIdField) {
    placeIdField.addEventListener('input', updateValidateButton);
    updateValidateButton(); // Initial check
  }

  // Set up website button
  const websiteBtn = document.getElementById('website-btn');
  if (websiteBtn) {
    websiteBtn.addEventListener('click', openWebsite);
  }

  // Set up validate button
  const validateBtn = document.getElementById('validate-restaurant-btn');
  if (validateBtn) {
    validateBtn.addEventListener('click', validateRestaurantData);
  }

  // Set up clear place ID button
  const clearBtn = document.getElementById('clear-place-id-btn');
  if (clearBtn) {
    clearBtn.addEventListener('click', clearPlaceId);
  }

  // Set up event handlers for validation UI
  document.addEventListener('click', (event) => {
    // Handle apply fixes from toast (legacy)
    if (event.target.matches('[data-action="apply-fixes"]')) {
      const actionData = JSON.parse(event.target.getAttribute('data-action-data') || '{}');
      applyFixes(actionData);
    }

    // Handle apply all fixes from toast
    if (event.target.matches('[data-action="apply-all-fixes"]')) {
      applyAllFixes();
    }
  });
});
