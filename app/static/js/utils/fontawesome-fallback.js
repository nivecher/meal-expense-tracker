/**
 * Font Awesome Fallback Utility
 * Checks if Font Awesome loaded correctly and provides fallback if needed
 */

function initFontawesomeFallback() {
  const testIcon = document.createElement('i');
  testIcon.className = 'fas fa-check';
  testIcon.style.display = 'none';
  document.body.appendChild(testIcon);

  const computedStyle = window.getComputedStyle(testIcon);
  if (computedStyle.fontFamily.indexOf('Font Awesome') === -1) {
    console.warn('Font Awesome failed to load, trying fallback...');
    const fallbackLink = document.createElement('link');
    fallbackLink.rel = 'stylesheet';
    fallbackLink.href = 'https://use.fontawesome.com/releases/v6.6.0/css/all.css';
    document.head.appendChild(fallbackLink);
  }
  document.body.removeChild(testIcon);
}

// Auto-initialize when DOM is ready
document.addEventListener('DOMContentLoaded', initFontawesomeFallback);

// Export for manual initialization if needed
export { initFontawesomeFallback };
