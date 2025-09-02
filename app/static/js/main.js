/**
 * Enhanced main application entry point
 * Handles UI initialization, notifications, and page-specific modules
 *
 * @version 3.0.0
 * @author Meal Expense Tracker Team
 */

import { initNotifications } from './utils/notifications.js';
import { initExtensionErrorHandler, makeElementExtensionSafe } from './utils/extension-error-handler.js';

// Extension error handling is now managed by extension-error-handler.js
// Make extension safety utilities available globally
window.makeElementExtensionSafe = makeElementExtensionSafe;

// Enhanced page module loading with error handling
const pageModules = {
  '/restaurants/add': () => import('./pages/restaurant-form.js'),
  '/restaurants/search': () => import('./pages/restaurant-search.js'),
  '/expenses': () => import('./pages/expense-list.js'),
  '/restaurants': () => import('./pages/restaurant-list.js'),
};

// Initialize essential UI components directly
function initUI() {
  // Bootstrap tooltips
  document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach((el) => {
    new bootstrap.Tooltip(el);
  });

  // Bootstrap popovers
  document.querySelectorAll('[data-bs-toggle="popover"]').forEach((el) => {
    new bootstrap.Popover(el, { html: true });
  });

  // Smooth scrolling for anchor links
  document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
    anchor.addEventListener('click', (e) => {
      e.preventDefault();
      const href = anchor.getAttribute('href');
      // Only proceed if href contains an actual ID (not just '#')
      if (href && href.length > 1) {
        const target = document.querySelector(href);
        target?.scrollIntoView({ behavior: 'smooth' });
      }
    });
  });
}

// Load page-specific module if it exists
async function loadPageModule() {
  const moduleLoader = pageModules[window.location.pathname];
  if (!moduleLoader) return;

  try {
    const module = await moduleLoader();
    module.init?.();
  } catch (error) {
    console.error('Failed to load page module:', error);
  }
}

// Enhanced app initialization with toast notifications
async function init() {
  try {
    // Initialize core UI components
    initUI();

    // Initialize enhanced toast notifications
    initNotifications();

    // Load page-specific modules
    await loadPageModule();

    // Auto-dismiss alerts after 5 seconds with enhanced feedback
    document.querySelectorAll('.alert-dismissible').forEach((alert) => {
      setTimeout(() => {
        try {
          new bootstrap.Alert(alert).close();
        } catch (error) {
          console.warn('Error closing alert:', error);
          alert.remove(); // Fallback removal
        }
      }, 5000);
    });

    // Enhanced loading state for buttons with better UX
    document.querySelectorAll('[data-loading]').forEach((button) => {
      button.addEventListener('click', function(event) {
        // Prevent double-clicks during loading
        if (this.disabled) {
          event.preventDefault();
          return false;
        }

        const loadingText = this.dataset.loading || 'Processing...';
        this.dataset.originalText = this.innerHTML;
        this.disabled = true;
        this.innerHTML = `
          <span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
          ${loadingText}
        `;

        // Auto-restore button after 30 seconds as safety measure
        setTimeout(() => {
          if (this.disabled && this.dataset.originalText) {
            this.disabled = false;
            this.innerHTML = this.dataset.originalText;
            delete this.dataset.originalText;
            console.warn('Auto-restored button after timeout');
          }
        }, 30000);
      });
    });

    // Global error handler for unhandled promise rejections
    window.addEventListener('unhandledrejection', (event) => {
      console.error('Unhandled promise rejection:', event.reason);
      if (window.showErrorToast) {
        window.showErrorToast('An unexpected error occurred. Please try again.');
      }
      event.preventDefault(); // Prevent default browser error handling
    });

    // Global error handler for JavaScript errors
    window.addEventListener('error', (event) => {
      console.error('JavaScript error:', event.error);
      if (window.showErrorToast && !event.filename?.includes('chrome-extension')) {
        window.showErrorToast('An error occurred. Please refresh the page if problems persist.');
      }
    });

    // Dispatch initialization complete event
    document.dispatchEvent(new CustomEvent('app:initialized', {
      detail: { timestamp: Date.now() },
    }));

    // Show welcome message if this is a fresh page load
    if (window.showSuccessToast && !sessionStorage.getItem('app-initialized')) {
      sessionStorage.setItem('app-initialized', 'true');
      setTimeout(() => {
        window.showInfoToast('Application ready! 🎉', 2000, { showHeader: false });
      }, 500);
    }

    console.log('✅ Application initialized successfully');

  } catch (error) {
    console.error('❌ Failed to initialize application:', error);

    // Show error feedback
    if (window.showErrorToast) {
      window.showErrorToast('Failed to initialize application. Please refresh the page.');
    } else {
      alert('Failed to initialize application. Please refresh the page.');
    }
  }
}

// Start the app
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}

// Export for testing
export { init, initUI, loadPageModule };
