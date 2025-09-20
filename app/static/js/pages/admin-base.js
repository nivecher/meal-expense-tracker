/**
 * Admin Base Page
 *
 * Handles admin-specific functionality like confirmation dialogs for dangerous actions.
 * This replaces the inline JavaScript in the admin/base.html template.
 */

document.addEventListener('DOMContentLoaded', () => {
  // Confirm dangerous actions
  document.querySelectorAll('[data-confirm]').forEach((element) => {
    element.addEventListener('click', function(e) {
      const message = this.getAttribute('data-confirm');
      if (!confirm(message)) {
        e.preventDefault();
      }
    });
  });

  // Alert dismissal is handled by main.js
});
