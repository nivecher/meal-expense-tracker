/**
 * Auto-save Draft Functionality
 * Uses localStorage to save and restore form drafts
 * Follows TIGER principles: Simple, maintainable, focused
 */

const DRAFT_STORAGE_KEY = 'expense_form_draft';
const DRAFT_INDICATOR_ID = 'draft-indicator';
const SAVE_DEBOUNCE_MS = 1000;

/**
 * Get draft storage key for a specific form
 * @param {HTMLFormElement} form - The form element
 * @returns {string} Storage key
 */
function getDraftKey(form) {
  const formId = form.id || 'expenseForm';
  const formAction = form.action || window.location.pathname;
  return `${DRAFT_STORAGE_KEY}_${formId}_${formAction}`;
}

/**
 * Save form data to localStorage
 * @param {HTMLFormElement} form - The form to save
 */
function saveDraft(form) {
  try {
    const formData = new FormData(form);
    const draftData = {};

    // Convert FormData to plain object
    for (const [key, value] of formData.entries()) {
      if (draftData[key]) {
        // Handle multiple values (e.g., checkboxes)
        if (Array.isArray(draftData[key])) {
          draftData[key].push(value);
        } else {
          draftData[key] = [draftData[key], value];
        }
      } else {
        draftData[key] = value;
      }
    }

    const storageKey = getDraftKey(form);
    localStorage.setItem(storageKey, JSON.stringify(draftData));
    showDraftIndicator('Draft saved', 'success');
  } catch (error) {
    console.warn('Failed to save draft:', error);
  }
}

/**
 * Restore form data from localStorage
 * @param {HTMLFormElement} form - The form to restore
 * @returns {boolean} True if draft was restored
 */
function restoreDraft(form) {
  try {
    const storageKey = getDraftKey(form);
    const draftJson = localStorage.getItem(storageKey);

    if (!draftJson) {
      return false;
    }

    const draftData = JSON.parse(draftJson);

    // Restore form fields
    for (const [key, value] of Object.entries(draftData)) {
      const field = form.querySelector(`[name="${key}"]`);

      if (!field) {
        continue;
      }

      if (field.type === 'checkbox' || field.type === 'radio') {
        if (Array.isArray(value)) {
          value.forEach((val) => {
            const option = form.querySelector(`[name="${key}"][value="${val}"]`);
            if (option) {
              option.checked = true;
            }
          });
        } else {
          const option = form.querySelector(`[name="${key}"][value="${value}"]`);
          if (option) {
            option.checked = true;
          }
        }
      } else if (field.tagName === 'SELECT') {
        field.value = Array.isArray(value) ? value[0] : value;
      } else {
        field.value = Array.isArray(value) ? value.join(', ') : value;
      }

      // Trigger change event for fields that need it
      field.dispatchEvent(new Event('change', { bubbles: true }));
    }

    showDraftIndicator('Draft restored', 'info');
    return true;
  } catch (error) {
    console.warn('Failed to restore draft:', error);
    return false;
  }
}

/**
 * Clear draft from localStorage
 * @param {HTMLFormElement} form - The form to clear draft for
 */
function clearDraft(form) {
  try {
    const storageKey = getDraftKey(form);
    localStorage.removeItem(storageKey);
    hideDraftIndicator();
  } catch (error) {
    console.warn('Failed to clear draft:', error);
  }
}

/**
 * Show draft status indicator
 * @param {string} message - Message to display
 * @param {string} type - Indicator type (success, info, warning)
 */
function showDraftIndicator(message, type = 'info') {
  let indicator = document.getElementById(DRAFT_INDICATOR_ID);

  if (!indicator) {
    indicator = document.createElement('div');
    indicator.id = DRAFT_INDICATOR_ID;
    indicator.className = 'alert alert-sm alert-dismissible fade show';
    indicator.style.position = 'fixed';
    indicator.style.top = '20px';
    indicator.style.right = '20px';
    indicator.style.zIndex = '9999';
    indicator.style.minWidth = '200px';
    document.body.appendChild(indicator);
  }

  indicator.className = `alert alert-${type} alert-sm alert-dismissible fade show`;
  indicator.innerHTML = `
    <span>${message}</span>
    <button type="button" class="btn-close btn-close-sm" data-bs-dismiss="alert"></button>
  `;

  // Auto-hide after 3 seconds
  setTimeout(() => {
    if (indicator && indicator.parentNode) {
      indicator.classList.remove('show');
      setTimeout(() => {
        if (indicator && indicator.parentNode) {
          indicator.parentNode.removeChild(indicator);
        }
      }, 150);
    }
  }, 3000);
}

/**
 * Hide draft indicator
 */
function hideDraftIndicator() {
  const indicator = document.getElementById(DRAFT_INDICATOR_ID);
  if (indicator && indicator.parentNode) {
    indicator.classList.remove('show');
    setTimeout(() => {
      if (indicator && indicator.parentNode) {
        indicator.parentNode.removeChild(indicator);
      }
    }, 150);
  }
}

/**
 * Check if draft exists for a form
 * @param {HTMLFormElement} form - The form to check
 * @returns {boolean} True if draft exists
 */
function hasDraft(form) {
  try {
    const storageKey = getDraftKey(form);
    return localStorage.getItem(storageKey) !== null;
  } catch {
    return false;
  }
}

/**
 * Initialize auto-save for a form
 * @param {HTMLFormElement} form - The form to enable auto-save for
 */
function initAutoSave(form) {
  if (!form) {
    return;
  }

  let saveTimeout = null;

  // Save draft on input change (debounced)
  form.addEventListener('input', () => {
    clearTimeout(saveTimeout);
    saveTimeout = setTimeout(() => {
      saveDraft(form);
    }, SAVE_DEBOUNCE_MS);
  });

  // Clear draft on successful form submission
  form.addEventListener('submit', () => {
    clearTimeout(saveTimeout);
    // Clear draft after a short delay to allow form processing
    setTimeout(() => {
      clearDraft(form);
    }, 500);
  });

  // Restore draft on page load if it exists
  if (hasDraft(form)) {
    // Show restore button
    showRestoreButton(form);
  } else {
    // Try to restore immediately if no user interaction needed
    restoreDraft(form);
  }
}

/**
 * Show restore draft button
 * @param {HTMLFormElement} form - The form element
 */
function showRestoreButton(form) {
  // Check if button already exists
  if (document.getElementById('restore-draft-btn')) {
    return;
  }

  const button = document.createElement('button');
  button.id = 'restore-draft-btn';
  button.type = 'button';
  button.className = 'btn btn-outline-info btn-sm mb-3';
  button.innerHTML = '<i class="fas fa-undo me-1"></i> Restore Draft';

  button.addEventListener('click', () => {
    if (confirm('Restore your saved draft? This will replace current form values.')) {
      restoreDraft(form);
      button.remove();
    }
  });

  // Insert before form
  form.parentNode.insertBefore(button, form);
}

// Export functions
export {
  initAutoSave,
  saveDraft,
  restoreDraft,
  clearDraft,
  hasDraft,
  showDraftIndicator,
  hideDraftIndicator,
};
