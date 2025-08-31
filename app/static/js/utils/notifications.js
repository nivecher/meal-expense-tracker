/**
 * Enhanced Toast Notification System
 * Consolidated, responsive, and accessible notifications
 *
 * @module notifications
 * @version 3.0.0
 * @author Meal Expense Tracker Team
 */

import { logger } from './core-utils.js';

// Constants for better maintainability
const TOAST_CONFIG = {
  MAX_TOASTS: 5,
  DEFAULT_DURATION: 3000,
  POSITION_CLASS: 'toast-container position-fixed p-3',
  Z_INDEX: '1090',
  ICONS: {
    success: 'fa-check-circle',
    error: 'fa-exclamation-circle',
    danger: 'fa-exclamation-triangle',
    warning: 'fa-exclamation-triangle',
    info: 'fa-info-circle'
  }
};

// Toast container management with responsive positioning
function getOrCreateToastContainer() {
  let container = document.getElementById('toast-container');

  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    container.className = getResponsiveContainerClass();
    container.style.zIndex = TOAST_CONFIG.Z_INDEX;
    container.setAttribute('aria-live', 'polite');
    container.setAttribute('aria-label', 'Notifications');
    document.body.appendChild(container);

    // Add responsive listener
    window.addEventListener('resize', () => updateContainerPosition(container));
  }

  return container;
}

// Get responsive container class based on screen size
function getResponsiveContainerClass() {
  const isMobile = window.innerWidth <= 768;
  const isTablet = window.innerWidth > 768 && window.innerWidth <= 1024;

  if (isMobile) {
    // Mobile: full width at bottom
    return `${TOAST_CONFIG.POSITION_CLASS} bottom-0 start-0 end-0`;
  } else if (isTablet) {
    // Tablet: smaller width, bottom right
    return `${TOAST_CONFIG.POSITION_CLASS} bottom-0 end-0`;
  } else {
    // Desktop: top right
    return `${TOAST_CONFIG.POSITION_CLASS} top-0 end-0`;
  }
}

// Update container position on resize
function updateContainerPosition(container) {
  if (!container) return;
  container.className = getResponsiveContainerClass();
}

// Create enhanced toast element with accessibility and icons
function createToastElement(message, type, options = {}) {
  const {
    title = type.charAt(0).toUpperCase() + type.slice(1),
    showIcon = true,
    showHeader = true,
    customClass = ''
  } = options;

  // Validate inputs
  if (!message || typeof message !== 'string') {
    logger.warn('Invalid toast message provided');
    return null;
  }

  // Normalize type
  const normalizedType = type === 'error' ? 'danger' : type;
  const icon = TOAST_CONFIG.ICONS[normalizedType] || TOAST_CONFIG.ICONS.info;

  const toast = document.createElement('div');
  toast.className = `toast align-items-center text-white bg-${normalizedType} border-0 ${customClass}`.trim();
  toast.setAttribute('role', 'alert');
  toast.setAttribute('aria-live', 'assertive');
  toast.setAttribute('aria-atomic', 'true');

  // Create toast content
  const iconHtml = showIcon ? `<i class="fas ${icon} me-2" aria-hidden="true"></i>` : '';

  if (showHeader) {
    toast.innerHTML = `
      <div class="toast-header bg-${normalizedType} text-white border-0">
        <strong class="me-auto">${iconHtml}${title}</strong>
        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast" aria-label="Close notification"></button>
      </div>
      <div class="toast-body">
        ${message}
      </div>
    `;
  } else {
    toast.innerHTML = `
      <div class="d-flex">
        <div class="toast-body">
          ${iconHtml}${message}
        </div>
        <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close notification"></button>
      </div>
    `;
  }

  return toast;
}

// Enhanced cleanup with container management
function setupToastCleanup(toast, container) {
  if (!toast || !container) return;

  toast.addEventListener('hidden.bs.toast', () => {
    try {
      toast.remove();

      // Remove container if no toasts remaining
      if (container.children.length === 0) {
        container.remove();
      }
    } catch (error) {
      logger.warn('Error during toast cleanup:', error);
    }
  });
}

// Manage toast count to prevent overflow
function manageTotalToastCount(container) {
  const toasts = container.querySelectorAll('.toast');

  if (toasts.length >= TOAST_CONFIG.MAX_TOASTS) {
    // Remove oldest toast
    const oldestToast = toasts[0];
    if (oldestToast) {
      const bsToast = bootstrap.Toast.getOrCreateInstance(oldestToast);
      bsToast.hide();
    }
  }
}

// Main toast function with enhanced features
function showToast(message, type = 'info', duration = TOAST_CONFIG.DEFAULT_DURATION, options = {}) {
  // Validate bootstrap availability
  if (!window.bootstrap?.Toast) {
    logger.warn('Bootstrap Toast not available. Using fallback.');
    alert(`${type.toUpperCase()}: ${message}`);
    return null;
  }

  // Validate inputs
  if (!message) {
    logger.warn('Cannot show toast: message is required');
    return null;
  }

  if (duration < 0 || duration > 30000) {
    logger.warn('Toast duration out of bounds, using default');
    duration = TOAST_CONFIG.DEFAULT_DURATION;
  }

  try {
    const container = getOrCreateToastContainer();
    manageTotalToastCount(container);

    const toast = createToastElement(message, type, options);
    if (!toast) return null;

    container.appendChild(toast);

    const bsToast = new bootstrap.Toast(toast, {
      autohide: duration > 0,
      delay: duration
    });

    bsToast.show();
    setupToastCleanup(toast, container);

    logger.debug(`Toast shown: ${type} - ${message}`);
    return bsToast;

  } catch (error) {
    logger.error('Failed to show toast:', error);
    // Fallback to alert
    alert(`${type.toUpperCase()}: ${message}`);
    return null;
  }
}

// Enhanced confirmation dialog with accessibility
function showConfirmDialog({
  title = 'Are you sure?',
  message = 'This action cannot be undone.',
  confirmText = 'Confirm',
  cancelText = 'Cancel',
  type = 'warning',
  size = 'modal-sm'
} = {}) {
  return new Promise((resolve) => {
    // Bootstrap fallback
    if (!window.bootstrap?.Modal) {
      logger.warn('Bootstrap Modal not available. Using browser confirm.');
      resolve(confirm(`${title}\n\n${message}`));
      return;
    }

    const modalId = `confirm-modal-${Date.now()}`;
    const modal = document.createElement('div');
    modal.className = 'modal fade';
    modal.id = modalId;
    modal.tabIndex = '-1';
    modal.setAttribute('aria-labelledby', `${modalId}-title`);
    modal.setAttribute('aria-describedby', `${modalId}-body`);
    modal.setAttribute('aria-hidden', 'true');

    // Get button colors based on type
    const buttonClass = type === 'danger' ? 'btn-danger' : 'btn-primary';

    modal.innerHTML = `
      <div class="modal-dialog ${size}">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title" id="${modalId}-title">
              <i class="fas fa-exclamation-triangle text-warning me-2" aria-hidden="true"></i>
              ${title}
            </h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close dialog"></button>
          </div>
          <div class="modal-body" id="${modalId}-body">
            ${message}
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal" autofocus>
              ${cancelText}
            </button>
            <button type="button" class="btn ${buttonClass}" data-confirm>
              ${confirmText}
            </button>
          </div>
        </div>
      </div>
    `;

    document.body.appendChild(modal);

    try {
      const modalInstance = new bootstrap.Modal(modal, {
        backdrop: 'static',
        keyboard: true
      });

      modalInstance.show();

      // Handle confirm button
      const confirmBtn = modal.querySelector('[data-confirm]');
      confirmBtn?.addEventListener('click', () => {
        modalInstance.hide();
        resolve(true);
      });

      // Handle modal close
      modal.addEventListener('hidden.bs.modal', () => {
        modal.remove();
        resolve(false);
      });

      // Focus management
      modal.addEventListener('shown.bs.modal', () => {
        const cancelBtn = modal.querySelector('[autofocus]');
        cancelBtn?.focus();
      });

    } catch (error) {
      logger.error('Failed to show confirmation dialog:', error);
      modal.remove();
      resolve(confirm(`${title}\n\n${message}`));
    }
  });
}

// Enhanced loading overlay with better UX
function showLoadingOverlay(message = 'Loading...', options = {}) {
  const {
    showSpinner = true,
    backgroundColor = 'rgba(0, 0, 0, 0.5)',
    zIndex = '9999',
    allowClose = false
  } = options;

  const overlayId = `loading-overlay-${Date.now()}`;
  const overlay = document.createElement('div');
  overlay.id = overlayId;
  overlay.className = 'loading-overlay position-fixed top-0 start-0 w-100 h-100 d-flex justify-content-center align-items-center';
  overlay.style.backgroundColor = backgroundColor;
  overlay.style.zIndex = zIndex;
  overlay.setAttribute('aria-live', 'polite');
  overlay.setAttribute('aria-label', `Loading: ${message}`);

  const spinnerHtml = showSpinner ? `
    <div class="spinner-border text-primary me-3" role="status">
      <span class="visually-hidden">Loading...</span>
    </div>
  ` : '';

  const closeButtonHtml = allowClose ? `
    <button type="button" class="btn-close position-absolute top-0 end-0 m-3"
            onclick="this.closest('.loading-overlay').remove(); document.body.style.overflow = '';"
            aria-label="Close loading"></button>
  ` : '';

  overlay.innerHTML = `
    <div class="bg-white rounded p-4 d-flex align-items-center position-relative shadow">
      ${closeButtonHtml}
      ${spinnerHtml}
      <span class="h5 mb-0">${message}</span>
    </div>
  `;

  document.body.appendChild(overlay);
  document.body.style.overflow = 'hidden';

  return {
    hide() {
      try {
        if (overlay?.parentNode) {
          overlay.remove();
          document.body.style.overflow = '';
        }
      } catch (error) {
        logger.warn('Error hiding loading overlay:', error);
      }
    },
    updateMessage(newMessage) {
      try {
        const messageElement = overlay.querySelector('.h5');
        if (messageElement) {
          messageElement.textContent = newMessage;
          overlay.setAttribute('aria-label', `Loading: ${newMessage}`);
        }
      } catch (error) {
        logger.warn('Error updating loading message:', error);
      }
    }
  };
}

// Enhanced toast helper functions with better defaults
const showErrorToast = (message, duration = 5000, options = {}) =>
  showToast(message, 'error', duration, { ...options, showIcon: true });

const showSuccessToast = (message, duration = 3000, options = {}) =>
  showToast(message, 'success', duration, { ...options, showIcon: true });

const showInfoToast = (message, duration = 3000, options = {}) =>
  showToast(message, 'info', duration, { ...options, showIcon: true });

const showWarningToast = (message, duration = 4000, options = {}) =>
  showToast(message, 'warning', duration, { ...options, showIcon: true });

// Utility function to clear all toasts
function clearAllToasts() {
  try {
    const container = document.getElementById('toast-container');
    if (container) {
      const toasts = container.querySelectorAll('.toast');
      toasts.forEach(toast => {
        const bsToast = bootstrap.Toast.getInstance(toast);
        if (bsToast) {
          bsToast.hide();
        } else {
          toast.remove();
        }
      });
    }
  } catch (error) {
    logger.warn('Error clearing toasts:', error);
  }
}

// Initialize notifications system
function initNotifications() {
  try {
    // Add global access for legacy compatibility
    if (typeof window !== 'undefined') {
      window.showToast = showToast;
      window.showErrorToast = showErrorToast;
      window.showSuccessToast = showSuccessToast;
      window.showInfoToast = showInfoToast;
      window.showWarningToast = showWarningToast;
      window.showConfirmDialog = showConfirmDialog;
      window.showLoadingOverlay = showLoadingOverlay;
      window.clearAllToasts = clearAllToasts;
    }

    logger.info('Toast notification system initialized');
  } catch (error) {
    logger.error('Failed to initialize notifications:', error);
  }
}

// Auto-initialize when DOM is ready
if (typeof document !== 'undefined') {
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initNotifications);
  } else {
    initNotifications();
  }
}

// Export everything
export {
  showToast,
  showErrorToast,
  showSuccessToast,
  showInfoToast,
  showWarningToast,
  showConfirmDialog,
  showLoadingOverlay,
  clearAllToasts,
  initNotifications,
  TOAST_CONFIG
};

// Default export for backward compatibility
export default {
  showToast,
  showErrorToast,
  showSuccessToast,
  showInfoToast,
  showWarningToast,
  showConfirmDialog,
  showLoadingOverlay,
  clearAllToasts,
  initNotifications,
  TOAST_CONFIG
};
