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

function updateFormFields(restaurantData) {
  // Update form fields with fresh data
  const fields = [
    'name', 'type', 'cuisine', 'service_level', 'rating', 'price_level',
    'website', 'phone', 'description', 'google_place_id',
  ];

  fields.forEach((fieldName) => {
    const field = document.getElementById(fieldName);
    if (field && restaurantData[fieldName] !== undefined) {
      if (field.type === 'checkbox') {
        field.checked = Boolean(restaurantData[fieldName]);
      } else {
        field.value = restaurantData[fieldName] || '';
      }
    }
  });

  // Update address fields
  const addressFields = ['street_address', 'city', 'state', 'zip_code'];
  addressFields.forEach((fieldName) => {
    const field = document.getElementById(fieldName);
    if (field && restaurantData[fieldName] !== undefined) {
      field.value = restaurantData[fieldName] || '';
    }
  });

  // Update chain toggle
  const chainToggle = document.getElementById('is_chain');
  if (chainToggle) {
    chainToggle.checked = Boolean(restaurantData.is_chain);
  }

  // Update button states
  updateValidateButton();
  updateWebsiteButton();

  // Mobile-specific updates
  if (window.matchMedia && window.matchMedia('(max-width: 768px)').matches) {
    // Ensure form fields are properly updated on mobile
    const form = document.querySelector('form');
    if (form) {
      // Trigger change events for mobile form validation
      form.querySelectorAll('input, select, textarea').forEach((field) => {
        field.dispatchEvent(new Event('change', { bubbles: true }));
      });
    }
  }
}

async function refreshFormData() {
  try {
    console.log('Starting form data refresh...');
    const restaurantIdField = document.querySelector('[data-restaurant-id]');
    const restaurantId = restaurantIdField ? restaurantIdField.getAttribute('data-restaurant-id') : '';

    if (!restaurantId) {
      console.warn('No restaurant ID found for refresh');
      return;
    }

    console.log('Fetching restaurant data for ID:', restaurantId);

    // Add a small delay for mobile devices to ensure modal is fully closed
    await new Promise((resolve) => {
      setTimeout(() => resolve(), 100);
    });

    const response = await fetch(`/api/v1/restaurants/${restaurantId}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCSRFToken(),
      },
    });

    console.log('API response status:', response.status);

    if (response.ok) {
      const result = await response.json();
      console.log('API response data:', result);
      if (result.status === 'success' && result.data) {
        console.log('Updating form fields with fresh data');
        updateFormFields(result.data);

        // Trigger a visual update for mobile devices
        if (window.matchMedia && window.matchMedia('(max-width: 768px)').matches) {
          // Force a reflow on mobile
          document.body.offsetHeight; // eslint-disable-line no-unused-expressions
        }
        console.log('Form refresh completed successfully');
      }
    } else {
      console.error('API request failed with status:', response.status);
    }
  } catch (error) {
    console.error('Error refreshing form data:', error);
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
  const modal = document.getElementById('validationModal');
  const loadingDiv = document.getElementById('validation-loading');
  const resultsDiv = document.getElementById('validation-results');

  if (modal && loadingDiv && resultsDiv) {
    loadingDiv.classList.remove('d-none');
    resultsDiv.classList.add('d-none');

    // Show the modal (accessibility is handled by global event listeners)
    const bsModal = new bootstrap.Modal(modal, {
      focus: true,
      keyboard: true,
      backdrop: true,
      static: false,
    });

    bsModal.show();
  }
}

function showValidationError(message) {
  const modal = document.getElementById('validationModal');
  const loadingDiv = document.getElementById('validation-loading');
  const resultsDiv = document.getElementById('validation-results');
  const errorDiv = document.getElementById('validation-error');
  const successDiv = document.getElementById('validation-success');

  if (modal && loadingDiv && resultsDiv && errorDiv && successDiv) {
    loadingDiv.classList.add('d-none');
    resultsDiv.classList.remove('d-none');
    successDiv.classList.add('d-none');
    errorDiv.classList.remove('d-none');

    const errorMessageDiv = document.getElementById('validation-error-message');
    if (errorMessageDiv) {
      errorMessageDiv.textContent = message;
    }

    // Properly manage accessibility attributes
    modal.removeAttribute('aria-hidden');
    modal.setAttribute('aria-modal', 'true');

    // Show the modal with proper focus management
    const bsModal = new bootstrap.Modal(modal, {
      focus: true,
      keyboard: true,
      backdrop: true,
      static: false,
    });

    bsModal.show();

    // Set focus to the modal content after it's shown
    setTimeout(() => {
      const modalContent = modal.querySelector('.modal-content');
      if (modalContent) {
        modalContent.focus();
      }
    }, 100);
  }
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

      // Close the modal (form refresh will be handled by global event listener)
      const modal = document.getElementById('validationModal');
      if (modal) {
        const bsModal = bootstrap.Modal.getInstance(modal);
        if (bsModal) {
          bsModal.hide();
        }
      }
    } else {
      showErrorMessage(`Failed to apply fixes: ${result.message || 'Unknown error'}`);
    }

  } catch {
    showErrorMessage('Network error occurred while applying fixes. Please try again.');
  }
}

function showValidationResults(results) {
  const modal = document.getElementById('validationModal');
  const loadingDiv = document.getElementById('validation-loading');
  const resultsDiv = document.getElementById('validation-results');
  const successDiv = document.getElementById('validation-success');
  const errorDiv = document.getElementById('validation-error');

  if (!modal || !loadingDiv || !resultsDiv || !successDiv || !errorDiv) return;

  loadingDiv.classList.add('d-none');
  resultsDiv.classList.remove('d-none');
  errorDiv.classList.add('d-none');
  successDiv.classList.remove('d-none');

  if (results.status === 'success' && results.data) {
    const { data } = results;

    // Show mismatches if any
    const mismatchesDiv = document.getElementById('validation-mismatches');
    const noMismatchesDiv = document.getElementById('validation-no-mismatches');
    const mismatchListDiv = document.getElementById('mismatch-list');
    const applyFixesBtn = document.getElementById('apply-fixes-btn');

    if (data.mismatches && data.mismatches.length > 0) {
      // Show mismatches
      mismatchesDiv.classList.remove('d-none');
      noMismatchesDiv.classList.add('d-none');

      // Populate mismatch list
      if (mismatchListDiv) {
        mismatchListDiv.innerHTML = data.mismatches.map((mismatch) =>
          `<div class="alert alert-warning mb-2"><i class="fas fa-exclamation-triangle me-2"></i>${mismatch}</div>`,
        ).join('');
      }

      // Show apply fixes button
      if (applyFixesBtn) {
        applyFixesBtn.classList.remove('d-none');

        // Use both click and touch events for mobile compatibility
        const handleApplyFixes = () => applyFixes(data.fixes);
        applyFixesBtn.onclick = handleApplyFixes;
        applyFixesBtn.ontouchend = handleApplyFixes;

        // Ensure button is touch-friendly on mobile
        if (window.matchMedia && window.matchMedia('(max-width: 768px)').matches) {
          applyFixesBtn.style.minHeight = '44px'; // iOS recommended touch target size
          applyFixesBtn.style.minWidth = '44px';
        }
      }
    } else {
      // No mismatches
      mismatchesDiv.classList.add('d-none');
      noMismatchesDiv.classList.remove('d-none');

      // Hide apply fixes button
      if (applyFixesBtn) {
        applyFixesBtn.classList.add('d-none');
      }
    }

    // Properly manage accessibility attributes
    modal.removeAttribute('aria-hidden');
    modal.setAttribute('aria-modal', 'true');

    // Show the modal with proper focus management
    const bsModal = new bootstrap.Modal(modal, {
      focus: true,
      keyboard: true,
      backdrop: true,
      static: false,
    });

    bsModal.show();

    // Set focus to the modal content after it's shown
    setTimeout(() => {
      const modalContent = modal.querySelector('.modal-content');
      if (modalContent) {
        modalContent.focus();
      }
    }, 100);
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

  // Set up modal event listeners for proper accessibility and form refresh
  const validationModal = document.getElementById('validationModal');
  if (validationModal) {
    // Handle modal closing - refresh form data
    validationModal.addEventListener('hidden.bs.modal', () => {
      console.log('Modal closed, checking if form refresh is needed');
      // Only refresh if we're on an edit form (not add form)
      const restaurantIdField = document.querySelector('[data-restaurant-id]');
      if (restaurantIdField) {
        console.log('Refreshing form data for restaurant:', restaurantIdField.getAttribute('data-restaurant-id'));
        refreshFormData();
      } else {
        console.log('No restaurant ID found, skipping form refresh');
      }
    });

    // Handle modal showing - ensure proper accessibility
    validationModal.addEventListener('show.bs.modal', () => {
      validationModal.removeAttribute('aria-hidden');
      validationModal.setAttribute('aria-modal', 'true');

      // Set focus to the first focusable element
      setTimeout(() => {
        const firstFocusable = validationModal.querySelector('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
        if (firstFocusable) {
          firstFocusable.focus();
        }
      }, 100);
    });

    // Handle modal hiding - restore accessibility attributes
    validationModal.addEventListener('hide.bs.modal', () => {
      validationModal.setAttribute('aria-hidden', 'true');
      validationModal.removeAttribute('aria-modal');
    });
  }
});
