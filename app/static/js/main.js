/**
 * Enhanced main application entry point
 * Handles UI initialization, notifications, and page-specific modules
 *
 * @version 3.0.0
 * @author Meal Expense Tracker Team
 */

import { toast } from './utils/notifications.js';
import { EventHandlers } from './components/event-handlers.js';
import {
  clearFaviconCache,
  initializeRobustFaviconHandling,
} from './utils/robust-favicon-handler.js';

// Enhanced page module loading with error handling
const pageModules = {
  '/restaurants/search': () => import('./pages/restaurant-search.js'),
  '/expenses': () => import('./pages/expense-list.js'),
  '/restaurants': () => import('./pages/restaurant-list.js'),
};

// Apply tag colors from data attributes
function applyTagColors() {
  // Only handle tag-badge elements, not tagify__tag (those are handled in tagify-init.js)
  const tagBadges = document.querySelectorAll('.tag-badge[data-tag-color]:not(.tagify__tag)');
  tagBadges.forEach((badge) => {
    const color = badge.getAttribute('data-tag-color');
    if (color) {
      // Only set CSS variable - CSS handles the rest
      badge.style.setProperty('--tag-color', color);
      badge.style.setProperty('background-color', color);
    }
  });
}

// Watch for dynamically added tag badges
function initTagColorWatcher() {
  const observer = new MutationObserver((mutations) => {
    try {
      mutations.forEach((mutation) => {
        mutation.addedNodes.forEach((node) => {
          if (node.nodeType === Node.ELEMENT_NODE) {
            // Check if the added node is a tag badge (not Tagify tags - those are handled in tagify-init.js)
            if (node.classList && node.classList.contains('tag-badge') && !node.classList.contains('tagify__tag') && node.hasAttribute('data-tag-color')) {
              const color = node.getAttribute('data-tag-color');
              if (color) {
                // Only set CSS variable for tag badges - CSS handles the rest
                node.style.setProperty('--tag-color', color);
                node.style.setProperty('background-color', color);
              }
            }
            // Check for tag badges within the added node (exclude tagify__tag)
            const tagBadges = node.querySelectorAll && node.querySelectorAll('.tag-badge[data-tag-color]:not(.tagify__tag)');
            if (tagBadges) {
              tagBadges.forEach((badge) => {
                const color = badge.getAttribute('data-tag-color');
                if (color) {
                  // Only set CSS variable - CSS handles the rest
                  badge.style.setProperty('--tag-color', color);
                  badge.style.setProperty('background-color', color);
                }
              });
            }
          }
        });
      });
    } catch {
      // Silently handle any errors from browser extensions
      // console.debug('MutationObserver error (likely from browser extension)');
    }
  });

  observer.observe(document.body, {
    childList: true,
    subtree: true,
  });
}

// Refresh Tagify instance with updated tags
async function refreshTagifyInstance() {
  if (!window.tagifyInstance) return;

  try {
    // Update the whitelist with latest tags
    const response = await fetch('/expenses/tags');
    if (!response.ok) return;

    const data = await response.json();
    if (data.success && data.tags) {
      const { tagifyInstance } = window;
      if (tagifyInstance) {
        tagifyInstance.settings.whitelist = data.tags.map((tag) => ({
          value: tag.name,
          id: tag.id,
          title: tag.description || tag.name,
          description: tag.description || '',
          color: tag.color,
        }));
      }
    }

    // Re-apply colors to existing tags - only set CSS variable
    setTimeout(() => {
      const tagElements = document.querySelectorAll('.tagify__tag[data-tag-color]');
      tagElements.forEach((tagEl) => {
        const tagColor = tagEl.getAttribute('data-tag-color');
        if (tagColor) {
          // Only set CSS variable - CSS handles the rest
          tagEl.style.setProperty('--tag-color', tagColor);
        }
      });
    }, 100);
  } catch {
    console.error('Error refreshing Tagify instance:', error);
  }
}

// Initialize essential UI components directly
function initUI() {
  // Apply tag colors
  applyTagColors();

  // Bootstrap tooltips - check if bootstrap is available
  if (typeof bootstrap !== 'undefined') {
    document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach((el) => {
      new bootstrap.Tooltip(el); // eslint-disable-line no-new
    });

    // Bootstrap popovers
    document.querySelectorAll('[data-bs-toggle="popover"]').forEach((el) => {
      new bootstrap.Popover(el, { html: true }); // eslint-disable-line no-new
    });

    // Bootstrap dropdowns - Initialize manually for reliability
    document.querySelectorAll('[data-bs-toggle="dropdown"]').forEach((el) => {
      new bootstrap.Dropdown(el); // eslint-disable-line no-new
    });
  }

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
  } catch {
    console.error('Failed to load page module:', error);
  }
}

// Enhanced app initialization with toast notifications
async function init() {
  try {
    // Initialize core UI components
    initUI();

    // Toast system is ready (no initialization needed)

    // Initialize event handlers (replaces inline onclick handlers)
    new EventHandlers(); // eslint-disable-line no-new

    // Initialize robust favicon system
    initializeRobustFaviconHandling('.restaurant-favicon');
    initializeRobustFaviconHandling('.restaurant-favicon-table');

    // Initialize tag color watcher for dynamically added content
    initTagColorWatcher();

    // Listen for tag update events to refresh Tagify
    document.addEventListener('tagsUpdated', () => {
      if (window.tagifyInstance) {
        refreshTagifyInstance();
      }
    });

    document.addEventListener('tagDeleted', () => {
      if (window.tagifyInstance) {
        refreshTagifyInstance();
      }
    });

    // Error handling is now managed by unified-error-handler.js

    // DOM method protection is now handled by unified-error-handler.js

    // Initialize style replacer (replaces inline styles) - DISABLED BY DEFAULT
    // Uncomment to enable: new StyleReplacer({ enabled: true, verbose: false });

    // Load page-specific modules
    await loadPageModule();

    // Auto-dismiss alerts after 5 seconds with enhanced feedback
    document.querySelectorAll('.alert-dismissible').forEach((alert) => {
      setTimeout(() => {
        try {
          // Check if element still exists in DOM before trying to close
          if (alert && alert.parentNode) {
            new bootstrap.Alert(alert).close();
          }
        } catch {
          console.warn('Error closing alert:', error);
          // Safe fallback removal
          if (alert && alert.parentNode) {
            alert.remove();
          }
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

    // Error handling is now managed by the ErrorHandler class
    // The error handler is automatically initialized and will handle:
    // - JavaScript errors
    // - Unhandled promise rejections
    // - Resource loading errors
    // - Performance monitoring
    // - Console message filtering

    // Dispatch initialization complete event
    document.dispatchEvent(new CustomEvent('app:initialized', {
      detail: { timestamp: Date.now() },
    }));

    // Show welcome message if this is a fresh page load
    if (!sessionStorage.getItem('app-initialized')) {
      sessionStorage.setItem('app-initialized', 'true');
      setTimeout(() => {
        toast.info('Application ready! 🎉');
      }, 500);
    }

    // Only show debug messages if debug mode is enabled
    if (window.location.search.includes('debug=true') || localStorage.getItem('debugMode') === 'true') {
      console.warn('✅ Application initialized successfully');
    }

  } catch {
    console.error('❌ Failed to initialize application:', error);

    // Show error feedback
    toast.error('Failed to initialize application. Please refresh the page.');
  }
}

// Add favicon debug commands to global scope for development
if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
  window.faviconDebug = {
    clearCache: clearFaviconCache,
  };

  // Only show debug messages if debug mode is enabled
  if (window.location.search.includes('debug=true') || localStorage.getItem('debugMode') === 'true') {
    console.warn('🔧 Favicon debug commands available: window.faviconDebug.clearCache()');
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
