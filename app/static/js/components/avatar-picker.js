/**
 * Avatar Picker Component
 * Simple avatar selection from a curated list of free avatars
 * Follows TIGER Style principles: Safety, Performance, Developer Experience
 */

class AvatarPicker {
  constructor() {
    this.selectedAvatar = null;
    this.avatarList = [
      // Diverse, professional, free avatars from various sources
      {
        id: 'avatar-1',
        url: 'https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=150&h=150&fit=crop&crop=face',
        alt: 'Professional avatar 1',
        category: 'professional',
      },
      {
        id: 'avatar-2',
        url: 'https://images.unsplash.com/photo-1494790108755-2616b2e69b14?w=150&h=150&fit=crop&crop=face',
        alt: 'Professional avatar 2',
        category: 'professional',
      },
      {
        id: 'avatar-3',
        url: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=150&h=150&fit=crop&crop=face',
        alt: 'Professional avatar 3',
        category: 'professional',
      },
      {
        id: 'avatar-4',
        url: 'https://images.unsplash.com/photo-1438761681033-6461ffad8d80?w=150&h=150&fit=crop&crop=face',
        alt: 'Professional avatar 4',
        category: 'professional',
      },
      {
        id: 'avatar-5',
        url: 'https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=150&h=150&fit=crop&crop=face',
        alt: 'Professional avatar 5',
        category: 'professional',
      },
      {
        id: 'avatar-6',
        url: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150&h=150&fit=crop&crop=face',
        alt: 'Professional avatar 6',
        category: 'professional',
      },
      // Abstract/geometric avatars as backup
      {
        id: 'avatar-geometric-1',
        url: 'https://api.dicebear.com/7.x/shapes/svg?seed=1&backgroundColor=667eea',
        alt: 'Geometric avatar 1',
        category: 'geometric',
      },
      {
        id: 'avatar-geometric-2',
        url: 'https://api.dicebear.com/7.x/shapes/svg?seed=2&backgroundColor=764ba2',
        alt: 'Geometric avatar 2',
        category: 'geometric',
      },
      {
        id: 'avatar-geometric-3',
        url: 'https://api.dicebear.com/7.x/shapes/svg?seed=3&backgroundColor=f093fb',
        alt: 'Geometric avatar 3',
        category: 'geometric',
      },
      {
        id: 'avatar-geometric-4',
        url: 'https://api.dicebear.com/7.x/shapes/svg?seed=4&backgroundColor=4facfe',
        alt: 'Geometric avatar 4',
        category: 'geometric',
      },
      {
        id: 'avatar-initials',
        url: 'initials',
        alt: 'Use your initials',
        category: 'initials',
      },
    ];

    this.init();
  }

  init() {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', () => this.setupPicker());
    } else {
      this.setupPicker();
    }
  }

  setupPicker() {
    const pickerContainer = document.getElementById('avatar-picker-container');
    const avatarInput = document.getElementById('avatar-url-input');

    if (!pickerContainer) return;

    this.renderAvatarGrid(pickerContainer);
    this.setupEventListeners(avatarInput);
  }

  renderAvatarGrid(container) {
    const gridHTML = `
      <div class="avatar-picker-grid">
        ${this.avatarList.map((avatar) => this.createAvatarOption(avatar)).join('')}
      </div>
    `;

    container.innerHTML = gridHTML;
  }

  createAvatarOption(avatar) {
    const isInitials = avatar.url === 'initials';
    const imageHTML = isInitials
      ? `<div class="avatar-option-initials">${this.getUserInitials()}</div>`
      : `<img src="${avatar.url}" alt="${avatar.alt}" loading="lazy" />`;

    return `
      <div
        class="avatar-option ${isInitials ? 'avatar-option-initials-container' : ''}"
        data-avatar-id="${avatar.id}"
        data-avatar-url="${avatar.url}"
        data-category="${avatar.category}"
        title="${avatar.alt}"
      >
        ${imageHTML}
        <div class="avatar-option-overlay">
          <i class="fas fa-check"></i>
        </div>
      </div>
    `;
  }

  getUserInitials() {
    // Try to get initials from form fields or fall back to current user data
    const firstName = document.getElementById('first_name')?.value || '';
    const lastName = document.getElementById('last_name')?.value || '';
    const displayName = document.getElementById('display_name')?.value || '';
    const username = document.querySelector('[data-username]')?.dataset.username || '';

    if (firstName && lastName) {
      return (firstName[0] + lastName[0]).toUpperCase();
    } else if (displayName) {
      const parts = displayName.split(' ');
      if (parts.length >= 2) {
        return (parts[0][0] + parts[1][0]).toUpperCase();
      }
      return displayName.slice(0, 2).toUpperCase();
    } else if (username) {
      return username.slice(0, 2).toUpperCase();
    }

    return 'U';
  }

  setupEventListeners(avatarInput) {
    const container = document.getElementById('avatar-picker-container');

    if (!container) return;

    // Handle avatar selection
    container.addEventListener('click', (e) => {
      const option = e.target.closest('.avatar-option');
      if (!option) return;

      this.selectAvatar(option, avatarInput);
    });

    // Update initials when name fields change
    ['first_name', 'last_name', 'display_name'].forEach((fieldId) => {
      const field = document.getElementById(fieldId);
      if (field) {
        field.addEventListener('input', () => {
          this.updateInitialsDisplay();
        });
      }
    });
  }

  selectAvatar(option, avatarInput) {
    // Remove previous selection
    document.querySelectorAll('.avatar-option.selected').forEach((el) => {
      el.classList.remove('selected');
    });

    // Mark new selection
    option.classList.add('selected');

    const { avatarUrl } = option.dataset;
    const { avatarId } = option.dataset;

    this.selectedAvatar = {
      id: avatarId,
      url: avatarUrl,
      category: option.dataset.category,
    };

    // Update hidden input for form submission
    if (avatarInput) {
      avatarInput.value = avatarUrl === 'initials' ? '' : avatarUrl;
    }

    // Update preview avatar
    this.updatePreviewAvatar(avatarUrl);

    // Show feedback
    this.showSelectionFeedback(option);
  }

  updatePreviewAvatar(avatarUrl) {
    const previewAvatar = document.querySelector('.profile-avatar');
    if (!previewAvatar) return;

    if (avatarUrl === 'initials' || !avatarUrl) {
      // Let the modern avatar system handle initials
      previewAvatar.src = '';
      // Trigger avatar refresh
      if (window.modernAvatarManager) {
        window.modernAvatarManager.refreshAllAvatars();
      }
    } else {
      previewAvatar.src = avatarUrl;
    }
  }

  updateInitialsDisplay() {
    const initialsOption = document.querySelector('.avatar-option-initials');
    if (initialsOption) {
      initialsOption.textContent = this.getUserInitials();
    }
  }

  showSelectionFeedback(option) {
    // Add a brief highlight animation
    option.style.transform = 'scale(0.95)';
    setTimeout(() => {
      option.style.transform = '';
    }, 150);

    // Update the picker header text
    const pickerHeader = document.querySelector('.avatar-picker-header');
    if (pickerHeader) {
      const { category } = option.dataset;
      const feedbackText = {
        professional: 'Professional avatar selected!',
        geometric: 'Geometric design selected!',
        initials: 'Using your initials!',
      };

      pickerHeader.textContent = feedbackText[category] || 'Avatar selected!';
      pickerHeader.style.color = '#10b981';

      setTimeout(() => {
        pickerHeader.textContent = 'Choose your avatar:';
        pickerHeader.style.color = '';
      }, 2000);
    }
  }

  // Public method to get current selection
  getSelectedAvatar() {
    return this.selectedAvatar;
  }

  // Public method to set selection programmatically
  setSelectedAvatar(avatarUrl) {
    const option = document.querySelector(`[data-avatar-url="${avatarUrl}"]`);
    if (option) {
      const avatarInput = document.getElementById('avatar-url-input');
      this.selectAvatar(option, avatarInput);
    }
  }
}

// Initialize the avatar picker
const avatarPicker = new AvatarPicker();

// Export for potential use in other modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = AvatarPicker;
} else if (typeof window !== 'undefined') {
  window.AvatarPicker = AvatarPicker;
  window.avatarPicker = avatarPicker;
}
