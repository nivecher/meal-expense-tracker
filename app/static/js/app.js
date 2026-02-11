/**
 * Single application entrypoint (module).
 *
 * Goal: provide one stable place to initialize shared behavior and
 * incrementally replace page-specific scripts with HTMX/Alpine patterns.
 */

import config from './config.js';
import { toast } from './utils/notifications.js';

// Side-effect modules that register handlers / polyfills.
import './utils/timezone-handler.js';
import './utils/date-formatter.js';
import './utils/error-handler.js';
import './utils/logger.js';
import './utils/module-loader.js';
import './utils/select2-init.js';
import './utils/lazy-loading-optimizer.js';
import './utils/robust-favicon-handler.js';
import './utils/fontawesome-fallback.js';

import './components/sticky-tables.js';
import './components/resizable-columns.js';
import './components/modern-avatar.js';
import './components/sidebar.js';
import './components/image-fallback.js';

// Main app behavior (page-module loading, etc.)
import './main.js';

function maybeDisableServiceWorkerForDev() {
  const isDevEnv = config?.app?.env === 'development' || config?.app?.env === 'dev';
  const isDevHost = ['localhost', '127.0.0.1'].includes(window.location.hostname);
  const isDev = isDevEnv || isDevHost;
  if (!isDev) return;

  if (!('serviceWorker' in navigator)) return;

  // If a service worker was registered previously, it can serve stale cached CSS/JS
  // and make UI changes appear "stuck" even after refresh.
  navigator.serviceWorker.getRegistrations().then((registrations) => {
    registrations.forEach((registration) => {
      registration.unregister();
    });
  }).catch((error) => {
    console.warn('Failed to unregister service workers in development:', error);
  });

  if (!('caches' in window)) return;

  caches.keys().then((cacheNames) => {
    cacheNames
      .filter((name) => name.startsWith('meal-tracker-'))
      .forEach((name) => {
        caches.delete(name);
      });
  }).catch((error) => {
    console.warn('Failed to clear caches in development:', error);
  });
}

function initBootstrapEnhancements() {
  if (typeof bootstrap === 'undefined') return;

  // Performance: use delegated tooltips/popovers instead of instantiating one per element.
  // This avoids huge DOMContentLoaded stalls when pages have many tooltip targets.
  if (!window.mealTrackerTooltipDelegate) {
    window.mealTrackerTooltipDelegate = new bootstrap.Tooltip(document.body, {
      selector: '[data-bs-toggle="tooltip"], [data-tooltip="true"]',
    });
  }

  if (!window.mealTrackerPopoverDelegate) {
    // Popover extends Tooltip; binding both to the same root element can throw
    // "Bootstrap doesn't allow more than one instance per element. Bound instance: bs.tooltip."
    // Use a different root element for popover delegation to avoid conflicts.
    window.mealTrackerPopoverDelegate = new bootstrap.Popover(document.documentElement, {
      selector: '[data-bs-toggle="popover"]',
      html: true,
    });
  }
}

function convertFlashMessagesToToasts() {
  const flashMessages = document.querySelectorAll('.flash-messages .alert');
  if (!flashMessages.length) return;

  flashMessages.forEach((alert) => {
    // Only convert if this is a page load (not an AJAX response)
    if (alert.closest('[data-ajax-response]')) return;

    const message = alert.querySelector('.alert-message')?.innerHTML || alert.textContent.trim();
    const category = alert.classList.contains('alert-success')
      ? 'success'
      : alert.classList.contains('alert-danger')
        ? 'error'
        : alert.classList.contains('alert-warning')
          ? 'warning'
          : 'info';

    toast[category](message);
    alert.style.display = 'none';
  });
}

function maybeLoadAuthFormsModule() {
  const hasAuthForm = document.getElementById('login-form') || document.getElementById('register-form');
  if (!hasAuthForm) return;

  // Auth pages are server-rendered; load their small handler only when needed.
  import('./pages/auth-forms.js').catch((error) => {
    console.error('Failed to load auth forms module:', error);
  });
}

// Expose config for debugging and backward-compatibility (read-only).
window.MEAL_TRACKER_CONFIG = config;

document.addEventListener('DOMContentLoaded', () => {
  maybeDisableServiceWorkerForDev();
  initBootstrapEnhancements();
  convertFlashMessagesToToasts();
  maybeLoadAuthFormsModule();
});

document.addEventListener('htmx:afterSettle', () => {
  // Delegated tooltips/popovers automatically cover swapped content.
  // Keep this as a low-cost safety call in case bootstrap loads late.
  initBootstrapEnhancements();
});
