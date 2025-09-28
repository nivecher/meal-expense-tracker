/**
 * Restaurant Form Page
 *
 * Handles restaurant form functionality including website opening, place ID management,
 * and restaurant validation. This replaces the inline JavaScript in the restaurants/form.html template.
 */

// Global variable to store validation results (for future use)
// let validationData = null;

// Define all functions first
function getCSRFToken() {
  const token = document.querySelector('meta[name="csrf-token"]');
  return token ? token.getAttribute('content') : '';
}

// Toast notification functions
function createToastContainer() {
  let container = document.getElementById('toastContainer');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toastContainer';
    container.className = 'toast-container position-fixed top-0 end-0 p-3';
    container.style.zIndex = '1055';
    document.body.appendChild(container);
  }
  return container;
}

function getIconForType(type) {
  const icons = {
    success: 'fa-check-circle',
    error: 'fa-exclamation-circle',
    warning: 'fa-exclamation-triangle',
    info: 'fa-info-circle',
  };
  return icons[type] || icons.info;
}

function showToast(title, message, type = 'info', duration = 5000, actions = null) {
  const toastContainer = createToastContainer();
  const toastId = `toast-${Date.now()}`;

  // Determine styling based on type
  const bgClass = `bg-${type}`;
  const textClass = type === 'warning' ? 'text-dark' : 'text-white';
  const iconClass = getIconForType(type);

  // Build actions HTML if provided
  let actionsHtml = '';
  if (actions && Array.isArray(actions)) {
    actionsHtml = `<div class="mt-2">${
      actions.map((action) =>
        `<button class="btn btn-sm ${action.class || 'btn-outline-light'} me-2"
                 data-action="${action.action || 'default'}"
                 data-action-data='${JSON.stringify(action.data || {})}'>${action.icon ? `<i class="${action.icon} me-1"></i>` : ''}${action.text}</button>`,
      ).join('')
    }</div>`;
  }

  const toastHtml = `
    <div id="${toastId}" class="toast ${bgClass} ${textClass}" role="alert"
         aria-live="assertive" aria-atomic="true">
      <div class="toast-header ${bgClass} ${textClass}">
        <i class="fas ${iconClass} me-2"></i>
        <strong class="me-auto">${title}</strong>
        <button type="button" class="btn-close ${type === 'warning' ? 'btn-close-dark' : 'btn-close-white'}"
                data-bs-dismiss="toast" aria-label="Close"></button>
      </div>
      <div class="toast-body">
        ${message.replace(/\n/g, '<br>')}
        ${actionsHtml}
      </div>
    </div>
  `;

  toastContainer.insertAdjacentHTML('beforeend', toastHtml);

  const toastElement = document.getElementById(toastId);
  const toast = new bootstrap.Toast(toastElement, {
    autohide: duration > 0,
    delay: duration,
  });

  toast.show();

  // Clean up after toast is hidden
  toastElement.addEventListener('hidden.bs.toast', () => {
    toastElement.remove();
  });

  return toast;
}

function showSuccessToast(message, title = 'Success', duration = 4000) {
  showToast(title, message, 'success', duration);
}

function showErrorToast(message, title = 'Error', duration = 0) {
  showToast(title, message, 'danger', duration);
}

function showWarningToast(message, title = 'Warning', duration = 7000, actions = null) {
  showToast(title, message, 'warning', duration, actions);
}

function showInfoToast(message, title = 'Info', duration = 5000) {
  showToast(title, message, 'info', duration);
}

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

function showSuccessMessage(message) {
  // Create a temporary alert
  const alert = document.createElement('div');
  alert.className = 'alert alert-success alert-dismissible fade show position-fixed';
  alert.style.top = '20px';
  alert.style.right = '20px';
  alert.style.zIndex = '9999';
  alert.innerHTML = `
    ${message}
    <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
  `;

  document.body.appendChild(alert);

  // Auto-remove after 3 seconds
  setTimeout(() => {
    if (alert.parentNode) {
      alert.remove();
    }
  }, 3000);
}

function showErrorMessage(message) {
  // Create a temporary alert
  const alert = document.createElement('div');
  alert.className = 'alert alert-danger alert-dismissible fade show position-fixed';
  alert.style.top = '20px';
  alert.style.right = '20px';
  alert.style.zIndex = '9999';
  alert.innerHTML = `
    ${message}
    <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
  `;

  document.body.appendChild(alert);

  // Auto-remove after 5 seconds
  setTimeout(() => {
    if (alert.parentNode) {
      alert.remove();
    }
  }, 5000);
}

function showValidationLoading() {
  // Show loading toast instead of modal
  showInfoToast(
    'Validating Restaurant',
    'Validating restaurant information with Google Places...',
    0, // No auto-hide for loading state
  );
}

function showValidationError(message) {
  // Use toast notification instead of modal for better UX
  showErrorToast(message, 'Validation Failed', 0); // 0 = no auto-hide for errors
}

async function applyFixes(_fixes) {
  const placeIdField = document.getElementById('google_place_id');
  const placeId = placeIdField ? placeIdField.value.trim() : '';
  const restaurantIdField = document.querySelector('[data-restaurant-id]');
  const restaurantId = restaurantIdField ? restaurantIdField.getAttribute('data-restaurant-id') : '';

  if (!placeId || !restaurantId) {
    showErrorMessage('Missing required data for applying fixes.');
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
        showSuccessMessage('Restaurant information updated successfully!');
      } else {
        showSuccessMessage('No changes were needed - restaurant information is already up to date.');
      }

      // Show success message for applied fixes
      showSuccessToast('Fixes Applied', 'Restaurant information has been updated with Google Places data.');
    } else {
      showErrorMessage(`Failed to apply fixes: ${result.message || 'Unknown error'}`);
    }

  } catch {
    showErrorMessage('Network error occurred while applying fixes. Please try again.');
  }
}

function showValidationResults(results) {
  if (results.status === 'success' && results.data) {
    const { data } = results;

    if (data.mismatches && data.mismatches.length > 0) {
      // Show mismatches with action button to apply fixes
      const mismatchText = data.mismatches.join('\n• ');
      const actions = [
        {
          text: 'Apply Fixes',
          class: 'btn-primary',
          icon: 'fas fa-sync-alt',
          action: 'apply-fixes',
          data: data.fixes,
        },
      ];

      showWarningToast(
        'Validation Mismatches Found',
        `Found ${data.mismatches.length} mismatch(es):\n• ${mismatchText}`,
        0, // No auto-hide for important validation results
        actions,
      );
    } else {
      // No mismatches - show success toast
      showSuccessToast(
        'Validation Complete',
        'Restaurant information validated successfully! No mismatches found.',
        4000,
      );
    }
  } else {
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
    showSuccessMessage('Google Place ID cleared successfully');
  }
}

// Function to validate restaurant data
async function validateRestaurantData() {
  const placeIdField = document.getElementById('google_place_id');
  const placeId = placeIdField ? placeIdField.value.trim() : '';
  const restaurantIdField = document.querySelector('[data-restaurant-id]');
  const restaurantId = restaurantIdField ? restaurantIdField.getAttribute('data-restaurant-id') : '';

  if (!placeId) {
    showErrorMessage('No Google Place ID found. Please search for a restaurant first.');
    return;
  }

  if (!restaurantId) {
    showErrorMessage('Restaurant ID not found. Please refresh the page and try again.');
    return;
  }

  try {
    showValidationLoading();

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
      }),
    });

    const result = await response.json();
    showValidationResults(result);

  } catch {
    showValidationError('Network error occurred during validation. Please try again.');
  }
}

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

  // Set up toast action handlers for validation results
  document.addEventListener('click', (event) => {
    if (event.target.matches('[data-action="apply-fixes"]')) {
      const actionData = JSON.parse(event.target.getAttribute('data-action-data') || '{}');
      applyFixes(actionData);
    }
  });
});
