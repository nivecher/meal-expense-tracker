/**
 * Expense list: URL params, filter form sync, and view preferences.
 * Used by expense-list.js and expense-list-calendar.js.
 */

export function getUrlParams() {
  return new URLSearchParams(window.location.search);
}

export function getActiveExpenseFilterCount() {
  const urlParams = getUrlParams();
  let count = 0;

  const mealType = urlParams.get('meal_type');
  if (mealType && mealType !== 'None') {
    count += 1;
  }

  const category = urlParams.get('category');
  if (category && category !== 'None') {
    count += 1;
  }

  const orderType = urlParams.get('order_type');
  if (orderType && orderType !== 'None') {
    count += 1;
  }

  const startDate = urlParams.get('start_date');
  if (startDate && startDate !== 'None') {
    count += 1;
  }

  const endDate = urlParams.get('end_date');
  if (endDate && endDate !== 'None') {
    count += 1;
  }

  const tags = urlParams.getAll('tags').filter((tag) => tag && tag !== 'None');
  if (tags.length) {
    count += 1;
  }

  return count;
}

export function updateExpenseFilterIndicators() {
  const count = getActiveExpenseFilterCount();

  const filterButton = document.getElementById('expense-filter-button');
  const filterCountBadge = document.getElementById('expense-filter-count');
  if (filterButton) {
    if (count > 0) {
      filterButton.classList.remove('btn-outline-secondary');
      filterButton.classList.add('btn-primary');
      filterButton.setAttribute('title', `${count} filters active`);
    } else {
      filterButton.classList.remove('btn-primary');
      filterButton.classList.add('btn-outline-secondary');
      filterButton.setAttribute('title', 'Filter expenses');
    }
  }

  if (filterCountBadge) {
    if (count > 0) {
      filterCountBadge.textContent = `${count}`;
      filterCountBadge.classList.remove('d-none');
    } else {
      filterCountBadge.textContent = '';
      filterCountBadge.classList.add('d-none');
    }
  }

  const statusCount = document.getElementById('expense-filter-status-count');
  const statusText = document.getElementById('expense-filter-status-text');
  if (statusCount) {
    if (count > 0) {
      statusCount.textContent = `${count}`;
      statusCount.classList.remove('d-none');
    } else {
      statusCount.textContent = '';
      statusCount.classList.add('d-none');
    }
  }

  if (statusText) {
    statusText.classList.toggle('d-none', count === 0);
  }
}

function setSelectValue(selectId, value) {
  const select = document.getElementById(selectId);
  if (!select) return;
  const normalized = value || '';
  select.value = normalized;
}

function setInputValue(inputId, value) {
  const input = document.getElementById(inputId);
  if (!input) return;
  input.value = value || '';
}

function syncExpenseFilterTagsFromUrl() {
  const urlParams = getUrlParams();
  const tags = urlParams.getAll('tags').filter((tag) => tag && tag !== 'None');
  const filterTagsInput = document.getElementById('filterTagsInput');
  if (!filterTagsInput || !filterTagsInput.tagSelect) return;

  filterTagsInput.tagSelect.clear(true);
  tags.forEach((tag) => {
    filterTagsInput.tagSelect.addItem(tag, true);
  });
}

export function syncExpenseFilterFormFromUrl() {
  const urlParams = getUrlParams();
  setSelectValue('meal_type', urlParams.get('meal_type'));
  setSelectValue('order_type', urlParams.get('order_type'));
  setSelectValue('category', urlParams.get('category'));
  setInputValue('start_date', urlParams.get('start_date'));
  setInputValue('end_date', urlParams.get('end_date'));
  syncExpenseFilterTagsFromUrl();
}

function clearExpenseFilters() {
  setSelectValue('meal_type', '');
  setSelectValue('order_type', '');
  setSelectValue('category', '');
  setInputValue('start_date', '');
  setInputValue('end_date', '');

  const filterTagsInput = document.getElementById('filterTagsInput');
  if (filterTagsInput?.tagSelect) {
    filterTagsInput.tagSelect.clear(true);
  } else if (filterTagsInput) {
    filterTagsInput.value = '';
  }

  const form = document.getElementById('expense-filter-form');
  if (form?.requestSubmit) {
    form.requestSubmit();
  } else if (form) {
    form.dispatchEvent(new Event('submit', { cancelable: true }));
  }
}

export function initExpenseFilterClear() {
  const clearButton = document.getElementById('expense-filter-clear');
  if (!clearButton) return;
  clearButton.addEventListener('click', () => {
    clearExpenseFilters();
  });
}

function getCookieValue(name) {
  const cookieString = document.cookie || '';
  const parts = cookieString.split(';').map((c) => c.trim());
  const prefix = `${encodeURIComponent(name)}=`;
  const match = parts.find((p) => p.startsWith(prefix));
  if (!match) return null;
  try {
    return decodeURIComponent(match.slice(prefix.length));
  } catch {
    return match.slice(prefix.length);
  }
}

function setCookieValue(name, value, days = 365) {
  const maxAgeSeconds = Math.floor(days * 24 * 60 * 60);
  const encoded = encodeURIComponent(name);
  const encodedValue = encodeURIComponent(value);
  document.cookie = `${encoded}=${encodedValue}; Max-Age=${maxAgeSeconds}; Path=/; SameSite=Lax`;
}

function getStoredPreference(storageKey, cookieKey) {
  try {
    const localValue = localStorage.getItem(storageKey);
    if (localValue) return localValue;
  } catch {
    // localStorage may be unavailable (privacy mode / locked down browsers)
  }

  return getCookieValue(cookieKey);
}

function persistPreference(storageKey, cookieKey, value) {
  try {
    localStorage.setItem(storageKey, value);
  } catch {
    // localStorage may be unavailable (privacy mode / locked down browsers)
  }

  setCookieValue(cookieKey, value);
}

export function applyExpenseViewPreference() {
  const cardView = document.getElementById('card-view');
  const tableView = document.getElementById('table-view');
  const cardViewContainer = document.getElementById('card-view-container');
  const tableViewContainer = document.getElementById('table-view-container');

  if (!cardView || !tableView || !cardViewContainer || !tableViewContainer) {
    return;
  }

  const storedView = getStoredPreference('expenseViewPreference', 'expense_view_preference');
  const view = storedView === 'compact' ? 'table' : (storedView === 'table' || storedView === 'card' ? storedView : (tableView.checked ? 'table' : 'card'));
  persistPreference('expenseViewPreference', 'expense_view_preference', view);

  if (view === 'table') {
    cardView.checked = false;
    cardViewContainer.classList.add('d-none');
    tableView.checked = true;
    tableViewContainer.classList.remove('d-none');
    return;
  }

  cardView.checked = true;
  tableView.checked = false;
  tableViewContainer.classList.add('d-none');
  cardViewContainer.classList.remove('d-none');
}

export function initViewToggle() {
  const cardView = document.getElementById('card-view');
  const tableView = document.getElementById('table-view');

  if (!cardView || !tableView) {
    return;
  }

  if (cardView.dataset.listenerAttached === 'true') {
    applyExpenseViewPreference();
    return;
  }

  cardView.dataset.listenerAttached = 'true';
  tableView.dataset.listenerAttached = 'true';

  cardView.addEventListener('change', () => {
    if (!cardView.checked) return;
    persistPreference('expenseViewPreference', 'expense_view_preference', 'card');
    applyExpenseViewPreference();
  });

  tableView.addEventListener('change', () => {
    if (!tableView.checked) return;
    persistPreference('expenseViewPreference', 'expense_view_preference', 'table');
    applyExpenseViewPreference();
  });

  applyExpenseViewPreference();
}
