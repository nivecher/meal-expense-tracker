/**
 * Restaurant List Component
 * Handles view toggling, pagination, table sorting, and delete functionality
 */

import { initializeRobustFaviconHandling } from '../utils/robust-favicon-handler.js';
import { toast } from '../utils/notifications.js';
import { PlacesMapView } from '../components/places-map-view.js';

function ensureAddToMyRestaurantsHandler() {
  if (typeof window.addToMyRestaurants === 'function') {
    return;
  }

  window.addToMyRestaurants = async function addToMyRestaurants(placeId) {
    try {
      if (!placeId || placeId === 'null' || placeId === 'undefined') {
        throw new Error(`Invalid place ID: ${placeId}`);
      }

      const configElement = document.getElementById('places-map-config');
      const mapConfig = configElement ? JSON.parse(configElement.textContent) : {};
      const csrfToken = mapConfig.csrfToken || '';
      const addRestaurantUrl = mapConfig.addRestaurantUrl || '';

      if (!csrfToken || !addRestaurantUrl) {
        throw new Error('Missing configuration for restaurant addition');
      }

      toast.info('Adding restaurant to your list...');

      const detailsResponse = await fetch(`/restaurants/api/places/details/${placeId}?include_enterprise=false`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!detailsResponse.ok) {
        throw new Error(`Failed to get restaurant details: ${detailsResponse.status}`);
      }

      const restaurantData = await detailsResponse.json();

      const requestData = {
        name: restaurantData.name || '',
        type: restaurantData.type || 'restaurant',
        description: restaurantData.description || '',
        address_line_1: restaurantData.address_line_1 || '',
        address_line_2: restaurantData.address_line_2 || '',
        city: restaurantData.city || '',
        state: restaurantData.state || '',
        postal_code: restaurantData.postal_code || '',
        country: restaurantData.country || '',
        phone: restaurantData.phone || '',
        website: restaurantData.website || '',
        email: restaurantData.email || '',
        google_place_id: restaurantData.google_place_id || '',
        cuisine: restaurantData.cuisine || '',
        service_level: restaurantData.service_level || '',
        price_level: restaurantData.price_level ?? null,
        is_chain: restaurantData.is_chain ? true : false,
        rating: restaurantData.rating || '',
        notes: restaurantData.notes || '',
        latitude: restaurantData.latitude ?? null,
        longitude: restaurantData.longitude ?? null,
      };

      const addResponse = await fetch(addRestaurantUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken,
          'X-Requested-With': 'XMLHttpRequest',
        },
        body: JSON.stringify(requestData),
      });

      const responseData = await addResponse.json();

      if (addResponse.status === 200 || addResponse.status === 201) {
        toast.success('Restaurant added to your list!');
        return {
          success: true,
          exists: false,
          restaurantId: responseData?.restaurant_id || null,
        };
      }

      if (addResponse.status === 409) {
        toast.warning(responseData.message || 'Restaurant already exists in your list.');
        return {
          success: false,
          exists: true,
          restaurantId: responseData?.restaurant_id || null,
        };
      }

      throw new Error(responseData.message || 'Failed to add restaurant');
    } catch (error) {
      toast.error(error?.message || 'Failed to add restaurant');
      throw error;
    }
  };
}

function getActiveRestaurantFilterCount() {
  const urlParams = new URLSearchParams(window.location.search);
  let count = 0;

  const cuisine = urlParams.get('cuisine');
  if (cuisine && cuisine !== 'None') {
    count += 1;
  }

  const serviceLevel = urlParams.get('service_level');
  if (serviceLevel && serviceLevel !== 'None') {
    count += 1;
  }

  const city = urlParams.get('city');
  if (city && city !== 'None') {
    count += 1;
  }

  const isChain = urlParams.get('is_chain');
  if (isChain && isChain !== 'None') {
    count += 1;
  }

  const ratingMin = urlParams.get('rating_min');
  if (ratingMin && ratingMin !== 'None') {
    count += 1;
  }

  const ratingMax = urlParams.get('rating_max');
  if (ratingMax && ratingMax !== 'None') {
    count += 1;
  }

  return count;
}

function updateRestaurantFilterIndicators() {
  const count = getActiveRestaurantFilterCount();

  const filterButton = document.getElementById('restaurant-filter-button');
  const filterCountBadge = document.getElementById('restaurant-filter-count');
  if (filterButton) {
    if (count > 0) {
      filterButton.classList.remove('btn-outline-secondary');
      filterButton.classList.add('btn-primary');
      filterButton.setAttribute('title', `${count} filters active`);
    } else {
      filterButton.classList.remove('btn-primary');
      filterButton.classList.add('btn-outline-secondary');
      filterButton.setAttribute('title', 'Filter restaurants');
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

  const statusCount = document.getElementById('restaurant-filter-status-count');
  const statusText = document.getElementById('restaurant-filter-status-text');
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
  select.value = value || '';
}

function setInputValue(inputId, value) {
  const input = document.getElementById(inputId);
  if (!input) return;
  input.value = value || '';
}

function clearRestaurantFilters() {
  setSelectValue('cuisine', '');
  setSelectValue('service_level', '');
  setSelectValue('city', '');
  setSelectValue('is_chain', '');
  setInputValue('rating_min', '');
  setInputValue('rating_max', '');

  const form = document.getElementById('restaurant-filter-form');
  if (form?.requestSubmit) {
    form.requestSubmit();
  } else if (form) {
    form.dispatchEvent(new Event('submit', { cancelable: true }));
  }
}

function initRestaurantFilterClear() {
  const clearButton = document.getElementById('restaurant-filter-clear');
  if (!clearButton) return;
  clearButton.addEventListener('click', () => {
    clearRestaurantFilters();
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

function getSelectedRestaurantInputs() {
  return Array.from(document.querySelectorAll('input[name="restaurant-select"]:checked'));
}

function getSelectedRestaurantIds() {
  return getSelectedRestaurantInputs()
    .map((input) => input.value)
    .filter(Boolean);
}

let stickyOffsetUpdateScheduled = false;

function updateRestaurantTableStickyOffsets() {
  const stickyRoot = document.querySelector('#table-view-container .table-sticky-frozen');
  if (!stickyRoot) return;

  const toolbar = stickyRoot.querySelector('.table-actions-toolbar');
  const toolbarHeightPx = toolbar ? Math.ceil(toolbar.getBoundingClientRect().height) : 0;
  stickyRoot.style.setProperty('--sticky-header-top', `${toolbarHeightPx}px`);
}

function scheduleRestaurantStickyOffsetUpdate() {
  if (stickyOffsetUpdateScheduled) return;
  stickyOffsetUpdateScheduled = true;
  requestAnimationFrame(() => {
    stickyOffsetUpdateScheduled = false;
    updateRestaurantTableStickyOffsets();
  });
}

function updateRestaurantRowSelectionHighlight() {
  document.querySelectorAll('input[name="restaurant-select"]').forEach((input) => {
    if (!(input instanceof HTMLInputElement)) return;
    const row = input.closest('tr');
    if (!row) return;
    const selected = input.checked;
    row.classList.toggle('is-selected', selected);
    row.setAttribute('aria-selected', String(selected));
  });
}

function updateRestaurantSelectionStatus(selectedCount) {
  const status = document.getElementById('restaurant-selection-status');
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

function updateRestaurantBulkActions(selectedInputs) {
  const bulkExportButton = document.querySelector('[data-restaurant-bulk-export]');
  const hasSelection = selectedInputs.length > 0;
  if (bulkExportButton instanceof HTMLButtonElement) {
    bulkExportButton.disabled = !hasSelection;
  }
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

function updateRestaurantActionToolbar(selectedInputs) {
  const addExpenseLink = document.getElementById('restaurant-action-add-expense');
  const viewLink = document.getElementById('restaurant-action-view');
  const editLink = document.getElementById('restaurant-action-edit');
  const deleteButton = document.getElementById('restaurant-action-delete');

  if (!selectedInputs.length) {
    setActionAnchorState(addExpenseLink, '', false);
    setActionAnchorState(viewLink, '', false);
    setActionAnchorState(editLink, '', false);
    if (deleteButton) {
      deleteButton.disabled = true;
      deleteButton.removeAttribute('data-restaurant-id');
      deleteButton.removeAttribute('data-restaurant-name');
    }
    return;
  }

  if (deleteButton) {
    deleteButton.disabled = false;
    deleteButton.removeAttribute('data-restaurant-id');
    deleteButton.removeAttribute('data-restaurant-name');
  }

  if (selectedInputs.length !== 1) {
    // Multi-select: only delete/export should be enabled.
    setActionAnchorState(addExpenseLink, '', false);
    setActionAnchorState(viewLink, '', false);
    setActionAnchorState(editLink, '', false);
    return;
  }

  const [selectedInput] = selectedInputs;
  const addExpenseUrl = selectedInput.dataset.addExpenseUrl || '';
  const viewUrl = selectedInput.dataset.viewUrl || '';
  const editUrl = selectedInput.dataset.editUrl || '';
  setActionAnchorState(addExpenseLink, addExpenseUrl, Boolean(addExpenseUrl));
  setActionAnchorState(viewLink, viewUrl, Boolean(viewUrl));
  setActionAnchorState(editLink, editUrl, Boolean(editUrl));

  if (deleteButton) {
    deleteButton.dataset.restaurantId = selectedInput.dataset.restaurantId || '';
    deleteButton.dataset.restaurantName = selectedInput.dataset.restaurantName || '';
  }
}

function applyRestaurantSelectionState() {
  const selectedInputs = getSelectedRestaurantInputs();
  updateRestaurantRowSelectionHighlight();
  updateRestaurantSelectionStatus(selectedInputs.length);
  updateRestaurantActionToolbar(selectedInputs);
  updateRestaurantBulkActions(selectedInputs);
  scheduleRestaurantStickyOffsetUpdate();

  const selectAll = document.getElementById('restaurant-select-all');
  if (selectAll instanceof HTMLInputElement) {
    const total = document.querySelectorAll('input[name="restaurant-select"]').length;
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

function initRestaurantSelectionActions() {
  if (document.body.dataset.restaurantSelectionListener === 'true') return;
  document.body.dataset.restaurantSelectionListener = 'true';

  function handleRestaurantSelectionChange(event) {
    const { target } = event;
    if (!(target instanceof HTMLInputElement)) return;
    if (target.name === 'restaurant-select') {
      applyRestaurantSelectionState();
      return;
    }

    if (target.id === 'restaurant-select-all') {
      const shouldCheck = target.checked;
      document.querySelectorAll('input[name="restaurant-select"]').forEach((input) => {
        if (input instanceof HTMLInputElement) {
          input.checked = shouldCheck;
        }
      });
      applyRestaurantSelectionState();
    }
  }

  document.addEventListener('change', handleRestaurantSelectionChange);
  document.addEventListener('input', handleRestaurantSelectionChange);
}

function initRestaurantRowClickSelection() {
  if (document.body.dataset.restaurantRowClickListener === 'true') return;
  document.body.dataset.restaurantRowClickListener = 'true';

  document.addEventListener('click', (event) => {
    const { target } = event;
    if (!(target instanceof Element)) return;

    if (target.closest('input, a, button, label, select, textarea')) return;

    const row = target.closest('#restaurantTable tbody tr');
    if (!row || row.dataset.dividerRow === 'true') return;

    const checkbox = row.querySelector('input[name="restaurant-select"]');
    if (!(checkbox instanceof HTMLInputElement)) return;

    checkbox.checked = !checkbox.checked;
    applyRestaurantSelectionState();
  });
}

function getCityRows(cityLabel) {
  return Array.from(document.querySelectorAll(`tr[data-restaurant-city-group="${CSS.escape(cityLabel)}"]`));
}

function getAlphaRows(alphaLabel) {
  return Array.from(document.querySelectorAll(`tr[data-restaurant-alpha-group="${CSS.escape(alphaLabel)}"]`));
}

function setCityCollapsedState(dividerRow, cityLabel, isCollapsed) {
  const rows = getCityRows(cityLabel);
  rows.forEach((row) => {
    row.classList.toggle('city-hidden', isCollapsed);
  });
  if (!dividerRow) return;

  dividerRow.dataset.cityCollapsed = isCollapsed ? 'true' : 'false';
  dividerRow.classList.toggle('city-collapsed', isCollapsed);
  const toggleButton = dividerRow.querySelector('[data-city-toggle]');
  if (toggleButton) {
    toggleButton.setAttribute('aria-expanded', String(!isCollapsed));
    const icon = toggleButton.querySelector('i');
    if (icon) {
      icon.classList.toggle('fa-chevron-right', isCollapsed);
      icon.classList.toggle('fa-chevron-down', !isCollapsed);
    }
  }
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

function initRestaurantCityToggles() {
  if (document.body.dataset.restaurantCityToggleListener === 'true') return;
  document.body.dataset.restaurantCityToggleListener = 'true';

  document.addEventListener('click', (event) => {
    const { target } = event;
    if (!(target instanceof Element)) return;

    const cityToggleButton = target.closest('[data-city-toggle]');
    if (cityToggleButton) {
      const cityLabel = cityToggleButton.dataset.cityToggle || '';
      if (!cityLabel) return;
      const dividerRow = cityToggleButton.closest('tr');
      const currentlyCollapsed = dividerRow?.dataset.cityCollapsed === 'true';
      setCityCollapsedState(dividerRow, cityLabel, !currentlyCollapsed);
      return;
    }

    const alphaToggleButton = target.closest('[data-alpha-toggle]');
    if (!alphaToggleButton) return;
    const alphaLabel = alphaToggleButton.dataset.alphaToggle || '';
    if (!alphaLabel) return;
    const dividerRow = alphaToggleButton.closest('tr');
    const currentlyCollapsed = dividerRow?.dataset.alphaCollapsed === 'true';
    setAlphaCollapsedState(dividerRow, alphaLabel, !currentlyCollapsed);
  });
}

// Helper function to clean up modal backdrop
function buildRestaurantDeleteUrl(baseUrl, restaurantId) {
  if (!baseUrl || !restaurantId) return '';
  let normalizedBase = baseUrl;
  if (normalizedBase.endsWith('/')) normalizedBase = normalizedBase.slice(0, -1);
  return `${normalizedBase}/${restaurantId}`;
}

function openRestaurantBulkDeleteModal(selectedIds) {
  const modalElement = document.getElementById('bulkDeleteRestaurantsModal');
  const countElement = modalElement?.querySelector('[data-restaurant-bulk-count]');
  if (countElement) {
    countElement.textContent = `${selectedIds.length}`;
  }
  if (modalElement) {
    const modalInstance = new bootstrap.Modal(modalElement);
    modalInstance.show();
  }
}

function ensureDeleteRestaurantModal() {
  const existing = document.getElementById('deleteRestaurantModal');
  if (existing) return existing;

  const template = document.getElementById('deleteRestaurantModalTemplate');
  if (!(template instanceof HTMLTemplateElement)) return null;

  const modalNode = template.content.firstElementChild?.cloneNode(true);
  if (!(modalNode instanceof HTMLElement)) return null;

  document.body.appendChild(modalNode);

  const deleteForm = modalNode.querySelector('#deleteRestaurantForm');
  if (deleteForm instanceof HTMLFormElement && deleteForm.dataset.listenerAttached !== 'true') {
    deleteForm.dataset.listenerAttached = 'true';
    deleteForm.addEventListener('submit', () => {
      const submitButton = deleteForm.querySelector('button[type="submit"]');
      if (submitButton) {
        submitButton.disabled = true;
        submitButton.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Deleting...';
      }
    });
  }

  modalNode.addEventListener('hidden.bs.modal', () => {
    modalNode.remove();
  });

  return modalNode;
}

function openRestaurantDeleteModal(restaurantId, restaurantName) {
  if (!restaurantId) return;

  const modalElement = ensureDeleteRestaurantModal();
  if (!modalElement) return;

  const modalTitle = modalElement.querySelector('#deleteRestaurantModalLabel');
  const restaurantNameElement = modalElement.querySelector('#restaurantName');
  const deleteForm = modalElement.querySelector('#deleteRestaurantForm');

  if (modalTitle) {
    modalTitle.textContent = `Delete Restaurant: ${restaurantName || ''}`;
  }

  if (restaurantNameElement) {
    restaurantNameElement.textContent = restaurantName || '';
  }

  if (deleteForm) {
    const deleteUrlBase = deleteForm.getAttribute('data-delete-url') || '';
    const deleteUrl = buildRestaurantDeleteUrl(deleteUrlBase, restaurantId);
    if (deleteUrl) {
      deleteForm.action = deleteUrl;
    }
  }

  const modalInstance = bootstrap.Modal.getInstance(modalElement) || new bootstrap.Modal(modalElement);
  modalInstance.show();
}

async function performBulkRestaurantDelete(restaurantIds) {
  const csrfToken = getCsrfToken();
  if (!restaurantIds.length) return;
  const requests = restaurantIds.map((restaurantId) =>
    fetch(`/restaurants/delete/${restaurantId}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Requested-With': 'XMLHttpRequest',
        'X-CSRFToken': csrfToken,
      },
      body: JSON.stringify({ csrf_token: csrfToken }),
    }),
  );
  try {
    const results = await Promise.all(requests);
    const failed = results.filter((response) => !response.ok);
    if (failed.length) {
      toast.error('Some restaurants could not be deleted. Please retry.');
      return;
    }
    toast.success('Selected restaurants deleted.');
    window.location.reload();
  } catch {}
}

function initRestaurantBulkActions() {
  const bulkExportButton = document.querySelector('[data-restaurant-bulk-export]');
  if (bulkExportButton instanceof HTMLButtonElement) {
    bulkExportButton.addEventListener('click', () => {
      const selectedIds = getSelectedRestaurantIds();
      if (!selectedIds.length) return;
      const exportUrl = bulkExportButton.dataset.exportUrl || '';
      if (!exportUrl) return;
      const url = new URL(exportUrl, window.location.origin);
      url.searchParams.set('format', 'csv');
      url.searchParams.set('ids', selectedIds.join(','));
      window.location.assign(url.toString());
    });
  }

  const bulkConfirmButton = document.querySelector('[data-restaurant-bulk-confirm]');
  if (bulkConfirmButton instanceof HTMLButtonElement) {
    bulkConfirmButton.addEventListener('click', () => {
      const selectedIds = getSelectedRestaurantIds();
      if (!selectedIds.length) return;
      performBulkRestaurantDelete(selectedIds);
    });
  }
}

function initRestaurantDeleteSelected() {
  const deleteButton = document.getElementById('restaurant-action-delete');
  if (!(deleteButton instanceof HTMLButtonElement)) return;
  if (deleteButton.dataset.listenerAttached === 'true') return;
  deleteButton.dataset.listenerAttached = 'true';

  deleteButton.addEventListener('click', () => {
    const selectedInputs = getSelectedRestaurantInputs();
    if (!selectedInputs.length) return;

    if (selectedInputs.length === 1) {
      const [selected] = selectedInputs;
      openRestaurantDeleteModal(selected.dataset.restaurantId || '', selected.dataset.restaurantName || '');
      return;
    }

    const selectedIds = selectedInputs.map((input) => input.value).filter(Boolean);
    if (!selectedIds.length) return;
    openRestaurantBulkDeleteModal(selectedIds);
  });
}

function applyRestaurantViewPreference() {
  const cardView = document.getElementById('card-view');
  const tableView = document.getElementById('table-view');
  const cardViewContainer = document.getElementById('card-view-container');
  const tableViewContainer = document.getElementById('table-view-container');

  if (!cardView || !tableView || !cardViewContainer || !tableViewContainer) {
    return;
  }

  const storedView = getStoredPreference('restaurantViewPreference', 'restaurant_view_preference');
  const inferredView = tableView.checked ? 'table' : 'card';
  const view = storedView === 'table' || storedView === 'card' ? storedView : inferredView;
  persistPreference('restaurantViewPreference', 'restaurant_view_preference', view);

  if (view === 'table') {
    tableView.checked = true;
    cardView.checked = false;
    cardViewContainer.classList.add('d-none');
    tableViewContainer.classList.remove('d-none');
    scheduleRestaurantStickyOffsetUpdate();
    return;
  }

  cardView.checked = true;
  tableView.checked = false;
  cardViewContainer.classList.remove('d-none');
  tableViewContainer.classList.add('d-none');
}

// View toggle functionality
function initViewToggle() {
  const cardView = document.getElementById('card-view');
  const tableView = document.getElementById('table-view');

  if (!cardView || !tableView) {
    return;
  }

  if (cardView.dataset.listenerAttached === 'true') {
    applyRestaurantViewPreference();
    return;
  }

  // Add event listeners for view toggle
  cardView.dataset.listenerAttached = 'true';
  tableView.dataset.listenerAttached = 'true';

  cardView.addEventListener('change', () => {
    if (!cardView.checked) return;
    persistPreference('restaurantViewPreference', 'restaurant_view_preference', 'card');
    applyRestaurantViewPreference();
  });

  tableView.addEventListener('change', () => {
    if (!tableView.checked) return;
    persistPreference('restaurantViewPreference', 'restaurant_view_preference', 'table');
    applyRestaurantViewPreference();
  });

  applyRestaurantViewPreference();
}

// Delete restaurant functionality - optimized with event delegation
function initDeleteRestaurant() {
  const template = document.getElementById('deleteRestaurantModalTemplate');
  if (!template) return;
  if (template.dataset.listenerAttached === 'true') return;
  template.dataset.listenerAttached = 'true';

  document.addEventListener('click', (event) => {
    const { target } = event;
    if (!(target instanceof Element)) return;

    const button = target.closest('[data-action="delete-restaurant"][data-restaurant-id]');
    if (!button) return;

    event.preventDefault();
    event.stopPropagation();
    event.stopImmediatePropagation();
    const restaurantId = button.getAttribute('data-restaurant-id') || '';
    const restaurantName = button.getAttribute('data-restaurant-name') || '';
    openRestaurantDeleteModal(restaurantId, restaurantName);
  });
}

// Favicon loading functionality - optimized for performance
function initFaviconLoading() {
  // Defer favicon loading to avoid blocking the main thread
  const loadFaviconsWhenIdle = () => {
    initializeRobustFaviconHandling('.restaurant-favicon');
    initializeRobustFaviconHandling('.restaurant-favicon-table');
  };

  // Use requestIdleCallback if available, otherwise setTimeout
  if (window.requestIdleCallback) {
    requestIdleCallback(loadFaviconsWhenIdle, { timeout: 200 });
  } else {
    setTimeout(loadFaviconsWhenIdle, 50);
  }
}

let reapplyAfterHtmxScheduled = false;

function scheduleReapplyAfterHtmx() {
  if (reapplyAfterHtmxScheduled) return;
  reapplyAfterHtmxScheduled = true;

  requestAnimationFrame(() => {
    reapplyAfterHtmxScheduled = false;
    applyRestaurantViewPreference();
    initFaviconLoading();
    applyRestaurantSelectionState();
    initRestaurantCityToggles();
    updateRestaurantFilterIndicators();
  });
}

function initHtmxIntegration() {
  function maybeReapply(event) {
    const target = event.detail?.target;
    if (target instanceof HTMLElement) {
      if (target.id === 'restaurant-list-results' || target.querySelector?.('#restaurant-list-results')) {
        scheduleReapplyAfterHtmx();
        return;
      }
    }

    if (document.getElementById('restaurant-list-results')) {
      scheduleReapplyAfterHtmx();
    }
  }

  document.addEventListener('htmx:afterSwap', maybeReapply);
  document.addEventListener('htmx:afterSettle', maybeReapply);
}

let placesMapViewInstance = null;

function initPlacesMapView() {
  if (placesMapViewInstance) return;

  const container = document.getElementById('places-map-container');
  if (!container) {
    toast.error('Places map container not found.');
    return;
  }

  try {
    ensureAddToMyRestaurantsHandler();

    placesMapViewInstance = new PlacesMapView(container, {
      onError: (err) => toast.error(err?.message || 'Map error'),
    });
  } catch (err) {
    toast.error(err?.message || 'Failed to load Places map.');
    const sidebar = document.getElementById('places-sidebar-content');
    if (sidebar) {
      sidebar.innerHTML =
        '<div class="alert alert-danger mb-0"><i class="fas fa-exclamation-triangle me-2"></i>Failed to load map. Check the console for details.</div>';
    }
  }
}

function initPlacesTabLazyLoad() {
  // Init when Places map container exists (/restaurants/places or Places tab)
  if (document.getElementById('places-map-container')) {
    initPlacesMapView();
  }
}

// Main initialization function - optimized for performance
function init() {
  // Critical functionality that must run immediately
  initViewToggle();
  initDeleteRestaurant();
  initRestaurantSelectionActions();
  initRestaurantRowClickSelection();
  initRestaurantBulkActions();
  initRestaurantDeleteSelected();
  initRestaurantFilterClear();
  initHtmxIntegration();
  initPlacesTabLazyLoad();
  applyRestaurantSelectionState();
  initRestaurantCityToggles();
  updateRestaurantFilterIndicators();
  scheduleRestaurantStickyOffsetUpdate();

  window.addEventListener('popstate', () => {
    updateRestaurantFilterIndicators();
  });

  window.addEventListener('resize', scheduleRestaurantStickyOffsetUpdate);

  // Non-critical functionality that can be deferred
  initFaviconLoading();
}

// Initialize when DOM is ready (or immediately if already loaded, e.g. after HTMX swap)
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}
