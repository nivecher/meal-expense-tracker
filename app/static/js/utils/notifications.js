/**
 * Enhanced Toast Notification System
 * Provides centralized notification management with Bootstrap toasts
 *
 * @version 1.0.0
 * @author Meal Expense Tracker Team
 */

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

  console.log('✅ Notification system initialized');
}

/**
 * Create toast container if it doesn't exist
 */
function createToastContainer() {
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    container.className = 'toast-container position-fixed bottom-0 end-0 p-3';
    container.style.zIndex = '1090';
    document.body.appendChild(container);
  }
  return container;
}

/**
 * Show a toast notification
 * @param {string} title - Toast title
 * @param {string} message - Toast message
 * @param {string} type - Toast type (success, danger, warning, info)
 * @param {number} duration - Auto-hide duration in ms (0 = no auto-hide)
 * @param {Array} actions - Optional action buttons
 * @returns {Object} Toast handle with hide() method
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
  const autohide = duration > 0;

  const toast = new bootstrap.Toast(toastElement, {
    autohide,
    delay: autohide ? duration : 0,
  });

  toast.show();

  // Remove toast element after it's hidden
  toastElement.addEventListener('hidden.bs.toast', () => {
    toastElement.remove();
  });

  // Return toast handle for programmatic control
  return {
    id: toastId,
    hide: () => {
      try {
        toast.hide();
      } catch (e) {
        console.warn('Error hiding toast:', e);
      }
    },
  };
}

/**
 * Get appropriate icon for toast type
 * @param {string} type - Toast type
 * @returns {string} FontAwesome icon class
 */
function getIconForType(type) {
  const iconMap = {
    success: 'fa-check-circle',
    danger: 'fa-exclamation-triangle',
    warning: 'fa-exclamation-triangle',
    info: 'fa-info-circle',
  };
  return iconMap[type] || 'fa-info-circle';
}

/**
 * Show a confirmation toast with action buttons
 * @param {string} title - Toast title
 * @param {string} message - Toast message
 * @param {Array} actions - Action buttons array
 * @returns {Object} Toast handle
 */
export function showConfirmationToast(title, message, actions) {
  return showToast(title, message, 'warning', 0, actions);
}

/**
 * Clear all toasts
 */
export function clearAllToasts() {
  const container = document.getElementById('toast-container');
  if (container) {
    container.innerHTML = '';
  }
}

// Export for testing
export { createToastContainer, getIconForType };
