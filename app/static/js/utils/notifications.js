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
    info: 'fa-info-circle',
  },
};

// Get responsive container class based on screen size
function getResponsiveContainerClass() {
  const isMobile = window.innerWidth <= 768;
  return isMobile ? 'top-0 start-0 w-100' : 'top-0 end-0';
}

// Update container position on resize
function updateContainerPosition(container) {
  if (container) {
    container.className = `${TOAST_CONFIG.POSITION_CLASS} ${getResponsiveContainerClass()}`;
  }
}

// Toast container management with responsive positioning
function getOrCreateToastContainer() {
  let container = document.getElementById('toast-container');

  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    container.className = `${TOAST_CONFIG.POSITION_CLASS} ${getResponsiveContainerClass()}`;
    container.style.zIndex = TOAST_CONFIG.Z_INDEX;
    container.setAttribute('aria-live', 'polite');
    container.setAttribute('aria-label', 'Notifications');
    document.body.appendChild(container);

    // Add responsive listener
    window.addEventListener('resize', () => updateContainerPosition(container));
  }

  return container;
}

// Clean up old toasts to prevent memory leaks
function cleanupOldToasts() {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const toasts = container.querySelectorAll('.toast');
  if (toasts.length > TOAST_CONFIG.MAX_TOASTS) {
    const toastsToRemove = Array.from(toasts).slice(0, toasts.length - TOAST_CONFIG.MAX_TOASTS);
    toastsToRemove.forEach((toast) => {
      const bsToast = bootstrap.Toast.getInstance(toast);
      if (bsToast) {
        bsToast.dispose();
      }
      toast.remove();
    });
  }
}

// Create toast element with proper structure
function createToastElement(id, type, title, message, duration) {
  const iconClass = TOAST_CONFIG.ICONS[type] || TOAST_CONFIG.ICONS.info;

  return `
    <div id="${id}" class="toast align-items-center text-white bg-${type} border-0" role="alert" aria-live="assertive" aria-atomic="true">
      <div class="d-flex">
        <div class="toast-body d-flex align-items-center">
          <i class="fas ${iconClass} me-2"></i>
          <div>
            ${title ? `<strong>${title}</strong><br>` : ''}
            ${message}
          </div>
        </div>
        <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
      </div>
    </div>
  `;
}

// Show toast notification
export function showToast(title, message, type = 'info', duration = TOAST_CONFIG.DEFAULT_DURATION) {
  try {
    // Validate inputs
    if (!message) {
      console.warn('showToast: message is required');
      return;
    }

    // Clean up old toasts
    cleanupOldToasts();

    // Get or create container
    const container = getOrCreateToastContainer();
    if (!container) {
      console.error('Failed to create toast container');
      return;
    }

    // Create unique ID
    const toastId = `toast-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

    // Create toast HTML
    const toastHtml = createToastElement(toastId, type, title, message, duration);
    container.insertAdjacentHTML('beforeend', toastHtml);

    // Get toast element
    const toastElement = document.getElementById(toastId);
    if (!toastElement) {
      console.error('Failed to create toast element');
      return;
    }

    // Initialize Bootstrap toast
    const toast = new bootstrap.Toast(toastElement, {
      autohide: true,
      delay: duration,
    });

    // Add event listeners
    toastElement.addEventListener('hidden.bs.toast', () => {
      toastElement.remove();
    });

    // Show toast
    toast.show();

    // Log for debugging
    logger.info(`Toast shown: ${type} - ${title || 'No title'}: ${message}`);

  } catch (error) {
    console.error('Error showing toast:', error);
    logger.error('Failed to show toast', { error: error.message, title, message, type });
  }
}

// Convenience functions for different toast types
export function showSuccessToast(message, title = 'Success', duration = TOAST_CONFIG.DEFAULT_DURATION) {
  showToast(title, message, 'success', duration);
}

export function showErrorToast(message, title = 'Error', duration = TOAST_CONFIG.DEFAULT_DURATION) {
  showToast(title, message, 'danger', duration);
}

export function showWarningToast(message, title = 'Warning', duration = TOAST_CONFIG.DEFAULT_DURATION) {
  showToast(title, message, 'warning', duration);
}

export function showInfoToast(message, title = 'Info', duration = TOAST_CONFIG.DEFAULT_DURATION) {
  showToast(title, message, 'info', duration);
}

// Initialize notifications system
export function initNotifications() {
  // Make toast functions globally available
  window.showToast = showToast;
  window.showSuccessToast = showSuccessToast;
  window.showErrorToast = showErrorToast;
  window.showWarningToast = showWarningToast;
  window.showInfoToast = showInfoToast;

  // Log initialization
  logger.info('Notifications system initialized');
}
