/**
 * Expense Tags overview page: report panels driven by TagManager tagsLoaded event.
 */

const CURRENCY_OPTIONS = {
  style: 'currency',
  currency: 'USD',
  minimumFractionDigits: 2,
};

const DATE_OPTIONS = {
  year: 'numeric',
  month: 'short',
  day: 'numeric',
};

function formatCurrency(value) {
  return new Intl.NumberFormat('en-US', CURRENCY_OPTIONS).format(value);
}

function formatDate(isoString) {
  if (!isoString) return '';
  try {
    return new Intl.DateTimeFormat('en-US', DATE_OPTIONS).format(new Date(isoString));
  } catch {
    return isoString;
  }
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

function renderReportTopSpend(tags) {
  const body = document.getElementById('reportTopSpendBody');
  if (!body) return;
  const sorted = [...tags]
    .filter((t) => (t.total_amount ?? 0) > 0)
    .sort((a, b) => (b.total_amount ?? 0) - (a.total_amount ?? 0))
    .slice(0, 5);
  if (sorted.length === 0) {
    body.innerHTML = '<div class="tag-reports-empty">No tagged expenses yet</div>';
    return;
  }
  const ul = document.createElement('ul');
  ul.className = 'tag-report-list';
  sorted.forEach((tag) => {
    const li = document.createElement('li');
    const badge = document.createElement('span');
    badge.className = 'tag-badge-mini';
    badge.setAttribute('data-tag-color', tag.color || '#6c757d');
    badge.style.backgroundColor = tag.color || '#6c757d';
    badge.style.color = (() => {
      const hex = (tag.color || '#6c757d').replace('#', '');
      const r = parseInt(hex.slice(0, 2), 16);
      const g = parseInt(hex.slice(2, 4), 16);
      const b = parseInt(hex.slice(4, 6), 16);
      const brightness = (r * 299 + g * 587 + b * 114) / 1000;
      return brightness > 128 ? '#000' : '#fff';
    })();
    badge.textContent = escapeHtml(tag.name);
    const meta = document.createElement('span');
    meta.className = 'tag-meta';
    meta.textContent = formatCurrency(tag.total_amount ?? 0);
    li.appendChild(badge);
    li.appendChild(meta);
    ul.appendChild(li);
  });
  body.replaceChildren(ul);
}

function renderReportMostUsed(tags) {
  const body = document.getElementById('reportMostUsedBody');
  if (!body) return;
  const sorted = [...tags]
    .filter((t) => (t.expense_count ?? 0) > 0)
    .sort((a, b) => (b.expense_count ?? 0) - (a.expense_count ?? 0))
    .slice(0, 5);
  if (sorted.length === 0) {
    body.innerHTML = '<div class="tag-reports-empty">No tagged expenses yet</div>';
    return;
  }
  const ul = document.createElement('ul');
  ul.className = 'tag-report-list';
  sorted.forEach((tag) => {
    const li = document.createElement('li');
    const badge = document.createElement('span');
    badge.className = 'tag-badge-mini';
    badge.setAttribute('data-tag-color', tag.color || '#6c757d');
    badge.style.backgroundColor = tag.color || '#6c757d';
    badge.style.color = (() => {
      const hex = (tag.color || '#6c757d').replace('#', '');
      const r = parseInt(hex.slice(0, 2), 16);
      const g = parseInt(hex.slice(2, 4), 16);
      const b = parseInt(hex.slice(4, 6), 16);
      const brightness = (r * 299 + g * 587 + b * 114) / 1000;
      return brightness > 128 ? '#000' : '#fff';
    })();
    badge.textContent = escapeHtml(tag.name);
    const meta = document.createElement('span');
    meta.className = 'tag-meta';
    meta.textContent = `${tag.expense_count ?? 0} expense${(tag.expense_count ?? 0) === 1 ? '' : 's'}`;
    li.appendChild(badge);
    li.appendChild(meta);
    ul.appendChild(li);
  });
  body.replaceChildren(ul);
}

function renderReportRecentlyUsed(tags) {
  const body = document.getElementById('reportRecentlyUsedBody');
  if (!body) return;
  const sorted = [...tags]
    .filter((t) => t.last_visit)
    .sort((a, b) => new Date(b.last_visit) - new Date(a.last_visit))
    .slice(0, 5);
  if (sorted.length === 0) {
    body.innerHTML = '<div class="tag-reports-empty">No recent usage</div>';
    return;
  }
  const ul = document.createElement('ul');
  ul.className = 'tag-report-list';
  sorted.forEach((tag) => {
    const li = document.createElement('li');
    const badge = document.createElement('span');
    badge.className = 'tag-badge-mini';
    badge.setAttribute('data-tag-color', tag.color || '#6c757d');
    badge.style.backgroundColor = tag.color || '#6c757d';
    badge.style.color = (() => {
      const hex = (tag.color || '#6c757d').replace('#', '');
      const r = parseInt(hex.slice(0, 2), 16);
      const g = parseInt(hex.slice(2, 4), 16);
      const b = parseInt(hex.slice(4, 6), 16);
      const brightness = (r * 299 + g * 587 + b * 114) / 1000;
      return brightness > 128 ? '#000' : '#fff';
    })();
    badge.textContent = escapeHtml(tag.name);
    const meta = document.createElement('span');
    meta.className = 'tag-meta';
    meta.textContent = formatDate(tag.last_visit);
    li.appendChild(badge);
    li.appendChild(meta);
    ul.appendChild(li);
  });
  body.replaceChildren(ul);
}

function renderReportUnused(tags) {
  const body = document.getElementById('reportUnusedBody');
  if (!body) return;
  const unused = tags.filter((t) => !t.expense_count || t.expense_count === 0);
  if (unused.length === 0) {
    body.innerHTML = '<div class="tag-reports-empty">All tags are in use</div>';
    return;
  }
  const ul = document.createElement('ul');
  ul.className = 'tag-report-list';
  unused.slice(0, 8).forEach((tag) => {
    const li = document.createElement('li');
    const badge = document.createElement('span');
    badge.className = 'tag-badge-mini';
    badge.setAttribute('data-tag-color', tag.color || '#6c757d');
    badge.style.backgroundColor = tag.color || '#6c757d';
    badge.style.color = (() => {
      const hex = (tag.color || '#6c757d').replace('#', '');
      const r = parseInt(hex.slice(0, 2), 16);
      const g = parseInt(hex.slice(2, 4), 16);
      const b = parseInt(hex.slice(4, 6), 16);
      const brightness = (r * 299 + g * 587 + b * 114) / 1000;
      return brightness > 128 ? '#000' : '#fff';
    })();
    badge.textContent = escapeHtml(tag.name);
    li.appendChild(badge);
    ul.appendChild(li);
  });
  if (unused.length > 8) {
    const extra = document.createElement('li');
    extra.className = 'tag-meta';
    extra.textContent = `+${unused.length - 8} more`;
    ul.appendChild(extra);
  }
  body.replaceChildren(ul);
}

function renderAllReports(tags) {
  renderReportTopSpend(tags);
  renderReportMostUsed(tags);
  renderReportRecentlyUsed(tags);
  renderReportUnused(tags);
}

function initExpenseTagsPage() {
  document.addEventListener('tagsLoaded', (e) => {
    const tags = e.detail?.tags ?? [];
    renderAllReports(tags);
  });

  document.addEventListener('tagsUpdated', () => {
    if (window.tagManager && typeof window.tagManager.loadAllTags === 'function') {
      window.tagManager.loadAllTags();
    }
  });

  document.addEventListener('tagDeleted', () => {
    if (window.tagManager && typeof window.tagManager.loadAllTags === 'function') {
      window.tagManager.loadAllTags();
    }
  });
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initExpenseTagsPage);
} else {
  initExpenseTagsPage();
}
