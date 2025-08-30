/**
 * UI Feedback Utility - TIGER-compliant
 * Standardized success/error messaging across the application
 */

function show_success_message(message, container_id = 'messages') {
  const container = document.getElementById(container_id);
  if (!container) {
    console.warn(`Message container '${container_id}' not found, using fallback`);
    show_toast_message(message, 'success');
    return;
  }

  container.innerHTML = `
    <div class="alert alert-success alert-dismissible fade show" role="alert">
      <i class="fas fa-check-circle me-2"></i>
      <strong>Success!</strong> ${message}
      <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    </div>
  `;

  container.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function show_error_message(message, container_id = 'messages') {
  const container = document.getElementById(container_id);
  if (!container) {
    console.warn(`Message container '${container_id}' not found, using fallback`);
    show_toast_message(message, 'error');
    return;
  }

  container.innerHTML = `
    <div class="alert alert-danger alert-dismissible fade show" role="alert">
      <i class="fas fa-exclamation-triangle me-2"></i>
      <strong>Error:</strong> ${message}
      <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    </div>
  `;

  container.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function show_warning_message(message, container_id = 'messages') {
  const container = document.getElementById(container_id);
  if (!container) {
    console.warn(`Message container '${container_id}' not found, using fallback`);
    show_toast_message(message, 'warning');
    return;
  }

  container.innerHTML = `
    <div class="alert alert-warning alert-dismissible fade show" role="alert">
      <i class="fas fa-info-circle me-2"></i>
      <strong>Notice:</strong> ${message}
      <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    </div>
  `;

  container.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function show_toast_message(message, type = 'info') {
  const toast_container = get_or_create_toast_container();
  const toast_id = `toast-${Date.now()}`;

  const icon_map = {
    success: 'fas fa-check-circle text-success',
    error: 'fas fa-exclamation-triangle text-danger',
    warning: 'fas fa-info-circle text-warning',
    info: 'fas fa-info-circle text-info',
  };

  const toast_html = `
    <div id="${toast_id}" class="toast show" role="alert">
      <div class="toast-header">
        <i class="${icon_map[type] || icon_map.info} me-2"></i>
        <strong class="me-auto">${capitalize(type)}</strong>
        <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close"></button>
      </div>
      <div class="toast-body">${message}</div>
    </div>
  `;

  toast_container.insertAdjacentHTML('beforeend', toast_html);

  // Auto-remove after 5 seconds
  setTimeout(() => {
    const toast_element = document.getElementById(toast_id);
    if (toast_element) toast_element.remove();
  }, 5000);
}

function get_or_create_toast_container() {
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

function capitalize(str) {
  return str.charAt(0).toUpperCase() + str.slice(1);
}

function clear_messages(container_id = 'messages') {
  const container = document.getElementById(container_id);
  if (container) {
    container.innerHTML = '';
  }
}

// Export with both naming conventions for compatibility
export {
  show_success_message,
  show_error_message,
  show_warning_message,
  show_toast_message,
  clear_messages,
  // Aliases for compatibility
  show_success_message as showSuccess,
  show_error_message as showError,
  show_warning_message as showWarning,
};
