/**
 * Initialize flash messages as toasts
 * @param {Array} messages - Array of message objects with type and message properties
 */

function processMessages(messages) {
  messages.forEach((msg, index) => {
    setTimeout(() => {
      window.showToast(msg.message, msg.type, 5000);
    }, index * 300);
    console.log('Flash message:', msg);
  });
}

export function initFlashMessages(messages) {
  if (!Array.isArray(messages) || messages.length === 0) return;

  // Load the toast component script if not already loaded
  if (typeof window.showToast !== 'function') {
    const script = document.createElement('script');
    script.src = '/static/js/components/toast.component.js';
    script.onload = () => processMessages(messages);
    script.onerror = (error) => {
      console.error('Failed to load toast component:', error);
    };
    document.head.appendChild(script);
  } else {
    processMessages(messages);
  }
}
