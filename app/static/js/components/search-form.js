/**
 * Search form functionality for restaurant search
 */

document.addEventListener('DOMContentLoaded', () => {
  // Auto-submit form when sort, order, or per_page changes
  const form = document.querySelector('form');
  if (!form) return;

  const selects = form.querySelectorAll('select');
  selects.forEach((select) => {
    select.addEventListener('change', () => {
      form.submit();
    });
  });
});
