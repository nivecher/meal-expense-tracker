/**
 * Resizable table columns with persisted widths.
 *
 * - Drag the handle on header cells to resize a column.
 * - Widths are stored in localStorage and a cookie as a fallback.
 * - Designed to work with HTMX swaps (re-initializes safely).
 */

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

function getStoredJson(storageKey, cookieKey) {
  try {
    const raw = localStorage.getItem(storageKey);
    if (raw) return JSON.parse(raw);
  } catch {
    // ignore
  }

  try {
    const rawCookie = getCookieValue(cookieKey);
    if (rawCookie) return JSON.parse(rawCookie);
  } catch {
    // ignore
  }

  return null;
}

function persistJson(storageKey, cookieKey, value) {
  const raw = JSON.stringify(value);
  try {
    localStorage.setItem(storageKey, raw);
  } catch {
    // ignore
  }
  setCookieValue(cookieKey, raw);
}

function ensureColgroup(table, columnCount) {
  let colgroup = table.querySelector('colgroup');
  if (colgroup) return colgroup;

  colgroup = document.createElement('colgroup');
  for (let i = 0; i < columnCount; i += 1) {
    colgroup.appendChild(document.createElement('col'));
  }

  table.insertBefore(colgroup, table.firstChild);
  return colgroup;
}

function getPreferenceKeys(table) {
  const key = table.getAttribute('data-column-prefs-key') || table.id || 'table';
  return {
    storageKey: `tableColumnWidths:${key}`,
    cookieKey: `table_column_widths_${key}`,
  };
}

function applySavedWidths(table, colgroup) {
  const cols = Array.from(colgroup.querySelectorAll('col'));
  const { storageKey, cookieKey } = getPreferenceKeys(table);
  const saved = getStoredJson(storageKey, cookieKey);
  if (!saved || typeof saved !== 'object') return;

  Object.entries(saved).forEach(([indexStr, widthValue]) => {
    const index = parseInt(indexStr, 10);
    const widthPx = typeof widthValue === 'number' ? widthValue : parseInt(String(widthValue), 10);
    if (!Number.isFinite(index) || !Number.isFinite(widthPx)) return;
    const col = cols[index];
    if (!col) return;
    col.style.width = `${Math.max(40, Math.min(widthPx, 1200))}px`;
  });
}

function saveWidths(table, colgroup) {
  const cols = Array.from(colgroup.querySelectorAll('col'));
  const { storageKey, cookieKey } = getPreferenceKeys(table);

  const widths = {};
  cols.forEach((col, index) => {
    const rawWidth = col.style.width || '';
    if (!rawWidth) return;
    const widthPx = parseInt(rawWidth.replace('px', ''), 10);
    if (!Number.isFinite(widthPx)) return;
    widths[String(index)] = widthPx;
  });

  persistJson(storageKey, cookieKey, widths);
}

function initResizableTable(table) {
  if (table.dataset.columnsResizableInitialized === 'true') return;
  table.dataset.columnsResizableInitialized = 'true';

  const headerRow = table.querySelector('thead tr');
  if (!headerRow) return;

  const headers = Array.from(headerRow.querySelectorAll('th'));
  if (!headers.length) return;

  const colgroup = ensureColgroup(table, headers.length);
  applySavedWidths(table, colgroup);

  const cols = Array.from(colgroup.querySelectorAll('col'));

  headers.forEach((th, index) => {
    const isNonResizable = th.classList.contains('actions')
      || th.classList.contains('select-col')
      || th.hasAttribute('data-col-fill');
    if (isNonResizable) {
      if (th.hasAttribute('data-col-fill')) {
        const col = cols[index];
        if (col) {
          col.style.width = 'auto';
        }
      }
      return;
    }

    // Avoid double handles if something else re-runs init on same DOM.
    if (th.querySelector('.col-resize-handle')) return;

    const handle = document.createElement('span');
    handle.className = 'col-resize-handle';
    handle.setAttribute('role', 'separator');
    handle.setAttribute('aria-orientation', 'vertical');
    handle.setAttribute('aria-label', `Resize column ${index + 1}`);
    handle.tabIndex = -1;

    handle.addEventListener('pointerdown', (event) => {
      event.preventDefault();
      event.stopPropagation();

      const col = cols[index];
      if (!col) return;

      const startX = event.clientX;
      const startWidth = Math.round(th.getBoundingClientRect().width);
      const minWidthPx = 60;
      const maxWidthPx = 800;

      handle.setPointerCapture(event.pointerId);

      function onMove(moveEvent) {
        const delta = moveEvent.clientX - startX;
        const nextWidth = Math.max(minWidthPx, Math.min(startWidth + delta, maxWidthPx));
        col.style.width = `${nextWidth}px`;
      }

      function onUp(upEvent) {
        handle.releasePointerCapture(upEvent.pointerId);
        document.removeEventListener('pointermove', onMove, true);
        document.removeEventListener('pointerup', onUp, true);
        saveWidths(table, colgroup);
      }

      document.addEventListener('pointermove', onMove, true);
      document.addEventListener('pointerup', onUp, true);
    });

    th.appendChild(handle);
  });
}

function initResizableColumns(root = document) {
  const tables = root.querySelectorAll?.('table[data-resizable-columns="true"]') || [];
  tables.forEach((table) => initResizableTable(table));
}

document.addEventListener('DOMContentLoaded', () => initResizableColumns(document));
document.addEventListener('htmx:afterSettle', (event) => {
  const target = event.detail?.target;
  if (target instanceof HTMLElement) {
    initResizableColumns(target);
  } else {
    initResizableColumns(document);
  }
});

export { initResizableColumns };
