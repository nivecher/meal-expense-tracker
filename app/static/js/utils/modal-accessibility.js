/**
 * Modal Accessibility Utility
 *
 * Provides consistent accessibility handling for Bootstrap modals
 * to prevent aria-hidden violations and ensure proper focus management.
 */

/**
 * Initialize accessibility for a modal element
 * @param {HTMLElement} modalElement - The modal DOM element
 * @param {Object} options - Configuration options
 * @param {boolean} options.returnFocus - Whether to return focus to the previous element (default: true)
 * @param {HTMLElement} options.focusElement - Specific element to focus when modal opens (default: first focusable)
 */
export function initializeModalAccessibility(modalElement, options = {}) {
  const {
    returnFocus = true,
    focusElement = null
  } = options;

  if (!modalElement || !modalElement.classList.contains('modal')) {
    console.warn('Modal accessibility: Element is not a modal', modalElement);
    return;
  }

  // Store the element that had focus before the modal opened
  let focusedElementBeforeModal = null;

  // When modal is about to be shown
  modalElement.addEventListener('show.bs.modal', () => {
    // Store the current focused element
    if (returnFocus) {
      focusedElementBeforeModal = document.activeElement;
    }

    // Update ARIA attributes when modal is shown
    modalElement.setAttribute('aria-hidden', 'false');
    modalElement.setAttribute('aria-modal', 'true');

    // Remove the inert attribute to make modal content accessible
    modalElement.removeAttribute('inert');
  });

  // When modal is fully shown
  modalElement.addEventListener('shown.bs.modal', () => {
    // Focus the specified element or find the first focusable element
    let elementToFocus = focusElement;

    if (!elementToFocus) {
      elementToFocus = modalElement.querySelector('button[autofocus]') ||
                      modalElement.querySelector('button:not([disabled])') ||
                      modalElement.querySelector('input:not([disabled])') ||
                      modalElement.querySelector('a[href]') ||
                      modalElement.querySelector('[tabindex]:not([tabindex="-1"])');
    }

    if (elementToFocus && elementToFocus.focus) {
      elementToFocus.focus();
    }
  });

  // When modal is fully hidden
  modalElement.addEventListener('hidden.bs.modal', () => {
    // Reset ARIA attributes when modal is hidden
    modalElement.setAttribute('aria-hidden', 'true');
    modalElement.setAttribute('aria-modal', 'false');

    // Add inert attribute to prevent interaction when hidden
    modalElement.setAttribute('inert', 'true');

    // Return focus to the element that had focus before the modal opened
    if (returnFocus && focusedElementBeforeModal && focusedElementBeforeModal.focus) {
      focusedElementBeforeModal.focus();
    }
  });
}

/**
 * Initialize accessibility for all modals on the page
 * @param {Object} options - Configuration options passed to initializeModalAccessibility
 */
export function initializeAllModals(options = {}) {
  const modals = document.querySelectorAll('.modal');
  modals.forEach(modal => {
    initializeModalAccessibility(modal, options);
  });
}

/**
 * Create a modal with proper accessibility
 * @param {Object} options - Modal configuration
 * @param {string} options.id - Modal ID
 * @param {string} options.title - Modal title
 * @param {string} options.content - Modal content HTML
 * @param {string} options.type - Modal type (default, warning, danger, success)
 * @param {boolean} options.returnFocus - Whether to return focus (default: true)
 * @returns {HTMLElement} The created modal element
 */
export function createAccessibleModal(options) {
  const {
    id,
    title,
    content,
    type = 'default',
    returnFocus = true
  } = options;

  const modalId = id || `modal-${Date.now()}`;
  const modal = document.createElement('div');
  modal.className = `modal fade modal-${type}`;
  modal.id = modalId;
  modal.tabIndex = '-1';
  modal.setAttribute('aria-labelledby', `${modalId}-label`);

  modal.innerHTML = `
    <div class="modal-dialog">
      <div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title" id="${modalId}-label">${title}</h5>
          <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
        </div>
        <div class="modal-body">
          ${content}
        </div>
      </div>
    </div>
  `;

  // Initialize accessibility
  initializeModalAccessibility(modal, { returnFocus });

  return modal;
}

// Auto-initialize when DOM is loaded
if (typeof document !== 'undefined') {
  document.addEventListener('DOMContentLoaded', () => {
    // Initialize any existing modals
    initializeAllModals();

    // Watch for dynamically added modals
    const observer = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        mutation.addedNodes.forEach((node) => {
          if (node.nodeType === Node.ELEMENT_NODE) {
            if (node.classList && node.classList.contains('modal')) {
              initializeModalAccessibility(node);
            }
            // Check for modals within added nodes
            const modals = node.querySelectorAll ? node.querySelectorAll('.modal') : [];
            modals.forEach(modal => initializeModalAccessibility(modal));
          }
        });
      });
    });

    observer.observe(document.body, {
      childList: true,
      subtree: true
    });
  });
}
