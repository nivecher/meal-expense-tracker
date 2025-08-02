/**
 * Table Sort Component
 * Handles client-side sorting of table columns
 */

export class TableSort {
  /**
     * Initialize table sorting
     * @param {string} tableSelector - CSS selector for the table
     */
  constructor (tableSelector) {
    this.table = document.querySelector(tableSelector);
    if (!this.table) return;

    this.tbody = this.table.querySelector('tbody');
    this.rows = Array.from(this.tbody.rows);
    this.headers = this.table.querySelectorAll('th[data-sort]');
    this.currentSort = {
      column: null,
      direction: 'asc',
    };

    this.init();
  }

  /**
     * Initialize event listeners for sortable headers
     */
  init () {
    this.headers.forEach((header, index) => {
      if (header.dataset.sort === 'true') {
        header.style.cursor = 'pointer';
        header.setAttribute('role', 'button');
        header.setAttribute('aria-label', `Sort by ${header.textContent.trim()}`);
        header.setAttribute('tabindex', '0');

        // Add sort indicator
        const indicator = document.createElement('span');
        indicator.className = 'sort-indicator ms-1';
        header.appendChild(indicator);

        // Add event listeners for click and keyboard
        header.addEventListener('click', () => this.sortByColumn(index));
        header.addEventListener('keydown', (e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            this.sortByColumn(index);
          }
        });
      }
    });
  }

  /**
     * Sort table by column
     * @param {number} columnIndex - Index of the column to sort by
     */
  sortByColumn (columnIndex) {
    const header = this.headers[columnIndex];
    const sortType = header.dataset.sortType || 'text';

    // Toggle direction if clicking the same column
    if (this.currentSort.column === columnIndex) {
      this.currentSort.direction = this.currentSort.direction === 'asc' ? 'desc' : 'asc';
    } else {
      this.currentSort.column = columnIndex;
      this.currentSort.direction = 'asc';
    }

    // Sort the rows
    this.rows.sort((rowA, rowB) => {
      const cellA = rowA.cells[columnIndex];
      const cellB = rowB.cells[columnIndex];

      const valueA = this.getCellValue(cellA, sortType);
      const valueB = this.getCellValue(cellB, sortType);

      // Handle null/undefined values
      if (valueA === null || valueA === undefined) return 1;
      if (valueB === null || valueB === undefined) return -1;

      // Compare values based on type
      if (sortType === 'number' || sortType === 'currency') {
        return this.currentSort.direction === 'asc'
          ? valueA - valueB
          : valueB - valueA;
      } else if (sortType === 'date') {
        return this.currentSort.direction === 'asc'
          ? new Date(valueA) - new Date(valueB)
          : new Date(valueB) - new Date(valueA);
      }
      // Text comparison
      return this.currentSort.direction === 'asc'
        ? valueA.toString().localeCompare(valueB.toString())
        : valueB.toString().localeCompare(valueA.toString());

    });

    // Update the table
    this.updateTable();
    this.updateSortIndicators();
  }

  /**
     * Get the value of a cell based on its data type
     * @param {HTMLElement} cell - The table cell
     * @param {string} type - The data type (text, number, currency, date)
     * @returns {*} The processed cell value
     */
  getCellValue (cell, type) {
    const value = cell.textContent.trim();

    switch (type) {
      case 'number':
        return parseFloat(value.replace(/[^\d.-]/g, '')) || 0;
      case 'currency':
        return parseFloat(value.replace(/[^\d.-]/g, '')) || 0;
      case 'date':
        // Try to parse date from text
        const date = new Date(value);
        return isNaN(date.getTime()) ? value : date;
      default:
        return value;
    }
  }

  /**
     * Update the table with sorted rows
     */
  updateTable () {
    // Remove existing rows
    while (this.tbody.firstChild) {
      this.tbody.removeChild(this.tbody.firstChild);
    }

    // Add sorted rows
    this.rows.forEach((row) => this.tbody.appendChild(row));
  }

  /**
     * Update sort indicators on column headers
     */
  updateSortIndicators () {
    this.headers.forEach((header, index) => {
      const indicator = header.querySelector('.sort-indicator');
      if (!indicator) return;

      if (index === this.currentSort.column) {
        indicator.textContent = this.currentSort.direction === 'asc' ? '↑' : '↓';
        indicator.setAttribute('aria-label', `Sorted ${this.currentSort.direction}ending`);
      } else {
        indicator.textContent = '';
        indicator.removeAttribute('aria-label');
      }
    });
  }
}

// Initialize table sort when the DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
  new TableSort('.restaurant-table');
});
