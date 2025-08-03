/**
 * Main application entry point.
 *
 * This module serves as the main entry point for the application, handling
 * initialization of UI components and dynamic loading of page-specific modules.
 *
 * @module main
 */

import { showErrorToast } from './utils/notifications.js';

/**
 * Maps URL paths to their corresponding module paths.
 * @type {Object.<string, string>}
 */
const PAGE_MODULES = {
  '/restaurants/add': '/static/js/pages/restaurant-form.js',
  '/restaurants/search': '/static/js/pages/restaurant-search.js',
  '/expenses/add': '/static/js/pages/expense-form.js',
  '/expenses': '/static/js/pages/expense-list.js',
  '/restaurants': '/static/js/pages/restaurant-list.js',
};

/**
 * Initialize global UI components.
 * Sets up tooltips, popovers, and other UI elements that are used across the application.
 * @returns {void}
 */
function initUI() {
  try {
    // Initialize tooltips
    const tooltipTriggerList = Array.from(
      document.querySelectorAll('[data-bs-toggle="tooltip"]'),
    );

    tooltipTriggerList.forEach((tooltipEl) => {
      new bootstrap.Tooltip(tooltipEl, {
        trigger: 'hover focus',
        boundary: 'viewport',
      });
    });

    // Initialize popovers
    const popoverTriggerList = Array.from(
      document.querySelectorAll('[data-bs-toggle="popover"]'),
    );

    popoverTriggerList.forEach((popoverEl) => {
      new bootstrap.Popover(popoverEl, {
        trigger: 'focus',
        html: true,
        sanitize: false,
      });
    });

    // Add smooth scrolling for anchor links
    document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
      anchor.addEventListener('click', function(e) {
        e.preventDefault();
        const targetId = this.getAttribute('href');
        const target = document.querySelector(targetId);

        if (target) {
          target.scrollIntoView({
            behavior: 'smooth',
          });
        }
      });
    });
  } catch (error) {
    console.error('UI initialization failed:', error);
    showErrorToast('Failed to initialize UI components.');
  }
}

/**
 * Load and initialize the appropriate page module based on current URL.
 * @async
 * @returns {Promise<void>}
 */
async function loadPageModule() {
  const currentPath = window.location.pathname;
  const modulePath = PAGE_MODULES[currentPath];

  if (!modulePath) {
    return;
  }

  try {
    const module = await import(modulePath);
    if (typeof module.init === 'function') {
      await module.init();
    }
  } catch (error) {
    console.error(`Failed to load module: ${modulePath}`, error);
    showErrorToast('Failed to load page module. Please refresh the page.');
  }
}

/**
 * Initialize the application.
 * Sets up UI components and loads the appropriate page module.
 * @async
 * @returns {Promise<void>}
 */
async function init() {
  try {
    initUI();
    await loadPageModule();

    // Add animation to cards on scroll
    const animateOnScroll = () => {
      const cards = document.querySelectorAll('.card, .animate-on-scroll');
      cards.forEach((card) => {
        const cardTop = card.getBoundingClientRect().top;
        const windowHeight = window.innerHeight;

        if (cardTop < windowHeight - 100) {
          card.classList.add('animate__animated', 'animate__fadeInUp');
        }
      });
    };

    // Add scroll event listener
    window.addEventListener('scroll', animateOnScroll);
    animateOnScroll(); // Run once on page load

    // Add loading state to buttons with data-loading attribute
    document.querySelectorAll('[data-loading]').forEach((button) => {
      button.addEventListener('click', function() {
        this.setAttribute('data-text', this.innerHTML);
        this.disabled = true;
        this.innerHTML = `
                    <span class="spinner-border spinner-border-sm"
                          role="status"
                          aria-hidden="true">
                    </span>
                    ${this.getAttribute('data-loading')}
                `;
      });
    });

    // Flash message auto-dismiss
    const alerts = document.querySelectorAll('.alert-dismissible');
    alerts.forEach((alert) => {
      setTimeout(() => {
        const bsAlert = new bootstrap.Alert(alert);
        bsAlert.close();
      }, 5000); // Auto-dismiss after 5 seconds
    });

    document.dispatchEvent(new CustomEvent('app:initialized'));
  } catch (error) {
    console.error('Application initialization failed:', error);
    showErrorToast('Failed to initialize application. Please refresh the page.');
  }
}

// Initialize the application when the DOM is fully loaded
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}

// Export for testing purposes
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    init,
    initUI,
    loadPageModule,

  };
}
