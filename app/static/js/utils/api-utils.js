/**
 * API Utilities
 * Consolidated API calls, service worker registration, and network utilities
 *
 * @module apiUtils
 * @version 2.0.0
 * @author Meal Expense Tracker Team
 */

import { logger } from './core-utils.js';
import { showErrorToast } from './ui-utils.js';

// ===== API UTILITIES =====

/**
 * Get CSRF token from meta tag
 */
function getCSRFToken() {
  const metaTag = document.querySelector('meta[name="csrf-token"]');
  return metaTag ? metaTag.getAttribute('content') : '';
}

/**
 * Make an API request with CSRF protection
 */
async function apiRequest(url, options = {}) {
  const headers = new Headers(options.headers || {});

  // Add CSRF token
  if (!headers.has('X-CSRFToken')) {
    const csrfToken = getCSRFToken();
    if (csrfToken) {
      headers.set('X-CSRFToken', csrfToken);
    }
  }

  // Handle JSON body
  if (options.body && typeof options.body === 'object' && !(options.body instanceof FormData)) {
    if (!headers.has('Content-Type')) {
      headers.set('Content-Type', 'application/json');
    }
    options.body = JSON.stringify(options.body);
  }

  // Add AJAX header
  if (!headers.has('X-Requested-With')) {
    headers.set('X-Requested-With', 'XMLHttpRequest');
  }

  const fetchOptions = {
    ...options,
    headers,
    credentials: 'same-origin',
  };

  try {
    const response = await fetch(url, fetchOptions);

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      const error = new Error(errorData.message || `HTTP error! status: ${response.status}`);
      error.status = response.status;
      error.data = errorData;
      throw error;
    }

    const contentType = response.headers.get('content-type');
    if (contentType && contentType.includes('application/json')) {
      return await response.json();
    }

    return await response.text();
  } catch (error) {
    logger.error('API request failed:', error);

    const errorMessage = error.data?.message || error.message || 'An error occurred. Please try again.';
    showErrorToast(errorMessage);

    throw error;
  }
}

// HTTP method helpers
const get = (url, params = {}, options = {}) => {
  const queryString = new URLSearchParams(params).toString();
  const urlWithParams = queryString ? `${url}?${queryString}` : url;
  return apiRequest(urlWithParams, { ...options, method: 'GET' });
};

const post = (url, data = {}, options = {}) => {
  return apiRequest(url, { ...options, method: 'POST', body: data });
};

const put = (url, data = {}, options = {}) => {
  return apiRequest(url, { ...options, method: 'PUT', body: data });
};

const del = (url, options = {}) => {
  return apiRequest(url, { ...options, method: 'DELETE' });
};

// ===== SERVICE WORKER UTILITIES =====

/**
 * Simple service worker manager
 */
class SimpleServiceWorkerManager {
  constructor() {
    this.registration = null;
    this.isSupported = 'serviceWorker' in navigator;
    this.updateAvailable = false;
  }

  async register() {
    logger.info('Service Worker registration disabled for development');

    // Unregister any existing service workers
    if ('serviceWorker' in navigator) {
      try {
        const registrations = await navigator.serviceWorker.getRegistrations();
        for (const registration of registrations) {
          await registration.unregister();
          logger.info('Unregistered existing service worker');
        }
      } catch (error) {
        logger.warn('Failed to unregister existing service workers:', error);
      }
    }

    return null;
  }

  setupEventListeners() {
    if (!this.registration) return;

    this.registration.addEventListener('updatefound', () => {
      logger.info('Service Worker update found');

      const newWorker = this.registration.installing;
      if (newWorker) {
        newWorker.addEventListener('statechange', () => {
          if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
            this.updateAvailable = true;
            this.showUpdateNotification();
          }
        });
      }
    });

    navigator.serviceWorker.addEventListener('controllerchange', () => {
      logger.info('Service Worker controller changed');
      if (this.updateAvailable) {
        window.location.reload();
      }
    });
  }

  async checkForUpdates() {
    if (!this.registration) return;

    try {
      await this.registration.update();
      logger.debug('Service Worker update check completed');
    } catch (error) {
      logger.error('Failed to check for Service Worker updates:', error);
    }
  }

  showUpdateNotification() {
    const notification = document.createElement('div');
    notification.className = 'alert alert-info alert-dismissible fade show position-fixed';
    notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; max-width: 400px;';
    notification.innerHTML = `
      <i class="fas fa-download me-2"></i>
      <strong>Update Available</strong>
      <p class="mb-2">A new version is available. Click update to refresh.</p>
      <button type="button" class="btn btn-sm btn-primary me-2" data-action="update-now">
        Update Now
      </button>
      <button type="button" class="btn btn-sm btn-secondary" data-action="dismiss">
        Later
      </button>
    `;

    // Add event delegation for buttons
    notification.addEventListener('click', (event) => {
      const action = event.target.dataset.action;
      if (action === 'update-now') {
        window.location.reload();
      } else if (action === 'dismiss') {
        notification.remove();
      }
    });

    document.body.appendChild(notification);

    setTimeout(() => {
      if (notification.parentNode) {
        notification.remove();
      }
    }, 30000);
  }

  getStatus() {
    if (!this.registration) {
      return { status: 'not-registered', supported: this.isSupported };
    }

    return {
      status: this.registration.active ? 'active' : 'installing',
      supported: this.isSupported,
      updateAvailable: this.updateAvailable,
      scope: this.registration.scope,
    };
  }
}

// Create singleton instance
const serviceWorkerManager = new SimpleServiceWorkerManager();

// ===== NETWORK UTILITIES =====

/**
 * Show offline indicator
 */
function showOfflineIndicator() {
  if (document.getElementById('offline-indicator')) return;

  const indicator = document.createElement('div');
  indicator.id = 'offline-indicator';
  indicator.className = 'offline-indicator alert alert-warning alert-dismissible fade show position-fixed';
  indicator.style.cssText = 'top: 20px; left: 50%; transform: translateX(-50%); z-index: 9999; max-width: 400px;';
  indicator.innerHTML = `
    <i class="fas fa-wifi-slash me-2"></i>
    <strong>You're Offline</strong>
    <p class="mb-2">Some features may be limited while offline.</p>
    <button type="button" class="btn-close" data-action="dismiss" aria-label="Close"></button>
  `;

  // Add event listener for close button
  indicator.addEventListener('click', (event) => {
    if (event.target.dataset.action === 'dismiss') {
      indicator.remove();
    }
  });

  document.body.appendChild(indicator);
}

/**
 * Check if online
 */
function isOnline() {
  return navigator.onLine;
}

/**
 * Wait for network connection
 */
function waitForOnline() {
  return new Promise((resolve) => {
    if (navigator.onLine) {
      resolve();
    } else {
      const handleOnline = () => {
        window.removeEventListener('online', handleOnline);
        resolve();
      };
      window.addEventListener('online', handleOnline);
    }
  });
}

/**
 * Network status monitor
 */
function setupNetworkMonitoring() {
  let isCurrentlyOnline = navigator.onLine;

  const updateOnlineStatus = () => {
    const wasOnline = isCurrentlyOnline;
    isCurrentlyOnline = navigator.onLine;

    if (!wasOnline && isCurrentlyOnline) {
      logger.info('Connection restored');
      // Remove offline indicators
      document.querySelectorAll('.offline-indicator').forEach((el) => el.remove());
    } else if (wasOnline && !isCurrentlyOnline) {
      logger.warn('Connection lost');
      showOfflineIndicator();
    }
  };

  window.addEventListener('online', updateOnlineStatus);
  window.addEventListener('offline', updateOnlineStatus);

  return () => {
    window.removeEventListener('online', updateOnlineStatus);
    window.removeEventListener('offline', updateOnlineStatus);
  };
}

// ===== INITIALIZATION =====

/**
 * Initialize API utilities
 */
function initAPIUtils() {
  // Register service worker
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      serviceWorkerManager.register();
    });
  } else {
    serviceWorkerManager.register();
  }

  // Setup network monitoring
  setupNetworkMonitoring();

  logger.info('API utilities initialized');
}

// Auto-initialize
initAPIUtils();

// ===== EXPORTS =====

export {
  // API methods
  apiRequest,
  get,
  post,
  put,
  del,
  getCSRFToken,

  // Service worker
  serviceWorkerManager,

  // Network utilities
  isOnline,
  waitForOnline,
  setupNetworkMonitoring,
  showOfflineIndicator,

  // Initialization
  initAPIUtils,
};

// ===== ENHANCED ERROR RECOVERY =====

/**
 * Enhanced API request with comprehensive error recovery
 */
export async function apiRequestWithRecovery(url, options = {}) {
  const MAX_RETRIES = 3;
  const RETRY_DELAY_BASE_MS = 1000;
  const REQUEST_TIMEOUT_MS = 15000;

  // Circuit breaker state
  const circuit_breaker_key = `circuit_breaker_${url.split('/')[3] || 'default'}`;
  const circuit_breaker_data = getCircuitBreakerState(circuit_breaker_key);

  // Check circuit breaker
  if (circuit_breaker_data.is_open) {
    const time_since_failure = Date.now() - circuit_breaker_data.last_failure;
    if (time_since_failure < 60000) { // 1 minute circuit breaker
      throw new Error('Service temporarily unavailable. Please try again later.');
    } else {
      // Reset circuit breaker
      resetCircuitBreaker(circuit_breaker_key);
    }
  }

  for (let attempt = 1; attempt <= MAX_RETRIES; attempt++) {
    try {
      console.log(`Enhanced API request attempt ${attempt}/${MAX_RETRIES} to ${url}`);

      // Check network connectivity
      if (!navigator.onLine) {
        throw new Error('No internet connection. Please check your network and try again.');
      }

      // Create request with timeout
      const controller = new AbortController();
      const timeout_id = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

      const headers = new Headers(options.headers || {});

      // Add CSRF token
      if (!headers.has('X-CSRFToken')) {
        const csrf_token = getCSRFToken();
        if (csrf_token) {
          headers.set('X-CSRFToken', csrf_token);
        }
      }

      // Handle JSON body
      let body = options.body;
      if (body && typeof body === 'object' && !(body instanceof FormData)) {
        if (!headers.has('Content-Type')) {
          headers.set('Content-Type', 'application/json');
        }
        body = JSON.stringify(body);
      }

      // Add AJAX header
      if (!headers.has('X-Requested-With')) {
        headers.set('X-Requested-With', 'XMLHttpRequest');
      }

      const final_options = {
        method: 'GET',
        ...options,
        headers,
        body,
        signal: controller.signal
      };

      const response = await fetch(url, final_options);

      clearTimeout(timeout_id);

      // Reset circuit breaker on success
      resetCircuitBreaker(circuit_breaker_key);

      if (!response.ok) {
        const error_data = await response.json().catch(() => ({}));

        // Handle different error types
        if (response.status === 401) {
          throw new Error('Session expired. Please refresh the page and log in again.');
        } else if (response.status === 403) {
          throw new Error('Access denied. You do not have permission to perform this action.');
        } else if (response.status === 404) {
          throw new Error('Resource not found. The requested item may have been deleted.');
        } else if (response.status === 422) {
          throw new Error(error_data.message || 'Validation error. Please check your input.');
        } else if (response.status >= 500) {
          // Server error - can retry
          throw new Error(error_data.message || `Server error (${response.status}). Retrying...`);
        } else {
          // Client error - don't retry
          throw new Error(error_data.message || `Request failed (${response.status})`);
        }
      }

      console.log(`Enhanced API request successful on attempt ${attempt}`);
      return await response.json();

    } catch (error) {
      console.warn(`Enhanced API request attempt ${attempt} failed:`, error.message);

      // Record failure for circuit breaker
      recordCircuitBreakerFailure(circuit_breaker_key);

      // Don't retry certain errors
      const non_retryable_errors = [
        'Session expired',
        'Access denied',
        'Resource not found',
        'Validation error',
        'No internet connection'
      ];

      const is_non_retryable = non_retryable_errors.some(err => error.message.includes(err));

      if (attempt === MAX_RETRIES || is_non_retryable) {
        // Provide user-friendly error messages
        if (error.name === 'AbortError') {
          throw new Error('Request timed out. Please check your connection and try again.');
        }

        if (error.message.includes('NetworkError') || error.message.includes('fetch')) {
          throw new Error('Network error. Please check your internet connection.');
        }

        throw error;
      }

      // Wait before retrying with exponential backoff + jitter
      const base_delay = RETRY_DELAY_BASE_MS * Math.pow(2, attempt - 1);
      const jitter = Math.random() * 1000; // Add up to 1 second of jitter
      const delay_ms = base_delay + jitter;

      console.log(`Retrying in ${Math.round(delay_ms)}ms...`);
      await new Promise(resolve => setTimeout(resolve, delay_ms));
    }
  }
}

/**
 * Circuit breaker implementation
 */
function getCircuitBreakerState(key) {
  try {
    const stored = localStorage.getItem(`circuit_breaker_${key}`);
    if (stored) {
      return JSON.parse(stored);
    }
  } catch (error) {
    console.warn('Failed to read circuit breaker state:', error);
  }

  return {
    failure_count: 0,
    last_failure: 0,
    is_open: false
  };
}

function recordCircuitBreakerFailure(key) {
  try {
    const state = getCircuitBreakerState(key);
    state.failure_count++;
    state.last_failure = Date.now();

    // Open circuit breaker after 5 failures
    if (state.failure_count >= 5) {
      state.is_open = true;
      console.warn(`Circuit breaker opened for ${key}`);
    }

    localStorage.setItem(`circuit_breaker_${key}`, JSON.stringify(state));
  } catch (error) {
    console.warn('Failed to record circuit breaker failure:', error);
  }
}

function resetCircuitBreaker(key) {
  try {
    localStorage.removeItem(`circuit_breaker_${key}`);
  } catch (error) {
    console.warn('Failed to reset circuit breaker:', error);
  }
}

/**
 * Wrapper for backward compatibility with existing apiRequest calls
 */
export async function apiRequestEnhanced(url, options = {}) {
  try {
    return await apiRequestWithRecovery(url, options);
  } catch (error) {
    // Log for monitoring
    console.error('API request failed with recovery:', {
      url,
      error: error.message,
      timestamp: new Date().toISOString()
    });

    // Re-throw for calling code to handle
    throw error;
  }
}

// Default export
export default {
  apiRequest,
  apiRequestWithRecovery,
  apiRequestEnhanced,
  get,
  post,
  put,
  del,
  getCSRFToken,
  serviceWorkerManager,
  isOnline,
  waitForOnline,
  setupNetworkMonitoring,
  showOfflineIndicator,
  initAPIUtils,
};
