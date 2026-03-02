/**
 * Restaurant Detail Page Functionality
 * Handles progress bar initialization and edit mode navigation
 */

export function initRestaurantDetail() {
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
        window.location.href = `/restaurants/${restaurantId}?edit=True`;
      }
    });
  }

  // Handle cancel edit button navigation
  const cancelEditBtn = document.getElementById('cancel-edit');
  if (cancelEditBtn) {
    cancelEditBtn.addEventListener('click', () => {
      const { restaurantId } = cancelEditBtn.dataset;
      if (restaurantId) {
        window.location.href = `/restaurants/${restaurantId}`;
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
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', initRestaurantDetail);
