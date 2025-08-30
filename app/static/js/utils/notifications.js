/**
 * Simple notifications - toast, confirm, and loading
 */

// Get or create toast container
function getToastContainer() {
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    container.className = 'toast-container position-fixed bottom-0 end-0 p-3';
    document.body.appendChild(container);
  }
  return container;
}

// Create toast element
function createToast(message, type) {
  const toast = document.createElement('div');
  const bgClass = type === 'error' ? 'bg-danger' : `bg-${type}`;
  const title = type.charAt(0).toUpperCase() + type.slice(1);

  toast.className = `toast align-items-center text-white ${bgClass} border-0`;
  toast.setAttribute('role', 'alert');
  toast.innerHTML = `
    <div class="toast-header ${bgClass} text-white">
      <strong class="me-auto">${title}</strong>
      <button type="button" class="btn-close" data-bs-dismiss="toast"></button>
    </div>
    <div class="toast-body">${message}</div>
  `;

  return toast;
}

// Setup toast cleanup
function setupToastCleanup(toast, container) {
  toast.addEventListener('hidden.bs.toast', () => {
    toast.remove();
    if (container.children.length === 0) {
      container.remove();
    }
  });
}

// Show toast notification
function showToast(message, type = 'info', duration = 3000) {
  if (!bootstrap?.Toast) {
    alert(`${type.toUpperCase()}: ${message}`);
    return;
  }

  const container = getToastContainer();
  const toast = createToast(message, type);

  container.appendChild(toast);

  const bsToast = new bootstrap.Toast(toast, { autohide: true, delay: duration });
  bsToast.show();

  setupToastCleanup(toast, container);
  return bsToast;
}

// Show confirmation dialog
function showConfirmDialog({
  title = 'Are you sure?',
  message = 'This action cannot be undone.',
  confirmText = 'Confirm',
  cancelText = 'Cancel',
} = {}) {
  return new Promise((resolve) => {
    if (!bootstrap?.Modal) {
      resolve(confirm(`${title}\n\n${message}`));
      return;
    }

    const modalId = `confirm-modal-${Date.now()}`;
    const modal = document.createElement('div');
    modal.className = 'modal fade';
    modal.innerHTML = `
      <div class="modal-dialog">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">${title}</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
          </div>
          <div class="modal-body">${message}</div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">${cancelText}</button>
            <button type="button" class="btn btn-primary" data-confirm>${confirmText}</button>
          </div>
        </div>
      </div>
    `;

    document.body.appendChild(modal);
    const modalInstance = new bootstrap.Modal(modal);
    modalInstance.show();

    // Handle buttons
    modal.querySelector('[data-confirm]').addEventListener('click', () => {
      modalInstance.hide();
      resolve(true);
    });

    modal.addEventListener('hidden.bs.modal', () => {
      modal.remove();
      resolve(false);
    });
  });
}

// Show loading overlay
function showLoadingOverlay(message = 'Loading...') {
  const overlay = document.createElement('div');
  overlay.className = 'position-fixed top-0 start-0 w-100 h-100 d-flex justify-content-center align-items-center';
  overlay.style.cssText = 'background: rgba(0,0,0,0.5); z-index: 9999;';
  overlay.innerHTML = `
    <div class="bg-white rounded p-4 d-flex align-items-center">
      <div class="spinner-border text-primary me-3"></div>
      <span class="h5 mb-0">${message}</span>
    </div>
  `;

  document.body.appendChild(overlay);
  document.body.style.overflow = 'hidden';

  return {
    hide() {
      overlay.remove();
      document.body.style.overflow = '';
    },
  };
}

// Toast helper functions
const showErrorToast = (message, duration = 5000) => showToast(message, 'error', duration);
const showSuccessToast = (message, duration = 3000) => showToast(message, 'success', duration);
const showInfoToast = (message, duration = 3000) => showToast(message, 'info', duration);
const showWarningToast = (message, duration = 4000) => showToast(message, 'warning', duration);

// Export everything
export {
  showToast,
  showErrorToast,
  showSuccessToast,
  showInfoToast,
  showWarningToast,
  showConfirmDialog,
  showLoadingOverlay,
};

export default {
  showToast,
  showErrorToast,
  showSuccessToast,
  showInfoToast,
  showWarningToast,
  showConfirmDialog,
  showLoadingOverlay,
};
