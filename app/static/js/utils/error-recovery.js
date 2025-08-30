/**
 * Enhanced Error Recovery and Fallback Mechanisms
 * Following TigerStyle principles for robust error handling
 */

import { showErrorToast, showWarningToast, showInfoToast } from './notifications.js';

// Error types for categorized handling
export const ERROR_TYPES = {
  NETWORK: 'network',
  GOOGLE_MAPS: 'google_maps',
  FORM_VALIDATION: 'form_validation',
  API_RESPONSE: 'api_response',
  PERMISSION: 'permission',
  TIMEOUT: 'timeout',
  UNKNOWN: 'unknown'
};

// Retry configuration with exponential backoff
const RETRY_CONFIG = {
  max_attempts: 3,
  initial_delay_ms: 1000,
  max_delay_ms: 10000,
  backoff_multiplier: 2
};

/**
 * Enhanced error class with recovery context
 */
export class RecoverableError extends Error {
  constructor(message, type = ERROR_TYPES.UNKNOWN, recovery_options = {}) {
    super(message);
    this.name = 'RecoverableError';
    this.type = type;
    this.recovery_options = recovery_options;
    this.timestamp = new Date();
    this.user_friendly_message = recovery_options.user_message || message;
  }
}

/**
 * Retry mechanism with exponential backoff and circuit breaker
 */
export class RetryManager {
  constructor() {
    this.failure_counts = new Map();
    this.circuit_breaker_threshold = 5;
    this.circuit_breaker_reset_time_ms = 60000;
  }

  async retry_with_backoff(operation, context = '', options = {}) {
    const config = { ...RETRY_CONFIG, ...options };
    const operation_key = context || 'default';

    // Check circuit breaker
    if (this.is_circuit_open(operation_key)) {
      throw new RecoverableError(
        `Service temporarily unavailable: ${context}`,
        ERROR_TYPES.TIMEOUT,
        {
          user_message: 'Service is temporarily unavailable. Please try again later.',
          retry_after_ms: this.circuit_breaker_reset_time_ms
        }
      );
    }

    let last_error = null;
    let delay_ms = config.initial_delay_ms;

    for (let attempt = 1; attempt <= config.max_attempts; attempt++) {
      try {
        const result = await operation(attempt);

        // Reset failure count on success
        this.failure_counts.delete(operation_key);

        return result;
      } catch (error) {
        last_error = error;
        this.record_failure(operation_key);

        console.warn(`Attempt ${attempt}/${config.max_attempts} failed for ${context}:`, error.message);

        if (attempt === config.max_attempts) {
          break;
        }

        // Wait before retrying with exponential backoff
        await this.wait(delay_ms);
        delay_ms = Math.min(delay_ms * config.backoff_multiplier, config.max_delay_ms);
      }
    }

    // All attempts failed
    throw new RecoverableError(
      `Operation failed after ${config.max_attempts} attempts: ${last_error.message}`,
      this.classify_error(last_error),
      {
        user_message: 'Operation failed. Please check your connection and try again.',
        original_error: last_error,
        attempts_made: config.max_attempts
      }
    );
  }

  is_circuit_open(operation_key) {
    const failure_count = this.failure_counts.get(operation_key);
    return failure_count && failure_count.count >= this.circuit_breaker_threshold;
  }

  record_failure(operation_key) {
    const current = this.failure_counts.get(operation_key) || { count: 0, first_failure: Date.now() };
    current.count++;

    // Reset circuit breaker after timeout
    if (Date.now() - current.first_failure > this.circuit_breaker_reset_time_ms) {
      current.count = 1;
      current.first_failure = Date.now();
    }

    this.failure_counts.set(operation_key, current);
  }

  classify_error(error) {
    if (error instanceof TypeError && error.message.includes('fetch')) {
      return ERROR_TYPES.NETWORK;
    }
    if (error.message.includes('google') || error.message.includes('maps')) {
      return ERROR_TYPES.GOOGLE_MAPS;
    }
    if (error.name === 'ValidationError') {
      return ERROR_TYPES.FORM_VALIDATION;
    }
    if (error.message.includes('timeout') || error.name === 'AbortError') {
      return ERROR_TYPES.TIMEOUT;
    }
    return ERROR_TYPES.UNKNOWN;
  }

  wait(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}

// Global retry manager instance
const retry_manager = new RetryManager();

/**
 * Google Maps API fallback and recovery
 */
export class GoogleMapsRecovery {
  constructor() {
    this.fallback_enabled = true;
    this.initialization_timeout_ms = 10000;
    this.backup_geocoding_service = 'nominatim'; // OpenStreetMap Nominatim as fallback
  }

  async initialize_with_fallback(api_key, libraries = ['places']) {
    try {
      return await retry_manager.retry_with_backoff(
        async (attempt) => {
          console.log(`Google Maps initialization attempt ${attempt}`);

          return await this.load_google_maps_api(api_key, libraries);
        },
        'google_maps_init',
        { max_attempts: 3, initial_delay_ms: 2000 }
      );
    } catch (error) {
      console.error('Google Maps initialization failed completely:', error);

      if (this.fallback_enabled) {
        showWarningToast('Map services degraded. Basic functionality available.');
        return this.setup_fallback_geocoding();
      }

      throw new RecoverableError(
        'Map services unavailable',
        ERROR_TYPES.GOOGLE_MAPS,
        {
          user_message: 'Map features are currently unavailable. You can still add restaurants manually.',
          enable_manual_entry: true
        }
      );
    }
  }

  async load_google_maps_api(api_key, libraries) {
    return new Promise((resolve, reject) => {
      const timeout_id = setTimeout(() => {
        reject(new Error('Google Maps API load timeout'));
      }, this.initialization_timeout_ms);

      const script = document.createElement('script');
      script.src = `https://maps.googleapis.com/maps/api/js?key=${api_key}&libraries=${libraries.join(',')}&loading=async`;
      script.async = true;
      script.defer = true;

      script.onload = () => {
        clearTimeout(timeout_id);
        if (window.google?.maps) {
          resolve(window.google);
        } else {
          reject(new Error('Google Maps API loaded but not available'));
        }
      };

      script.onerror = () => {
        clearTimeout(timeout_id);
        reject(new Error('Failed to load Google Maps API script'));
      };

      document.head.appendChild(script);
    });
  }

  setup_fallback_geocoding() {
    // Provide basic geocoding fallback using Nominatim (OpenStreetMap)
    return {
      geocode_address: async (address) => {
        try {
          const encoded_address = encodeURIComponent(address);
          const response = await fetch(
            `https://nominatim.openstreetmap.org/search?format=json&q=${encoded_address}&limit=1`,
            { timeout: 5000 }
          );

          const data = await response.json();
          if (data && data.length > 0) {
            return {
              lat: parseFloat(data[0].lat),
              lng: parseFloat(data[0].lon),
              formatted_address: data[0].display_name
            };
          }

          throw new Error('No results found');
        } catch (error) {
          console.warn('Fallback geocoding failed:', error);
          return null;
        }
      },

      is_fallback: true
    };
  }
}

/**
 * Form submission recovery with offline support
 */
export class FormRecovery {
  constructor() {
    this.offline_storage_key = 'meal_tracker_offline_forms';
    this.auto_save_interval_ms = 30000; // 30 seconds
    this.auto_save_enabled = true;
  }

  async submit_with_recovery(form_data, endpoint, options = {}) {
    const submission_id = this.generate_submission_id();

    try {
      // Auto-save form data before submission
      if (this.auto_save_enabled) {
        this.save_form_draft(form_data, submission_id);
      }

      const result = await retry_manager.retry_with_backoff(
        async (attempt) => {
          console.log(`Form submission attempt ${attempt}`);

          if (!navigator.onLine) {
            throw new RecoverableError(
              'No internet connection',
              ERROR_TYPES.NETWORK,
              { user_message: 'No internet connection. Form will be saved for later.' }
            );
          }

          const response = await fetch(endpoint, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'X-CSRFToken': this.get_csrf_token(),
              ...options.headers
            },
            body: JSON.stringify(form_data),
            signal: this.create_timeout_signal(options.timeout_ms || 10000)
          });

          if (!response.ok) {
            const error_data = await response.json().catch(() => ({}));
            throw new RecoverableError(
              error_data.message || `HTTP ${response.status}`,
              ERROR_TYPES.API_RESPONSE,
              {
                user_message: error_data.user_message || 'Server error. Please try again.',
                status: response.status,
                server_errors: error_data.errors
              }
            );
          }

          return await response.json();
        },
        `form_submit_${endpoint}`,
        { max_attempts: 3, initial_delay_ms: 1000 }
      );

      // Clear draft on successful submission
      this.clear_form_draft(submission_id);
      return result;

    } catch (error) {
      if (error.type === ERROR_TYPES.NETWORK) {
        // Save for offline submission
        this.save_for_offline_submission(form_data, endpoint, submission_id);
        showInfoToast('Form saved. Will submit when connection is restored.');
        return { offline_saved: true, submission_id };
      }

      throw error;
    }
  }

  save_form_draft(form_data, submission_id) {
    try {
      const drafts = this.get_stored_drafts();
      drafts[submission_id] = {
        data: form_data,
        timestamp: Date.now(),
        type: 'draft'
      };
      localStorage.setItem(this.offline_storage_key, JSON.stringify(drafts));
    } catch (error) {
      console.warn('Failed to save form draft:', error);
    }
  }

  save_for_offline_submission(form_data, endpoint, submission_id) {
    try {
      const stored_data = this.get_stored_drafts();
      stored_data[submission_id] = {
        data: form_data,
        endpoint: endpoint,
        timestamp: Date.now(),
        type: 'pending_submission'
      };
      localStorage.setItem(this.offline_storage_key, JSON.stringify(stored_data));
    } catch (error) {
      console.warn('Failed to save for offline submission:', error);
    }
  }

  async retry_offline_submissions() {
    if (!navigator.onLine) return;

    const stored_data = this.get_stored_drafts();
    const pending_submissions = Object.entries(stored_data)
      .filter(([_, data]) => data.type === 'pending_submission');

    for (const [submission_id, submission_data] of pending_submissions) {
      try {
        await this.submit_with_recovery(
          submission_data.data,
          submission_data.endpoint,
          { timeout_ms: 5000 }
        );

        showInfoToast('Offline form submitted successfully!');
        this.clear_form_draft(submission_id);

      } catch (error) {
        console.warn(`Failed to submit offline form ${submission_id}:`, error);
        // Keep for next retry
      }
    }
  }

  get_stored_drafts() {
    try {
      const stored = localStorage.getItem(this.offline_storage_key);
      return stored ? JSON.parse(stored) : {};
    } catch (error) {
      console.warn('Failed to read stored drafts:', error);
      return {};
    }
  }

  clear_form_draft(submission_id) {
    try {
      const drafts = this.get_stored_drafts();
      delete drafts[submission_id];
      localStorage.setItem(this.offline_storage_key, JSON.stringify(drafts));
    } catch (error) {
      console.warn('Failed to clear form draft:', error);
    }
  }

  generate_submission_id() {
    return `form_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  get_csrf_token() {
    return document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';
  }

  create_timeout_signal(timeout_ms) {
    const controller = new AbortController();
    setTimeout(() => controller.abort(), timeout_ms);
    return controller.signal;
  }
}

/**
 * Global error recovery initialization
 */
export function initialize_error_recovery() {
  const google_maps_recovery = new GoogleMapsRecovery();
  const form_recovery = new FormRecovery();

  // Set up online/offline event listeners
  window.addEventListener('online', () => {
    console.log('Connection restored, retrying offline submissions');
    form_recovery.retry_offline_submissions();
  });

  window.addEventListener('offline', () => {
    console.log('Connection lost, enabling offline mode');
    showWarningToast('Connection lost. Forms will be saved for later submission.');
  });

  // Set up global error handler
  window.addEventListener('error', (event) => {
    console.error('Global error caught:', event.error);

    const error = new RecoverableError(
      event.error.message,
      ERROR_TYPES.UNKNOWN,
      { user_message: 'An unexpected error occurred. Please refresh the page if problems persist.' }
    );

    handle_error_with_recovery(error);
  });

  // Set up unhandled promise rejection handler
  window.addEventListener('unhandledrejection', (event) => {
    console.error('Unhandled promise rejection:', event.reason);

    const error = new RecoverableError(
      event.reason.message || 'Unknown promise rejection',
      ERROR_TYPES.UNKNOWN,
      { user_message: 'An error occurred. Please try again.' }
    );

    handle_error_with_recovery(error);
    event.preventDefault(); // Prevent console error
  });

  return {
    google_maps_recovery,
    form_recovery,
    retry_manager
  };
}

/**
 * Centralized error handling with user-friendly recovery options
 */
export function handle_error_with_recovery(error) {
  console.error('Handling error with recovery:', error);

  if (error instanceof RecoverableError) {
    switch (error.type) {
      case ERROR_TYPES.NETWORK:
        showWarningToast(error.user_friendly_message);
        break;

      case ERROR_TYPES.GOOGLE_MAPS:
        showWarningToast(error.user_friendly_message);
        if (error.recovery_options.enable_manual_entry) {
          show_manual_entry_fallback();
        }
        break;

      case ERROR_TYPES.FORM_VALIDATION:
        showErrorToast(error.user_friendly_message);
        break;

      case ERROR_TYPES.TIMEOUT:
        showWarningToast(error.user_friendly_message);
        break;

      default:
        showErrorToast(error.user_friendly_message);
    }
  } else {
    // Handle regular errors
    showErrorToast('An unexpected error occurred. Please try again.');
  }
}

function show_manual_entry_fallback() {
  // Show a hint that manual entry is available when maps fail
  const form = document.getElementById('restaurantForm');
  if (form) {
    const address_input = form.querySelector('#address');
    if (address_input) {
      address_input.placeholder = 'Enter address manually (maps unavailable)';
      address_input.style.borderColor = '#ffc107'; // Warning color
    }
  }
}

// Export instances for global use
export const global_retry_manager = retry_manager;
export const google_maps_recovery = new GoogleMapsRecovery();
export const form_recovery = new FormRecovery();
