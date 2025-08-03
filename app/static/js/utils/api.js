/**
 * API utility functions for making HTTP requests with CSRF protection
 * @module api
 */

import { showToast } from './notifications.js';

/**
 * Get the CSRF token from the meta tag
 * @returns {string} The CSRF token
 */
const getCSRFToken = () => {
  const metaTag = document.querySelector('meta[name="csrf-token"]');
  return metaTag ? metaTag.getAttribute('content') : '';
};

/**
 * Make an API request with CSRF protection
 * @param {string} url - The URL to fetch
 * @param {Object} options - Fetch options
 * @returns {Promise<Object>} The JSON response
 * @throws {Error} If the request fails
 */
const apiRequest = async (url, options = {}) => {
  // Ensure headers exist
  const headers = new Headers(options.headers || {});

  // Add CSRF token if not already set
  if (!headers.has('X-CSRFToken')) {
    const csrfToken = getCSRFToken();
    if (csrfToken) {
      headers.set('X-CSRFToken', csrfToken);
    }
  }

  // Ensure we're sending the right content type for JSON
  if (options.body && typeof options.body === 'object' && !(options.body instanceof FormData)) {
    if (!headers.has('Content-Type')) {
      headers.set('Content-Type', 'application/json');
    }
    options.body = JSON.stringify(options.body);
  }

  // Add X-Requested-With header for AJAX requests
  if (!headers.has('X-Requested-With')) {
    headers.set('X-Requested-With', 'XMLHttpRequest');
  }

  // Ensure credentials are included for cross-origin requests
  const fetchOptions = {
    ...options,
    headers,
    credentials: 'same-origin',
  };

  try {
    const response = await fetch(url, fetchOptions);

    // Handle non-2xx responses
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      const error = new Error(errorData.message || `HTTP error! status: ${response.status}`);
      error.status = response.status;
      error.data = errorData;
      throw error;
    }

    // Return JSON if response has content
    const contentType = response.headers.get('content-type');
    if (contentType && contentType.includes('application/json')) {
      return await response.json();
    }

    return await response.text();
  } catch (error) {
    console.error('API request failed:', error);

    // Show user-friendly error message
    const errorMessage = error.data?.message || error.message || 'An error occurred. Please try again.';
    showToast.error(errorMessage);

    throw error;
  }
};

/**
 * Make a GET request
 * @param {string} url - The URL to fetch
 * @param {Object} params - Query parameters
 * @param {Object} options - Additional fetch options
 * @returns {Promise<Object>} The JSON response
 */
const get = (url, params = {}, options = {}) => {
  const queryString = new URLSearchParams(params).toString();
  const urlWithParams = queryString ? `${url}?${queryString}` : url;

  return apiRequest(urlWithParams, {
    ...options,
    method: 'GET',
  });
};

/**
 * Make a POST request
 * @param {string} url - The URL to fetch
 * @param {Object} data - The request body
 * @param {Object} options - Additional fetch options
 * @returns {Promise<Object>} The JSON response
 */
const post = (url, data = {}, options = {}) => {
  return apiRequest(url, {
    ...options,
    method: 'POST',
    body: data,
  });
};

/**
 * Make a PUT request
 * @param {string} url - The URL to fetch
 * @param {Object} data - The request body
 * @param {Object} options - Additional fetch options
 * @returns {Promise<Object>} The JSON response
 */
const put = (url, data = {}, options = {}) => {
  return apiRequest(url, {
    ...options,
    method: 'PUT',
    body: data,
  });
};

/**
 * Make a DELETE request
 * @param {string} url - The URL to fetch
 * @param {Object} options - Additional fetch options
 * @returns {Promise<Object>} The JSON response
 */
const del = (url, options = {}) => {
  return apiRequest(url, {
    ...options,
    method: 'DELETE',
  });
};

export { apiRequest, get, post, put, del, getCSRFToken };
