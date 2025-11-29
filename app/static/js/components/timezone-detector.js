/**
 * Timezone Detector Component
 * Handles auto-detection of browser timezone and updates user profile
 */

// Import security utilities for XSS prevention
let escapeHtml;
if (typeof window !== 'undefined' && window.SecurityUtils) {
  ({ escapeHtml } = window.SecurityUtils);
} else {
  // Fallback escapeHtml implementation
  escapeHtml = function(text) {
    if (text === null || text === undefined) {
      return '';
    }
    const textString = String(text);
    const map = {
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#x27;',
      '/': '&#x2F;',
    };
    return textString.replace(/[&<>"'/]/g, (char) => map[char]);
  };
}

/**
 * Detect browser timezone using Intl API.
 * @returns {string} IANA timezone string (e.g., 'America/New_York') or 'UTC' as fallback
 */
function detectBrowserTimezone() {
  try {
    if (typeof Intl !== 'undefined' && Intl.DateTimeFormat) {
      // eslint-disable-next-line new-cap
      const options = Intl.DateTimeFormat().resolvedOptions();
      if (options && options.timeZone && typeof options.timeZone === 'string') {
        return options.timeZone;
      }
    }
  } catch (error) {
    console.warn('Timezone detection failed:', error);
  }
  return 'UTC';
}

/**
 * Update user's timezone via AJAX
 * @param {string} timezone - The timezone to set
 */
async function updateUserTimezone(timezone) {
  try {
    const form = document.querySelector('.profile-form');
    if (!form) {
      return { success: false, message: 'Profile form not found' };
    }

    const formData = new FormData();
    formData.append('timezone', timezone);
    const csrfToken = form.querySelector('[name="csrf_token"]')?.value;
    if (csrfToken) {
      formData.append('csrf_token', csrfToken);
    }

    const response = await fetch('/auth/profile', {
      method: 'POST',
      headers: {
        'X-Requested-With': 'XMLHttpRequest',
      },
      body: formData,
    });

    const data = await response.json();

    if (data.success) {
      return { success: true, message: data.message || 'Timezone updated successfully' };
    }
    return { success: false, message: data.message || 'Failed to update timezone' };
  } catch (error) {
    console.error('Error updating timezone:', error);
    return { success: false, message: 'Network error while updating timezone' };
  }
}

/**
 * Initialize timezone detector button
 */
function initializeTimezoneDetector() {
  const detectButton = document.querySelector('[data-action="detect-timezone"]');
  const resultDiv = document.getElementById('timezone-detected');
  const timezoneSelect = document.getElementById('timezone');

  if (!detectButton) {
    return;
  }

  detectButton.addEventListener('click', async() => {
    // Disable button during detection
    detectButton.disabled = true;
    detectButton.textContent = 'Detecting...';

    if (resultDiv) {
      resultDiv.style.display = 'block';
      resultDiv.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Detecting timezone...';
      resultDiv.className = 'timezone-detection-result mt-2 text-info';
    }

    try {
      // Detect browser timezone
      const detectedTimezone = detectBrowserTimezone();
      console.log('Detected browser timezone:', detectedTimezone);

      // Update the select dropdown
      if (timezoneSelect) {
        timezoneSelect.value = detectedTimezone;
      }

      // Update user's timezone via AJAX
      const result = await updateUserTimezone(detectedTimezone);

      if (result.success) {
        if (resultDiv) {
          // Escape message to prevent XSS
          const escapedMessage = escapeHtml(result.message || 'Timezone updated successfully');
          resultDiv.innerHTML = `<i class="fas fa-check-circle me-1"></i>${escapedMessage}`;
          resultDiv.className = 'timezone-detection-result mt-2 text-success';
        }
        // Reload page after a short delay to show updated timezone
        setTimeout(() => {
          window.location.reload();
        }, 1000);
      } else {
        if (resultDiv) {
          // Escape message to prevent XSS
          const escapedMessage = escapeHtml(result.message || 'Failed to update timezone');
          resultDiv.innerHTML = `<i class="fas fa-exclamation-circle me-1"></i>${escapedMessage}`;
          resultDiv.className = 'timezone-detection-result mt-2 text-danger';
        }
        detectButton.disabled = false;
        detectButton.innerHTML = '<i class="fas fa-location-dot me-1"></i>Auto-detect';
      }
    } catch (error) {
      console.error('Error in timezone detection:', error);
      if (resultDiv) {
        resultDiv.innerHTML = '<i class="fas fa-exclamation-circle me-1"></i>Failed to detect timezone';
        resultDiv.className = 'timezone-detection-result mt-2 text-danger';
      }
      detectButton.disabled = false;
      detectButton.innerHTML = '<i class="fas fa-location-dot me-1"></i>Auto-detect';
    }
  });
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', initializeTimezoneDetector);
