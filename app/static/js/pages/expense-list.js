/**
 * Expense List Page
 * Orchestrates filters, calendar, delete, selection, tabs, and HTMX re-apply.
 */

import { initializeRobustFaviconHandling } from '../utils/robust-favicon-handler.js';
import { toast } from '../utils/notifications.js';
import {
  updateExpenseFilterIndicators,
  syncExpenseFilterFormFromUrl,
  initExpenseFilterClear,
  applyExpenseViewPreference,
  initViewToggle,
} from './expense-list-filters.js';
import { initExpenseCalendar, updateCalendarFilterSummary } from './expense-list-calendar.js';

// --- Delete expense (single) ---
function initDeleteExpense() {
  const deleteForm = document.getElementById('delete-expense-form');
  if (!deleteForm) return;

  if (deleteForm.dataset.listenerAttached === 'true') return;
  deleteForm.dataset.listenerAttached = 'true';

  document.addEventListener('click', (event) => {
    const button = event.target.closest('[data-bs-target="#deleteExpenseModal"][data-expense-id]');
    if (!button) return;

    const expenseId = button.getAttribute('data-expense-id');
    const expenseName = button.getAttribute('data-expense-description') || 'Expense';

    const deleteUrlBase = deleteForm.getAttribute('data-delete-url') || '';
    if (expenseId && deleteUrlBase) {
      deleteForm.action = `${deleteUrlBase}${expenseId}/delete`;
    }

    const modalTitle = document.getElementById('deleteExpenseModalLabel');
    if (modalTitle) {
      modalTitle.textContent = `Delete Expense: ${expenseName}`;
    }
  });

  deleteForm.addEventListener('submit', () => {
    const submitButton = deleteForm.querySelector('button[type="submit"]');
    if (submitButton) {
      submitButton.disabled = true;
      submitButton.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Deleting...';
    }
  });
}

function initFaviconLoading() {
  initializeRobustFaviconHandling('.restaurant-favicon');
  initializeRobustFaviconHandling('.restaurant-favicon-table');
}

function initFilterTagSelector() {
  function tryInitTagSelector() {
    const filterTagsInput = document.getElementById('filterTagsInput');
    if (!filterTagsInput) return;

    if (typeof window.initTagSelectorWidget !== 'function') return;
    if (typeof TomSelect === 'undefined') return;

    if (filterTagsInput.tagSelect) {
      filterTagsInput.tagSelect.refreshOptions(false);
      return;
    }

    const urlParams = new URLSearchParams(window.location.search);
    const selectedTags = urlParams.getAll('tags');
    const tagSelectInstance = window.initTagSelectorWidget(filterTagsInput, {
      allowCreate: false,
      selectedTags,
    });

    if (tagSelectInstance) {
      window.tagSelectInstance = tagSelectInstance;
    }
  }

  tryInitTagSelector();

  const filterCollapse = document.getElementById('filterCollapse');
  if (filterCollapse) {
    filterCollapse.addEventListener('shown.bs.collapse', () => {
      setTimeout(() => {
        tryInitTagSelector();
        const filterTagsInput = document.getElementById('filterTagsInput');
        if (filterTagsInput?.tagSelect && typeof filterTagsInput.tagSelect.refreshOptions === 'function') {
          filterTagsInput.tagSelect.refreshOptions(false);
        }
      }, 150);
    });
  }

  setTimeout(tryInitTagSelector, 500);
}

function initTagManagerModal() {
  const manageTagsLink = document.getElementById('manageTagsLink');
  if (!manageTagsLink) {
    return;
  }

  manageTagsLink.addEventListener('click', (event) => {
    event.preventDefault();

    if (window.tagManager && window.tagManager.modal) {
      const modalInstance = new bootstrap.Modal(window.tagManager.modal);
      modalInstance.show();
      return;
    }

    if (window.tagManager) {
      window.tagManager.init();
      if (window.tagManager.modal) {
        const modalInstance = new bootstrap.Modal(window.tagManager.modal);
        modalInstance.show();
      }
      return;
    }

    console.warn('Tag manager not available for manage tags modal');
  });
}

function getCsrfToken() {
  const metaToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
  if (metaToken) return metaToken;
  const inputToken = document.querySelector('input[name="csrf_token"]');
  return inputToken ? inputToken.value : '';
}

// --- Tabs ---
function setExpenseTabActive(button, pane, allButtons, allPanes) {
  allButtons.forEach((tabButton) => {
    tabButton.classList.remove('active');
    tabButton.setAttribute('aria-selected', 'false');
  });
  allPanes.forEach((tabPane) => {
    tabPane.classList.remove('show', 'active');
  });
  button.classList.add('active');
  button.setAttribute('aria-selected', 'true');
  pane.classList.add('show', 'active');
}

function initExpenseTabs() {
  const tabList = document.getElementById('expensesTabs');
  if (!tabList) return;
  const buttons = Array.from(tabList.querySelectorAll('[data-bs-target]'));
  if (!buttons.length) return;
  const panes = Array.from(document.querySelectorAll('#expensesTabsContent .tab-pane'));
  const urlParams = new URLSearchParams(window.location.search);
  const initialView = urlParams.get('view');

  buttons.forEach((button) => {
    if (button.dataset.listenerAttached === 'true') return;
    button.dataset.listenerAttached = 'true';
    button.addEventListener('click', (event) => {
      event.preventDefault();
      const targetSelector = button.getAttribute('data-bs-target');
      if (!targetSelector) return;
      const pane = document.querySelector(targetSelector);
      if (!pane) return;
      setExpenseTabActive(button, pane, buttons, panes);
      const viewValue = targetSelector.replace('#', '').replace('-pane', '');
      const nextParams = new URLSearchParams(window.location.search);
      if (viewValue === 'expenses') {
        nextParams.delete('view');
      } else {
        nextParams.set('view', viewValue);
      }
      const nextUrl = `${window.location.pathname}?${nextParams.toString()}`.replace(/\?$/, '');
      window.history.replaceState({}, '', nextUrl);
    });
  });

  if (initialView) {
    const initialTarget = `#${initialView}-pane`;
    const initialPane = document.querySelector(initialTarget);
    const initialButton = buttons.find((btn) => btn.getAttribute('data-bs-target') === initialTarget);
    if (initialButton && initialPane) {
      setExpenseTabActive(initialButton, initialPane, buttons, panes);
    }
  }
}

// --- Sticky table ---
let stickyOffsetUpdateScheduled = false;

function updateExpenseTableStickyOffsets() {
  const stickyRoot = document.querySelector('#table-view-container .table-sticky-frozen');
  if (!stickyRoot) return;

  const toolbar = stickyRoot.querySelector('.table-actions-toolbar');
  const toolbarHeightPx = toolbar ? Math.ceil(toolbar.getBoundingClientRect().height) : 0;
  stickyRoot.style.setProperty('--sticky-header-top', `${toolbarHeightPx}px`);
}

function scheduleExpenseStickyOffsetUpdate() {
  if (stickyOffsetUpdateScheduled) return;
  stickyOffsetUpdateScheduled = true;
  requestAnimationFrame(() => {
    stickyOffsetUpdateScheduled = false;
    updateExpenseTableStickyOffsets();
  });
}

// --- Selection & bulk actions ---
function setActionAnchorState(anchor, href, enabled) {
  if (!anchor) return;
  if (enabled) {
    anchor.classList.remove('disabled');
    anchor.setAttribute('aria-disabled', 'false');
    anchor.removeAttribute('tabindex');
    anchor.setAttribute('href', href);
    return;
  }

  anchor.classList.add('disabled');
  anchor.setAttribute('aria-disabled', 'true');
  anchor.setAttribute('tabindex', '-1');
  anchor.removeAttribute('href');
}

function getSelectedExpenseInputs() {
  return Array.from(document.querySelectorAll('input[name="expense-select"]:checked'));
}

function getSelectedExpenseIds() {
  return getSelectedExpenseInputs().map((input) => input.value).filter(Boolean);
}

function updateExpenseRowSelectionHighlight() {
  document.querySelectorAll('input[name="expense-select"]').forEach((input) => {
    if (!(input instanceof HTMLInputElement)) return;
    const row = input.closest('tr');
    if (!row) return;
    const selected = input.checked;
    row.classList.toggle('is-selected', selected);
    row.setAttribute('aria-selected', String(selected));
  });
}

function updateExpenseSelectionStatus(selectedCount) {
  const status = document.getElementById('expense-selection-status');
  if (!status) return;
  if (selectedCount === 0) {
    status.textContent = '0 selected';
    return;
  }
  if (selectedCount === 1) {
    status.textContent = '1 selected';
    return;
  }
  status.textContent = `${selectedCount} selected`;
}

function updateExpenseBulkActions(selectedInputs) {
  const bulkExportButton = document.querySelector('[data-expense-bulk-export]');
  const hasSelection = selectedInputs.length > 0;
  if (bulkExportButton instanceof HTMLButtonElement) {
    bulkExportButton.disabled = !hasSelection;
  }
}

function updateExpenseActionToolbar(selectedInputs) {
  const viewLink = document.getElementById('expense-action-view');
  const editLink = document.getElementById('expense-action-edit');
  const deleteButton = document.getElementById('expense-action-delete');

  if (!selectedInputs.length) {
    setActionAnchorState(viewLink, '', false);
    setActionAnchorState(editLink, '', false);
    if (deleteButton) {
      deleteButton.disabled = true;
      deleteButton.removeAttribute('data-expense-id');
      deleteButton.removeAttribute('data-expense-description');
      deleteButton.removeAttribute('data-expense-amount');
      deleteButton.removeAttribute('data-expense-date');
    }
    return;
  }

  if (deleteButton) {
    deleteButton.disabled = false;
    deleteButton.removeAttribute('data-expense-id');
    deleteButton.removeAttribute('data-expense-description');
    deleteButton.removeAttribute('data-expense-amount');
    deleteButton.removeAttribute('data-expense-date');
  }

  if (selectedInputs.length !== 1) {
    setActionAnchorState(viewLink, '', false);
    setActionAnchorState(editLink, '', false);
    return;
  }

  const [selectedInput] = selectedInputs;
  const viewUrl = selectedInput.dataset.viewUrl || '';
  const editUrl = selectedInput.dataset.editUrl || '';
  setActionAnchorState(viewLink, viewUrl, Boolean(viewUrl));
  setActionAnchorState(editLink, editUrl, Boolean(editUrl));

  if (deleteButton) {
    deleteButton.dataset.expenseId = selectedInput.dataset.expenseId || '';
    deleteButton.dataset.expenseDescription = selectedInput.dataset.expenseDescription || 'Expense';
    deleteButton.dataset.expenseAmount = selectedInput.dataset.expenseAmount || '';
    deleteButton.dataset.expenseDate = selectedInput.dataset.expenseDate || '';
  }
}

function applyExpenseSelectionState() {
  const selectedInputs = getSelectedExpenseInputs();
  updateExpenseRowSelectionHighlight();
  updateExpenseSelectionStatus(selectedInputs.length);
  updateExpenseActionToolbar(selectedInputs);
  updateExpenseBulkActions(selectedInputs);

  const selectAll = document.getElementById('expense-select-all');
  if (selectAll instanceof HTMLInputElement) {
    const total = document.querySelectorAll('input[name="expense-select"]').length;
    const checked = selectedInputs.length;
    const someSelected = checked > 0 && checked < total;
    const allSelected = total > 0 && checked === total;
    selectAll.checked = allSelected;
    selectAll.indeterminate = someSelected;
    if (someSelected) {
      selectAll.indeterminate = false;
      requestAnimationFrame(() => {
        selectAll.indeterminate = true;
      });
    }
  }
}

// eslint-disable-next-line no-unused-vars -- reserved for bulk delete UI
function openBulkDeleteModal(selectedIds) {
  const modalElement = document.getElementById('bulkDeleteExpensesModal');
  const countElement = modalElement?.querySelector('[data-expense-bulk-count]');
  if (countElement) {
    countElement.textContent = `${selectedIds.length}`;
  }
  if (modalElement) {
    const modalInstance = new bootstrap.Modal(modalElement);
    modalInstance.show();
  }
}

async function performBulkExpenseDelete(expenseIds) {
  const csrfToken = getCsrfToken();
  const deleteUrlBase = document.getElementById('delete-expense-form')?.dataset.deleteUrl || '';
  if (!deleteUrlBase || !expenseIds.length) return;
  try {
    const requests = expenseIds.map((expenseId) =>
      fetch(`${deleteUrlBase}${expenseId}/delete`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Requested-With': 'XMLHttpRequest',
          'X-CSRFToken': csrfToken,
        },
        body: JSON.stringify({ csrf_token: csrfToken }),
      }),
    );
    const results = await Promise.all(requests);
    const failed = results.filter((response) => !response.ok);
    if (failed.length) {
      toast.error('Some expenses could not be deleted. Please retry.');
      return;
    }
    toast.success('Selected expenses deleted.');
    window.location.reload();
  } catch (error) {
    console.warn('Bulk delete failed', error);
    toast.error('Unable to delete selected expenses.');
  }
}

function initExpenseBulkActions() {
  const bulkExportButton = document.querySelector('[data-expense-bulk-export]');
  if (bulkExportButton instanceof HTMLButtonElement) {
    bulkExportButton.addEventListener('click', () => {
      const selectedIds = getSelectedExpenseIds();
      if (!selectedIds.length) return;
      const exportUrl = bulkExportButton.dataset.exportUrl || '';
      if (!exportUrl) return;
      const url = new URL(exportUrl, window.location.origin);
      url.searchParams.set('format', 'csv');
      url.searchParams.set('ids', selectedIds.join(','));
      window.location.assign(url.toString());
    });
  }

  const bulkConfirmButton = document.querySelector('[data-expense-bulk-confirm]');
  if (bulkConfirmButton instanceof HTMLButtonElement) {
    bulkConfirmButton.addEventListener('click', () => {
      const selectedIds = getSelectedExpenseIds();
      if (!selectedIds.length) return;
      performBulkExpenseDelete(selectedIds);
    });
  }
}

function openExpenseDeleteModal(expenseId, expenseName) {
  if (!expenseId) return;
  const deleteForm = document.getElementById('delete-expense-form');
  if (!deleteForm) return;

  const deleteUrlBase = deleteForm.getAttribute('data-delete-url') || '';
  if (deleteUrlBase) {
    deleteForm.action = `${deleteUrlBase}${expenseId}/delete`;
  }

  const modalTitle = document.getElementById('deleteExpenseModalLabel');
  if (modalTitle) {
    modalTitle.textContent = `Delete Expense: ${expenseName || 'Expense'}`;
  }

  const modalElement = document.getElementById('deleteExpenseModal');
  if (modalElement) {
    const modalInstance = bootstrap.Modal.getInstance(modalElement) || new bootstrap.Modal(modalElement);
    modalInstance.show();
  }
}

function updateBulkDeleteCount(selectedIds) {
  const modalElement = document.getElementById('bulkDeleteExpensesModal');
  const countElement = modalElement?.querySelector('[data-expense-bulk-count]');
  if (countElement) {
    countElement.textContent = `${selectedIds.length}`;
  }
}

function initExpenseDeleteSelected() {
  const deleteButton = document.getElementById('expense-action-delete');
  if (!(deleteButton instanceof HTMLButtonElement)) return;
  if (deleteButton.dataset.listenerAttached === 'true') return;
  deleteButton.dataset.listenerAttached = 'true';

  deleteButton.addEventListener('click', () => {
    const selectedInputs = getSelectedExpenseInputs();
    if (!selectedInputs.length) return;

    if (selectedInputs.length === 1) {
      const [selected] = selectedInputs;
      openExpenseDeleteModal(selected.dataset.expenseId || '', selected.dataset.expenseDescription || 'Expense');
      return;
    }

    const selectedIds = selectedInputs.map((input) => input.value).filter(Boolean);
    if (!selectedIds.length) return;
    updateBulkDeleteCount(selectedIds);
    const modalElement = document.getElementById('bulkDeleteExpensesModal');
    if (modalElement) {
      const modalInstance = bootstrap.Modal.getInstance(modalElement) || new bootstrap.Modal(modalElement);
      modalInstance.show();
    }
  });
}

function initExpenseSelectionActions() {
  if (document.body.dataset.expenseSelectionListener === 'true') return;
  document.body.dataset.expenseSelectionListener = 'true';

  function handleExpenseSelectionChange(event) {
    const { target } = event;
    if (!(target instanceof HTMLInputElement)) return;
    if (target.name === 'expense-select') {
      applyExpenseSelectionState();
      return;
    }

    if (target.id === 'expense-select-all') {
      const shouldCheck = target.checked;
      document.querySelectorAll('input[name="expense-select"]').forEach((input) => {
        if (input instanceof HTMLInputElement) {
          input.checked = shouldCheck;
        }
      });
      applyExpenseSelectionState();
    }
  }

  document.addEventListener('change', handleExpenseSelectionChange);
  document.addEventListener('input', handleExpenseSelectionChange);
}

// --- Month toggles (table) ---
function getMonthRows(monthKey) {
  return Array.from(document.querySelectorAll(`tr[data-expense-month="${monthKey}"]`));
}

function setMonthCollapsedState(dividerRow, monthKey, isCollapsed) {
  const rows = getMonthRows(monthKey);
  rows.forEach((row) => {
    row.classList.toggle('month-hidden', isCollapsed);
  });
  if (dividerRow) {
    dividerRow.dataset.monthCollapsed = isCollapsed ? 'true' : 'false';
    dividerRow.classList.toggle('month-collapsed', isCollapsed);
    const toggleButton = dividerRow.querySelector('[data-month-toggle]');
    if (toggleButton) {
      toggleButton.setAttribute('aria-expanded', String(!isCollapsed));
      const icon = toggleButton.querySelector('i');
      if (icon) {
        icon.classList.toggle('fa-chevron-right', isCollapsed);
        icon.classList.toggle('fa-chevron-down', !isCollapsed);
      }
    }
  }
}

function initExpenseMonthToggles() {
  if (document.body.dataset.expenseMonthToggleListener === 'true') return;
  document.body.dataset.expenseMonthToggleListener = 'true';

  document.addEventListener('click', (event) => {
    const toggleButton = event.target.closest('[data-month-toggle]');
    if (!toggleButton) return;
    const monthKey = toggleButton.dataset.monthToggle || '';
    if (!monthKey) return;
    const dividerRow = toggleButton.closest('tr');
    const currentlyCollapsed = dividerRow?.dataset.monthCollapsed === 'true';
    setMonthCollapsedState(dividerRow, monthKey, !currentlyCollapsed);
  });
}

// --- HTMX re-apply ---
let reapplyAfterHtmxScheduled = false;

function scheduleReapplyAfterHtmx() {
  if (reapplyAfterHtmxScheduled) return;
  reapplyAfterHtmxScheduled = true;

  requestAnimationFrame(() => {
    reapplyAfterHtmxScheduled = false;
    applyExpenseViewPreference();
    initFaviconLoading();
    applyExpenseSelectionState();
    updateExpenseFilterIndicators();
    updateCalendarFilterSummary();
    initExpenseCalendar();
  });
}

function initHtmxIntegration() {
  function maybeReapply(event) {
    const target = event.detail?.target;
    if (target instanceof HTMLElement) {
      if (target.id === 'expense-list-results' || target.querySelector?.('#expense-list-results')) {
        scheduleReapplyAfterHtmx();
        return;
      }
    }

    if (document.getElementById('expense-list-results')) {
      scheduleReapplyAfterHtmx();
    }
  }

  document.addEventListener('htmx:afterSwap', maybeReapply);
  document.addEventListener('htmx:afterSettle', maybeReapply);
}

// --- Init ---
function init() {
  initExpenseTabs();
  initViewToggle();
  initDeleteExpense();
  initFaviconLoading();
  initFilterTagSelector();
  initTagManagerModal();
  initExpenseSelectionActions();
  initExpenseBulkActions();
  initExpenseDeleteSelected();
  initExpenseFilterClear();
  initExpenseMonthToggles();
  applyExpenseSelectionState();
  initHtmxIntegration();
  initExpenseCalendar();
  updateExpenseFilterIndicators();
  updateCalendarFilterSummary();
  syncExpenseFilterFormFromUrl();
  scheduleExpenseStickyOffsetUpdate();

  const filterModal = document.getElementById('expenseFilterModal');
  if (filterModal) {
    filterModal.addEventListener('shown.bs.modal', () => {
      syncExpenseFilterFormFromUrl();
    });
  }

  window.addEventListener('popstate', () => {
    updateExpenseFilterIndicators();
    syncExpenseFilterFormFromUrl();
  });

  window.addEventListener('resize', scheduleExpenseStickyOffsetUpdate);
}

document.addEventListener('DOMContentLoaded', init);
