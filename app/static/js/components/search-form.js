/**
 * Simple search form - auto-submit on select changes
 */

// Auto-submit form when select values change
const form = document.querySelector('form');
if (form) {
  form.querySelectorAll('select').forEach(select => {
    select.addEventListener('change', () => form.submit());
  });
}
