/**
 * Expense Table Sorting - Uses Unified Table Sorting System
 * Clean separation of concerns - no embedded JavaScript in HTML
 */

// Initialize immediately if DOM is already loaded, otherwise wait for DOMContentLoaded
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    initExpenseTableSorting();
  });
} else {
  // DOM is already loaded
  initExpenseTableSorting();
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

function sortExpenseTable(columnIndex, ascending) {
  const table = document.getElementById('expenseTable');
  const tbody = table.querySelector('tbody');
  const rows = Array.from(tbody.querySelectorAll('tr'));

  rows.sort((a, b) => {
    const aValue = getExpenseCellValue(a, columnIndex);
    const bValue = getExpenseCellValue(b, columnIndex);

    // Multi-level sort for restaurant column
    if (columnIndex === 1) {
      const aRestaurant = aValue.toLowerCase();
      const bRestaurant = bValue.toLowerCase();
      if (aRestaurant === bRestaurant) {
        // Secondary sort by date
        const aDate = getExpenseCellValue(a, 0);
        const bDate = getExpenseCellValue(b, 0);
        return ascending ? aDate - bDate : bDate - aDate;
      }
      return ascending ? aRestaurant.localeCompare(bRestaurant) : bRestaurant.localeCompare(aRestaurant);
    }

    return compareValues(aValue, bValue, ascending);
  });

  // Re-append sorted rows
  rows.forEach((row) => tbody.appendChild(row));
}

function getExpenseCellValue(row, columnIndex) {
  const cell = row.children[columnIndex];
  const sortValue = cell.getAttribute('data-sort-value');

  if (sortValue !== null) {
    if (columnIndex === 0) { // Date column
      return new Date(sortValue);
    } else if (columnIndex === 6 || columnIndex === 7) { // Currency columns
      return parseFloat(sortValue) || 0;
    } else if (columnIndex === 5) { // Party size column
      return parseInt(sortValue) || 0;
    }
    return sortValue;
  }

  return cell.textContent.trim();
}

function sortRestaurantTable(columnIndex, ascending) {
  const table = document.getElementById('restaurantTable');
  const tbody = table.querySelector('tbody');
  const rows = Array.from(tbody.querySelectorAll('tr'));

  rows.sort((a, b) => {
    const aValue = getRestaurantCellValue(a, columnIndex);
    const bValue = getRestaurantCellValue(b, columnIndex);

    // Multi-level sort for restaurant name column
    if (columnIndex === 1) {
      const aRestaurant = aValue.toLowerCase();
      const bRestaurant = bValue.toLowerCase();
      if (aRestaurant === bRestaurant) {
        // Secondary sort by cuisine
        const aCuisine = getRestaurantCellValue(a, 2);
        const bCuisine = getRestaurantCellValue(b, 2);
        return ascending ? aCuisine.localeCompare(bCuisine) : bCuisine.localeCompare(aCuisine);
      }
      return ascending ? aRestaurant.localeCompare(bRestaurant) : bRestaurant.localeCompare(aRestaurant);
    }

    return compareValues(aValue, bValue, ascending);
  });

  // Re-append sorted rows
  rows.forEach((row) => tbody.appendChild(row));
}

function getRestaurantCellValue(row, columnIndex) {
  const cell = row.children[columnIndex];
  const sortValue = cell.getAttribute('data-sort-value');

  if (sortValue !== null) {
    if (columnIndex === 3) { // Rating column
      return parseFloat(sortValue) || 0;
    } else if (columnIndex === 4) { // Visit count column
      return parseInt(sortValue, 10) || 0;
    }
    return sortValue;
  }

  return cell.textContent.trim();
}

function compareValues(a, b, ascending) {
  if (a instanceof Date && b instanceof Date) {
    return ascending ? a - b : b - a;
  }

  if (typeof a === 'number' && typeof b === 'number') {
    return ascending ? a - b : b - a;
  }

  const aStr = String(a).toLowerCase();
  const bStr = String(b).toLowerCase();
  return ascending ? aStr.localeCompare(bStr) : bStr.localeCompare(aStr);
}
