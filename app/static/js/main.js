/**
 * Simple main application entry point.
 * Focuses on essential UI initialization without over-engineering.
 */

// Simple page module loading - direct and clear
const pageModules = {
  '/restaurants/add': () => import('./pages/restaurant-form.js'),
  '/restaurants/search': () => import('./pages/restaurant-search.js'),
  '/expenses/add': () => import('./pages/expense-form.js'),
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
      const target = document.querySelector(anchor.getAttribute('href'));
      target?.scrollIntoView({ behavior: 'smooth' });
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

// Simple app initialization
async function init() {
  initUI();
  await loadPageModule();

  // Auto-dismiss alerts after 5 seconds
  document.querySelectorAll('.alert-dismissible').forEach((alert) => {
    setTimeout(() => new bootstrap.Alert(alert).close(), 5000);
  });

  // Loading state for buttons
  document.querySelectorAll('[data-loading]').forEach((button) => {
    button.addEventListener('click', function() {
      const loadingText = this.dataset.loading;
      this.dataset.originalText = this.innerHTML;
      this.disabled = true;
      this.innerHTML = `<span class="spinner-border spinner-border-sm me-2"></span>${loadingText}`;
    });
  });

  document.dispatchEvent(new CustomEvent('app:initialized'));
}

// Start the app
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}

// Export for testing
export { init, initUI, loadPageModule };
