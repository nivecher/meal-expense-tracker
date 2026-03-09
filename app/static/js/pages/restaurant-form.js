/**
 * Restaurant Form Page
 *
 * Handles restaurant form functionality including website opening, place ID management,
 * and restaurant validation. This replaces the inline JavaScript in the restaurants/form.html template.
 */

// Global variables to store validation results

let validationData = null;

let currentValidationStatus = null;

const ENTERPRISE_FIELDS = new Set(['phone', 'price_level', 'rating']);

// Define all functions first
function getCSRFToken() {
  const token = document.querySelector('meta[name="csrf-token"]');
  return token ? token.getAttribute('content') : '';
}

// Import toast functions
import { toast } from '../utils/notifications.js';
import { attachIntlPhoneFormatting } from '../utils/contact-fields.js';

function updateWebsiteButton() {
  const websiteField = document.getElementById('website');
  const websiteBtn = document.getElementById('open-website-btn');

  if (websiteField && websiteBtn) {
    const hasWebsite = websiteField.value.trim().length > 0;
    websiteBtn.disabled = !hasWebsite;
    websiteBtn.dataset.website = websiteField.value.trim();
  }
}

function updatePlaceIdActions() {
  const placeIdField = document.getElementById('google_place_id');
  const actionsDiv = document.getElementById('google-place-id-actions');
  const viewLink = document.getElementById('view-on-google-maps-link');

  if (!placeIdField || !actionsDiv) return;

  const placeId = placeIdField.value.trim();
  if (placeId) {
    actionsDiv.classList.remove('d-none');
    if (viewLink) {
      viewLink.href = `https://www.google.com/maps/place/?q=place_id:${placeId}`;
    }
  } else {
    actionsDiv.classList.add('d-none');
    if (viewLink) {
      viewLink.href = '#';
    }
  }
}

function updateValidateButton() {
  const placeIdField = document.getElementById('google_place_id');
  const validateBtn = document.getElementById('validate-restaurant-btn');

  if (placeIdField && validateBtn) {
    const hasPlaceId = placeIdField.value.trim().length > 0;
    validateBtn.disabled = !hasPlaceId;
  }

  updatePlaceIdActions();
}

function getSelectedMerchantChainState() {
  const merchantInput = document.getElementById('merchant_name');
  if (!(merchantInput instanceof HTMLInputElement)) {
    return false;
  }

  return merchantInput.dataset.merchantIsChain === 'true';
}

function updateLocationNameRequirement() {
  const locationNameField = document.getElementById('location_name');
  const requiredIndicator = document.getElementById('location-name-required-indicator');
  const chainHelp = document.getElementById('location-name-chain-help');
  const isChainMerchant = getSelectedMerchantChainState();

  if (locationNameField instanceof HTMLInputElement) {
    locationNameField.required = isChainMerchant;
    locationNameField.setAttribute('aria-required', isChainMerchant ? 'true' : 'false');
  }

  if (requiredIndicator) {
    requiredIndicator.classList.toggle('d-none', !isChainMerchant);
  }

  if (chainHelp) {
    chainHelp.classList.toggle('d-none', !isChainMerchant);
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

  // Update form field styling (try data-field, data_field, then id)
  const field =
    document.querySelector(`[data-field="${fieldName}"]`) ||
    document.querySelector(`[data_field="${fieldName}"]`) ||
    document.getElementById(fieldName);
  if (field) {
    // Remove existing validation classes
    field.classList.remove('validation-match', 'validation-mismatch', 'validation-no-data');

    // Add new validation class
    if (status !== 'not-validated') {
      field.classList.add(`validation-${status}`);
    }
  }
}

function updateFieldValidationBorder(field, status) {
  if (!field) return;
  field.classList.remove('validation-match', 'validation-mismatch', 'validation-no-data');
  if (status !== 'not-validated') {
    field.classList.add(`validation-${status}`);
  }
  // If field is inside input-group, also update the form control (border may be on it)
  const inputGroup = field.closest('.input-group');
  if (inputGroup) {
    const formControl = inputGroup.querySelector('.form-control, .form-select');
    if (formControl && formControl !== field) {
      formControl.classList.remove('validation-match', 'validation-mismatch', 'validation-no-data');
      if (status !== 'not-validated') {
        formControl.classList.add(`validation-${status}`);
      }
    }
  }
}

function hideReconciliationPanel() {
  const panelDiv = document.getElementById('restaurant-reconciliation-panel');
  if (panelDiv) {
    panelDiv.classList.add('d-none');
  }
}

function resetAllValidationIndicators() {
  const fields = [
    'name',
    'location_name',
    'type',
    'address_line_1',
    'address_line_2',
    'city',
    'state',
    'postal_code',
    'country',
    'cuisine',
    'service_level',
    'price_level',
    'phone',
    'website',
    'coordinates',
  ];
  fields.forEach((field) => {
    updateValidationIndicator(field, 'not-validated', 'Not validated', '', null);
  });

  // Reset validation status badges (section-level)
  document.querySelectorAll('.section-validation-status').forEach((statusEl) => {
    statusEl.classList.add('d-none');
    statusEl
      .querySelectorAll('.validation-badge-good, .validation-badge-warnings, .validation-badge-errors')
      .forEach((el) => el.classList.add('d-none'));
  });

  hideReconciliationPanel();
  validationData = null;
  currentValidationStatus = null;
}

function updateFieldValidationIndicators(data) {
  // Reset all field indicators to "not validated"
  const fields = [
    'name',
    'address_line_1',
    'address_line_2',
    'city',
    'state',
    'postal_code',
    'country',
    'cuisine',
    'service_level',
    'price_level',
    'rating',
    'phone',
    'website',
    'type',
    'coordinates',
  ];
  fields.forEach((field) => {
    updateValidationIndicator(field, 'not-validated', 'Not validated', '', null);
  });

  // Use google_data from API response (nested under data)
  const googleData = data.google_data || {};
  const mismatches = data.mismatches || [];

  // Map mismatch display names to form field names
  const mismatchFieldMapping = {
    name: 'name',
    'address line 1': 'address_line_1',
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
    coordinates: 'coordinates',
  };

  // Build set of fields that have mismatches (coordinates maps to lat/lng in fixes)
  const mismatchFields = new Set();
  mismatches.forEach((mismatch) => {
    const fieldNameMatch = mismatch.match(/^([^:]+):\s/);
    if (fieldNameMatch) {
      const displayName = fieldNameMatch[1].toLowerCase().trim();
      const formField = mismatchFieldMapping[displayName] || mismatchFieldMapping[displayName.replace(/\s+/g, ' ')];
      if (formField) {
        mismatchFields.add(formField);
      }
    }
  });

  // Determine status per field: match (green), mismatch (orange), or no-data
  const fieldStatuses = {};
  fields.forEach((field) => {
    let hasGoogleData;
    if (field === 'coordinates') {
      const lat = googleData.latitude;
      const lng = googleData.longitude;
      hasGoogleData =
        lat !== undefined &&
        lat !== null &&
        lng !== undefined &&
        lng !== null &&
        String(lat).trim() !== '' &&
        String(lng).trim() !== '';
    } else {
      const googleValue = googleData[field];
      hasGoogleData = googleValue !== undefined && googleValue !== null && String(googleValue).trim() !== '';
    }

    if (mismatchFields.has(field)) {
      fieldStatuses[field] = 'mismatch';
    } else if (hasGoogleData) {
      fieldStatuses[field] = 'match';
    } else {
      fieldStatuses[field] = 'no-data';
    }
  });

  // Update field indicators: Matches (green check) or Mismatch (orange warning)
  Object.entries(fieldStatuses).forEach(([fieldName, status]) => {
    let statusText, tooltipText, iconClass;
    const advancedUnavailable = ENTERPRISE_FIELDS.has(fieldName) && data.advanced_features_enabled === false;

    if (advancedUnavailable) {
      statusText = 'Advanced';
      tooltipText = 'Requires Advanced Features (Google Places Enterprise integration)';
      iconClass = 'fas fa-bolt text-info';
    } else if (status === 'match') {
      statusText = 'Matches';
      tooltipText = 'Matches Google data';
      iconClass = 'fas fa-check-circle text-success';
    } else if (status === 'mismatch') {
      statusText = 'Mismatch';
      tooltipText = 'Differs from Google data - use reconciliation panel to apply';
      iconClass = 'fas fa-exclamation-triangle text-warning';
    } else if (status === 'no-data') {
      statusText = 'No data';
      tooltipText = 'Google has no data for this field';
      iconClass = 'fas fa-question-circle text-muted';
    } else {
      statusText = 'Not validated';
      tooltipText = '';
      iconClass = 'fas fa-question-circle text-secondary';
    }

    updateValidationIndicator(fieldName, status, statusText, tooltipText, iconClass);
  });
}

function updateValidationStatus(status, mismatchCount = 0) {
  const statusContainers = document.querySelectorAll('.section-validation-status');

  statusContainers.forEach((statusContainer) => {
    const goodBadge = statusContainer.querySelector('.validation-badge-good');
    const warningsBadge = statusContainer.querySelector('.validation-badge-warnings');
    const errorsBadge = statusContainer.querySelector('.validation-badge-errors');

    if (!goodBadge || !warningsBadge || !errorsBadge) return;

    goodBadge.classList.add('d-none');
    warningsBadge.classList.add('d-none');
    errorsBadge.classList.add('d-none');

    statusContainer.classList.remove('d-none');

    if (status === 'valid' && mismatchCount === 0) {
      goodBadge.classList.remove('d-none');
    } else if (mismatchCount > 0) {
      warningsBadge.classList.remove('d-none');
      warningsBadge.innerHTML = `<i class="fas fa-exclamation-triangle me-1"></i> ${mismatchCount} Issue${mismatchCount !== 1 ? 's' : ''}`;
    } else if (status === 'error') {
      errorsBadge.classList.remove('d-none');
    }
  });

  currentValidationStatus = { status, mismatchCount };
}

const FIELD_DISPLAY_NAMES = {
  name: 'Restaurant Name',
  type: 'Type',
  address_line_1: 'Address Line 1',
  address_line_2: 'Address Line 2',
  city: 'City',
  state: 'State',
  postal_code: 'Postal Code',
  country: 'Country',
  cuisine: 'Cuisine',
  service_level: 'Service Level',
  price_level: 'Price Level',
  rating: 'Your Rating',
  phone: 'Phone',
  website: 'Website',
  latitude: 'Latitude',
  longitude: 'Longitude',
  coordinates: 'Coordinates',
};

function escapeForDisplay(str) {
  if (str === null || str === undefined) return '—';
  const s = String(str).trim();
  return s === '' ? '—' : s;
}

function refreshCoordinatesDisplayFromForm() {
  const latField = document.getElementById('latitude');
  const lngField = document.getElementById('longitude');
  const displayEl = document.getElementById('restaurant-coordinates-display');
  const textEl = document.getElementById('coordinates-text');
  const mapContainer = document.getElementById('restaurant-map-container');
  const mapIframe = document.getElementById('restaurant-map-iframe');

  if (!latField || !lngField) return;

  const lat = parseFloat(latField.value);
  const lng = parseFloat(lngField.value);
  const hasCoords = !Number.isNaN(lat) && !Number.isNaN(lng);

  if (displayEl && textEl) {
    if (hasCoords) {
      textEl.textContent = `${lat.toFixed(6)}°, ${lng.toFixed(6)}°`;
      displayEl.classList.remove('d-none');
    } else {
      displayEl.classList.add('d-none');
    }
  }

  if (mapContainer && mapIframe && hasCoords) {
    const apiKey = mapContainer.dataset.apiKey || window.GOOGLE_MAPS_API_KEY || '';
    const placeIdField = document.getElementById('google_place_id');
    const placeId = placeIdField ? placeIdField.value.trim() : '';
    if (apiKey) {
      const q = placeId ? `place_id:${placeId}` : `${lat},${lng}`;
      mapIframe.src = `https://www.google.com/maps/embed/v1/place?key=${apiKey}&q=${encodeURIComponent(q)}&zoom=16`;
      mapContainer.classList.remove('d-none');
    }
  }
}

function applySingleFixValue(fieldName, value) {
  const field =
    document.getElementById(fieldName) ||
    document.querySelector(`[name="${fieldName}"]`) ||
    document.querySelector(`[data-field="${fieldName}"]`) ||
    document.querySelector(`[data_field="${fieldName}"]`);
  if (!field) return false;

  const stringValue = String(value ?? '').trim();
  if (field.tagName === 'SELECT') {
    const option = Array.from(field.options).find(
      (opt) =>
        String(opt.value).trim().toLowerCase() === stringValue.toLowerCase() ||
        opt.textContent.trim().toLowerCase() === stringValue.toLowerCase(),
    );
    if (option) {
      field.value = option.value;
    } else {
      field.value = stringValue;
    }
  } else {
    field.value = stringValue;
  }

  field.dispatchEvent(new Event('change', { bubbles: true }));

  if (fieldName === 'latitude' || fieldName === 'longitude') {
    refreshCoordinatesDisplayFromForm();
  }

  // Update indicator and border immediately (ensure border re-renders after apply)
  updateValidationIndicator(fieldName, 'match', 'Matches', 'Matches Google data', 'fas fa-check-circle text-success');
  updateFieldValidationBorder(field, 'match');
  return true;
}

function applyGoogleSuggestion(fieldName, value) {
  if (!applySingleFixValue(fieldName, value)) return;

  toast.success(`Applied Google value for ${FIELD_DISPLAY_NAMES[fieldName] || fieldName}`);

  if (validationData && validationData.fixes) {
    delete validationData.fixes[fieldName];
    const hasLatOrLng = 'latitude' in validationData.fixes || 'longitude' in validationData.fixes;
    if ((fieldName === 'latitude' || fieldName === 'longitude') && !hasLatOrLng) {
      updateValidationIndicator(
        'coordinates',
        'match',
        'Matches',
        'Matches Google data',
        'fas fa-check-circle text-success',
      );
    }
    if (Object.keys(validationData.fixes).length === 0) {
      hideReconciliationPanel();
      updateValidationStatus('valid', 0);
    } else {
      /* eslint-disable-next-line no-use-before-define */
      displayReconciliationPanel(validationData);
      updateValidationStatus('valid', Object.keys(validationData.fixes).length);
    }
  }
}

function displayReconciliationPanel(data) {
  const panelDiv = document.getElementById('restaurant-reconciliation-panel');
  const resultsDiv = document.getElementById('restaurant-reconciliation-results');

  if (!panelDiv || !resultsDiv) return;

  const fixes = data.fixes || {};
  const currentData = data.current_data || {};

  if (Object.keys(fixes).length === 0) {
    panelDiv.classList.add('d-none');
    return;
  }

  const fragment = document.createDocumentFragment();
  const table = document.createElement('table');
  table.className = 'table table-sm table-bordered reconciliation-table';

  const thead = document.createElement('thead');
  const headerRow = document.createElement('tr');
  ['Field', 'Form Value', 'Google Value', 'Action'].forEach((text) => {
    const th = document.createElement('th');
    th.textContent = text;
    headerRow.appendChild(th);
  });
  thead.appendChild(headerRow);
  table.appendChild(thead);

  const tbody = document.createElement('tbody');

  Object.entries(fixes).forEach(([fieldName, googleValue]) => {
    const row = document.createElement('tr');
    const displayName = FIELD_DISPLAY_NAMES[fieldName] || fieldName.replace(/_/g, ' ');
    const currentValue = currentData[fieldName];

    const fieldCell = document.createElement('td');
    const strong = document.createElement('strong');
    strong.textContent = displayName;
    fieldCell.appendChild(strong);
    if (ENTERPRISE_FIELDS.has(fieldName)) {
      const advancedBadge = document.createElement('span');
      advancedBadge.className = 'badge bg-info text-dark ms-2';
      advancedBadge.textContent = 'Advanced';
      advancedBadge.title = 'Google Places Enterprise integration';
      fieldCell.appendChild(advancedBadge);
    }
    const icon = document.createElement('i');
    icon.className = 'fas fa-exclamation-triangle text-warning ms-1';
    fieldCell.appendChild(icon);
    row.appendChild(fieldCell);

    const formValueCell = document.createElement('td');
    formValueCell.className = 'text-warning';
    formValueCell.textContent = escapeForDisplay(currentValue);
    row.appendChild(formValueCell);

    const googleValueCell = document.createElement('td');
    googleValueCell.className = 'text-success';
    googleValueCell.textContent = escapeForDisplay(googleValue);
    row.appendChild(googleValueCell);

    const actionCell = document.createElement('td');
    const applyBtn = document.createElement('button');
    applyBtn.className = 'btn btn-sm btn-primary';
    applyBtn.textContent = 'Apply';
    applyBtn.setAttribute('data-field', fieldName);
    applyBtn.setAttribute('data-value', String(googleValue ?? ''));
    actionCell.appendChild(applyBtn);
    row.appendChild(actionCell);

    tbody.appendChild(row);
  });

  table.appendChild(tbody);
  fragment.appendChild(table);
  resultsDiv.innerHTML = '';
  resultsDiv.appendChild(fragment);
  panelDiv.classList.remove('d-none');

  // Attach Apply button listeners
  resultsDiv.querySelectorAll('button.btn-primary').forEach((btn) => {
    const field = btn.getAttribute('data-field');
    const value = btn.getAttribute('data-value');
    if (field && value !== undefined) {
      btn.addEventListener('click', (e) => {
        e.preventDefault();
        applyGoogleSuggestion(field, value);
      });
    }
  });
}

function applyAllFixes() {
  if (!validationData || !validationData.fixes) {
    toast.error('No validation data available for fixes');
    return;
  }

  let appliedCount = 0;
  const fixes = { ...validationData.fixes };

  Object.entries(fixes).forEach(([fieldName, value]) => {
    if (applySingleFixValue(fieldName, value)) {
      appliedCount++;
    }
  });

  if (appliedCount > 0) {
    validationData.fixes = {};
    hideReconciliationPanel();
    updateValidationStatus('valid', 0);
    toast.success(`Applied ${appliedCount} fix${appliedCount !== 1 ? 'es' : ''}`);
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
      displayReconciliationPanel(data);
      toast.info(`Found ${mismatchCount} mismatch(es). Use comparison panel below to apply changes.`, 0);
    } else {
      hideReconciliationPanel();
      toast.success('Restaurant information validated successfully! All data matches Google Places.');
    }
  } else {
    updateValidationStatus('error');
    hideReconciliationPanel();
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
    'name',
    'type',
    'located_within',
    'description',
    'address_line_1',
    'address_line_2',
    'city',
    'state',
    'postal_code',
    'country',
    'phone',
    'email',
    'website',
    'cuisine',
    'service_level',
    'rating',
    'price_level',
    'latitude',
    'longitude',
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
      } else if ((fieldName === 'latitude' || fieldName === 'longitude') && value) {
        value = parseFloat(value);
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
  if (
    confirm('Are you sure you want to clear the Google Place ID? This will remove the connection to Google Places.')
  ) {
    const placeIdField = document.getElementById('google_place_id');
    if (placeIdField) {
      placeIdField.value = '';
      updateValidateButton();
    }

    const searchInput = document.getElementById('restaurant-search');
    if (searchInput) {
      searchInput.value = '';
    }

    const latField = document.getElementById('latitude');
    const lngField = document.getElementById('longitude');
    if (latField) latField.value = '';
    if (lngField) lngField.value = '';

    const coordsDisplay = document.getElementById('restaurant-coordinates-display');
    if (coordsDisplay) coordsDisplay.classList.add('d-none');

    const mapContainer = document.getElementById('restaurant-map-container');
    const mapIframe = document.getElementById('restaurant-map-iframe');
    if (mapContainer) mapContainer.classList.add('d-none');
    if (mapIframe) mapIframe.src = '';

    toast.success('Google Place ID cleared successfully');
  }
}

// Function to prompt user for advanced fields inclusion
async function shouldIncludeAdvancedFields() {
  try {
    // Check if user has advanced features
    const response = await fetch('/api/v1/user/current', {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCSRFToken(),
      },
    });

    if (!response.ok) {
      console.warn('Could not verify user privileges, defaulting to basic validation');
      return false;
    }

    const userData = await response.json();
    const hasAdvancedFeatures = userData.data?.has_advanced_features || false;

    if (!hasAdvancedFeatures) {
      return false;
    }

    // Show confirmation dialog for advanced features
    return new Promise((resolve) => {
      const modal = document.createElement('div');
      modal.className = 'modal fade';
      modal.innerHTML = `
        <div class="modal-dialog modal-dialog-centered">
          <div class="modal-content">
            <div class="modal-header">
              <h5 class="modal-title">Advanced Validation</h5>
              <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body">
              <p>You have access to advanced features. Would you like to include advanced fields in this validation?</p>
              <div class="form-check">
                <input class="form-check-input" type="checkbox" id="include-advanced-checkbox" checked>
                <label class="form-check-label" for="include-advanced-checkbox">
                  <strong>Include advanced fields:</strong>
                  <ul class="mb-0 mt-2">
                    <li>Price Level</li>
                    <li>Rating</li>
                    <li>Phone Number</li>
                  </ul>
                  <small class="text-muted">These fields use Google Places Enterprise data and may provide more comprehensive validation.</small>
                </label>
              </div>
            </div>
            <div class="modal-footer">
              <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Basic Only</button>
              <button type="button" class="btn btn-primary" id="confirm-advanced-btn">Include Advanced</button>
            </div>
          </div>
        </div>
      `;

      document.body.appendChild(modal);
      const bsModal = new bootstrap.Modal(modal);

      const confirmBtn = modal.querySelector('#confirm-advanced-btn');
      const checkbox = modal.querySelector('#include-advanced-checkbox');

      const handleConfirm = () => {
        const includeAdvanced = checkbox.checked;
        bsModal.hide();
        resolve(includeAdvanced);
      };

      confirmBtn.addEventListener('click', handleConfirm);

      // Handle modal close events
      modal.addEventListener('hidden.bs.modal', () => {
        document.body.removeChild(modal);
        // If modal was closed without clicking confirm, default to false
        if (!confirmBtn.dataset.clicked) {
          resolve(false);
        }
      });

      // Mark button as clicked when confirmed
      confirmBtn.addEventListener('click', () => {
        confirmBtn.dataset.clicked = 'true';
      });

      bsModal.show();
    });
  } catch (error) {
    console.error('Error checking user privileges:', error);
    return false;
  }
}

// Function to validate restaurant data
async function validateRestaurantData() {
  const placeIdField = document.getElementById('google_place_id');
  const placeId = placeIdField ? placeIdField.value.trim() : '';
  const restaurantIdField = document.querySelector('#validate-restaurant-btn[data-restaurant-id]');
  const restaurantIdRaw = restaurantIdField ? restaurantIdField.getAttribute('data-restaurant-id') : '';
  const restaurantId = restaurantIdRaw ? parseInt(restaurantIdRaw, 10) : null;

  if (!placeId) {
    toast.error('No Google Place ID found. Please search for a restaurant first.');
    return;
  }

  // Check if user has advanced features and prompt for inclusion
  const includeAdvanced = await shouldIncludeAdvancedFields();

  // Reset validation indicators before starting
  resetAllValidationIndicators();

  try {
    showValidationLoading();

    const formData = collectCurrentFormData();
    const payload = {
      google_place_id: placeId,
      fix_mismatches: false,
      form_data: formData,
      include_advanced_fields: includeAdvanced,
    };
    if (restaurantId) {
      payload.restaurant_id = restaurantId;
    }

    const response = await fetch('/api/v1/restaurants/validate', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCSRFToken(),
      },
      body: JSON.stringify(payload),
    });

    const result = await response.json();
    showValidationResults(result);
  } catch {
    showValidationError('Network error occurred during validation. Please try again.');
  }
}

// Fields that participate in Google validation (clearing when user edits)
const VALIDATED_FIELD_NAMES = [
  'name',
  'type',
  'address_line_1',
  'address_line_2',
  'city',
  'state',
  'postal_code',
  'country',
  'cuisine',
  'service_level',
  'price_level',
  'rating',
  'phone',
  'website',
  'latitude',
  'longitude',
];

function isValidatedField(element) {
  if (!element) return false;
  const fieldName = element.getAttribute('data-field') || element.getAttribute('data_field') || element.id;
  return fieldName && VALIDATED_FIELD_NAMES.includes(fieldName);
}

function clearValidationOnFieldEdit(event) {
  if (!currentValidationStatus) return;
  if (!event.isTrusted) return; // Skip programmatic changes (e.g. Apply)
  const { target } = event;
  if (isValidatedField(target)) {
    resetAllValidationIndicators();
  }
}

// Initialize restaurant form event handlers
function initRestaurantForm() {
  attachIntlPhoneFormatting('#restaurantForm', ['phone']);

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
  const websiteBtn = document.getElementById('open-website-btn');
  if (websiteBtn) {
    websiteBtn.addEventListener('click', openWebsite);
  }

  // Set up validate button
  const validateBtn = document.getElementById('validate-restaurant-btn');
  if (validateBtn) {
    validateBtn.addEventListener('click', validateRestaurantData);
  }

  // Clear validation when user edits any validated field
  const form = document.getElementById('restaurantForm');
  if (form) {
    form.addEventListener('input', clearValidationOnFieldEdit);
    form.addEventListener('change', clearValidationOnFieldEdit);
  }

  // Set up event handlers for validation UI (delegation for dynamically shown elements)
  document.addEventListener('click', (event) => {
    if (event.target.closest('[data-action="clear-place-id"]')) {
      clearPlaceId();
    }
    if (event.target.matches('[data-action="apply-fixes"]')) {
      const actionData = JSON.parse(event.target.getAttribute('data-action-data') || '{}');
      applyFixes(actionData);
    }
    if (event.target.matches('[data-action="apply-all-fixes"]')) {
      applyAllFixes();
    }
  });

  // Reconciliation panel buttons
  const applyAllBtn = document.getElementById('restaurant-apply-all-btn');
  if (applyAllBtn) {
    applyAllBtn.addEventListener('click', applyAllFixes);
  }
  const dismissBtn = document.getElementById('restaurant-dismiss-reconciliation-btn');
  if (dismissBtn) {
    dismissBtn.addEventListener('click', hideReconciliationPanel);
  }

  const searchInput = document.getElementById('restaurant-search');
  if (searchInput instanceof HTMLInputElement) {
    const initialQuery = searchInput.dataset.initialQuery?.trim() || '';
    if (initialQuery && !searchInput.dataset.initialQueryApplied) {
      searchInput.dataset.initialQueryApplied = 'true';
      window.setTimeout(() => {
        searchInput.dispatchEvent(new Event('input', { bubbles: true }));
      }, 250);
    }
  }

  updateLocationNameRequirement();

  document.addEventListener('merchant-selected', updateLocationNameRequirement);
  document.addEventListener('merchant-cleared', updateLocationNameRequirement);
}

// Run init when DOM is ready (handles both normal and deferred/module load timing)
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initRestaurantForm);
} else {
  initRestaurantForm();
}
