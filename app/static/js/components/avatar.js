// Handle avatar image loading and error states
class AvatarManager {
  constructor() {
    this.avatars = [];
    this.defaultAvatar = '/static/img/default-avatar.png';
    this.init();
  }

  init() {
    document.addEventListener('DOMContentLoaded', () => this.setupAvatars());
  }

  setupAvatars() {
    this.avatars = Array.from(document.querySelectorAll('[data-avatar]'));

    this.avatars.forEach((avatar) => {
      // Add loading class
      avatar.classList.add('avatar-loading');

      // Set up loading handler
      avatar.addEventListener('load', (e) => this.handleLoad(e.target));

      // Set up error handler
      avatar.addEventListener('error', (e) => this.handleError(e.target));

      // If image is already loaded (from cache)
      if (avatar.complete) {
        this.handleLoad(avatar);
      }
    });
  }

  handleLoad(img) {
    img.classList.remove('avatar-loading');
    img.classList.add('avatar-loaded');

    // Add a slight delay to ensure the loaded class is applied
    setTimeout(() => {
      img.style.opacity = '1';
    }, 10);
  }

  handleError(img) {
    const defaultSrc = img.dataset.defaultSrc || this.defaultAvatar;

    // Only try to recover once to prevent loops
    if (img.src !== defaultSrc) {
      img.src = defaultSrc;
    } else {
      // If default image also fails, show a placeholder
      img.alt = 'User Avatar';
      img.classList.add('avatar-error');
      img.classList.remove('avatar-loading');
    }
  }
}

// Initialize the avatar manager
new AvatarManager();
