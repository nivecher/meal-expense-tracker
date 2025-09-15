/**
 * Expense List Page
 * Handles view toggling, pagination, table sorting, delete functionality, and favicon loading
 */

import { handleFaviconError } from '../utils/favicon-handler.js';

// Make handleFaviconError globally available for inline onerror handlers
window.handleFaviconError = handleFaviconError;

// Initialize Bootstrap tooltips
function init_tooltips() {
    if (typeof bootstrap !== 'undefined') {
        // Handle standard tooltip triggers
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        const tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });

        // Handle custom tooltip triggers (for elements that also have other data-bs-toggle attributes)
        const customTooltipTriggerList = [].slice.call(document.querySelectorAll('[data-tooltip="true"]'));
        const customTooltipList = customTooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }
}

// View toggle functionality
function init_view_toggle() {
    const cardView = document.getElementById("card-view");
    const tableView = document.getElementById("table-view");
    const cardViewContainer = document.getElementById("card-view-container");
    const tableViewContainer = document.getElementById("table-view-container");

    if (!cardView || !tableView || !cardViewContainer || !tableViewContainer) {
        return;
    }

    // Load saved view preference or default to card view
    const savedView = localStorage.getItem("expenseViewPreference") || "card";

    if (savedView === "table") {
        tableView.checked = true;
        cardViewContainer.classList.add("d-none");
        tableViewContainer.classList.remove("d-none");
    }

    // Add event listeners for view toggle
    cardView.addEventListener("change", function () {
        if (this.checked) {
            cardViewContainer.classList.remove("d-none");
            tableViewContainer.classList.add("d-none");
            localStorage.setItem("expenseViewPreference", "card");
        }
    });

    tableView.addEventListener("change", function () {
        if (this.checked) {
            cardViewContainer.classList.add("d-none");
            tableViewContainer.classList.remove("d-none");
            localStorage.setItem("expenseViewPreference", "table");
        }
    });
}

// Delete expense modal functionality
function init_delete_expense() {
    const deleteModal = document.getElementById("deleteExpenseModal");
    if (!deleteModal) return;

    // Set up the modal to show the expense details
    deleteModal.addEventListener("show.bs.modal", function (event) {
        const button = event.relatedTarget;
        const expenseId = button.getAttribute("data-expense-id");
        const description = button.getAttribute("data-expense-description");
        const amount = button.getAttribute("data-expense-amount");
        const date = button.getAttribute("data-expense-date");

        // Update the modal content
        const modalTitle = deleteModal.querySelector(".modal-title");
        const deleteDetails = document.getElementById("delete-expense-details");
        const deleteForm = document.getElementById("delete-expense-form");

        if (deleteDetails) {
            deleteDetails.innerHTML = `
                <strong>Description:</strong> ${description}<br>
                <strong>Amount:</strong> $${amount}<br>
                <strong>Date:</strong> ${date}
            `;
        }
        if (deleteForm) {
            deleteForm.action = `/expenses/${expenseId}/delete`;
        }
    });

    // Handle form submission with fetch
    const deleteForm = document.getElementById("delete-expense-form");
    if (deleteForm) {
        deleteForm.addEventListener("submit", function (e) {
            e.preventDefault();

            const formData = new FormData(deleteForm);
            const url = deleteForm.action;

            fetch(url, {
                method: "POST",
                body: formData,
                headers: {
                    "X-CSRFToken": formData.get("csrf_token"),
                },
            })
                .then((response) => {
                    if (response.redirected) {
                        window.location.href = response.url;
                    } else {
                        return response.json().then((data) => {
                            if (data.error) {
                                showToast("Error", data.error, "danger");
                            } else {
                                window.location.reload();
                            }
                        });
                    }
                })
                .catch((error) => {
                    console.error("Error:", error);
                    showToast("Error", "An error occurred while deleting the expense.", "danger");
                });
        });
    }
}

// Toast notification functionality
function showToast(title, message, type = "info") {
    const toastContainer = document.getElementById("toastContainer") || createToastContainer();
    const toastId = "toast-" + Date.now();
    const toastHtml = `
        <div id="${toastId}" class="toast align-items-center text-white bg-${type} border-0" role="alert" aria-live="assertive" aria-atomic="true">
            <div class="d-flex">
                <div class="toast-body">
                    <strong>${title}</strong><br>${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        </div>
    `;

    toastContainer.insertAdjacentHTML("beforeend", toastHtml);
    const toastElement = document.getElementById(toastId);
    const toast = new bootstrap.Toast(toastElement);
    toast.show();

    // Remove the toast after it's hidden
    toastElement.addEventListener("hidden.bs.toast", function () {
        toastElement.remove();
    });
}

function createToastContainer() {
    const container = document.createElement("div");
    container.id = "toastContainer";
    container.className = "toast-container position-fixed bottom-0 end-0 p-3";
    container.style.zIndex = "1100";
    document.body.appendChild(container);
    return container;
}

// Favicon loading is now handled by the imported handleFaviconError function

// Pagination functionality
function init_pagination() {
    const perPageSelector = document.getElementById("per_page");
    if (perPageSelector) {
        perPageSelector.addEventListener("change", function() {
            if (!this || !this.value) return;

            const newPerPage = this.value;

            // Save page size preference to cookie
            setCookie("expense_page_size", newPerPage);

            const currentUrl = new URL(window.location);

            // Update per_page parameter
            currentUrl.searchParams.set("per_page", newPerPage);

            // Reset to page 1 when changing per_page
            currentUrl.searchParams.set("page", "1");

            // Navigate to the new URL
            window.location.href = currentUrl.toString();
        });
    }
}

// Cookie utility functions
function setCookie(name, value, days = 365) {
    const expires = new Date();
    expires.setTime(expires.getTime() + (days * 24 * 60 * 60 * 1000));
    document.cookie = `${name}=${value};expires=${expires.toUTCString()};path=/;SameSite=Lax`;
}

// Table sorting functionality
function init_table_sorting() {
    const table = document.querySelector('.expense-table');
    if (!table) return;

    const headers = table.querySelectorAll('th[data-sort="true"]');

    headers.forEach((header, index) => {
        header.style.cursor = 'pointer';
        header.addEventListener('click', () => {
            sortExpenseTable(header, index);
        });
    });
}

function sortExpenseTable(header, columnIndex) {
    const table = header.closest('table');
    if (!table) return;

    const tbody = table.querySelector('tbody');
    if (!tbody) return;

    const rows = Array.from(tbody.querySelectorAll('tr'));
    const sortType = header.getAttribute('data-sort-type');
    const isAscending = header.classList.contains('sort-asc');

    // Remove existing sort classes
    const headers = document.querySelectorAll('.expense-table th[data-sort="true"]');
    headers.forEach((h) => {
        if (h && h.classList) {
            h.classList.remove('sort-asc', 'sort-desc');
        }
    });

    // Add sort class to current header
    if (header.classList) {
        header.classList.add(isAscending ? 'sort-desc' : 'sort-asc');
    }

    rows.sort((a, b) => {
        const aValue = getExpenseCellValue(a.cells[columnIndex], sortType);
        const bValue = getExpenseCellValue(b.cells[columnIndex], sortType);

        if (sortType === 'currency' || sortType === 'number') {
            return isAscending ? bValue - aValue : aValue - bValue;
        } else if (sortType === 'date') {
            return isAscending ? new Date(bValue) - new Date(aValue) : new Date(aValue) - new Date(bValue);
        } else {
            return isAscending ? bValue.localeCompare(aValue) : aValue.localeCompare(bValue);
        }
    });

    // Reorder rows
    rows.forEach((row) => tbody.appendChild(row));
}

function getExpenseCellValue(cell, sortType) {
    if (!cell) return '';

    if (sortType === 'currency' || sortType === 'number') {
        // Extract numeric value from currency or number cells
        const text = cell.textContent.trim();
        const match = text.match(/[\d,]+\.?\d*/);
        return match ? parseFloat(match[0].replace(/,/g, '')) : 0;
    } else if (sortType === 'date') {
        // Extract date from link text or cell content
        const link = cell.querySelector('a');
        const dateText = link ? link.textContent.trim() : cell.textContent.trim();
        return new Date(dateText);
    } else {
        // Text comparison - get the main text content
        const link = cell.querySelector('a');
        const badge = cell.querySelector('.badge, .tag-badge');
        if (link) {
            return link.textContent.trim();
        } else if (badge) {
            return badge.textContent.trim();
        } else {
            return cell.textContent.trim();
        }
    }
}

// Main initialization function
export function init() {
    init_tooltips();
    init_view_toggle();
    init_delete_expense();
    init_pagination();
    init_table_sorting();
}

// Auto-initialize when DOM is ready
document.addEventListener("DOMContentLoaded", init);
