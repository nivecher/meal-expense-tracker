import { initializeRobustFaviconHandling } from '../utils/robust-favicon-handler.js';
import { toast } from '../utils/notifications.js';

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

function getStoredPreference(storageKey, cookieKey) {
  try {
    const localValue = localStorage.getItem(storageKey);
    if (localValue) return localValue;
  } catch {}

  return getCookieValue(cookieKey);
}

function persistPreference(storageKey, cookieKey, value) {
  try {
    localStorage.setItem(storageKey, value);
  } catch {}

  setCookieValue(cookieKey, value);
}

function getCsrfToken() {
  const metaToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
  if (metaToken) return metaToken;
  const inputToken = document.querySelector('input[name="csrf_token"]');
  return inputToken ? inputToken.value : '';
}

let stickyOffsetUpdateScheduled = false;

function updateMerchantTableStickyOffsets() {
  const stickyRoot = document.querySelector('#table-view-container .table-sticky-frozen');
  if (!stickyRoot) return;

  const toolbar = stickyRoot.querySelector('.table-actions-toolbar');
  const toolbarHeightPx = toolbar ? Math.ceil(toolbar.getBoundingClientRect().height) : 0;
  stickyRoot.style.setProperty('--sticky-header-top', `${toolbarHeightPx}px`);
}

function scheduleMerchantStickyOffsetUpdate() {
  if (stickyOffsetUpdateScheduled) return;
  stickyOffsetUpdateScheduled = true;
  requestAnimationFrame(() => {
    stickyOffsetUpdateScheduled = false;
    updateMerchantTableStickyOffsets();
  });
}

function applyMerchantViewPreference() {
  const cardView = document.getElementById('card-view');
  const tableView = document.getElementById('table-view');
  const cardViewContainer = document.getElementById('card-view-container');
  const tableViewContainer = document.getElementById('table-view-container');

  if (!cardView || !tableView || !cardViewContainer || !tableViewContainer) {
    return;
  }

  const storedView = getStoredPreference('merchantViewPreference', 'merchant_view_preference');
  const inferredView = tableView.checked ? 'table' : 'card';
  const view = storedView === 'table' || storedView === 'card' ? storedView : inferredView;
  persistPreference('merchantViewPreference', 'merchant_view_preference', view);

  if (view === 'table') {
    tableView.checked = true;
    cardView.checked = false;
    cardViewContainer.classList.add('d-none');
    tableViewContainer.classList.remove('d-none');
    scheduleMerchantStickyOffsetUpdate();
    return;
  }

  cardView.checked = true;
  tableView.checked = false;
  cardViewContainer.classList.remove('d-none');
  tableViewContainer.classList.add('d-none');
}

function initViewToggle() {
  const cardView = document.getElementById('card-view');
  const tableView = document.getElementById('table-view');

  if (!cardView || !tableView) {
    return;
  }

  if (cardView.dataset.listenerAttached === 'true') {
    applyMerchantViewPreference();
    return;
  }

  cardView.dataset.listenerAttached = 'true';
  tableView.dataset.listenerAttached = 'true';

  cardView.addEventListener('change', () => {
    if (!cardView.checked) return;
    persistPreference('merchantViewPreference', 'merchant_view_preference', 'card');
    applyMerchantViewPreference();
  });

  tableView.addEventListener('change', () => {
    if (!tableView.checked) return;
    persistPreference('merchantViewPreference', 'merchant_view_preference', 'table');
    applyMerchantViewPreference();
  });

  applyMerchantViewPreference();
}

function initFaviconLoading() {
  initializeRobustFaviconHandling('.restaurant-favicon');
  initializeRobustFaviconHandling('.restaurant-favicon-table');
}

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

function getSelectedMerchantInputs() {
  return Array.from(document.querySelectorAll('input[name="merchant-select"]:checked'));
}

function getSelectedMerchantIds() {
  return getSelectedMerchantInputs()
    .map((input) => input.value)
    .filter(Boolean);
}

function updateMerchantRowSelectionHighlight() {
  document.querySelectorAll('input[name="merchant-select"]').forEach((input) => {
    if (!(input instanceof HTMLInputElement)) return;
    const row = input.closest('tr');
    if (!row) return;
    const selected = input.checked;
    row.classList.toggle('is-selected', selected);
    row.setAttribute('aria-selected', String(selected));
  });
}

function updateMerchantSelectionStatus(selectedCount) {
  const status = document.getElementById('merchant-selection-status');
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

function updateMerchantActionToolbar(selectedInputs) {
  const viewLink = document.getElementById('merchant-action-view');
  const editLink = document.getElementById('merchant-action-edit');
  const deleteButton = document.getElementById('merchant-action-delete');

  if (!selectedInputs.length) {
    setActionAnchorState(viewLink, '', false);
    setActionAnchorState(editLink, '', false);
    if (deleteButton) {
      deleteButton.disabled = true;
      deleteButton.removeAttribute('data-delete-url');
      deleteButton.removeAttribute('data-merchant-name');
    }
    return;
  }

  if (deleteButton) {
    deleteButton.disabled = false;
    deleteButton.removeAttribute('data-delete-url');
    deleteButton.removeAttribute('data-merchant-name');
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
    deleteButton.dataset.deleteUrl = selectedInput.dataset.deleteUrl || '';
    deleteButton.dataset.merchantName = selectedInput.dataset.merchantName || '';
  }
}

function updateMerchantBulkActions(selectedInputs) {
  const bulkExportButton = document.querySelector('[data-merchant-bulk-export]');
  const hasSelection = selectedInputs.length > 0;
  if (bulkExportButton instanceof HTMLButtonElement) {
    bulkExportButton.disabled = !hasSelection;
  }
}

function applyMerchantSelectionState() {
  const selectedInputs = getSelectedMerchantInputs();
  updateMerchantRowSelectionHighlight();
  updateMerchantSelectionStatus(selectedInputs.length);
  updateMerchantActionToolbar(selectedInputs);
  updateMerchantBulkActions(selectedInputs);

  const selectAll = document.getElementById('merchant-select-all');
  if (selectAll instanceof HTMLInputElement) {
    const total = document.querySelectorAll('input[name="merchant-select"]').length;
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

function initMerchantSelectionActions() {
  if (document.body.dataset.merchantSelectionListener === 'true') return;
  document.body.dataset.merchantSelectionListener = 'true';

  function handleMerchantSelectionChange(event) {
    const { target } = event;
    if (!(target instanceof HTMLInputElement)) return;
    if (target.name === 'merchant-select') {
      applyMerchantSelectionState();
      return;
    }

    if (target.id === 'merchant-select-all') {
      const shouldCheck = target.checked;
      document.querySelectorAll('input[name="merchant-select"]').forEach((input) => {
        if (input instanceof HTMLInputElement) {
          input.checked = shouldCheck;
        }
      });
      applyMerchantSelectionState();
    }
  }

  document.addEventListener('change', handleMerchantSelectionChange);
  document.addEventListener('input', handleMerchantSelectionChange);
}

function initMerchantRowClickSelection() {
  if (document.body.dataset.merchantRowClickListener === 'true') return;
  document.body.dataset.merchantRowClickListener = 'true';

  document.addEventListener('click', (event) => {
    const { target } = event;
    if (!(target instanceof Element)) return;

    if (target.closest('input, a, button, label, select, textarea')) return;

    const row = target.closest('#merchantTable tbody tr');
    if (!row || row.dataset.dividerRow === 'true') return;

    const checkbox = row.querySelector('input[name="merchant-select"]');
    if (!(checkbox instanceof HTMLInputElement)) return;

    checkbox.checked = !checkbox.checked;
    applyMerchantSelectionState();
  });
}

function cleanupModalBackdrop() {
  const backdrops = document.querySelectorAll('.modal-backdrop');
  backdrops.forEach((backdrop) => {
    backdrop.remove();
  });
  document.body.classList.remove('modal-open');
  document.body.style.overflow = '';
  document.body.style.paddingRight = '';
}

function openMerchantDeleteModal(deleteUrl, merchantName) {
  if (!deleteUrl) return;

  const merchantNameElement = document.getElementById('merchantName');
  const deleteForm = document.getElementById('deleteMerchantForm');
  if (merchantNameElement) {
    merchantNameElement.textContent = merchantName || '';
  }
  if (deleteForm instanceof HTMLFormElement) {
    deleteForm.action = deleteUrl;
  }

  const modalElement = document.getElementById('deleteMerchantModal');
  if (modalElement) {
    const modalInstance = bootstrap.Modal.getInstance(modalElement) || new bootstrap.Modal(modalElement);
    modalInstance.show();
  }
}

async function performBulkMerchantDelete(selectedInputs) {
  if (!selectedInputs.length) return;
  const csrfToken = getCsrfToken();
  try {
    const requests = selectedInputs
      .map((input) => input.dataset.deleteUrl || '')
      .filter(Boolean)
      .map((deleteUrl) =>
        fetch(deleteUrl, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': csrfToken,
          },
          body: JSON.stringify({ csrf_token: csrfToken }),
        }),
      );

    if (!requests.length) return;
    const results = await Promise.all(requests);
    const failed = results.filter((response) => !response.ok);
    if (failed.length) {
      toast.error('Some merchants could not be deleted. Please retry.');
      return;
    }
    toast.success('Selected merchants deleted.');
    window.location.reload();
  } catch {}
}

function initMerchantDeleteFlow() {
  const deleteForm = document.getElementById('deleteMerchantForm');
  if (deleteForm instanceof HTMLFormElement && deleteForm.dataset.listenerAttached !== 'true') {
    deleteForm.dataset.listenerAttached = 'true';
    deleteForm.addEventListener('submit', async(event) => {
      event.preventDefault();
      const deleteUrl = deleteForm.action;
      if (!deleteUrl) return;
      try {
        const response = await fetch(deleteUrl, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
        });
        const data = await response.json();
        if (!response.ok || data.status !== 'success') {
          toast.error(data.message || 'Failed to delete merchant');
          return;
        }

        const modalElement = document.getElementById('deleteMerchantModal');
        const modalInstance = modalElement
          ? bootstrap.Modal.getInstance(modalElement) || new bootstrap.Modal(modalElement)
          : null;
        modalInstance?.hide();
        if (modalElement) {
          modalElement.addEventListener('hidden.bs.modal', cleanupModalBackdrop, { once: true });
        }
        toast.success('Merchant deleted.');
        window.location.reload();
      } catch {}
    });
  }

  document.addEventListener('click', (event) => {
    const { target } = event;
    if (!(target instanceof Element)) return;

    const cardDeleteAction = target.closest('#card-view-container [data-delete-url]');
    if (cardDeleteAction) {
      event.preventDefault();
      const deleteUrl = cardDeleteAction.getAttribute('data-delete-url') || '';
      const merchantName = cardDeleteAction.getAttribute('data-merchant-name') || '';
      openMerchantDeleteModal(deleteUrl, merchantName);
      return;
    }

    const deleteButton = target.closest('#merchant-action-delete');
    if (deleteButton instanceof HTMLButtonElement) {
      const selectedInputs = getSelectedMerchantInputs();
      if (!selectedInputs.length) return;

      if (selectedInputs.length === 1) {
        const [selected] = selectedInputs;
        openMerchantDeleteModal(selected.dataset.deleteUrl || '', selected.dataset.merchantName || '');
        return;
      }

      const bulkModalElement = document.getElementById('bulkDeleteMerchantsModal');
      const countElement = bulkModalElement?.querySelector('[data-merchant-bulk-count]');
      if (countElement) {
        countElement.textContent = `${selectedInputs.length}`;
      }
      if (bulkModalElement) {
        const bulkModal = bootstrap.Modal.getInstance(bulkModalElement) || new bootstrap.Modal(bulkModalElement);
        bulkModal.show();
      }
      return;
    }

    const bulkConfirmButton = target.closest('[data-merchant-bulk-confirm]');
    if (!(bulkConfirmButton instanceof HTMLButtonElement)) return;
    const selectedInputs = getSelectedMerchantInputs();
    performBulkMerchantDelete(selectedInputs);
  });
}

function initMerchantBulkExport() {
  const bulkExportButton = document.querySelector('[data-merchant-bulk-export]');
  if (!(bulkExportButton instanceof HTMLButtonElement)) return;

  bulkExportButton.addEventListener('click', () => {
    const selectedIds = getSelectedMerchantIds();
    if (!selectedIds.length) return;
    const exportUrl = bulkExportButton.dataset.exportUrl || '';
    if (!exportUrl) return;
    const url = new URL(exportUrl, window.location.origin);
    url.searchParams.set('format', 'csv');
    url.searchParams.set('ids', selectedIds.join(','));
    window.location.assign(url.toString());
  });
}

function getAlphaRows(alphaLabel) {
  return Array.from(document.querySelectorAll(`tr[data-merchant-alpha-group="${CSS.escape(alphaLabel)}"]`));
}

function getCategoryRows(categoryLabel) {
  return Array.from(document.querySelectorAll(`tr[data-merchant-category-group="${CSS.escape(categoryLabel)}"]`));
}

function setAlphaCollapsedState(dividerRow, alphaLabel, isCollapsed) {
  const rows = getAlphaRows(alphaLabel);
  rows.forEach((row) => {
    row.classList.toggle('alpha-hidden', isCollapsed);
  });
  if (!dividerRow) return;

  dividerRow.dataset.alphaCollapsed = isCollapsed ? 'true' : 'false';
  dividerRow.classList.toggle('alpha-collapsed', isCollapsed);
  const toggleButton = dividerRow.querySelector('[data-alpha-toggle]');
  if (toggleButton) {
    toggleButton.setAttribute('aria-expanded', String(!isCollapsed));
    const icon = toggleButton.querySelector('i');
    if (icon) {
      icon.classList.toggle('fa-chevron-right', isCollapsed);
      icon.classList.toggle('fa-chevron-down', !isCollapsed);
    }
  }
}

function setCategoryCollapsedState(dividerRow, categoryLabel, isCollapsed) {
  const rows = getCategoryRows(categoryLabel);
  rows.forEach((row) => {
    row.classList.toggle('city-hidden', isCollapsed);
  });
  if (!dividerRow) return;

  dividerRow.dataset.merchantCategoryCollapsed = isCollapsed ? 'true' : 'false';
  dividerRow.classList.toggle('city-collapsed', isCollapsed);
  const toggleButton = dividerRow.querySelector('[data-merchant-category-toggle]');
  if (toggleButton) {
    toggleButton.setAttribute('aria-expanded', String(!isCollapsed));
    const icon = toggleButton.querySelector('i');
    if (icon) {
      icon.classList.toggle('fa-chevron-right', isCollapsed);
      icon.classList.toggle('fa-chevron-down', !isCollapsed);
    }
  }
}

function initMerchantGroupToggles() {
  if (document.body.dataset.merchantGroupToggleListener === 'true') return;
  document.body.dataset.merchantGroupToggleListener = 'true';

  document.addEventListener('click', (event) => {
    const { target } = event;
    if (!(target instanceof Element)) return;

    const alphaToggle = target.closest('[data-alpha-toggle]');
    if (alphaToggle) {
      const alphaLabel = alphaToggle.getAttribute('data-alpha-toggle') || '';
      if (!alphaLabel) return;
      const dividerRow = alphaToggle.closest('tr');
      const currentlyCollapsed = dividerRow?.dataset.alphaCollapsed === 'true';
      setAlphaCollapsedState(dividerRow, alphaLabel, !currentlyCollapsed);
      return;
    }

    const categoryToggle = target.closest('[data-merchant-category-toggle]');
    if (!categoryToggle) return;
    const categoryLabel = categoryToggle.getAttribute('data-merchant-category-toggle') || '';
    if (!categoryLabel) return;
    const dividerRow = categoryToggle.closest('tr');
    const currentlyCollapsed = dividerRow?.dataset.merchantCategoryCollapsed === 'true';
    setCategoryCollapsedState(dividerRow, categoryLabel, !currentlyCollapsed);
  });
}

function init() {
  initViewToggle();
  initFaviconLoading();
  initMerchantSelectionActions();
  initMerchantRowClickSelection();
  initMerchantBulkExport();
  initMerchantDeleteFlow();
  initMerchantGroupToggles();
  applyMerchantSelectionState();
  scheduleMerchantStickyOffsetUpdate();

  window.addEventListener('resize', scheduleMerchantStickyOffsetUpdate);
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}
