/**
 * Debug utilities for development
 *
 * This module provides debugging utilities that can be conditionally loaded
 * based on the environment.
 */

/**
 * Initialize debug logging for Google Maps API
 * @param {string} apiKey - The Google Maps API key
 */
export function initGoogleMapsDebug(apiKey) {
    console.log('Debug: Initializing Google Maps debug tools');

    if (!apiKey) {
        console.error('Google Maps API key is missing!');
        console.log('Current config.GOOGLE_MAPS_API_KEY:', window.GOOGLE_MAPS_API_KEY || 'Not set');
        console.log('Current google_maps_api_key:', window.google_maps_api_key || 'Not set');
    } else {
        console.log('Google Maps API key is configured');
    }

    // Add debug styles for better visibility
    const style = document.createElement('style');
    style.textContent = `
        .debug-panel {
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: rgba(0,0,0,0.8);
            color: #fff;
            padding: 10px 15px;
            border-radius: 4px;
            font-family: monospace;
            font-size: 12px;
            z-index: 9999;
            max-width: 300px;
            max-height: 200px;
            overflow: auto;
        }
        .debug-panel h4 {
            margin: 0 0 8px 0;
            padding-bottom: 4px;
            border-bottom: 1px solid #555;
        }
        .debug-panel pre {
            margin: 0;
            white-space: pre-wrap;
        }
    `;
    document.head.appendChild(style);

    // Create debug panel
    const panel = document.createElement('div');
    panel.className = 'debug-panel';
    panel.innerHTML = `
        <h4>Google Maps Debug</h4>
        <pre>API Key: ${apiKey ? '***PRESENT***' : 'MISSING'}</pre>
        <pre>Window.GOOGLE_MAPS_API_KEY: ${window.GOOGLE_MAPS_API_KEY ? 'PRESENT' : 'MISSING'}</pre>
    `;
    document.body.appendChild(panel);
}

// Auto-initialize if in debug mode
if (window.GOOGLE_MAPS_DEBUG) {
    document.addEventListener('DOMContentLoaded', () => {
        initGoogleMapsDebug(window.GOOGLE_MAPS_API_KEY);
    });
}
