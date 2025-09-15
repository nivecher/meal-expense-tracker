/**
 * Expense Detail Page Functionality
 * Handles delete modal and tooltips
 */


export function initExpenseDetail() {
    // Initialize Bootstrap tooltips
    if (typeof bootstrap !== 'undefined') {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        const tooltipList = tooltipTriggerList.map((tooltipTriggerEl) => {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }

    // Handle delete expense modal
    const deleteModal = document.getElementById("deleteExpenseModal");
    if (deleteModal) {
        deleteModal.addEventListener("show.bs.modal", function (event) {
            const button = event.relatedTarget;
            const expenseId = button.getAttribute("data-expense-id");
            const expenseDescription = button.getAttribute("data-expense-description");
            const expenseAmount = button.getAttribute("data-expense-amount");
            const expenseDate = button.getAttribute("data-expense-date");

            // Update modal content
            const detailsDiv = deleteModal.querySelector("#delete-expense-details");
            if (detailsDiv) {
                detailsDiv.innerHTML = `
                    <div class="alert alert-light">
                        <strong>Restaurant:</strong> ${expenseDescription}<br>
                        <strong>Amount:</strong> $${expenseAmount}<br>
                        <strong>Date:</strong> ${expenseDate}
                    </div>
                `;
            }

            // Update form action
            const form = deleteModal.querySelector("#delete-expense-form");
            if (form) {
                form.action = `/expenses/${expenseId}/delete`;
            }
        });
    }

}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', initExpenseDetail);
