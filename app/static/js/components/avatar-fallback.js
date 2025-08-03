/**
 * Avatar Fallback Component
 * Handles avatar image loading errors by falling back to a default image
 */

export function initAvatarFallback() {
  document.addEventListener('DOMContentLoaded', () => {
    const avatarImages = document.querySelectorAll('img[data-avatar]');

    avatarImages.forEach((img) => {
      // Store the original source
      const { defaultSrc } = img.dataset;

      // Add error handler
      img.addEventListener('error', () => {
        if (img.src !== defaultSrc) {
          img.src = defaultSrc;
        }
      });

      // Check if image loaded successfully
      if (img.complete && img.naturalWidth === 0) {
        // Image failed to load
        img.src = defaultSrc;
      }
    });
  });
}

// Auto-initialize if this script is loaded directly
if (typeof document !== 'undefined') {
  initAvatarFallback();
}
