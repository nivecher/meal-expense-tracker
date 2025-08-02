/**
 * Error Handler Utility
 *
 * Provides consistent error handling across the application
 */

import { showErrorToast, showWarningToast } from './notifications.js';

class ErrorHandler {
  /**
     * Handle API errors consistently
     * @param {Error|Object} error - The error object
     * @param {string} defaultMessage - Default error message
     * @returns {Object} Error details
     */
  static handleApiError (error, defaultMessage = 'An error occurred') {
    let message = defaultMessage;
    let details = null;
    let status = null;

    if (error.response) {
      // Server responded with error status
      const { status: responseStatus, data } = error.response;
      status = responseStatus;
      message = data?.message || defaultMessage;
      details = data?.details || null;

      switch (status) {
        case 400:
          message = 'Invalid request. Please check your input.';
          break;
        case 401:
          this.handleUnauthorized();
          return { error: 'Session expired. Please log in again.', status };
        case 403:
          message = 'You do not have permission to perform this action';
          break;
        case 404:
          message = 'The requested resource was not found';
          break;
        case 422:
          return {
            error: 'Validation failed',
            details: data?.errors || {},
            validation: true,
            status,
          };
        case 429:
          message = 'Too many requests. Please try again later.';
          break;
        case 500:
          message = 'A server error occurred. Please try again.';
          break;
      }
    } else if (error.request) {
      // Request was made but no response received
      message = 'Unable to connect to the server. Please check your connection.';
    } else if (error.message) {
      // Something happened in setting up the request
      message = error.message;
    }

    showErrorToast(message);
    console.error('API Error:', error);
    return { error: message, details, status };
  }

  /**
     * Handle unauthorized access
     */
  static handleUnauthorized () {
    // Redirect to login with a message
    const currentPath = encodeURIComponent(window.location.pathname + window.location.search);
    window.location.href = `/auth/login?next=${currentPath}`;
  }

  /**
     * Handle network errors
     * @param {Error} error - The error object
     * @returns {Object} Error details
     */
  static handleNetworkError (error) {
    const message = 'Network error. Please check your connection.';
    showErrorToast(message);
    console.error('Network Error:', error);
    return { error: message };
  }

  /**
     * Handle Google Maps API errors
     * @param {Error} error - The error object
     * @returns {Object} Error details
     */
  static handleMapsError (error) {
    let message = 'Failed to load Google Maps';

    switch(error?.code) {
      case 'PERMISSION_DENIED':
        message = 'Location permission denied. Using default location instead.';
        break;
      case 'POSITION_UNAVAILABLE':
        message = 'Location information is unavailable.';
        break;
      case 'TIMEOUT':
        message = 'The request to get user location timed out.';
        break;
      default:
        message = error?.message || message;
    }

    showWarningToast(message);
    console.warn('Maps Error:', error);
    return { error: message };
  }
}

export default ErrorHandler;
