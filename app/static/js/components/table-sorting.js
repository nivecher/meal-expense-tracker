/**
 * Expense Table Sorting - Uses Unified Table Sorting System
 * Clean separation of concerns - no embedded JavaScript in HTML
 */

function getCookieValue(name) {
  const cookieString = document.cookie || '';
  const parts = cookieString.split(';').map((c) => c.trim());
  const prefix = `${encodeURIComponent(name)}=`;
  const match = parts.find((p) => p.startsWith(prefix));
  if (!match) return null;
  try {
    return decodeURIComponent(match.slice(prefix.length));
  } catch {}
}

function setCookieValue(name, value, days = 365) {
  const maxAgeSeconds = Math.floor(days * 24 * 60 * 60);
  const encoded = encodeURIComponent(name);
  const encodedValue = encodeURIComponent(value);
  document.cookie = `${encoded}=${encodedValue}; Max-Age=${maxAgeSeconds}; Path=/; SameSite=Lax`;
}

function getStoredJson(storageKey, cookieKey) {
  try {
    const raw = localStorage.getItem(storageKey);
    if (raw) return JSON.parse(raw);
  } catch {}

  try {
    const rawCookie = getCookieValue(cookieKey);
    if (rawCookie) return JSON.parse(rawCookie);
  } catch {}

  return null;
}

function persistJson(storageKey, cookieKey, value) {
  const raw = JSON.stringify(value);
  try {
    localStorage.setItem(storageKey, raw);
  } catch {}
  setCookieValue(cookieKey, raw);
}

// Define all functions first
function getExpenseCellValue(row, columnIndex) {
  const cell = row.cells[columnIndex];
  if (!cell) return '';

  const { sortValue } = cell.dataset;
  if (sortValue !== null && sortValue !== undefined) {
    if (columnIndex === 1) {
      // Date column
      return new Date(sortValue);
    } else if (columnIndex === 6 || columnIndex === 7) {
      // $/person and Amount (currency)
      return parseFloat(sortValue) || 0;
    } else if (columnIndex === 5) {
      // Party size column
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
  if (sortValue !== null && sortValue !== undefined) {
    if (columnIndex === 2) {
      // Location column - handle special location sorting
      if (sortValue === 'No location') {
        return 'ZZZ'; // Put "No location" at the end
      }
      return sortValue.toLowerCase();
    } else if (columnIndex === 4) {
      // Rating column
      return parseFloat(sortValue) || 0;
    } else if (columnIndex === 3) {
      // Price level column
      return parseInt(sortValue, 10) || 0;
    }
    return sortValue;
  }

  return cell.textContent.trim();
}

function getMerchantCellValue(row, columnIndex) {
  const cell = row.cells[columnIndex];
  if (!cell) return '';

  const { sortValue } = cell.dataset;
  if (sortValue !== null && sortValue !== undefined) {
    if (columnIndex === 3) {
      return parseInt(sortValue, 10) || 0;
    }

    if (columnIndex === 2) {
      if (sortValue === 'Uncategorized') {
        return 'zzz';
      }
      return sortValue.toLowerCase();
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

function isDividerRow(row) {
  return row?.dataset?.dividerRow === 'true';
}

function getExpenseRows(tbody) {
  return Array.from(tbody.querySelectorAll('tr')).filter((row) => !isDividerRow(row));
}

function getRestaurantRows(tbody) {
  return Array.from(tbody.querySelectorAll('tr')).filter((row) => !isDividerRow(row));
}

function getMerchantRows(tbody) {
  return Array.from(tbody.querySelectorAll('tr')).filter((row) => !isDividerRow(row));
}

function createMonthDividerRow(monthKey, monthLabel, columnCount) {
  const dividerRow = document.createElement('tr');
  dividerRow.className = 'table-month-divider';
  dividerRow.dataset.dividerRow = 'true';
  dividerRow.dataset.monthKey = monthKey;
  dividerRow.dataset.monthLabel = monthLabel;
  dividerRow.dataset.monthCollapsed = 'false';
  const cell = document.createElement('td');
  cell.colSpan = columnCount;
  const toggleButton = document.createElement('button');
  toggleButton.type = 'button';
  toggleButton.className = 'month-toggle';
  toggleButton.dataset.monthToggle = monthKey;
  toggleButton.setAttribute('aria-expanded', 'true');
  const toggleIcon = document.createElement('i');
  toggleIcon.className = 'fas fa-chevron-down';
  toggleIcon.setAttribute('aria-hidden', 'true');
  toggleButton.appendChild(toggleIcon);
  const label = document.createElement('span');
  label.className = 'text-muted text-uppercase';
  label.textContent = monthLabel || monthKey;
  cell.append(toggleButton, label);
  dividerRow.appendChild(cell);
  return dividerRow;
}

function rebuildExpenseTableBody(tbody, rows, columnCount, groupByMonth = true) {
  tbody.textContent = '';
  if (!groupByMonth) {
    rows.forEach((row) => tbody.appendChild(row));
    return;
  }

  let currentMonthKey = '';
  rows.forEach((row) => {
    const monthKey = row.dataset.expenseMonth || '';
    const monthLabel = row.dataset.expenseMonthLabel || '';
    if (monthKey && monthKey !== currentMonthKey) {
      currentMonthKey = monthKey;
      const dividerRow = createMonthDividerRow(monthKey, monthLabel, columnCount);
      tbody.appendChild(dividerRow);
    }
    tbody.appendChild(row);
  });
}

function createCityDividerRow(cityLabel, columnCount) {
  const dividerRow = document.createElement('tr');
  dividerRow.className = 'table-city-divider';
  dividerRow.dataset.dividerRow = 'true';
  dividerRow.dataset.cityLabel = cityLabel;
  dividerRow.dataset.cityCollapsed = 'false';
  const cell = document.createElement('td');
  cell.colSpan = columnCount;
  const content = document.createElement('div');
  content.className = 'city-divider-content';
  const left = document.createElement('div');
  left.className = 'city-divider-left';
  const toggleButton = document.createElement('button');
  toggleButton.type = 'button';
  toggleButton.className = 'city-toggle';
  toggleButton.dataset.cityToggle = cityLabel;
  toggleButton.setAttribute('aria-expanded', 'true');
  const toggleIcon = document.createElement('i');
  toggleIcon.className = 'fas fa-chevron-down';
  toggleIcon.setAttribute('aria-hidden', 'true');
  toggleButton.appendChild(toggleIcon);
  const label = document.createElement('span');
  label.className = 'city-divider-label text-muted text-uppercase';
  label.textContent = cityLabel;
  left.append(toggleButton, label);
  content.appendChild(left);
  cell.appendChild(content);
  dividerRow.appendChild(cell);
  return dividerRow;
}

function createAlphaDividerRow(alphaLabel, columnCount) {
  const dividerRow = document.createElement('tr');
  dividerRow.className = 'table-alpha-divider';
  dividerRow.dataset.dividerRow = 'true';
  dividerRow.dataset.alphaLabel = alphaLabel;
  dividerRow.dataset.alphaCollapsed = 'false';
  const cell = document.createElement('td');
  cell.colSpan = columnCount;
  const content = document.createElement('div');
  content.className = 'alpha-divider-content';
  const left = document.createElement('div');
  left.className = 'alpha-divider-left';
  const toggleButton = document.createElement('button');
  toggleButton.type = 'button';
  toggleButton.className = 'alpha-toggle';
  toggleButton.dataset.alphaToggle = alphaLabel;
  toggleButton.setAttribute('aria-expanded', 'true');
  const toggleIcon = document.createElement('i');
  toggleIcon.className = 'fas fa-chevron-down';
  toggleIcon.setAttribute('aria-hidden', 'true');
  toggleButton.appendChild(toggleIcon);
  const label = document.createElement('span');
  label.className = 'alpha-divider-label text-muted text-uppercase';
  label.textContent = alphaLabel;
  left.append(toggleButton, label);
  content.appendChild(left);
  cell.appendChild(content);
  dividerRow.appendChild(cell);
  return dividerRow;
}

function createMerchantCategoryDividerRow(categoryLabel, columnCount) {
  const dividerRow = document.createElement('tr');
  dividerRow.className = 'table-city-divider';
  dividerRow.dataset.dividerRow = 'true';
  dividerRow.dataset.merchantCategoryLabel = categoryLabel;
  dividerRow.dataset.merchantCategoryCollapsed = 'false';
  const cell = document.createElement('td');
  cell.colSpan = columnCount;
  const content = document.createElement('div');
  content.className = 'city-divider-content';
  const left = document.createElement('div');
  left.className = 'city-divider-left';
  const toggleButton = document.createElement('button');
  toggleButton.type = 'button';
  toggleButton.className = 'city-toggle';
  toggleButton.dataset.merchantCategoryToggle = categoryLabel;
  toggleButton.setAttribute('aria-expanded', 'true');
  const toggleIcon = document.createElement('i');
  toggleIcon.className = 'fas fa-chevron-down';
  toggleIcon.setAttribute('aria-hidden', 'true');
  toggleButton.appendChild(toggleIcon);
  const label = document.createElement('span');
  label.className = 'city-divider-label text-muted text-uppercase';
  label.textContent = categoryLabel;
  left.append(toggleButton, label);
  content.appendChild(left);
  cell.appendChild(content);
  dividerRow.appendChild(cell);
  return dividerRow;
}

function getRestaurantAlphaGroup(value) {
  const normalized = (value || '').toString().trim();
  if (!normalized) return '#';
  const first = normalized[0]?.toUpperCase() || '#';
  return /[A-Z]/.test(first) ? first : '#';
}

function getRestaurantLocationGroup(row) {
  return row.dataset.restaurantCity || 'No location';
}

function getMerchantCategoryGroup(row) {
  const rawCategory = row.dataset.merchantCategory || '';
  if (!rawCategory) return 'Uncategorized';
  if (rawCategory === 'Uncategorized') return rawCategory;
  return rawCategory.replace(/_/g, ' ').replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function rebuildRestaurantTableBody(tbody, rows, columnCount, groupBy) {
  tbody.textContent = '';
  if (!groupBy) {
    rows.forEach((row) => {
      delete row.dataset.restaurantGroupType;
      delete row.dataset.restaurantGroupLabel;
      delete row.dataset.restaurantAlphaGroup;
      tbody.appendChild(row);
    });
    return;
  }

  let currentGroup = '';
  rows.forEach((row) => {
    let groupLabel = '';
    if (groupBy === 'alpha') {
      const [, nameCell] = row.cells;
      const nameValue = nameCell?.dataset.sortValue || nameCell?.textContent || '';
      groupLabel = getRestaurantAlphaGroup(nameValue);
    } else if (groupBy === 'location') {
      groupLabel = getRestaurantLocationGroup(row);
    }

    if (groupLabel && groupLabel !== currentGroup) {
      currentGroup = groupLabel;
      const dividerRow =
        groupBy === 'location'
          ? createCityDividerRow(groupLabel, columnCount)
          : createAlphaDividerRow(groupLabel, columnCount);
      tbody.appendChild(dividerRow);
    }

    row.dataset.restaurantGroupType = groupBy;
    row.dataset.restaurantGroupLabel = groupLabel;
    if (groupBy === 'location') {
      row.dataset.restaurantCityGroup = groupLabel;
      delete row.dataset.restaurantAlphaGroup;
    } else if (groupBy === 'alpha') {
      row.dataset.restaurantAlphaGroup = groupLabel;
    }
    tbody.appendChild(row);
  });
}

function rebuildMerchantTableBody(tbody, rows, columnCount, groupBy) {
  tbody.textContent = '';
  if (!groupBy) {
    rows.forEach((row) => {
      delete row.dataset.merchantAlphaGroup;
      delete row.dataset.merchantCategoryGroup;
      tbody.appendChild(row);
    });
    return;
  }

  let currentGroup = '';
  rows.forEach((row) => {
    let groupLabel = '';
    if (groupBy === 'alpha') {
      const [, nameCell] = row.cells;
      const nameValue = nameCell?.dataset.sortValue || nameCell?.textContent || '';
      groupLabel = getRestaurantAlphaGroup(nameValue);
    } else if (groupBy === 'category') {
      groupLabel = getMerchantCategoryGroup(row);
    }

    if (groupLabel && groupLabel !== currentGroup) {
      currentGroup = groupLabel;
      const dividerRow =
        groupBy === 'category'
          ? createMerchantCategoryDividerRow(groupLabel, columnCount)
          : createAlphaDividerRow(groupLabel, columnCount);
      tbody.appendChild(dividerRow);
    }

    if (groupBy === 'alpha') {
      row.dataset.merchantAlphaGroup = groupLabel;
      delete row.dataset.merchantCategoryGroup;
    } else if (groupBy === 'category') {
      row.dataset.merchantCategoryGroup = groupLabel;
      delete row.dataset.merchantAlphaGroup;
    }

    tbody.appendChild(row);
  });
}

function getHeaderByCellIndex(headers, columnIndex) {
  return Array.from(headers).find((header) => header.cellIndex === columnIndex) || null;
}

function getSortPreferenceKeys(tableId) {
  return {
    storageKey: `tableSort:${tableId}`,
    cookieKey: `table_sort_${tableId}`,
  };
}

function loadSortPreference(tableId) {
  const { storageKey, cookieKey } = getSortPreferenceKeys(tableId);
  const pref = getStoredJson(storageKey, cookieKey);
  if (!pref || typeof pref !== 'object') return null;

  const columnIndex = parseInt(String(pref.columnIndex), 10);
  const direction = String(pref.direction || '').toLowerCase();
  if (!Number.isFinite(columnIndex)) return null;
  if (direction !== 'asc' && direction !== 'desc') return null;

  return { columnIndex, direction };
}

function saveSortPreference(tableId, columnIndex, direction) {
  const { storageKey, cookieKey } = getSortPreferenceKeys(tableId);
  persistJson(storageKey, cookieKey, { columnIndex, direction });
}

function sortExpenseTable(columnIndex, ascending) {
  const table = document.getElementById('expenseTable');
  if (!table) return;
  const tbody = table.querySelector('tbody');
  if (!tbody) return;
  const rows = getExpenseRows(tbody);

  rows.sort((a, b) => {
    const aValue = getExpenseCellValue(a, columnIndex);
    const bValue = getExpenseCellValue(b, columnIndex);

    // Multi-level sort for restaurant column
    if (columnIndex === 2) {
      // Restaurant column
      const aRestaurant = (aValue || '').toString().toLowerCase();
      const bRestaurant = (bValue || '').toString().toLowerCase();
      if (aRestaurant !== bRestaurant) {
        return ascending ? compareValues(aRestaurant, bRestaurant) : compareValues(bRestaurant, aRestaurant);
      }
      // If restaurants are the same, sort by date (column 1)
      const aDate = getExpenseCellValue(a, 1);
      const bDate = getExpenseCellValue(b, 1);
      return ascending ? compareValues(aDate, bDate) : compareValues(bDate, aDate);
    }

    return ascending ? compareValues(aValue, bValue) : compareValues(bValue, aValue);
  });

  // Re-append sorted rows
  const columnCount = table.querySelectorAll('thead th').length;
  const groupByMonth = columnIndex === 1;
  rebuildExpenseTableBody(tbody, rows, columnCount, groupByMonth);
}

function sortRestaurantTable(columnIndex, ascending) {
  const table = document.getElementById('restaurantTable');
  if (!table) return;
  const tbody = table.querySelector('tbody');
  if (!tbody) return;
  const rows = getRestaurantRows(tbody);

  rows.sort((a, b) => {
    const aValue = getRestaurantCellValue(a, columnIndex);
    const bValue = getRestaurantCellValue(b, columnIndex);

    // Multi-level sort for name column
    if (columnIndex === 1) {
      // Name column
      const aName = (aValue || '').toString().toLowerCase();
      const bName = (bValue || '').toString().toLowerCase();
      if (aName !== bName) {
        return ascending ? compareValues(aName, bName) : compareValues(bName, aName);
      }
      // If names are the same, sort by rating (column 1)
      const aRating = getRestaurantCellValue(a, 4);
      const bRating = getRestaurantCellValue(b, 4);
      return ascending ? compareValues(aRating, bRating) : compareValues(bRating, aRating);
    }

    return ascending ? compareValues(aValue, bValue) : compareValues(bValue, aValue);
  });

  // Re-append sorted rows with appropriate groupings
  const columnCount = table.querySelectorAll('thead th').length;
  let groupBy = null;
  if (columnIndex === 1) {
    groupBy = 'alpha';
  } else if (columnIndex === 2) {
    groupBy = 'location';
  }
  rebuildRestaurantTableBody(tbody, rows, columnCount, groupBy);
}

function sortMerchantTable(columnIndex, ascending) {
  const table = document.getElementById('merchantTable');
  if (!table) return;
  const tbody = table.querySelector('tbody');
  if (!tbody) return;
  const rows = getMerchantRows(tbody);

  rows.sort((a, b) => {
    const aValue = getMerchantCellValue(a, columnIndex);
    const bValue = getMerchantCellValue(b, columnIndex);

    if (columnIndex === 1) {
      const aName = (aValue || '').toString().toLowerCase();
      const bName = (bValue || '').toString().toLowerCase();
      if (aName !== bName) {
        return ascending ? compareValues(aName, bName) : compareValues(bName, aName);
      }
      const aCount = getMerchantCellValue(a, 3);
      const bCount = getMerchantCellValue(b, 3);
      return ascending ? compareValues(aCount, bCount) : compareValues(bCount, aCount);
    }

    return ascending ? compareValues(aValue, bValue) : compareValues(bValue, aValue);
  });

  const columnCount = table.querySelectorAll('thead th').length;
  let groupBy = null;
  if (columnIndex === 1) {
    groupBy = 'alpha';
  } else if (columnIndex === 2) {
    groupBy = 'category';
  }
  rebuildMerchantTableBody(tbody, rows, columnCount, groupBy);
}

function initTableSorting(tableId) {
  const table = document.getElementById(tableId);
  if (!table) return;

  // Prevent double-initialization (HTMX swaps replace the table element)
  if (table.dataset.sortInitialized === 'true') return;
  table.dataset.sortInitialized = 'true';

  const headers = table.querySelectorAll('th[data-sort="true"]');
  const saved = loadSortPreference(tableId);

  headers.forEach((header) => {
    header.style.cursor = 'pointer';
    header.addEventListener('click', () => {
      const isAscending = header.classList.contains('sort-asc');
      const columnIndex = header.cellIndex;

      // Remove sort classes and arrows from all headers
      headers.forEach((h) => {
        h.classList.remove('sort-asc', 'sort-desc');
      });

      // Add appropriate sort class
      const newAscending = !isAscending;
      header.classList.add(newAscending ? 'sort-asc' : 'sort-desc');
      saveSortPreference(tableId, columnIndex, newAscending ? 'asc' : 'desc');

      // Sort the table based on table type
      if (tableId === 'expenseTable') {
        sortExpenseTable(columnIndex, newAscending);
      } else if (tableId === 'restaurantTable') {
        sortRestaurantTable(columnIndex, newAscending);
      } else if (tableId === 'merchantTable') {
        sortMerchantTable(columnIndex, newAscending);
      }
    });
  });

  // Apply saved sort (if any) after listeners exist.
  if (saved) {
    const header = getHeaderByCellIndex(headers, saved.columnIndex);
    if (header) {
      header.classList.add(saved.direction === 'asc' ? 'sort-asc' : 'sort-desc');
      if (tableId === 'expenseTable') {
        sortExpenseTable(saved.columnIndex, saved.direction === 'asc');
      } else if (tableId === 'restaurantTable') {
        sortRestaurantTable(saved.columnIndex, saved.direction === 'asc');
      } else if (tableId === 'merchantTable') {
        sortMerchantTable(saved.columnIndex, saved.direction === 'asc');
      }
    }
    return;
  }

  if (tableId === 'restaurantTable' || tableId === 'merchantTable') {
    const nameHeader = getHeaderByCellIndex(headers, 1);
    if (nameHeader) {
      nameHeader.classList.add('sort-asc');
      if (tableId === 'restaurantTable') {
        sortRestaurantTable(1, true);
      } else {
        sortMerchantTable(1, true);
      }
    }
  }
}

function initExpenseTableSorting() {
  // Initialize table sorting for both expense and restaurant tables
  initTableSorting('expenseTable');
  initTableSorting('restaurantTable');
  initTableSorting('merchantTable');

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

// Re-initialize after HTMX swaps (new tables need fresh listeners)
document.addEventListener('htmx:afterSettle', () => {
  initExpenseTableSorting();
});
