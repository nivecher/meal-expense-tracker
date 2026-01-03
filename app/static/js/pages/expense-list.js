/**
 * Expense List Page
 * Handles view toggling, pagination, table sorting, delete functionality, and favicon loading
 */

import { initializeRobustFaviconHandling } from '../utils/robust-favicon-handler.js';

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

// Initialize Bootstrap tooltips
function initTooltips() {
  if (typeof bootstrap !== 'undefined') {
    // Handle standard tooltip triggers
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map((tooltipTriggerEl) => {
      return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Handle custom tooltip triggers (for elements that also have other data-bs-toggle attributes)
    const customTooltipTriggerList = [].slice.call(document.querySelectorAll('[data-tooltip="true"]'));
    customTooltipTriggerList.map((tooltipTriggerEl) => {
      return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Fix tooltip stuck issue on dropdown buttons
    const dropdownButtons = document.querySelectorAll('[data-bs-toggle="dropdown"]');
    dropdownButtons.forEach((button) => {
      button.addEventListener('show.bs.dropdown', () => {
        // Hide any visible tooltips when dropdown opens
        const tooltips = document.querySelectorAll('.tooltip');
        tooltips.forEach((tooltip) => {
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

// Delete expense functionality - simple form submission
function initDeleteExpense() {
  // Prevent multiple initialization
  if (window.deleteExpenseInitialized) return;
  window.deleteExpenseInitialized = true;

  const deleteButtons = document.querySelectorAll('[data-bs-target="#deleteExpenseModal"]');
  const deleteForm = document.getElementById('delete-expense-form');
  deleteButtons.forEach((button) => {
    // Check if listener already attached
    if (button.hasAttribute('data-delete-listener-attached')) return;
    button.setAttribute('data-delete-listener-attached', 'true');

    button.addEventListener('click', function() {
      const expenseId = this.getAttribute('data-expense-id');
      const expenseName = this.getAttribute('data-expense-description') || 'Expense';

      // Set the form action dynamically
      if (deleteForm && expenseId) {
        const deleteUrl = deleteForm.getAttribute('data-delete-url');
        deleteForm.action = `${deleteUrl}${expenseId}/delete`;
      }

      // Update modal with expense details
      const modalTitle = document.getElementById('deleteExpenseModalLabel');
      if (modalTitle) {
        modalTitle.textContent = `Delete Expense: ${expenseName}`;
      }

      // Let the modal open normally - no extra browser confirm needed
    });
  });

  // Handle the actual form submission (when user clicks "Delete Expense" in modal)
  if (deleteForm) {
    deleteForm.addEventListener('submit', () => {
      // Don't prevent default - let the form submit normally
      // This will redirect to the server, which will handle the delete and redirect back
      const submitButton = deleteForm.querySelector('button[type="submit"]');
      if (submitButton) {
        submitButton.disabled = true;
        submitButton.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Deleting...';
      }
    });
  }
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
    perPageSelect.addEventListener('change', (e) => {
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
