/**
 * Toast notification system
 */

// Use an IIFE to prevent global scope pollution
(function () {
  // Initialize toast container if it doesn't exist
  let toastContainer = document.getElementById('toast-container');
  if (!toastContainer) {
    toastContainer = document.createElement('div');
    toastContainer.id = 'toast-container';
    toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
    toastContainer.style.zIndex = '1100';
    document.body.appendChild(toastContainer);
  }

  /**
 * Show a toast notification
 * @param {string} message - The message to display
 * @param {string} type - The type of toast (success, error, warning, info)
 * @param {number} [duration=5000] - Duration in milliseconds
 */
  function showToast (message, type = 'info', duration = 5000) {
    // Create toast element
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-bg-${type} border-0 show`;
    toast.role = 'alert';
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');

    // Toast content
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                <i class="fas ${getToastIcon(type)} me-2"></i>
                ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
    `;

    // Add to container
    toastContainer.appendChild(toast);

    // Initialize Bootstrap toast
    const bsToast = new bootstrap.Toast(toast, {
      autohide: true,
      delay: duration,
    });

    // Remove from DOM after hide
    toast.addEventListener('hidden.bs.toast', () => {
      toast.remove();
    });

    // Show the toast
    bsToast.show();

    return bsToast;
  }

  /**
 * Get appropriate icon for toast type
 * @private
 */
  function getToastIcon (type) {
    const icons = {
      success: 'fa-check-circle',
      error: 'fa-times-circle',
      warning: 'fa-exclamation-triangle',
      info: 'fa-info-circle',
      primary: 'fa-flag',
      secondary: 'fa-bell',
      danger: 'fa-exclamation-circle',
    };

    return icons[type] || 'fa-info-circle';
  }

  // Add convenience methods
  showToast.success = (message, duration) => showToast(message, 'success', duration);
  showToast.error = (message, duration) => showToast(message, 'danger', duration);
  showToast.warning = (message, duration) => showToast(message, 'warning', duration);
  showToast.info = (message, duration) => showToast(message, 'info', duration);

  // Add to global scope
  window.showToast = showToast;
})();
