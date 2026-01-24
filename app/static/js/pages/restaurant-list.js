/**
 * Restaurant List Component
 * Handles view toggling, pagination, table sorting, and delete functionality
 */

import { initializeRobustFaviconHandling } from '../utils/robust-favicon-handler.js';
import { toast } from '../utils/notifications.js';

function setCookie(name, value, days) {
  const expires = new Date();
  expires.setTime(expires.getTime() + (days * 24 * 60 * 60 * 1000));
  // For CORS compatibility: use SameSite=None; Secure in HTTPS environments
  // This ensures cookies work when CloudFront proxies to API Gateway
  const isHttps = window.location.protocol === 'https:';
  const sameSite = isHttps ? 'SameSite=None' : 'SameSite=Lax';
  const secureFlag = isHttps ? '; Secure' : '';
  document.cookie = `${name}=${value};expires=${expires.toUTCString()};path=/;${sameSite}${secureFlag}`;
}

// View toggle functionality
function initViewToggle() {
  const cardView = document.getElementById('card-view');
  const tableView = document.getElementById('table-view');
  const cardViewContainer = document.getElementById('card-view-container');
  const tableViewContainer = document.getElementById('table-view-container');

  if (!cardView || !tableView || !cardViewContainer || !tableViewContainer) {
    return;
  }

  // Load saved view preference or default to card view
  const savedView = localStorage.getItem('restaurantViewPreference') || 'card';

  if (savedView === 'table') {
    tableView.checked = true;
    cardViewContainer.classList.add('d-none');
    tableViewContainer.classList.remove('d-none');
  }

  // Add event listeners for view toggle
  cardView.addEventListener('change', function() {
    if (this.checked) {
      cardViewContainer.classList.remove('d-none');
      tableViewContainer.classList.add('d-none');
      localStorage.setItem('restaurantViewPreference', 'card');
    }
  });

  tableView.addEventListener('change', function() {
    if (this.checked) {
      tableViewContainer.classList.remove('d-none');
      cardViewContainer.classList.add('d-none');
      localStorage.setItem('restaurantViewPreference', 'table');
    }
  });
}

// Helper function to clean up modal backdrop
function cleanupModalBackdrop() {
  const backdrops = document.querySelectorAll('.modal-backdrop');
  backdrops.forEach((backdrop) => {
    backdrop.remove();
  });
  document.body.classList.remove('modal-open');
  document.body.style.overflow = '';
  document.body.style.paddingRight = '';
}

// Delete restaurant functionality - optimized with event delegation
function initDeleteRestaurant() {
  // Use event delegation for better performance
  document.addEventListener('click', (event) => {
    const button = event.target.closest('[data-action="delete-restaurant"]');
    if (!button) return;

    event.preventDefault();

    const restaurantId = button.getAttribute('data-restaurant-id');
    const restaurantName = button.getAttribute('data-restaurant-name');
    const modalTitle = document.getElementById('deleteRestaurantModalLabel');
    const restaurantNameElement = document.getElementById('restaurantName');
    const deleteForm = document.getElementById('deleteRestaurantForm');

    if (modalTitle) {
      modalTitle.textContent = `Delete Restaurant: ${restaurantName}`;
    }

    if (restaurantNameElement) {
      restaurantNameElement.textContent = restaurantName;
    }

    if (deleteForm) {
      const deleteUrl = deleteForm.getAttribute('data-delete-url');
      deleteForm.action = `${deleteUrl}/${restaurantId}`;
    }

    // Show the modal
    const modalElement = document.getElementById('deleteRestaurantModal');
    const modal = new bootstrap.Modal(modalElement);
    modal.show();

    // Handle form submission
    if (deleteForm) {
      deleteForm.onsubmit = (e) => {
        e.preventDefault();

        fetch(`/restaurants/delete/${restaurantId}`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest',
          },
          body: JSON.stringify({
            csrf_token: document.querySelector('input[name="csrf_token"]').value,
          }),
        })
          .then((response) => {
            if (response.ok) {
              toast.success('Restaurant deleted successfully.');
              // Remove restaurant from both card view and table view
              const elementsWithId = document.querySelectorAll(`[data-restaurant-id="${restaurantId}"]`);
              elementsWithId.forEach((element) => {
                // For card view: find the parent .col div and remove it
                const cardContainer = element.closest('.col');
                if (cardContainer) {
                  cardContainer.remove();
                }
                // For table view: find the parent tr and remove it
                const tableRow = element.closest('tr');
                if (tableRow) {
                  tableRow.remove();
                }
              });
              // Close the modal and clean up backdrop
              modal.hide();
              // Wait for modal to fully close, then remove any leftover backdrop
              if (modalElement) {
                modalElement.addEventListener('hidden.bs.modal', cleanupModalBackdrop, { once: true });
              }
            } else {
              return response.json().then((data) => {
                if (data.error) {
                  toast.error(data.error);
                } else {
                  window.location.reload();
                }
              });
            }
          })
          .catch((error) => {
            console.error('Error:', error);
            toast.error('An error occurred while deleting the restaurant.');
            // Clean up backdrop on error as well
            cleanupModalBackdrop();
          });
      };
    }
  });
}

// Pagination functionality
function initPagination() {
  const paginationLinks = document.querySelectorAll('.pagination a');
  paginationLinks.forEach((link) => {
    link.addEventListener('click', function(e) {
      e.preventDefault();
      const page = this.getAttribute('data-page');
      if (page) {
        setCookie('restaurantPage', page, 7);
        window.location.href = this.href;
      }
    });
  });

  // Handle page size change
  const perPageSelect = document.getElementById('per_page');
  if (perPageSelect) {
    perPageSelect.addEventListener('change', (e) => {
      const newPerPage = e.target.value;

      // Save page size preference to cookie
      setCookie('restaurant_page_size', newPerPage, 365);

      // Update URL with new page size and reset to page 1
      const url = new URL(window.location);
      url.searchParams.set('per_page', newPerPage);
      url.searchParams.set('page', '1'); // Reset to first page

      // Navigate to new URL
      window.location.href = url.toString();
    });
  }
}

// Favicon loading functionality - optimized for performance
function initFaviconLoading() {
  // Defer favicon loading to avoid blocking the main thread
  const loadFaviconsWhenIdle = () => {
    initializeRobustFaviconHandling('.restaurant-favicon');
    initializeRobustFaviconHandling('.restaurant-favicon-table');
  };

  // Use requestIdleCallback if available, otherwise setTimeout
  if (window.requestIdleCallback) {
    requestIdleCallback(loadFaviconsWhenIdle, { timeout: 200 });
  } else {
    setTimeout(loadFaviconsWhenIdle, 50);
  }
}

// Tooltip initialization - optimized for performance
function initTooltips() {
  if (typeof bootstrap === 'undefined') {
    return;
  }

  // Use requestIdleCallback for non-critical tooltip initialization
  const initTooltipsWhenIdle = () => {
    // Handle standard tooltip triggers
    const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    tooltipTriggerList.forEach((tooltipTriggerEl) => {
      new bootstrap.Tooltip(tooltipTriggerEl); // eslint-disable-line no-new
    });

    // Handle custom tooltip triggers (for elements that also have other data-bs-toggle attributes)
    const customTooltipTriggerList = document.querySelectorAll('[data-tooltip="true"]');
    customTooltipTriggerList.forEach((tooltipTriggerEl) => {
      new bootstrap.Tooltip(tooltipTriggerEl); // eslint-disable-line no-new
    });
  };

  // Use requestIdleCallback if available, otherwise setTimeout
  if (window.requestIdleCallback) {
    requestIdleCallback(initTooltipsWhenIdle, { timeout: 100 });
  } else {
    setTimeout(initTooltipsWhenIdle, 0);
  }

  // Fix tooltip stuck issue on dropdown buttons - use event delegation
  document.addEventListener('show.bs.dropdown', (_event) => {
    // Hide any visible tooltips when dropdown opens
    const tooltips = document.querySelectorAll('.tooltip');
    tooltips.forEach((tooltip) => {
      if (tooltip.parentNode) {
        tooltip.parentNode.removeChild(tooltip);
      }
    });
  });
}

// Main initialization function - optimized for performance
function init() {
  // Critical functionality that must run immediately
  initViewToggle();
  initDeleteRestaurant();
  initPagination();

  // Non-critical functionality that can be deferred
  initFaviconLoading();
  initTooltips();
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', init);
