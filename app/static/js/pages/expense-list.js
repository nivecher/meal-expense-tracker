/**
 * Expense List Page
 * Handles view toggling, pagination, table sorting, delete functionality, and favicon loading
 */

import { initializeRobustFaviconHandling, handleFaviconError } from '../utils/robust-favicon-handler.js';

// Make handleFaviconError globally available for inline onerror handlers
window.handleFaviconError = handleFaviconError;

// Utility functions - defined first
function createToastContainer() {
  const container = document.createElement('div');
  container.id = 'toastContainer';
  container.className = 'toast-container position-fixed top-0 end-0 p-3';
  container.style.zIndex = '1055';
  document.body.appendChild(container);
  return container;
}

function showToast(title, message, type = 'info') {
  const toastContainer = document.getElementById('toastContainer') || createToastContainer();
  const toastId = `toast-${Date.now()}`;
  const toastHtml = `
        <div id="${toastId}" class="toast align-items-center text-white bg-${type} border-0" role="alert" aria-live="assertive" aria-atomic="true">
            <div class="d-flex">
                <div class="toast-body">
                    <strong>${title}</strong><br>${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        </div>
    `;
  toastContainer.insertAdjacentHTML('beforeend', toastHtml);

  const toastElement = document.getElementById(toastId);
  const toast = new bootstrap.Toast(toastElement, {
    autohide: true,
    delay: 5000,
  });
  toast.show();

  // Remove the toast element after it's hidden
  toastElement.addEventListener('hidden.bs.toast', () => {
    toastElement.remove();
  });
}

function setCookie(name, value, days) {
  const expires = new Date();
  expires.setTime(expires.getTime() + (days * 24 * 60 * 60 * 1000));
  document.cookie = `${name}=${value};expires=${expires.toUTCString()};path=/`;
}


// Initialize Bootstrap tooltips
function initTooltips() {
  if (typeof bootstrap !== 'undefined') {
    // Handle standard tooltip triggers
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    const tooltipList = tooltipTriggerList.map((tooltipTriggerEl) => {
      return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Handle custom tooltip triggers (for elements that also have other data-bs-toggle attributes)
    const customTooltipTriggerList = [].slice.call(document.querySelectorAll('[data-tooltip="true"]'));
    const customTooltipList = customTooltipTriggerList.map((tooltipTriggerEl) => {
      return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Fix tooltip stuck issue on dropdown buttons
    const dropdownButtons = document.querySelectorAll('[data-bs-toggle="dropdown"]');
    dropdownButtons.forEach(button => {
      button.addEventListener('show.bs.dropdown', function() {
        // Hide any visible tooltips when dropdown opens
        const tooltips = document.querySelectorAll('.tooltip');
        tooltips.forEach(tooltip => {
          if (tooltip.parentNode) {
            tooltip.parentNode.removeChild(tooltip);
          }
        });
      });
    });
  }
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
  const savedView = localStorage.getItem('expenseViewPreference') || 'card';

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
      localStorage.setItem('expenseViewPreference', 'card');
    }
  });

  tableView.addEventListener('change', function() {
    if (this.checked) {
      tableViewContainer.classList.remove('d-none');
      cardViewContainer.classList.add('d-none');
      localStorage.setItem('expenseViewPreference', 'table');
    }
  });
}

// Delete expense functionality
function initDeleteExpense() {
  const deleteButtons = document.querySelectorAll('[data-action="delete-expense"]');
  deleteButtons.forEach((button) => {
    button.addEventListener('click', function() {
      const expenseId = this.getAttribute('data-expense-id');
      const expenseName = this.getAttribute('data-expense-name');
      const modalTitle = document.getElementById('deleteModalLabel');

      if (modalTitle) {
        modalTitle.textContent = `Delete Expense: ${expenseName}`;
      }

      // Set up the delete button in the modal
      const confirmDeleteBtn = document.getElementById('confirmDeleteBtn');
      if (confirmDeleteBtn) {
        confirmDeleteBtn.onclick = () => {
          fetch(`/expenses/delete/${expenseId}`, {
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
                showToast('Success', 'Expense deleted successfully.', 'success');
                // Remove the row from the table
                const row = document.querySelector(`[data-expense-id="${expenseId}"]`);
                if (row) {
                  row.remove();
                }
                // Close the modal
                const modal = bootstrap.Modal.getInstance(document.getElementById('deleteModal'));
                if (modal) {
                  modal.hide();
                }
              } else {
                return response.json().then((data) => {
                  if (data.error) {
                    showToast('Error', data.error, 'danger');
                  } else {
                    window.location.reload();
                  }
                });
              }
            })
            .catch((error) => {
              console.error('Error:', error);
              showToast('Error', 'An error occurred while deleting the expense.', 'danger');
            });
        };
      }
    });
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
        setCookie('expensePage', page, 7);
        window.location.href = this.href;
      }
    });
  });

  // Handle page size change
  const perPageSelect = document.getElementById('per_page');
  if (perPageSelect) {
    perPageSelect.addEventListener('change', function(e) {
      const newPerPage = e.target.value;

      // Save page size preference to cookie
      setCookie('expense_page_size', newPerPage, 365);

      // Update URL with new page size and reset to page 1
      const url = new URL(window.location);
      url.searchParams.set('per_page', newPerPage);
      url.searchParams.set('page', '1'); // Reset to first page

      // Navigate to new URL
      window.location.href = url.toString();
    });
  }
}


// Favicon loading functionality
function initFaviconLoading() {
  // Initialize robust favicon handling for any new elements
  initializeRobustFaviconHandling('.restaurant-favicon');
  initializeRobustFaviconHandling('.restaurant-favicon-table');
}

// Main initialization function
function init() {
  initTooltips();
  initViewToggle();
  initDeleteExpense();
  initPagination();
  initFaviconLoading();
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', init);
