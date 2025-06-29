/**
 * Google Maps Authentication Utilities
 * Handles authentication failures and provides utility functions for Google Maps
 */

// Global authentication failure handler
window.gm_authFailure = function() {
    console.error('Google Maps API authentication failed. Please check your API key and billing status.');

    // Dispatch a custom event that other parts of the app can listen for
    const event = new CustomEvent('googleMapsAuthFailure', {
        detail: {
            message: 'Google Maps API authentication failed',
            timestamp: new Date().toISOString()
        }
    });
    document.dispatchEvent(event);
};

// Export for testing
export const gm_authFailure = window.gm_authFailure;
