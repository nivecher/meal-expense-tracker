/**
 * Enhanced Toast Notification System
 * Provides centralized notification management with Bootstrap toasts
 *
 * @version 1.0.0
 * @author Meal Expense Tracker Team
 */

/**
 * Get icon class for toast type
 * @param {string} type - Toast type (success, error, warning, info)
 * @returns {string} Font Awesome icon class
 */
function getIconForType(type) {
  const icons = {
    success: 'fa-check-circle',
    danger: 'fa-exclamation-circle',
    error: 'fa-exclamation-circle',
    warning: 'fa-exclamation-triangle',
    info: 'fa-info-circle',
  };
  return icons[type] || icons.info;
}

/**
 * Create toast container if it doesn't exist
 * @returns {HTMLElement} Toast container element
 */
function createToastContainer() {
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    container.className = 'toast-container position-fixed top-0 end-0 p-3';
    container.style.zIndex = '9999';
    document.body.appendChild(container);
  }
  return container;
}

/**
 * Show a toast notification
 * @param {string} title - Toast title
 * @param {string} message - Toast message
 * @param {string} type - Toast type (success, error, warning, info)
 * @param {number} duration - Auto-hide duration in ms (0 = no auto-hide)
 * @param {Array} actions - Optional action buttons
 */
export function showToast(title, message, type = 'info', duration = 5000, actions = null) {
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
                 onclick="${action.onclick || ''}">${action.text}</button>`,
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
        ${message}
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

/**
 * Initialize the notification system
 * Sets up global toast functions and ensures toast container exists
 */
export function initNotifications() {
  // Ensure toast container exists
  createToastContainer();

  // Set up global toast functions
  window.showSuccessToast = (message, title = 'Success', duration = 4000) => {
    showToast(title, message, 'success', duration);
  };

  window.showErrorToast = (message, title = 'Error', duration = 0) => {
    showToast(title, message, 'danger', duration);
  };

  window.showWarningToast = (message, title = 'Warning', duration = 7000) => {
    showToast(title, message, 'warning', duration);
  };

  window.showInfoToast = (message, title = 'Info', duration = 5000) => {
    showToast(title, message, 'info', duration);
  };

  // Legacy compatibility
  window.showToast = showToast;
}

/**
 * Show success notification
 * @param {string} message - Success message
 * @param {string} title - Optional title (default: 'Success')
 * @param {number} duration - Auto-hide duration (default: 4000ms)
 */
export function showSuccess(message, title = 'Success', duration = 4000) {
  return showToast(title, message, 'success', duration);
}

/**
 * Show error notification
 * @param {string} message - Error message
 * @param {string} title - Optional title (default: 'Error')
 * @param {number} duration - Auto-hide duration (default: 0 = no auto-hide)
 */
export function showError(message, title = 'Error', duration = 0) {
  return showToast(title, message, 'danger', duration);
}

/**
 * Show warning notification
 * @param {string} message - Warning message
 * @param {string} title - Optional title (default: 'Warning')
 * @param {number} duration - Auto-hide duration (default: 7000ms)
 */
export function showWarning(message, title = 'Warning', duration = 7000) {
  return showToast(title, message, 'warning', duration);
}

/**
 * Show info notification
 * @param {string} message - Info message
 * @param {string} title - Optional title (default: 'Info')
 * @param {number} duration - Auto-hide duration (default: 5000ms)
 */
export function showInfo(message, title = 'Info', duration = 5000) {
  return showToast(title, message, 'info', duration);
}
