/**
 * Avatar Picker Component
 * Provides avatar selection from Unsplash, DiceBear, and custom initials
 * Follows TIGER Style principles: Safety, Performance, Developer Experience
 */

class AvatarPicker {
  constructor() {
    this.container = null;
    this.avatarInput = null;
    this.selectedAvatarUrl = null;
    this.avatarOptions = [];

    // Avatar generation configurations
    this.unsplashAvatars = [
      'https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=150&h=150&fit=crop&crop=faces',
      'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=150&h=150&fit=crop&crop=faces',
      'https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=150&h=150&fit=crop&crop=faces',
      'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150&h=150&fit=crop&crop=faces',
      'https://images.unsplash.com/photo-1527980965255-d3b416303d12?w=150&h=150&fit=crop&crop=faces',
      'https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?w=150&h=150&fit=crop&crop=faces',
      'https://images.unsplash.com/photo-1517841905240-472988babdf9?w=150&h=150&fit=crop&crop=faces',
      'https://images.unsplash.com/photo-1539571696357-5a69c17a67c6?w=150&h=150&fit=crop&crop=faces',
    ];

    this.dicebearStyles = [
      'avataaars',
      'bottts',
      'identicon',
      'personas',
      'pixel-art',
    ];

    this.init();
  }

  init() {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', () => this.setup());
    } else {
      this.setup();
    }
  }

  setup() {
    this.container = document.getElementById('avatar-picker-container');
    this.avatarInput = document.getElementById('avatar-url-input');

    if (!this.container) {
      console.warn('Avatar picker container not found');
      return;
    }

    if (!this.avatarInput) {
      console.warn('Avatar URL input not found');
      return;
    }

    // Get current selection
    this.selectedAvatarUrl = this.avatarInput.value || null;

    // Generate and render avatar options
    this.generateAvatarOptions();
    this.renderAvatars();

    // Expose globally for profile.js
    window.avatarPicker = this;
  }

  generateAvatarOptions() {
    this.avatarOptions = [];

    // Add Unsplash avatars
    this.unsplashAvatars.forEach((url, index) => {
      this.avatarOptions.push({
        url,
        type: 'unsplash',
        id: `unsplash-${index}`,
      });
    });

    // Add DiceBear avatars (using seed for variety)
    this.dicebearStyles.forEach((style, index) => {
      const seed = `avatar-${index}-${Date.now()}`;
      const url = `https://api.dicebear.com/7.x/${style}/svg?seed=${seed}`;
      this.avatarOptions.push({
        url,
        type: 'dicebear',
        id: `dicebear-${index}`,
      });
    });

    // Add initials option (will be handled specially in render)
    this.avatarOptions.push({
      url: null,
      type: 'initials',
      id: 'initials',
    });
  }

  renderAvatars() {
    if (!this.container) {
      return;
    }

    // Create grid container
    const grid = document.createElement('div');
    grid.className = 'avatar-picker-grid';

    // Render each avatar option
    this.avatarOptions.forEach((option) => {
      const avatarElement = this.createAvatarElement(option);
      grid.appendChild(avatarElement);
    });

    // Clear and add grid
    this.container.innerHTML = '';
    this.container.appendChild(grid);
  }

  createAvatarElement(option) {
    const avatarDiv = document.createElement('div');
    avatarDiv.className = 'avatar-option';
    avatarDiv.dataset.avatarId = option.id;
    avatarDiv.dataset.avatarUrl = option.url || '';

    // Mark as selected if it matches current selection
    if (this.isSelected(option)) {
      avatarDiv.classList.add('selected');
    }

    // Create content based on type
    if (option.type === 'initials') {
      this.createInitialsAvatar(avatarDiv);
    } else {
      this.createImageAvatar(avatarDiv, option);
    }

    // Add click handler
    avatarDiv.addEventListener('click', () => this.selectAvatar(option));

    return avatarDiv;
  }

  createImageAvatar(container, option) {
    const img = document.createElement('img');
    img.src = option.url;
    img.alt = `Avatar ${option.type}`;
    img.loading = 'lazy';

    // Handle image errors
    img.addEventListener('error', () => {
      container.innerHTML = '<div class="avatar-placeholder">?</div>';
    });

    container.appendChild(img);
    this.addCheckmark(container);
  }

  createInitialsAvatar(container) {
    // Get user initials from page context
    const userInitials = this.getUserInitials();
    const placeholder = document.createElement('div');
    placeholder.className = 'avatar-placeholder';
    placeholder.textContent = userInitials;
    container.appendChild(placeholder);
    this.addCheckmark(container);
  }

  addCheckmark(container) {
    const checkmark = document.createElement('div');
    checkmark.className = 'checkmark';
    checkmark.innerHTML = '<i class="fas fa-check"></i>';
    container.appendChild(checkmark);
  }

  getUserInitials() {
    // Try to get initials from user data on the page
    const firstNameInput = document.getElementById('first_name');
    const lastNameInput = document.getElementById('last_name');
    const displayNameInput = document.getElementById('display_name');

    let firstInitial = '';
    let lastInitial = '';

    if (firstNameInput && firstNameInput.value) {
      firstInitial = firstNameInput.value.charAt(0).toUpperCase();
    }

    if (lastNameInput && lastNameInput.value) {
      lastInitial = lastNameInput.value.charAt(0).toUpperCase();
    }

    // Fallback to display name or username
    if (!firstInitial && !lastInitial) {
      if (displayNameInput && displayNameInput.value) {
        const displayName = displayNameInput.value.trim();
        if (displayName.length > 0) {
          firstInitial = displayName.charAt(0).toUpperCase();
          if (displayName.includes(' ')) {
            const parts = displayName.split(' ');
            lastInitial = parts[parts.length - 1].charAt(0).toUpperCase();
          }
        }
      }
    }

    // Final fallback
    if (!firstInitial && !lastInitial) {
      return 'U';
    }

    return firstInitial + lastInitial;
  }

  isSelected(option) {
    if (!this.selectedAvatarUrl) {
      return false;
    }

    // For initials, check if current avatar is empty or null
    if (option.type === 'initials') {
      return !this.selectedAvatarUrl || this.selectedAvatarUrl.trim() === '';
    }

    // For image avatars, check URL match
    return option.url === this.selectedAvatarUrl;
  }

  selectAvatar(option) {
    // Update selected state
    // For initials, set to empty string explicitly
    this.selectedAvatarUrl = option.type === 'initials' ? '' : (option.url || '');

    // Update hidden input
    if (this.avatarInput) {
      this.avatarInput.value = this.selectedAvatarUrl;
      // Trigger input event to ensure form knows value changed
      this.avatarInput.dispatchEvent(new Event('input', { bubbles: true }));
    }

    // Update visual selection
    const allOptions = this.container.querySelectorAll('.avatar-option');
    allOptions.forEach((el) => {
      el.classList.remove('selected');
    });

    const selectedElement = this.container.querySelector(
      `[data-avatar-id="${option.id}"]`,
    );
    if (selectedElement) {
      selectedElement.classList.add('selected');
    }

    // Update main avatar preview if it exists
    this.updateAvatarPreview();
  }

  updateAvatarPreview() {
    // Find the main profile avatar container
    const profileAvatarContainer = document.querySelector('.profile-avatar');
    if (!profileAvatarContainer) {
      return;
    }

    const profileAvatarImg = profileAvatarContainer.querySelector('img[data-avatar]');
    const profileAvatarInitials = profileAvatarContainer.querySelector('.avatar-initials');

    if (!profileAvatarImg) {
      return;
    }

    // Mark as manually updated to prevent modern-avatar.js from interfering
    profileAvatarImg.dataset.avatarManuallyUpdated = 'true';
    profileAvatarImg.dataset.avatarProcessed = 'false'; // Reset so it won't auto-process

    // Remove the inline onerror handler to prevent automatic fallback
    profileAvatarImg.removeAttribute('onerror');
    const originalOnError = profileAvatarImg.onerror;
    profileAvatarImg.onerror = null;

    if (this.selectedAvatarUrl) {
      // Set image source if URL is provided
      profileAvatarImg.src = this.selectedAvatarUrl;
      profileAvatarImg.style.display = '';
      if (profileAvatarInitials) {
        profileAvatarInitials.style.display = 'none';
      }

      // Wait for image to load, then restore error handler
      const img = new Image();
      img.onload = () => {
        // Image loaded successfully, keep it visible
        profileAvatarImg.style.display = '';
        if (profileAvatarInitials) {
          profileAvatarInitials.style.display = 'none';
        }
        // Restore error handler for future errors
        profileAvatarImg.onerror = originalOnError;
      };
      img.onerror = () => {
        // Image failed to load, show initials
        profileAvatarImg.style.display = 'none';
        if (profileAvatarInitials) {
          profileAvatarInitials.style.display = 'flex';
        }
        // Restore error handler
        profileAvatarImg.onerror = originalOnError;
      };
      img.src = this.selectedAvatarUrl;
    } else {
      // For initials, hide image and show initials
      profileAvatarImg.src = '';
      profileAvatarImg.style.display = 'none';
      if (profileAvatarInitials) {
        profileAvatarInitials.style.display = 'flex';
      }
      // Restore error handler
      profileAvatarImg.onerror = originalOnError;
    }
  }

  setSelectedAvatar(avatarUrl) {
    if (!avatarUrl) {
      this.selectedAvatarUrl = null;
      if (this.avatarInput) {
        this.avatarInput.value = '';
      }
      return;
    }

    this.selectedAvatarUrl = avatarUrl;

    // Update input
    if (this.avatarInput) {
      this.avatarInput.value = avatarUrl;
    }

    // Update visual selection
    const allOptions = this.container?.querySelectorAll('.avatar-option');
    if (allOptions) {
      allOptions.forEach((el) => {
        el.classList.remove('selected');
        const optionUrl = el.dataset.avatarUrl || '';
        if (optionUrl === avatarUrl) {
          el.classList.add('selected');
        }
      });
    }

    // If no match found and URL is empty, select initials
    if (!avatarUrl || avatarUrl.trim() === '') {
      const initialsOption = this.container?.querySelector(
        '[data-avatar-id="initials"]',
      );
      if (initialsOption) {
        initialsOption.classList.add('selected');
      }
    }
  }
}

// Initialize avatar picker
// eslint-disable-next-line no-new
new AvatarPicker();
