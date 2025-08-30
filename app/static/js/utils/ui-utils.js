/**
 * UI Utilities
 * Consolidated notifications, modals, loading, and UI interactions
 *
 * @module uiUtils
 * @version 2.0.0
 * @author Meal Expense Tracker Team
 */

import { logger } from './core-utils.js';

// ===== TOAST NOTIFICATIONS =====

/**
 * Creates and returns the toast container element
 */
function getOrCreateToastContainer() {
  let toastContainer = document.getElementById('toast-container');

  if (!toastContainer) {
    toastContainer = document.createElement('div');
    toastContainer.id = 'toast-container';
    toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
    document.body.appendChild(toastContainer);
  }

  return toastContainer;
}

/**
 * Creates a toast element
 */
function createToastElement(message, type, title) {
  const toast = document.createElement('div');
  toast.className = `toast align-items-center text-white bg-${type} border-0`;
  toast.setAttribute('role', 'alert');
  toast.setAttribute('aria-live', 'assertive');
  toast.setAttribute('aria-atomic', 'true');

  toast.innerHTML = `
    <div class="toast-header bg-${type} text-white">
      <strong class="me-auto">${title}</strong>
      <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close"></button>
    </div>
    <div class="toast-body">
      ${message}
    </div>
  `;

  return toast;
}

/**
 * Shows a toast notification
 */
function showToast(message, type = 'info', duration = 3000) {
  // Bootstrap fallback
  if (typeof bootstrap === 'undefined' || !bootstrap.Toast) {
    logger.warn('Bootstrap Toast not available. Using fallback.');
    alert(`${type.toUpperCase()}: ${message}`);
    return null;
  }

  const toastContainer = getOrCreateToastContainer();
  const title = type.charAt(0).toUpperCase() + type.slice(1);
  const toast = createToastElement(message, type, title);

  toastContainer.appendChild(toast);

  const bsToast = new bootstrap.Toast(toast, { autohide: true, delay: duration });
  bsToast.show();

  // Cleanup after toast is hidden
  toast.addEventListener('hidden.bs.toast', () => {
    toast.remove();
    if (toastContainer.children.length === 0) {
      toastContainer.remove();
    }
  });

  return bsToast;
}

// Toast helper functions
const showErrorToast = (message, duration = 5000) => showToast(message, 'danger', duration);
const showSuccessToast = (message, duration = 3000) => showToast(message, 'success', duration);
const showInfoToast = (message, duration = 3000) => showToast(message, 'info', duration);
const showWarningToast = (message, duration = 4000) => showToast(message, 'warning', duration);

// ===== MODAL UTILITIES =====

/**
 * Initialize accessibility for a modal element
 */
function initializeModalAccessibility(modalElement, options = {}) {
  const { returnFocus = true, focusElement = null } = options;

  if (!modalElement || !modalElement.classList.contains('modal')) {
    logger.warn('Element is not a modal', modalElement);
    return;
  }

  let focusedElementBeforeModal = null;

  modalElement.addEventListener('show.bs.modal', () => {
    if (returnFocus) {
      focusedElementBeforeModal = document.activeElement;
    }
    modalElement.setAttribute('aria-hidden', 'false');
    modalElement.setAttribute('aria-modal', 'true');
  });

  modalElement.addEventListener('shown.bs.modal', () => {
    const elementToFocus = focusElement ||
      modalElement.querySelector('button[autofocus]') ||
      modalElement.querySelector('button:not([disabled])') ||
      modalElement.querySelector('input:not([disabled])') ||
      modalElement.querySelector('a[href]');

    if (elementToFocus && elementToFocus.focus) {
      elementToFocus.focus();
    }
  });

  modalElement.addEventListener('hidden.bs.modal', () => {
    modalElement.setAttribute('aria-hidden', 'true');
    modalElement.setAttribute('aria-modal', 'false');

    if (returnFocus && focusedElementBeforeModal && focusedElementBeforeModal.focus) {
      focusedElementBeforeModal.focus();
    }
  });
}

/**
 * Shows a confirmation dialog
 */
function showConfirmDialog({
  title = 'Are you sure?',
  message = 'This action cannot be undone.',
  confirmText = 'Confirm',
  cancelText = 'Cancel',
  type = 'warning',
} = {}) {
  return new Promise((resolve) => {
    // Bootstrap fallback
    if (typeof bootstrap === 'undefined' || !bootstrap.Modal) {
      logger.warn('Bootstrap Modal not available. Using browser confirm.');
      resolve(confirm(`${title}\n\n${message}`));
      return;
    }

    const modalId = `confirm-modal-${Date.now()}`;
    const modal = document.createElement('div');
    modal.className = `modal fade modal-${type}`;
    modal.id = modalId;
    modal.tabIndex = '-1';
    modal.setAttribute('aria-labelledby', `${modalId}-label`);

    modal.innerHTML = `
      <div class="modal-dialog">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title" id="${modalId}-label">${title}</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
          </div>
          <div class="modal-body">
            ${message}
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">${cancelText}</button>
            <button type="button" class="btn btn-primary" id="${modalId}-confirm">${confirmText}</button>
          </div>
        </div>
      </div>
    `;

    document.body.appendChild(modal);

    const modalInstance = new bootstrap.Modal(modal);
    initializeModalAccessibility(modal);
    modalInstance.show();

    // Handle confirm button
    document.getElementById(`${modalId}-confirm`).addEventListener('click', () => {
      modalInstance.hide();
      resolve(true);
    });

    // Handle modal close
    modal.addEventListener('hidden.bs.modal', () => {
      modal.remove();
      resolve(false);
    });
  });
}

// ===== LOADING UTILITIES =====

/**
 * Shows a loading overlay
 */
function showLoadingOverlay(message = 'Loading...', showSpinner = true) {
  const overlayId = `loading-overlay-${Date.now()}`;
  const overlay = document.createElement('div');
  overlay.id = overlayId;
  overlay.className = 'loading-overlay position-fixed top-0 start-0 w-100 h-100 d-flex justify-content-center align-items-center';
  overlay.style.backgroundColor = 'rgba(0, 0, 0, 0.5)';
  overlay.style.zIndex = '9999';

  const spinner = showSpinner ? `
    <div class="spinner-border text-primary me-3" role="status">
      <span class="visually-hidden">Loading...</span>
    </div>
  ` : '';

  overlay.innerHTML = `
    <div class="bg-white rounded p-4 d-flex align-items-center">
      ${spinner}
      <span class="h5 mb-0">${message}</span>
    </div>
  `;

  document.body.appendChild(overlay);
  document.body.style.overflow = 'hidden';

  return {
    hide() {
      if (overlay?.parentNode) {
        overlay.remove();
        document.body.style.overflow = '';
      }
    },
  };
}

/**
 * Simple lazy loading for images and elements
 */
function initLazyLoading() {
  if ('IntersectionObserver' in window) {
    const imageObserver = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          const img = entry.target;
          if (img.dataset.src) {
            img.src = img.dataset.src;
            img.removeAttribute('data-src');
          }
          imageObserver.unobserve(img);
        }
      });
    });

    // Observe all images with data-src attribute
    document.querySelectorAll('img[data-src]').forEach((img) => {
      imageObserver.observe(img);
    });

    return imageObserver;
  }
  // Fallback: load all images immediately
  document.querySelectorAll('img[data-src]').forEach((img) => {
    img.src = img.dataset.src;
    img.removeAttribute('data-src');
  });

}

// ===== FORM UTILITIES =====

/**
 * Show loading state on form
 */
function showFormLoading(form, message = 'Processing...') {
  const submitBtn = form.querySelector('button[type="submit"]');
  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.dataset.originalText = submitBtn.textContent;
    submitBtn.innerHTML = `
      <span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
      ${message}
    `;
  }
}

/**
 * Hide loading state on form
 */
function hideFormLoading(form) {
  const submitBtn = form.querySelector('button[type="submit"]');
  if (submitBtn) {
    submitBtn.disabled = false;
    if (submitBtn.dataset.originalText) {
      submitBtn.textContent = submitBtn.dataset.originalText;
      delete submitBtn.dataset.originalText;
    }
  }
}

// ===== INITIALIZATION =====

/**
 * Initialize UI utilities
 */
function initUIUtils() {
  // Initialize modal accessibility for existing modals
  document.querySelectorAll('.modal').forEach((modal) => {
    initializeModalAccessibility(modal);
  });

  // Initialize lazy loading
  initLazyLoading();

  // Watch for dynamically added modals
  const observer = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
      mutation.addedNodes.forEach((node) => {
        if (node.nodeType === Node.ELEMENT_NODE) {
          if (node.classList && node.classList.contains('modal')) {
            initializeModalAccessibility(node);
          }
          const modals = node.querySelectorAll ? node.querySelectorAll('.modal') : [];
          modals.forEach((modal) => initializeModalAccessibility(modal));
        }
      });
    });
  });

  observer.observe(document.body, {
    childList: true,
    subtree: true,
  });

  logger.info('UI utilities initialized');
}

// Auto-initialize when DOM is ready
if (typeof document !== 'undefined') {
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initUIUtils);
  } else {
    initUIUtils();
  }
}

// ===== EXPORTS =====

export {
  // Toast notifications
  showToast,
  showErrorToast,
  showSuccessToast,
  showInfoToast,
  showWarningToast,

  // Modals
  showConfirmDialog,
  initializeModalAccessibility,

  // Loading
  showLoadingOverlay,
  initLazyLoading,

  // Forms
  showFormLoading,
  hideFormLoading,

  // Initialization
  initUIUtils,
};

// Default export
export default {
  showToast,
  showErrorToast,
  showSuccessToast,
  showInfoToast,
  showWarningToast,
  showConfirmDialog,
  initializeModalAccessibility,
  showLoadingOverlay,
  initLazyLoading,
  showFormLoading,
  hideFormLoading,
  initUIUtils,
};
