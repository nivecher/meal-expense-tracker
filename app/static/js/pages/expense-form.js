/**
 * Initialize the expense form page
 */
function init() {
  const elements = cache_form_elements();
  if (!elements.form) return;

  setup_expense_form_handlers(elements);
}

function cache_form_elements() {
  return {
    form: document.getElementById('expenseForm'),
    categorySelect: document.getElementById('category_id'),
    restaurantSelect: document.getElementById('restaurant_id'),
  };
}

function setup_expense_form_handlers(elements) {
  const { form, categorySelect, restaurantSelect } = elements;

  // Track if category was manually changed
  let categoryManuallyChanged = false;

  // Function to update category based on restaurant type
  function updateCategory(restaurantId) {
    if (categoryManuallyChanged || !categorySelect) return;
    if (!restaurantId) return;

    // Reset to default selection
    categorySelect.value = '';
  }

  // Handle restaurant change
  if (restaurantSelect) {
    restaurantSelect.addEventListener('change', function() {
      updateCategory(this.value);
    });
  }

  // Track manual category changes
  if (categorySelect) {
    categorySelect.addEventListener('change', function() {
      categoryManuallyChanged = this.value !== '';
    });
  }

  // Handle form submission
  form.addEventListener('submit', (e) => {
    if (!form.checkValidity()) {
      e.preventDefault();
      e.stopPropagation();
    }
    form.classList.add('was-validated');
  }, false);
}

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}

// Export for testing and explicit initialization
export { init };
