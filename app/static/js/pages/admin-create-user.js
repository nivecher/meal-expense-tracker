/**
 * Admin Create User Page
 * 
 * Handles form validation and confirmation for user creation functionality.
 * This replaces the inline JavaScript in the admin/create_user.html template.
 */

document.addEventListener('DOMContentLoaded', () => {
  // Form validation
  const form = document.querySelector('form');
  const usernameInput = document.getElementById('username');
  const emailInput = document.getElementById('email');

  // Username validation
  usernameInput.addEventListener('input', function() {
    const username = this.value.trim();
    if (username.length > 0 && username.length < 3) {
      this.setCustomValidity('Username must be at least 3 characters long');
    } else {
      this.setCustomValidity('');
    }
  });

  // Email validation
  emailInput.addEventListener('input', function() {
    const email = this.value.trim();
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (email.length > 0 && !emailRegex.test(email)) {
      this.setCustomValidity('Please enter a valid email address');
    } else {
      this.setCustomValidity('');
    }
  });

  // Form submission confirmation
  form.addEventListener('submit', (e) => {
    const isAdmin = document.getElementById('is_admin').checked;
    const sendEmail = document.getElementById('send_password_email').checked;

    let message = 'Are you sure you want to create this user?';
    if (isAdmin) {
      message += '\n\nThis user will have admin privileges.';
    }
    if (sendEmail) {
      message += '\n\nA password will be sent to their email address.';
    }

    if (!confirm(message)) {
      e.preventDefault();
    }
  });
});
