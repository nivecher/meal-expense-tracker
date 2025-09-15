/**
 * Restaurant List Component
 * Handles view toggling, pagination, table sorting, and delete functionality
 */

import { handleFaviconError } from '../utils/favicon-handler.js';

// Global favicon error handler for backward compatibility
window.handleFaviconError = handleFaviconError;

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
    const savedView = localStorage.getItem("restaurantViewPreference") || "card";

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
            localStorage.setItem("restaurantViewPreference", "card");
        }
    });

    tableView.addEventListener("change", function () {
        if (this.checked) {
            cardViewContainer.classList.add("d-none");
            tableViewContainer.classList.remove("d-none");
            localStorage.setItem("restaurantViewPreference", "table");
        }
    });
}

// Delete restaurant functionality
function init_delete_restaurant() {
    const deleteModal = document.getElementById("deleteRestaurantModal");
    if (!deleteModal) return;

    // Set up the modal to show the restaurant name
    deleteModal.addEventListener("show.bs.modal", function (event) {
        const button = event.relatedTarget;
        const restaurantId = button.getAttribute("data-restaurant-id");
        const restaurantName = button.getAttribute("data-restaurant-name");

        // Update the modal content
        const modalTitle = deleteModal.querySelector(".modal-title");
        const modalBody = deleteModal.querySelector("#restaurantName");
        const deleteForm = document.getElementById("deleteRestaurantForm");

        modalBody.textContent = restaurantName;
        deleteForm.action = `${deleteForm.dataset.deleteUrl}/${restaurantId}`;
    });

    // Handle form submission with fetch
    const deleteForm = document.getElementById("deleteRestaurantForm");
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
                    showToast("Error", "An error occurred while deleting the restaurant.", "danger");
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

// Table sorting functionality
function init_table_sorting() {
    const headers = document.querySelectorAll('.restaurant-table th[data-sort="true"]');
    headers.forEach((header) => {
        if (header) {
            header.style.cursor = "pointer";
            header.addEventListener("click", function () {
                sortRestaurantTable(this);
            });
        }
    });
}

function sortRestaurantTable(header) {
    if (!header) return;

    const table = header.closest("table");
    if (!table) return;

    const tbody = table.querySelector("tbody");
    if (!tbody) return;

    const rows = Array.from(tbody.querySelectorAll("tr"));
    const columnIndex = Array.from(header.parentNode.children).indexOf(header);
    const sortType = header.getAttribute("data-sort-type");
    const isAscending = header.classList.contains("sort-asc");

    // Remove existing sort classes
    const headers = document.querySelectorAll('.restaurant-table th[data-sort="true"]');
    headers.forEach((h) => {
        if (h && h.classList) {
            h.classList.remove("sort-asc", "sort-desc");
        }
    });

    // Add sort class to current header
    if (header.classList) {
        header.classList.add(isAscending ? "sort-desc" : "sort-asc");
    }

    rows.sort((a, b) => {
        const aValue = getRestaurantCellValue(a.cells[columnIndex], sortType);
        const bValue = getRestaurantCellValue(b.cells[columnIndex], sortType);

        if (sortType === "currency" || sortType === "number") {
            return isAscending ? bValue - aValue : aValue - bValue;
        } else if (sortType === "date") {
            return isAscending ? new Date(bValue) - new Date(aValue) : new Date(aValue) - new Date(bValue);
        } else {
            return isAscending ? bValue.localeCompare(aValue) : aValue.localeCompare(bValue);
        }
    });

    // Reorder rows
    rows.forEach((row) => tbody.appendChild(row));
}

function getRestaurantCellValue(cell, sortType) {
    if (!cell) return "";

    if (sortType === "currency") {
        const text = cell.textContent ? cell.textContent.trim() : "";
        return parseFloat(text.replace(/[$,]/g, "")) || 0;
    } else if (sortType === "number") {
        const text = cell.textContent ? cell.textContent.trim() : "";
        return parseFloat(text) || 0;
    } else if (sortType === "date") {
        // Look for data-sort-value attribute first (for last visit column)
        const spanWithSortValue = cell.querySelector("[data-sort-value]");
        if (spanWithSortValue) {
            const sortValue = spanWithSortValue.getAttribute("data-sort-value");
            return sortValue || ""; // Return empty string for "No visits"
        }
        // Fallback to text content for other date columns
        const link = cell.querySelector("a");
        return link ? (link.textContent ? link.textContent.trim() : "") : (cell.textContent ? cell.textContent.trim() : "");
    } else {
        return cell.textContent ? cell.textContent.trim().toLowerCase() : "";
    }
}

// Pagination functionality
function init_pagination() {
    const perPageSelector = document.getElementById("per_page");
    if (perPageSelector) {
        perPageSelector.addEventListener("change", function() {
            if (!this || !this.value) return;

            const newPerPage = this.value;

            // Save page size preference to cookie
            setCookie("restaurant_page_size", newPerPage);

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

// Favicon loading functionality
function init_favicon_loading() {
    const faviconImages = document.querySelectorAll('.restaurant-favicon, .restaurant-favicon-table');
    faviconImages.forEach(img => {
        if (!img) return;

        // Add a more robust error handler
        img.addEventListener('error', function() {
            if (!this) return;

            // Use the centralized favicon error handler
            handleFaviconError(this);
        });

        // Add load handler for smooth transition
        img.addEventListener('load', function() {
            if (this) {
                this.style.opacity = '1';
            }
        });
    });
}

// Initialize tooltips
function init_tooltips() {
    if (typeof bootstrap !== 'undefined') {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }
}

// Main initialization function
export function init() {
    init_view_toggle();
    init_delete_restaurant();
    init_table_sorting();
    init_pagination();
    init_favicon_loading();
    init_tooltips();
}

// Auto-initialize when DOM is ready
document.addEventListener("DOMContentLoaded", init);
