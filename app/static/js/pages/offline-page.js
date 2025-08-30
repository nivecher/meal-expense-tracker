/**
 * Offline Page Module
 * Handles offline page functionality with proper HTML-JS separation
 */

function init() {
  // Event delegation for offline page actions
  document.addEventListener('click', (event) => {
    const button = event.target.closest('[data-action="check-connection"]');
    if (button) {
      checkConnection();
    }
  });

  // Auto-check connection every 5 seconds
  setInterval(checkConnection, 5000);

  // Initial check
  checkConnection();
}

function checkConnection() {
  const statusEl = document.getElementById('status');
  if (!statusEl) return;

  if (navigator.onLine) {
    statusEl.innerHTML = '<span class="connection-status online"></span>Connection restored!';
    // Optionally reload the page or redirect
    setTimeout(() => {
      window.location.reload();
    }, 2000);
  } else {
    statusEl.innerHTML = '<span class="connection-status offline"></span>Still offline...';
  }
}

// Handle online/offline events
function setupConnectionMonitoring() {
  window.addEventListener('online', () => {
    const statusEl = document.getElementById('status');
    if (statusEl) {
      statusEl.innerHTML = '<span class="connection-status online"></span>Connection restored!';
      setTimeout(() => {
        window.location.reload();
      }, 1000);
    }
  });

  window.addEventListener('offline', () => {
    const statusEl = document.getElementById('status');
    if (statusEl) {
      const statusDot = statusEl.querySelector('.connection-status');
      statusDot.className = 'connection-status offline';
      statusEl.innerHTML = '<span class="connection-status offline"></span>Connection lost';
    }
  });
}

// Initialize when the DOM is fully loaded
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    init();
    setupConnectionMonitoring();
  });
} else {
  init();
  setupConnectionMonitoring();
}

// Export for testing
export { init, checkConnection, setupConnectionMonitoring };
