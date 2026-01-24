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

// Ensure proper display of Tom Select wrapper and control
function ensureTagSelectDisplay(tagSelect) {
  if (!tagSelect || !tagSelect.wrapper) return;
  tagSelect.wrapper.style.width = '100%';
  tagSelect.wrapper.style.display = 'block';
  tagSelect.wrapper.style.position = 'relative';

  if (tagSelect.control) {
    tagSelect.control.style.width = '100%';
    tagSelect.control.style.display = 'flex';
    tagSelect.control.style.overflow = 'visible';
    tagSelect.control.style.maxHeight = 'none';
    tagSelect.control.style.cursor = 'text';
  }

  // Ensure input field is interactive
  if (tagSelect.control_input) {
    tagSelect.control_input.style.pointerEvents = 'auto';
    tagSelect.control_input.style.cursor = 'text';
    tagSelect.control_input.style.zIndex = '1';
  }
}

// Hide original select element completely
function hideOriginalSelect(selectElement) {
  if (!selectElement) return;

  selectElement.classList.add('ts-hidden');
  selectElement.setAttribute('aria-hidden', 'true');
  selectElement.setAttribute('tabindex', '-1');

  const hideStyles = {
    display: 'none',
    visibility: 'hidden',
    position: 'absolute',
    opacity: '0',
    pointerEvents: 'none',
    height: '0',
    width: '0',
    maxHeight: '0',
    maxWidth: '0',
    overflow: 'hidden',
    margin: '0',
    padding: '0',
    border: 'none',
    lineHeight: '0',
    fontSize: '0',
    top: '-9999px',
    left: '-9999px',
  };
  Object.assign(selectElement.style, hideStyles);

  // Also hide any input-sizer elements that Tom Select creates
  setTimeout(() => {
    const inputSizer = selectElement.parentElement?.querySelector('.input-sizer');
    if (inputSizer) {
      inputSizer.style.display = 'none';
      inputSizer.style.visibility = 'hidden';
      inputSizer.style.position = 'absolute';
      inputSizer.style.opacity = '0';
      inputSizer.style.height = '0';
      inputSizer.style.width = '0';
    }
  }, 0);
}

// Preload tags for tag select instance
function preloadTagsForSelect(tagSelectInstance) {
  setTimeout(() => {
    if (!tagSelectInstance || !tagSelectInstance.load) return;
    tagSelectInstance.load('', (options) => {
      if (options && options.length > 0) {
        tagSelectInstance.addOptions(options);
        tagSelectInstance.refreshOptions(false);
      }
    });
  }, 100);
}

// Handle already initialized tag selector
function refreshExistingTagSelect(filterTagsInput) {
  const { tagSelect } = filterTagsInput;
  hideOriginalSelect(filterTagsInput);
  ensureTagSelectDisplay(tagSelect);
  if (typeof tagSelect.refreshOptions === 'function') {
    tagSelect.refreshOptions(false);
  }
}

// Initialize new tag selector
function initializeNewTagSelect(filterTagsInput) {
  if (typeof TomSelect === 'undefined') {
    console.warn('TomSelect not available for filter tag selector');
    return;
  }

  if (typeof window.initializeTagSelector !== 'function') {
    return;
  }

  const urlParams = new URLSearchParams(window.location.search);
  const selectedTags = urlParams.getAll('tags');

  try {
    const tagSelectInstance = window.initializeTagSelector(filterTagsInput, {
      allowCreate: false,
      selectedTags,
    });

    if (tagSelectInstance) {
      hideOriginalSelect(filterTagsInput);
      ensureTagSelectDisplay(tagSelectInstance);
      preloadTagsForSelect(tagSelectInstance);
    }
  } catch (error) {
    console.error('Failed to initialize filter tag selector:', error);
  }
}

// Initialize tag selector when filter collapse is shown
function initFilterTagSelector() {
  // Initialize tag selector if filterTagsInput exists and TomSelect is available
  function tryInitTagSelector() {
    const filterTagsInput = document.getElementById('filterTagsInput');
    if (!filterTagsInput) return;

    // Check if already initialized - if so, just refresh options
    if (filterTagsInput.tagSelect) {
      refreshExistingTagSelect(filterTagsInput);
      return;
    }

    // Initialize new tag selector
    initializeNewTagSelect(filterTagsInput);
  }

  // Try to initialize immediately (in case collapse is already open or element exists)
  tryInitTagSelector();

  // Also initialize when collapse is shown (when it becomes visible)
  const filterCollapse = document.getElementById('filterCollapse');
  if (filterCollapse) {
    filterCollapse.addEventListener('shown.bs.collapse', () => {
      // Delay to ensure element is fully visible and DOM is ready
      setTimeout(() => {
        tryInitTagSelector();
        // Force refresh of Tom Select to ensure proper rendering when visible
        const filterTagsInput = document.getElementById('filterTagsInput');
        if (filterTagsInput && filterTagsInput.tagSelect) {
          const { tagSelect } = filterTagsInput;
          if (typeof tagSelect.refreshOptions === 'function') {
            tagSelect.refreshOptions(false);
          }
        }
      }, 150);
    });
  }

  // Also try after a short delay in case DOM isn't fully ready
  setTimeout(tryInitTagSelector, 500);
}

// Main initialization function
function init() {
  initTooltips();
  initViewToggle();
  initDeleteExpense();
  initPagination();
  initFaviconLoading();
  initFilterTagSelector();
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', init);
