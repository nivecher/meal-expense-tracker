/**
 * Expense Form Handling
 * Handles form validation, dynamic fields, and other interactive elements
 * for the expense add/edit form.
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize date picker if it exists
    const dateInput = document.getElementById('date');
    if (dateInput) {
        // Initialize flatpickr if available
        if (typeof flatpickr !== 'undefined') {
            flatpickr(dateInput, {
                dateFormat: 'Y-m-d',
                allowInput: true,
                defaultDate: dateInput.value || 'today'
            });
        }
    }

    // Handle form submission
    const form = document.getElementById('expenseForm');
    if (form) {
        form.addEventListener('submit', function(e) {
            // Add any client-side validation here
            const amount = document.getElementById('amount');
            if (amount && isNaN(parseFloat(amount.value))) {
                e.preventDefault();
                alert('Please enter a valid amount');
                amount.focus();
                return false;
            }
            return true;
        });
    }
});
