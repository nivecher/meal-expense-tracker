/**
 * Restaurant Detail Page Functionality
 * Handles progress bar initialization and edit mode navigation
 */

import { attachIntlPhoneFormatting } from '../utils/contact-fields.js';

function isSafeInternalUrl(url) {
  if (!url) return false;

  try {
    const parsed = new URL(url, window.location.origin);
    return parsed.origin === window.location.origin && parsed.pathname.startsWith('/');
  } catch {
    return false;
  }
}

function navigateToRestaurant(restaurantId, search = '') {
  if (!restaurantId) return;
  window.location.assign(`/restaurants/${encodeURIComponent(restaurantId)}${search}`);
}

function handleExpenseDeleteSubmit(event) {
  const form = event.target;
  if (!(form instanceof HTMLFormElement) || !form.action) return;
  if (!form.action.includes('/expenses/') || !form.action.includes('/delete')) return;

  const expenseHistory = document.getElementById('expense-history');
  const restaurantId = expenseHistory?.getAttribute('data-restaurant-id');
  if (!restaurantId) return;

  event.preventDefault();

  const submitButton = form.querySelector('button[type="submit"]');
  if (submitButton) {
    submitButton.disabled = true;
    submitButton.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Deleting...';
  }

  const formData = new FormData(form);
  fetch(form.action, {
    method: 'POST',
    body: formData,
  })
    .then((response) => {
      if (response.redirected && isSafeInternalUrl(response.url)) {
        window.location.assign(response.url);
        return;
      }
      navigateToRestaurant(restaurantId);
    })
    .catch(() => {
      navigateToRestaurant(restaurantId);
    })
    .finally(() => {
      const submitButton = form.querySelector('button[type="submit"]');
      if (submitButton) {
        submitButton.disabled = false;
        submitButton.innerHTML = '<i class="fas fa-trash-alt me-1"></i>Delete Expense';
      }
    });
}

export function initRestaurantDetail() {
  attachIntlPhoneFormatting('#restaurant-form', ['phone']);

  // Set progress bar width from data attribute
  const progressBar = document.querySelector('[data-width]');
  if (progressBar) {
    progressBar.style.width = `${progressBar.dataset.width}%`;
  }

  // Handle edit button navigation
  const editBtn = document.getElementById('edit-btn');
  if (editBtn) {
    editBtn.addEventListener('click', () => {
      const { restaurantId } = editBtn.dataset;
      if (restaurantId) {
        navigateToRestaurant(restaurantId, '?edit=True');
      }
    });
  }

  // Handle cancel edit button navigation
  const cancelEditBtn = document.getElementById('cancel-edit');
  if (cancelEditBtn) {
    cancelEditBtn.addEventListener('click', () => {
      const { restaurantId } = cancelEditBtn.dataset;
      if (restaurantId) {
        navigateToRestaurant(restaurantId);
      }
    });
  }

  function buildRestaurantDeleteUrl(baseUrl, restaurantId) {
    if (!baseUrl || !restaurantId) return '';
    let normalizedBase = baseUrl;
    if (normalizedBase.endsWith('/')) normalizedBase = normalizedBase.slice(0, -1);
    return `${normalizedBase}/${restaurantId}`;
  }

  function ensureDeleteRestaurantModal() {
    const existing = document.getElementById('deleteRestaurantModal');
    if (existing) return existing;

    const template = document.getElementById('deleteRestaurantModalTemplate');
    if (!(template instanceof HTMLTemplateElement)) return null;

    const modalNode = template.content.firstElementChild?.cloneNode(true);
    if (!(modalNode instanceof HTMLElement)) return null;

    document.body.appendChild(modalNode);

    const deleteForm = modalNode.querySelector('#deleteRestaurantForm');
    if (deleteForm instanceof HTMLFormElement && deleteForm.dataset.listenerAttached !== 'true') {
      deleteForm.dataset.listenerAttached = 'true';
      deleteForm.addEventListener('submit', () => {
        const submitButton = deleteForm.querySelector('button[type="submit"]');
        if (submitButton) {
          submitButton.disabled = true;
          submitButton.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Deleting...';
        }
      });
    }

    modalNode.addEventListener('hidden.bs.modal', () => {
      modalNode.remove();
    });

    return modalNode;
  }

  function openRestaurantDeleteModal(restaurantId, restaurantName) {
    if (!restaurantId) return;

    const modalElement = ensureDeleteRestaurantModal();
    if (!modalElement) return;

    const modalTitle = modalElement.querySelector('#deleteRestaurantModalLabel');
    const restaurantNameElement = modalElement.querySelector('#restaurantName');
    const deleteForm = modalElement.querySelector('#deleteRestaurantForm');

    if (modalTitle) {
      modalTitle.textContent = `Delete Restaurant: ${restaurantName || ''}`;
    }

    if (restaurantNameElement) {
      restaurantNameElement.textContent = restaurantName || '';
    }

    if (deleteForm) {
      const deleteUrlBase = deleteForm.getAttribute('data-delete-url') || '';
      const deleteUrl = buildRestaurantDeleteUrl(deleteUrlBase, restaurantId);
      if (deleteUrl) {
        deleteForm.action = deleteUrl;
      }
    }

    const modalInstance = bootstrap.Modal.getInstance(modalElement) || new bootstrap.Modal(modalElement);
    modalInstance.show();
  }

  const deleteButton = document.querySelector('[data-action="delete-restaurant"][data-restaurant-id]');
  if (deleteButton) {
    deleteButton.addEventListener('click', (event) => {
      event.preventDefault();
      event.stopPropagation();
      event.stopImmediatePropagation();
      const restaurantId = deleteButton.getAttribute('data-restaurant-id') || '';
      const restaurantName = deleteButton.getAttribute('data-restaurant-name') || '';
      openRestaurantDeleteModal(restaurantId, restaurantName);
    });
  }

  // Intercept expense delete form submit so we can reload the detail page after delete
  const expenseHistory = document.getElementById('expense-history');
  if (expenseHistory) {
    const restaurantId = expenseHistory.getAttribute('data-restaurant-id');
    if (restaurantId) {
      document.addEventListener('submit', handleExpenseDeleteSubmit);
    }
  }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', initRestaurantDetail);
