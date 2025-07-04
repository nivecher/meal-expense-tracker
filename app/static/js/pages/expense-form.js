// Initialize the expense form
document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('expenseForm');
    if (!form) return;

    // Track if category was manually changed
    let categoryManuallyChanged = false;
    const categorySelect = document.getElementById('category_id');
    const restaurantSelect = document.getElementById('restaurant_id');

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
    form.addEventListener('submit', function(e) {
        if (!form.checkValidity()) {
            e.preventDefault();
            e.stopPropagation();
        }
        form.classList.add('was-validated');
    }, false);
});
