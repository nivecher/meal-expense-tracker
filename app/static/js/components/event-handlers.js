/**
 * Centralized Event Handlers
 * Replaces inline onclick handlers with proper event delegation
 *
 * @version 1.0.0
 * @author Meal Expense Tracker Team
 */

/**
 * EventHandlers class for managing global event delegation
 * Follows TIGER principles: Safety, Performance, Developer Experience
 */
export class EventHandlers {
  constructor() {
    this.handlers = new Map();
    this.init();
  }

  /**
   * Initialize event handlers
   * Sets up event delegation for common UI interactions
   */
  init() {
    this.setupFormHandlers();
    this.setupButtonHandlers();
    this.setupLinkHandlers();
    this.setupModalHandlers();
    this.setupDropdownHandlers();

    // Only show debug messages if debug mode is enabled
    if (window.location.search.includes('debug=true') || localStorage.getItem('debugMode') === 'true') {
      console.warn('✅ Event handlers initialized');
    }
  }

  /**
   * Setup form-related event handlers
   * Handles form submission, validation, and auto-save
   */
  setupFormHandlers() {
    // Form submission with loading states
    document.addEventListener('submit', (event) => {
      const form = event.target;
      if (form.tagName !== 'FORM') return;

      // Handle forms with data-loading attribute
      const submitButton = form.querySelector('[type="submit"]');
      if (submitButton && submitButton.dataset.loading) {
        this.handleFormSubmission(form, submitButton);
      }
    });

    // Auto-save functionality for forms with data-autosave
    document.addEventListener('input', (event) => {
      const form = event.target.closest('form');
      if (form && form.dataset.autosave) {
        this.handleAutoSave(form, event.target);
      }
    });
  }

  /**
   * Setup button-related event handlers
   * Handles loading states, confirmations, and actions
   */
  setupButtonHandlers() {
    // Loading buttons
    document.addEventListener('click', (event) => {
      const button = event.target.closest('[data-loading]');
      if (button) {
        this.handleLoadingButton(button);
      }
    });

    // Confirmation buttons
    document.addEventListener('click', (event) => {
      const button = event.target.closest('[data-confirm]');
      if (button) {
        event.preventDefault();
        this.handleConfirmationButton(button);
      }
    });

    // Copy to clipboard buttons
    document.addEventListener('click', (event) => {
      const button = event.target.closest('[data-copy]');
      if (button) {
        event.preventDefault();
        this.handleCopyButton(button);
      }
    });
  }

  /**
   * Setup link-related event handlers
   * Handles external links, navigation, and smooth scrolling
   */
  setupLinkHandlers() {
    // External link handling
    document.addEventListener('click', (event) => {
      const link = event.target.closest('a[href^="http"]');
      if (link && !link.target) {
        // Open external links in new tab
        link.target = '_blank';
        link.rel = 'noopener noreferrer';
      }
    });

    // Smooth scrolling for anchor links
    document.addEventListener('click', (event) => {
      const link = event.target.closest('a[href^="#"]');
      if (link) {
        event.preventDefault();
        this.handleSmoothScroll(link);
      }
    });
  }

  /**
   * Setup modal-related event handlers
   * Handles modal opening, closing, and form submission
   */
  setupModalHandlers() {
    // Modal form submission
    document.addEventListener('submit', (event) => {
      const form = event.target;
      const modal = form.closest('.modal');
      if (modal && !form.hasAttribute('data-skip-ajax')) {
        event.preventDefault();
        this.handleModalFormSubmission(form, modal);
      }
    });

    // Modal cleanup on close
    document.addEventListener('hidden.bs.modal', (event) => {
      const modal = event.target;
      this.cleanupModal(modal);
    });
  }

  /**
   * Setup dropdown-related event handlers
   * Handles dropdown interactions and keyboard navigation
   */
  setupDropdownHandlers() {
    // Keyboard navigation for dropdowns
    document.addEventListener('keydown', (event) => {
      const dropdown = event.target.closest('.dropdown');
      if (dropdown) {
        this.handleDropdownKeyboard(event, dropdown);
      }
    });
  }

  /**
   * Handle form submission with loading state
   * @param {HTMLFormElement} form - The form being submitted
   * @param {HTMLButtonElement} submitButton - The submit button
   */
  handleFormSubmission(form, submitButton) {
    const originalText = submitButton.innerHTML;
    const loadingText = submitButton.dataset.loading || 'Processing...';

    // Set loading state
    submitButton.disabled = true;
    submitButton.innerHTML = `
      <span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
      ${loadingText}
    `;

    // Auto-restore after timeout (safety measure)
    setTimeout(() => {
      if (submitButton.disabled) {
        submitButton.disabled = false;
        submitButton.innerHTML = originalText;
        console.warn('Auto-restored button after timeout');
      }
    }, 30000);
  }

  /**
   * Handle auto-save functionality
   * @param {HTMLFormElement} form - The form to auto-save
   * @param {HTMLElement} input - The input that changed
   */
  handleAutoSave(form, _input) {
    // Debounce auto-save to avoid excessive requests
    clearTimeout(this.autoSaveTimeout);
    this.autoSaveTimeout = setTimeout(() => {
      this.performAutoSave(form);
    }, 1000);
  }

  /**
   * Perform auto-save operation
   * @param {HTMLFormElement} form - The form to save
   */
  async performAutoSave(form) {
    try {
      const formData = new FormData(form);
      const response = await fetch(form.action || window.location.href, {
        method: 'POST',
        body: formData,
        headers: {
          'X-CSRFToken': this.getCSRFToken(),
        },
      });

      if (response.ok) {
        // Show subtle success indicator
        this.showAutoSaveIndicator('Saved', 'success');
      } else {
        throw new Error('Auto-save failed');
      }
    } catch {
      console.warn('Auto-save failed:', error);
      this.showAutoSaveIndicator('Save failed', 'danger');
    }
  }

  /**
   * Handle loading button clicks
   * @param {HTMLButtonElement} button - The button clicked
   */
  handleLoadingButton(button) {
    const originalText = button.innerHTML;
    const loadingText = button.dataset.loading || 'Loading...';

    button.disabled = true;
    button.innerHTML = `
      <span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
      ${loadingText}
    `;

    // Auto-restore after 30 seconds
    setTimeout(() => {
      if (button.disabled) {
        button.disabled = false;
        button.innerHTML = originalText;
      }
    }, 30000);
  }

  /**
   * Handle confirmation button clicks
   * @param {HTMLButtonElement} button - The button clicked
   */
  handleConfirmationButton(button) {
    const message = button.dataset.confirm || 'Are you sure?';
    // const action = button.dataset.confirmAction || 'proceed'; // Unused for now

    if (confirm(message)) {
      // Execute the original action
      if (button.type === 'submit') {
        button.closest('form')?.submit();
      } else if (button.onclick) {
        button.onclick();
      } else {
        // Navigate to href if it's a link button
        const href = button.dataset.href || button.getAttribute('href');
        if (href) {
          window.location.href = href;
        }
      }
    }
  }

  /**
   * Handle copy to clipboard button clicks
   * @param {HTMLButtonElement} button - The button clicked
   */
  async handleCopyButton(button) {
    const textToCopy = button.dataset.copy || button.textContent;

    try {
      await navigator.clipboard.writeText(textToCopy);
      this.showCopySuccess(button);
    } catch {
      console.error('Copy failed:', error);
      this.showCopyError(button);
    }
  }

  /**
   * Handle smooth scrolling for anchor links
   * @param {HTMLAnchorElement} link - The anchor link
   */
  handleSmoothScroll(link) {
    const href = link.getAttribute('href');
    if (href && href.length > 1) {
      const target = document.querySelector(href);
      if (target) {
        target.scrollIntoView({ behavior: 'smooth' });
      }
    }
  }

  /**
   * Handle modal form submission
   * @param {HTMLFormElement} form - The form in the modal
   * @param {HTMLElement} modal - The modal element
   */
  async handleModalFormSubmission(form, modal) {
    try {
      const formData = new FormData(form);
      const response = await fetch(form.action || window.location.href, {
        method: 'POST',
        body: formData,
        headers: {
          'X-CSRFToken': this.getCSRFToken(),
        },
      });

      if (response.ok) {
        // Close modal and show success
        const modalInstance = bootstrap.Modal.getInstance(modal);
        modalInstance?.hide();

        // Operation completed successfully - toast shown by server response
      } else {
        throw new Error('Form submission failed');
      }
    } catch (error) {
      console.error('Modal form submission failed:', error);
      // Error toast shown by server response
    }
  }

  /**
   * Clean up modal when closed
   * @param {HTMLElement} modal - The modal element
   */
  cleanupModal(modal) {
    // Clear form data
    const form = modal.querySelector('form');
    if (form) {
      form.reset();
    }

    // Clear any validation states
    modal.querySelectorAll('.is-invalid').forEach((el) => {
      el.classList.remove('is-invalid');
    });
  }

  /**
   * Handle dropdown keyboard navigation
   * @param {KeyboardEvent} event - The keyboard event
   * @param {HTMLElement} dropdown - The dropdown element
   */
  handleDropdownKeyboard(event, dropdown) {
    const items = dropdown.querySelectorAll('.dropdown-item');
    const currentIndex = Array.from(items).indexOf(document.activeElement);

    switch (event.key) {
      case 'ArrowDown':
        event.preventDefault();
        const nextIndex = (currentIndex + 1) % items.length;
        items[nextIndex]?.focus();
        break;
      case 'ArrowUp':
        event.preventDefault();
        const prevIndex = currentIndex <= 0 ? items.length - 1 : currentIndex - 1;
        items[prevIndex]?.focus();
        break;
      case 'Escape':
        event.preventDefault();
        const toggle = dropdown.querySelector('[data-bs-toggle="dropdown"]');
        toggle?.focus();
        break;
    }
  }

  /**
   * Show auto-save indicator
   * @param {string} message - The message to show
   * @param {string} type - The indicator type
   */
  showAutoSaveIndicator(message, type) {
    // Create or update auto-save indicator
    let indicator = document.getElementById('auto-save-indicator');
    if (!indicator) {
      indicator = document.createElement('div');
      indicator.id = 'auto-save-indicator';
      indicator.className = 'position-fixed top-0 end-0 p-2';
      indicator.style.zIndex = '1100';
      document.body.appendChild(indicator);
    }

    indicator.innerHTML = `
      <div class="alert alert-${type} alert-dismissible fade show" role="alert">
        <small>${message}</small>
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
      </div>
    `;

    // Auto-hide after 3 seconds
    setTimeout(() => {
      const alert = indicator.querySelector('.alert');
      if (alert) {
        const bsAlert = new bootstrap.Alert(alert);
        bsAlert.close();
      }
    }, 3000);
  }

  /**
   * Show copy success feedback
   * @param {HTMLButtonElement} button - The button that was clicked
   */
  showCopySuccess(button) {
    const originalText = button.innerHTML;
    button.innerHTML = '<i class="fas fa-check me-1"></i>Copied!';
    button.classList.add('btn-success');

    setTimeout(() => {
      button.innerHTML = originalText;
      button.classList.remove('btn-success');
    }, 2000);
  }

  /**
   * Show copy error feedback
   * @param {HTMLButtonElement} button - The button that was clicked
   */
  showCopyError(button) {
    const originalText = button.innerHTML;
    button.innerHTML = '<i class="fas fa-times me-1"></i>Failed';
    button.classList.add('btn-danger');

    setTimeout(() => {
      button.innerHTML = originalText;
      button.classList.remove('btn-danger');
    }, 2000);
  }

  /**
   * Get CSRF token from meta tag or form
   * @returns {string} CSRF token
   */
  getCSRFToken() {
    const metaTag = document.querySelector('meta[name="csrf-token"]');
    if (metaTag) {
      return metaTag.getAttribute('content');
    }

    const form = document.querySelector('form');
    if (form) {
      const tokenInput = form.querySelector('input[name="csrf_token"]');
      if (tokenInput) {
        return tokenInput.value;
      }
    }

    return '';
  }

  /**
   * Clean up event handlers
   */
  destroy() {
    // Clear any pending timeouts
    if (this.autoSaveTimeout) {
      clearTimeout(this.autoSaveTimeout);
    }

    // Clear handlers map
    this.handlers.clear();
  }
}
