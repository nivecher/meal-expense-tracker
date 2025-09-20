/**
 * Expense Table Sorting - Uses Unified Table Sorting System
 * Clean separation of concerns - no embedded JavaScript in HTML
 */

// Define all functions first
function getExpenseCellValue(row, columnIndex) {
  const cell = row.cells[columnIndex];
  if (!cell) return '';

  const { sortValue } = cell.dataset;
  if (sortValue !== null) {
    if (columnIndex === 0) { // Date column
      return new Date(sortValue);
    } else if (columnIndex === 6 || columnIndex === 7) { // Currency columns
      return parseFloat(sortValue) || 0;
    } else if (columnIndex === 5) { // Party size column
      return parseInt(sortValue, 10) || 0;
    }
    return sortValue;
  }

  return cell.textContent.trim();
}

function getRestaurantCellValue(row, columnIndex) {
  const cell = row.cells[columnIndex];
  if (!cell) return '';

  const { sortValue } = cell.dataset;
  if (sortValue !== null) {
    if (columnIndex === 1) { // Rating column
      return parseFloat(sortValue) || 0;
    } else if (columnIndex === 2) { // Price level column
      return parseInt(sortValue, 10) || 0;
    }
    return sortValue;
  }

  return cell.textContent.trim();
}

function compareValues(a, b) {
  if (a === b) return 0;
  if (a < b) return -1;
  return 1;
}

function sortExpenseTable(columnIndex, ascending) {
  const table = document.getElementById('expenseTable');
  const tbody = table.querySelector('tbody');
  const rows = Array.from(tbody.querySelectorAll('tr'));

  rows.sort((a, b) => {
    const aValue = getExpenseCellValue(a, columnIndex);
    const bValue = getExpenseCellValue(b, columnIndex);

    // Multi-level sort for restaurant column
    if (columnIndex === 1) { // Restaurant column
      const aRestaurant = aValue.toLowerCase();
      const bRestaurant = bValue.toLowerCase();
      if (aRestaurant !== bRestaurant) {
        return ascending ? compareValues(aRestaurant, bRestaurant) : compareValues(bRestaurant, aRestaurant);
      }
      // If restaurants are the same, sort by date (column 0)
      const aDate = getExpenseCellValue(a, 0);
      const bDate = getExpenseCellValue(b, 0);
      return ascending ? compareValues(aDate, bDate) : compareValues(bDate, aDate);
    }

    return ascending ? compareValues(aValue, bValue) : compareValues(bValue, aValue);
  });

  // Re-append sorted rows
  rows.forEach((row) => tbody.appendChild(row));
}

function sortRestaurantTable(columnIndex, ascending) {
  const table = document.getElementById('restaurantTable');
  const tbody = table.querySelector('tbody');
  const rows = Array.from(tbody.querySelectorAll('tr'));

  rows.sort((a, b) => {
    const aValue = getRestaurantCellValue(a, columnIndex);
    const bValue = getRestaurantCellValue(b, columnIndex);

    // Multi-level sort for name column
    if (columnIndex === 0) { // Name column
      const aName = aValue.toLowerCase();
      const bName = bValue.toLowerCase();
      if (aName !== bName) {
        return ascending ? compareValues(aName, bName) : compareValues(bName, aName);
      }
      // If names are the same, sort by rating (column 1)
      const aRating = getRestaurantCellValue(a, 1);
      const bRating = getRestaurantCellValue(b, 1);
      return ascending ? compareValues(aRating, bRating) : compareValues(bRating, aRating);
    }

    return ascending ? compareValues(aValue, bValue) : compareValues(bValue, aValue);
  });

  // Re-append sorted rows
  rows.forEach((row) => tbody.appendChild(row));
}

function initTableSorting(tableId) {
  const table = document.getElementById(tableId);
  if (!table) return;

  const headers = table.querySelectorAll('th[data-sort="true"]');
  headers.forEach((header, index) => {
    header.style.cursor = 'pointer';
    header.addEventListener('click', () => {
      const isAscending = header.classList.contains('sort-asc');

      // Remove sort classes and arrows from all headers
      headers.forEach((h) => {
        h.classList.remove('sort-asc', 'sort-desc');
        // Remove any existing arrows - more comprehensive regex
        h.innerHTML = h.innerHTML.replace(/<span[^>]*>[↑↓]<\/span>/g, '');
      });

      // Add appropriate sort class and arrow to clicked header
      const newSortDirection = !isAscending;
      header.classList.add(newSortDirection ? 'sort-asc' : 'sort-desc');

      // Add simple text arrow with blue color
      const arrow = newSortDirection ? '↑' : '↓';
      header.innerHTML = `${header.innerHTML}<span style="color: #007bff; font-weight: bold; margin-left: 5px;">${arrow}</span>`;

      // Sort the table based on table type
      if (tableId === 'expenseTable') {
        sortExpenseTable(index, newSortDirection);
      } else if (tableId === 'restaurantTable') {
        sortRestaurantTable(index, newSortDirection);
      }
    });
  });
}

function initExpenseTableSorting() {
  // Initialize table sorting for both expense and restaurant tables
  initTableSorting('expenseTable');
  initTableSorting('restaurantTable');

  // Initialize other expense-specific functionality
  if (typeof initExpenseList === 'function') {
    initExpenseList();
  }
}

// Initialize immediately if DOM is already loaded, otherwise wait for DOMContentLoaded
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    initExpenseTableSorting();
  });
} else {
  // DOM is already loaded
  initExpenseTableSorting();
}
