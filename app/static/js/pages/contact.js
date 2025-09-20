/**
 * Contact Page
 *
 * Handles contact form validation functionality.
 * This replaces the inline JavaScript in the main/contact.html template.
 */

document.addEventListener('DOMContentLoaded', () => {
  // Initialize form validation
  const form = document.getElementById('contactForm');
  if (form) {
    form.addEventListener(
      'submit',
      (event) => {
        if (!form.checkValidity()) {
          event.preventDefault();
          event.stopPropagation();
        }
        form.classList.add('was-validated');
      },
      false,
    );
  }
});
