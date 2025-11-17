/**
 * Simple Toast Notification System
 * Clean, minimal toast notifications for the app
 */

/**
 * Get icon class for toast type
 */
function getIcon(type) {
  const icons = {
    success: 'fa-check-circle',
    error: 'fa-exclamation-circle',
    warning: 'fa-exclamation-triangle',
    info: 'fa-info-circle',
  };
  return icons[type] || icons.info;
}

/**
 * Create or get toast container
 */
function getContainer() {
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    container.className = 'toast-container position-fixed bottom-0 end-0 p-3';
    container.style.zIndex = '9999';
    document.body.appendChild(container);
  }
  return container;
}

/**
 * Show a toast notification
 * @param {string} message - Message to display
 * @param {string} type - Type: success, error, warning, info
 * @param {number} duration - Auto-hide delay in ms (0 = no auto-hide)
 */
export function showToast(message, type = 'info', duration = 4000) {
  const container = getContainer();
  const id = `toast-${Date.now()}`;

  const bgClass = `bg-${type}`;
  const textClass = type === 'warning' ? 'text-dark' : 'text-white';
  const iconClass = getIcon(type);

  const html = `
    <div id="${id}" class="toast ${bgClass} ${textClass}" role="alert" aria-live="assertive" aria-atomic="true">
      <div class="toast-body">
        <i class="fas ${iconClass} me-2"></i>
        ${message}
        <button type="button" class="btn-close ${type === 'warning' ? 'btn-close-dark' : 'btn-close-white'}"
                data-bs-dismiss="toast" aria-label="Close"></button>
      </div>
    </div>
  `;

  container.insertAdjacentHTML('beforeend', html);

  const element = document.getElementById(id);
  const toast = new bootstrap.Toast(element, {
    autohide: duration > 0,
    delay: duration,
  });

  toast.show();

  // Clean up after hide
  element.addEventListener('hidden.bs.toast', () => {
    element.remove();
  });

  return toast;
}

/**
 * Convenience functions
 */
export const toast = {
  success: (message, duration = 4000) => showToast(message, 'success', duration),
  error: (message, duration = 0) => showToast(message, 'error', duration),
  warning: (message, duration = 6000) => showToast(message, 'warning', duration),
  info: (message, duration = 4000) => showToast(message, 'info', duration),
};
