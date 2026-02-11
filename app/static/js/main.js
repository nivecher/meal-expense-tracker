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

function runWhenIdle(callback, timeoutMs = 1200) {
  if (typeof callback !== 'function') return;
  if (window.requestIdleCallback) {
    window.requestIdleCallback(callback, { timeout: timeoutMs });
    return;
  }
  setTimeout(callback, 0);
}

function safeSessionGet(key) {
  try {
    return sessionStorage.getItem(key);
  } catch {
    return null;
  }
}

function safeSessionSet(key, value) {
  try {
    sessionStorage.setItem(key, value);
  } catch {
    // ignore (tracking prevention / blocked storage)
  }
}

function safeLocalGet(key) {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

// Enhanced page module loading with error handling
const pageModules = {
  '/restaurants/search': () => import('./pages/restaurant-search.js'),
  '/expenses': () => import('./pages/expense-list.js'),
  '/restaurants': () => import('./pages/restaurant-list.js'),
};

// Apply tag colors from data attributes
function applyTagColors() {
  // Handle tag-badge elements (exclude Tom Select internal elements)
  const tagBadges = document.querySelectorAll('.tag-badge[data-tag-color]:not(.tag-select-item-badge)');
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
            // Check if the added node is a tag badge (not Tom Select items - those are handled in tag-select-init.js)
            if (node.classList && node.classList.contains('tag-badge') && !node.classList.contains('tag-select-item') && node.hasAttribute('data-tag-color')) {
              const color = node.getAttribute('data-tag-color');
              if (color) {
                // Only set CSS variable for tag badges - CSS handles the rest
                node.style.setProperty('--tag-color', color);
                node.style.setProperty('background-color', color);
              }
            }
            // Check for tag badges within the added node (exclude Tom Select items)
            const tagBadges = node.querySelectorAll && node.querySelectorAll('.tag-badge[data-tag-color]:not(.tag-select-item)');
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

// Helper function to calculate text color based on background brightness
function getTextColor(backgroundColor) {
  const hexToRgb = (hex) => {
    const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
    return result ? {
      r: parseInt(result[1], 16),
      g: parseInt(result[2], 16),
      b: parseInt(result[3], 16),
    } : null;
  };

  const rgb = hexToRgb(backgroundColor);
  if (!rgb) return '#000';
  const brightness = (rgb.r * 299 + rgb.g * 587 + rgb.b * 114) / 1000;
  return brightness > 128 ? '#000' : '#fff';
}

// Refresh Tom Select instance with updated tags
async function refreshTagSelectInstance() {
  if (!window.tagSelectInstance) {
    console.warn('Tag select instance not found, cannot refresh');
    return;
  }

  try {
    // Preserve currently selected tags before refreshing
    const { tagSelectInstance } = window;
    const currentSelections = tagSelectInstance.getValue() || [];
    const selectedTagNames = Array.isArray(currentSelections) ? currentSelections : [currentSelections];

    // Add cache-busting parameter to ensure fresh data
    const cacheBuster = `?t=${Date.now()}`;
    const response = await fetch(`/expenses/tags${cacheBuster}`, {
      method: 'GET',
      headers: {
        'X-Requested-With': 'XMLHttpRequest',
        Accept: 'application/json',
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        Pragma: 'no-cache',
      },
      credentials: 'include', // Include cookies for authentication (required for CORS)
      cache: 'no-store', // Prevent browser caching
    });

    if (!response.ok) {
      console.warn('Failed to fetch tags for refresh:', response.status);
      return;
    }

    // Check if response is JSON before parsing
    const contentType = response.headers.get('content-type');
    if (!contentType || !contentType.includes('application/json')) {
      console.warn('Non-JSON response when refreshing tags');
      return;
    }

    const data = await response.json();
    if (data.success && data.tags) {
      // Map new tags to options format
      const newOptions = data.tags.map((tag) => ({
        id: tag.id,
        name: tag.name,
        color: tag.color || '#6c757d',
        description: tag.description || tag.name,
      }));

      // Clear existing options and add new ones
      tagSelectInstance.clearOptions();
      tagSelectInstance.addOptions(newOptions);
      // Refresh options to ensure Tom Select recognizes the new data
      tagSelectInstance.refreshOptions(false);

      // Restore previously selected tags (if they still exist)
      // Filter out any tags that were deleted
      const validSelections = selectedTagNames.filter((tagName) => {
        return newOptions.some((option) => option.name === tagName);
      });

      if (validSelections.length > 0) {
        // Remove all current items to force re-render with updated colors
        const currentItems = [...tagSelectInstance.items];
        currentItems.forEach((item) => {
          tagSelectInstance.removeItem(item, true); // true = silent
        });

        // Re-add valid selections with updated data (this will trigger render.item with new colors)
        validSelections.forEach((tagName) => {
          const option = newOptions.find((opt) => opt.name === tagName);
          if (option) {
            // Ensure the option is in Tom Select's options before adding
            if (!tagSelectInstance.options[tagName]) {
              tagSelectInstance.addOption(option);
            } else {
              // Update existing option with new data
              tagSelectInstance.options[tagName] = option;
            }
            tagSelectInstance.addItem(tagName, true); // true = silent (don't trigger events)
          }
        });

        // Manually update DOM elements with new colors after a short delay
        // This ensures the render.item function has been called and we can update any missed elements
        setTimeout(() => {
          validSelections.forEach((tagName) => {
            const option = newOptions.find((opt) => opt.name === tagName);
            if (option) {
              // Find the DOM element for this tag by searching all tag items
              const controlItems = tagSelectInstance.control?.querySelector('.ts-control-items');
              if (controlItems) {
                const allItems = controlItems.querySelectorAll('.tag-select-item');
                allItems.forEach((item) => {
                  const badge = item.querySelector('.tag-select-item-badge');
                  if (badge && badge.textContent.trim() === tagName) {
                    // Update the data-color attribute and inline styles with new color
                    const tagColor = option.color || '#6c757d';
                    const textColor = getTextColor(tagColor);
                    item.setAttribute('data-color', tagColor);
                    item.style.setProperty('--tag-color', tagColor);
                    badge.style.backgroundColor = tagColor;
                    badge.style.color = textColor;
                  }
                });
              }
            }
          });

          // Ensure input field appears after all tags
          if (tagSelectInstance.control && tagSelectInstance.control_input) {
            const controlItems = tagSelectInstance.control.querySelector('.ts-control-items');
            if (controlItems) {
              // Move input to the end of control-items (after all tag items)
              controlItems.appendChild(tagSelectInstance.control_input);
              // Also set CSS order as backup
              tagSelectInstance.control_input.style.order = '9999';
            }
          }
        }, 150);
      }

      // Initialize tooltips for all tag items after refresh
      setTimeout(() => {
        const tagItems = document.querySelectorAll('.tag-select-item[data-bs-toggle="tooltip"]');
        tagItems.forEach((item) => {
          // Dispose existing tooltip if any
          const existingTooltip = bootstrap.Tooltip.getInstance(item);
          if (existingTooltip) {
            existingTooltip.dispose();
          }
          // Initialize new tooltip with consistent top placement
          if (item.getAttribute('data-tag-description')) {
            new bootstrap.Tooltip(item, { placement: 'top' }); // eslint-disable-line no-new
          }
        });
      }, 200);

      // Tag selector refreshed successfully
    } else {
      console.warn('Invalid response format when refreshing tags:', data);
    }
  } catch (error) {
    console.error('Error refreshing Tom Select instance:', error);
  }
}

// Initialize essential UI components directly
function initUI() {
  // Apply tag colors
  applyTagColors();

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
  const path = window.location.pathname.replace(/\/$/, '') || '/';
  const moduleLoader = pageModules[path];
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
    // Initialize event handlers early (critical)
    new EventHandlers(); // eslint-disable-line no-new

    // Defer non-critical UI polish work so DOMContentLoaded isn't blocked
    runWhenIdle(() => initUI(), 800);
    runWhenIdle(() => {
      initializeRobustFaviconHandling('.restaurant-favicon');
      initializeRobustFaviconHandling('.restaurant-favicon-table');
    }, 1500);
    runWhenIdle(() => initTagColorWatcher(), 1500);

    // Listen for tag update events to refresh Tom Select
    document.addEventListener('tagsUpdated', () => {
      if (window.tagSelectInstance) {
        refreshTagSelectInstance();
      }
    });

    document.addEventListener('tagDeleted', () => {
      if (window.tagSelectInstance) {
        refreshTagSelectInstance();
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
    if (!safeSessionGet('app-initialized')) {
      safeSessionSet('app-initialized', 'true');
      setTimeout(() => {
        toast.info('Application ready!');
      }, 500);
    }

    // Only show debug messages if debug mode is enabled
    if (window.location.search.includes('debug=true') || safeLocalGet('debugMode') === 'true') {
      console.warn('✅ Application initialized successfully');
    }

  } catch (error) {
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
  if (window.location.search.includes('debug=true') || safeLocalGet('debugMode') === 'true') {
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
