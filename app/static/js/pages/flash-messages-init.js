/**
 * Flash Messages Initialization Module
 * Handles automatic initialization of flash messages from HTML data attributes
 * Follows HTML-JS separation rules
 */

import { initFlashMessages } from '../utils/flash-messages.js';

/**
 * Initialize flash messages from HTML data attributes
 */
function init() {
  const flash_container = document.getElementById('flash-messages');
  if (!flash_container) {
    return;
  }

  const messages_data = flash_container.dataset.messages || '{}';

  try {
    const messages = Object.values(JSON.parse(messages_data));
    if (messages.length > 0) {
      initFlashMessages(messages);
    }
  } catch (error) {
    console.error('Error parsing flash messages:', error);
  }
}

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}

// Export for testing
export { init };
