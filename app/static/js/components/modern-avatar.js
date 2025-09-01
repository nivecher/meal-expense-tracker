/**
 * Modern Avatar Component
 * Handles avatar images with intelligent fallbacks to user initials
 * Follows TIGER Style principles: Safety, Performance, Developer Experience
 */

class ModernAvatarManager {
  constructor() {
    this.avatars = new Map();
    this.defaultColors = [
      ['#667eea', '#764ba2'], // Purple gradient
      ['#f093fb', '#f5576c'], // Pink gradient
      ['#4facfe', '#00f2fe'], // Blue gradient
      ['#43e97b', '#38f9d7'], // Green gradient
      ['#fa709a', '#fee140'], // Orange gradient
      ['#a8edea', '#fed6e3'], // Teal gradient
      ['#ffecd2', '#fcb69f'], // Peach gradient
      ['#ff9a9e', '#fecfef'],  // Rose gradient
    ];

    this.init();
  }

  init() {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', () => this.setupAvatars());
    } else {
      this.setupAvatars();
    }

    // Also run after a short delay to catch any dynamically loaded avatars
    setTimeout(() => this.setupAvatars(), 100);

    // Watch for dynamically added avatars
    this.setupMutationObserver();
  }

  setupMutationObserver() {
    if (typeof MutationObserver === 'undefined') return;

    const observer = new MutationObserver((mutations) => {
      let shouldUpdate = false;

      mutations.forEach((mutation) => {
        mutation.addedNodes.forEach((node) => {
          if (node.nodeType === Node.ELEMENT_NODE) {
            // Check if the added node is an avatar or contains avatars
            if (node.hasAttribute && node.hasAttribute('data-avatar')) {
              shouldUpdate = true;
            } else if (node.querySelector && node.querySelector('[data-avatar]')) {
              shouldUpdate = true;
            }
          }
        });
      });

      if (shouldUpdate) {
        setTimeout(() => this.setupAvatars(), 50);
      }
    });

    observer.observe(document.body, {
      childList: true,
      subtree: true
    });
  }

  setupAvatars() {
    const avatarElements = document.querySelectorAll('[data-avatar]');

    avatarElements.forEach((element, index) => {
      // Skip if already processed
      if (element.dataset.avatarProcessed) return;

      this.processAvatar(element, index);
      element.dataset.avatarProcessed = 'true';
    });
  }

  processAvatar(element, index = 0) {
    const avatarId = `avatar-${Date.now()}-${index}`;
    const avatarData = this.extractAvatarData(element);

    // Store avatar info
    this.avatars.set(avatarId, {
      element,
      ...avatarData,
    });

    // Check if there's already an initials div - if so, just show it immediately
    const container = element.parentNode;
    const existingInitials = container.querySelector('.avatar-initials');

    if (existingInitials) {
      // There's already an initials div, just show it and hide the image
      existingInitials.style.display = 'flex';
      element.style.display = 'none';
      element.classList.remove('avatar-loading');
      element.classList.add('avatar-loaded');
      return;
    }

    // Try to load the image only if there's a valid source
    if (avatarData.src && avatarData.src.trim() !== '' && avatarData.src !== avatarData.fallbackSrc) {
      // Add loading state only when we're actually loading an image
      this.setLoadingState(element);
      this.loadImage(avatarId, avatarData.src);
    } else {
      // No valid source, go straight to initials without loading state
      this.showInitials(avatarId);
    }
  }

  extractAvatarData(element) {
    const rect = element.getBoundingClientRect();
    const computedStyle = window.getComputedStyle(element);

    // Get the image source and clean it up
    let src = element.src || element.dataset.src || '';
    if (src && (src.trim() === '' || src === 'about:blank' || src === 'data:,')) {
      src = '';
    }

    return {
      src: src,
      fallbackSrc: element.dataset.defaultSrc,
      alt: element.alt || '',
      username: element.dataset.username || this.extractUsernameFromAlt(element.alt),
      email: element.dataset.email || '',
      size: {
        width: parseInt(computedStyle.width) || 32,
        height: parseInt(computedStyle.height) || 32,
      },
    };
  }

  extractUsernameFromAlt(alt) {
    // Extract username from alt text patterns like "admin" or "User Avatar"
    if (!alt) return 'U';

    // Remove common words and get the meaningful part
    const cleaned = alt.replace(/\b(avatar|user|profile|image)\b/gi, '').trim();
    return cleaned || 'U';
  }

  loadImage(avatarId, src) {
    const img = new Image();
    const avatarData = this.avatars.get(avatarId);

    img.onload = () => {
      // Validate image dimensions (avoid 1x1 tracking pixels, etc.)
      if (img.naturalWidth >= 16 && img.naturalHeight >= 16) {
        this.showImage(avatarId, src);
      } else {
        this.showInitials(avatarId);
      }
    };

    img.onerror = () => {
      // Try fallback image if available
      if (avatarData.fallbackSrc && src !== avatarData.fallbackSrc) {
        this.loadImage(avatarId, avatarData.fallbackSrc);
      } else {
        this.showInitials(avatarId);
      }
    };

    // Set timeout for slow-loading images (3 seconds max)
    setTimeout(() => {
      if (!img.complete) {
        img.onload = null;
        img.onerror = null;
        this.showInitials(avatarId);
      }
    }, 3000);

    img.src = src;
  }

  showImage(avatarId, src) {
    const avatarData = this.avatars.get(avatarId);
    if (!avatarData) return;

    const { element } = avatarData;

    // Update the actual element
    element.src = src;
    element.classList.remove('avatar-loading');
    element.classList.add('avatar-loaded');

    // Ensure image styling
    element.style.objectFit = 'cover';
    element.style.opacity = '1';
    element.style.display = 'block';

    // Hide any existing initials div
    const container = element.parentNode;
    const existingInitials = container.querySelector('.avatar-initials');
    if (existingInitials) {
      existingInitials.style.display = 'none';
    }
  }

  showInitials(avatarId) {
    const avatarData = this.avatars.get(avatarId);
    if (!avatarData) return;

    const { element, username, email, size } = avatarData;
    const initials = this.generateInitials(username, email, element);
    const colors = this.getColorForUser(username || email);

    // Check if there's already an initials div in the container
    const container = element.parentNode;
    const existingInitials = container.querySelector('.avatar-initials');

    if (existingInitials) {
      // Update existing initials div
      existingInitials.textContent = initials;
      existingInitials.style.background = `linear-gradient(135deg, ${colors[0]} 0%, ${colors[1]} 100%)`;
      existingInitials.style.display = 'flex';
      element.style.display = 'none';
    } else {
      // Create new initials div (fallback for old implementations)
      const initialsElement = this.createInitialsElement(initials, colors, size);

      // Copy over classes and attributes we want to preserve
      initialsElement.className = element.className;
      initialsElement.classList.remove('avatar-loading');
      initialsElement.classList.add('avatar-initials', 'avatar-loaded');

      // Copy data attributes
      Object.keys(element.dataset).forEach((key) => {
        initialsElement.dataset[key] = element.dataset[key];
      });

      // Replace element in DOM
      element.parentNode.replaceChild(initialsElement, element);

      // Update our reference
      avatarData.element = initialsElement;
    }
  }

  generateInitials(username, email, element = null) {
    // Try to get initials from the backend if available
    if (element && element.dataset.initials) {
      return element.dataset.initials.toUpperCase();
    }

    // Fallback to client-side generation
    // Priority: username > email local part > fallback
    let source = username || email || 'User';

    // Handle email addresses
    if (source.includes('@')) {
      source = source.split('@')[0];
    }

    // Split by common separators and take first letters
    const parts = source.split(/[\s\-_.]+/).filter((part) => part.length > 0);

    if (parts.length >= 2) {
      // Use first letter of first two parts
      return (parts[0][0] + parts[1][0]).toUpperCase();
    } else if (parts.length === 1 && parts[0].length >= 2) {
      // Use first two letters of single part
      return parts[0].slice(0, 2).toUpperCase();
    }
    // Fallback to first letter or 'U'
    return (parts[0] || 'U')[0].toUpperCase();

  }

  getColorForUser(identifier) {
    if (!identifier) return this.defaultColors[0];

    // Create a simple hash from the identifier
    let hash = 0;
    for (let i = 0; i < identifier.length; i++) {
      hash = identifier.charCodeAt(i) + ((hash << 5) - hash);
    }

    // Use hash to select color consistently
    const colorIndex = Math.abs(hash) % this.defaultColors.length;
    return this.defaultColors[colorIndex];
  }

  createInitialsElement(initials, colors, size) {
    const element = document.createElement('div');
    const fontSize = Math.max(Math.floor(size.width * 0.4), 12);

    element.textContent = initials;
    element.style.cssText = `
      width: ${size.width}px;
      height: ${size.height}px;
      background: linear-gradient(135deg, ${colors[0]} 0%, ${colors[1]} 100%);
      color: white;
      font-weight: 600;
      font-size: ${fontSize}px;
      display: flex;
      align-items: center;
      justify-content: center;
      border-radius: 50%;
      box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);
      transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
      border: 2px solid rgba(255, 255, 255, 0.9);
      text-transform: uppercase;
      letter-spacing: 0.5px;
      cursor: pointer;
    `;

    // Add hover effect
    element.addEventListener('mouseenter', () => {
      element.style.transform = 'translateY(-1px)';
      element.style.boxShadow = '0 4px 12px rgba(102, 126, 234, 0.4)';
      element.style.borderColor = 'rgba(255, 255, 255, 1)';
    });

    element.addEventListener('mouseleave', () => {
      element.style.transform = '';
      element.style.boxShadow = '0 2px 8px rgba(102, 126, 234, 0.3)';
      element.style.borderColor = 'rgba(255, 255, 255, 0.9)';
    });

    return element;
  }

  setLoadingState(element) {
    // Only show loading state if there's no existing initials div
    const container = element.parentNode;
    const existingInitials = container.querySelector('.avatar-initials');

    if (!existingInitials) {
      element.classList.add('avatar-loading');
      element.style.opacity = '0.7';
    }
  }

  // Public method to refresh a specific avatar
  refreshAvatar(selector) {
    const element = document.querySelector(selector);
    if (element) {
      this.processAvatar(element);
    }
  }

  // Public method to refresh all avatars
  refreshAllAvatars() {
    this.avatars.clear();
    this.setupAvatars();
  }
}

// Initialize the modern avatar manager
const modernAvatarManager = new ModernAvatarManager();

// Export for potential use in other modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = ModernAvatarManager;
} else if (typeof window !== 'undefined') {
  window.ModernAvatarManager = ModernAvatarManager;
  window.modernAvatarManager = modernAvatarManager;
}
