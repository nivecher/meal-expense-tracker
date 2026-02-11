/**
 * Expense list: calendar tab (month/week/day views, selection, navigation).
 * Uses expense-list-filters for URL params and filter count.
 */

import { getUrlParams, getActiveExpenseFilterCount } from './expense-list-filters.js';
import { initializeRobustFaviconHandling } from '../utils/robust-favicon-handler.js';

const CALENDAR_VIEWS = {
  month: 'month',
  week: 'week',
  day: 'day',
};

function getCalendarData() {
  const calendarScript = document.getElementById('expense-calendar-data');
  if (!calendarScript) return [];
  try {
    return JSON.parse(calendarScript.textContent || '[]');
  } catch {
    return [];
  }
}

function groupExpensesByDate(expenses) {
  const grouped = new Map();
  expenses.forEach((expense) => {
    if (!expense?.date) return;
    const existing = grouped.get(expense.date);
    if (existing) {
      existing.push(expense);
      return;
    }
    grouped.set(expense.date, [expense]);
  });
  return grouped;
}

function formatMonthLabel(year, month) {
  return new Intl.DateTimeFormat('en-US', { month: 'long', year: 'numeric' }).format(
    new Date(year, month, 1),
  );
}

function formatDateKey(date) {
  const year = date.getFullYear();
  const month = `${date.getMonth() + 1}`.padStart(2, '0');
  const day = `${date.getDate()}`.padStart(2, '0');
  return `${year}-${month}-${day}`;
}

function getInitialCalendarDate(container) {
  const raw = container.dataset.calendarInitialMonth;
  if (!raw) return null;
  const [yearText, monthText] = raw.split('-');
  const year = parseInt(yearText, 10);
  const month = parseInt(monthText, 10);
  if (!Number.isFinite(year) || !Number.isFinite(month)) return null;
  if (month < 1 || month > 12) return null;
  return new Date(year, month - 1, 1);
}

function getCalendarStartDate(referenceDate) {
  const firstDay = new Date(referenceDate.getFullYear(), referenceDate.getMonth(), 1);
  const startDay = new Date(firstDay);
  startDay.setDate(firstDay.getDate() - firstDay.getDay());
  return startDay;
}

function buildCalendarDates(referenceDate) {
  const startDay = getCalendarStartDate(referenceDate);
  return Array.from({ length: 42 }, (_value, index) => {
    const day = new Date(startDay);
    day.setDate(startDay.getDate() + index);
    return day;
  });
}

function formatMealTypeLabel(mealType) {
  if (!mealType) return '';
  return mealType
    .split(' ')
    .map((word) => `${word.charAt(0).toUpperCase()}${word.slice(1)}`)
    .join(' ');
}

function formatAmount(amount, formatter) {
  const numericAmount = Number(amount);
  if (!Number.isFinite(numericAmount)) return '';
  return formatter.format(numericAmount);
}

function buildEntryTooltip(entry, amountText, mealTypeLabel) {
  const topLine = [entry.restaurant, mealTypeLabel, amountText].filter(Boolean).join(' • ');
  if (!entry.timeLabel) return topLine;
  if (!topLine) return entry.timeLabel;
  return `${topLine}\n${entry.timeLabel}`;
}

function getDayTotalAmount(entries) {
  return entries.reduce((sum, entry) => {
    const numericAmount = Number(entry?.amount);
    if (!Number.isFinite(numericAmount)) return sum;
    return sum + numericAmount;
  }, 0);
}

function isSameMonthYear(dateKey, referenceDate) {
  if (!dateKey) return false;
  const [yearText, monthText] = dateKey.split('-');
  const year = parseInt(yearText, 10);
  const month = parseInt(monthText, 10);
  if (!Number.isFinite(year) || !Number.isFinite(month)) return false;
  return year === referenceDate.getFullYear() && month === referenceDate.getMonth() + 1;
}

function isSameDate(dateKey, referenceDate) {
  if (!dateKey) return false;
  return dateKey === formatDateKey(referenceDate);
}

function getWeekStart(referenceDate) {
  const start = new Date(referenceDate);
  start.setDate(referenceDate.getDate() - referenceDate.getDay());
  return new Date(start.getFullYear(), start.getMonth(), start.getDate());
}

function buildWeekDates(referenceDate) {
  const start = getWeekStart(referenceDate);
  return Array.from({ length: 7 }, (_value, index) => {
    const day = new Date(start);
    day.setDate(start.getDate() + index);
    return day;
  });
}

function buildWeekDateKeys(referenceDate) {
  return buildWeekDates(referenceDate).map((date) => formatDateKey(date));
}

function getMonthlyEntryCount(calendarData, referenceDate) {
  if (!Array.isArray(calendarData)) return 0;
  return calendarData.reduce((count, entry) => {
    if (!entry?.date) return count;
    if (!isSameMonthYear(entry.date, referenceDate)) return count;
    return count + 1;
  }, 0);
}

function isTodayDateKey(dateKey) {
  return dateKey === formatDateKey(new Date());
}

function sortEntriesByDateTime(entries) {
  return [...entries].sort((a, b) => {
    const left = new Date(a?.dateTimeIso || '');
    const right = new Date(b?.dateTimeIso || '');
    return left.getTime() - right.getTime();
  });
}

function getUniqueExpenseDates(calendarData) {
  const keys = new Set();
  calendarData.forEach((entry) => {
    if (entry?.date) {
      keys.add(entry.date);
    }
  });
  return Array.from(keys).sort();
}

function getFirstExpenseDateInMonth(calendarData, referenceDate) {
  const dates = getUniqueExpenseDates(calendarData);
  const monthPrefix = `${referenceDate.getFullYear()}-${`${referenceDate.getMonth() + 1}`.padStart(2, '0')}`;
  const match = dates.find((dateKey) => dateKey.startsWith(monthPrefix));
  return match || null;
}

function findNeighborExpenseDate(calendarData, referenceDate, direction) {
  const dates = getUniqueExpenseDates(calendarData);
  if (!dates.length) return null;
  const referenceKey = formatDateKey(referenceDate);
  const currentIndex = dates.findIndex((key) => key === referenceKey);
  if (currentIndex === -1) {
    if (direction === 'prev') {
      const before = dates.filter((key) => key < referenceKey);
      return before.length ? before[before.length - 1] : null;
    }
    const after = dates.filter((key) => key > referenceKey);
    return after.length ? after[0] : null;
  }
  if (direction === 'prev') {
    return currentIndex > 0 ? dates[currentIndex - 1] : null;
  }
  return currentIndex < dates.length - 1 ? dates[currentIndex + 1] : null;
}

function parseDateKey(dateKey) {
  if (!dateKey) return null;
  const [yearText, monthText, dayText] = dateKey.split('-');
  const year = parseInt(yearText, 10);
  const month = parseInt(monthText, 10);
  const day = parseInt(dayText, 10);
  if (!Number.isFinite(year) || !Number.isFinite(month) || !Number.isFinite(day)) return null;
  return new Date(year, month - 1, day);
}

function formatSelectedDateLabel(date) {
  if (!date) return '';
  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  }).format(date);
}

function getSelectedDateKey(container, referenceDate) {
  return container.dataset.calendarSelectedDate || formatDateKey(referenceDate);
}

function setSelectedDateKey(container, dateKey) {
  if (!dateKey) return;
  container.dataset.calendarSelectedDate = dateKey;
}

function normalizeSelectedDate(container, referenceDate, view) {
  const selectedKey = getSelectedDateKey(container, referenceDate);
  if (view === 'month' && !isSameMonthYear(selectedKey, referenceDate)) {
    const firstInMonth = getFirstExpenseDateInMonth(getCalendarData(), referenceDate);
    const normalized = firstInMonth || formatDateKey(referenceDate);
    setSelectedDateKey(container, normalized);
    return parseDateKey(normalized);
  }
  return parseDateKey(selectedKey) || referenceDate;
}

function updateSelectedDateLabel(container, selectedDate) {
  const label = document.querySelector('[data-calendar-selected-label]');
  if (!label) return;
  const formatted = formatSelectedDateLabel(selectedDate);
  label.textContent = formatted ? `• ${formatted}` : '';
  if (formatted) {
    label.setAttribute('data-bs-toggle', 'tooltip');
    label.setAttribute('title', `Selected date: ${formatted}`);
  } else {
    label.removeAttribute('data-bs-toggle');
    label.removeAttribute('title');
  }
}

function buildAddExpenseUrl(addUrlBase, dateKey) {
  if (!addUrlBase || !dateKey) return '';
  const params = new URLSearchParams({ date: dateKey });
  return `${addUrlBase}?${params.toString()}`;
}

function updateAddExpenseButton(container, selectedDate) {
  const button = document.querySelector('[data-calendar-add-selected]');
  if (!button) return;
  const addUrlBase = container.dataset.calendarAddUrl || '';
  const dateKey = formatDateKey(selectedDate);
  const url = buildAddExpenseUrl(addUrlBase, dateKey);
  if (url) {
    button.setAttribute('href', url);
    button.setAttribute('title', `Add expense for ${formatSelectedDateLabel(selectedDate)}`);
    button.removeAttribute('aria-disabled');
    button.classList.remove('disabled');
  } else {
    button.setAttribute('aria-disabled', 'true');
    button.classList.add('disabled');
  }
}

function updateTodayButtonState(selectedDate) {
  const todayButton = document.querySelector('[data-calendar-today]');
  if (!todayButton) return;
  const isToday = formatDateKey(selectedDate) === formatDateKey(new Date());
  todayButton.classList.toggle('calendar-today-active', isToday);
}

// eslint-disable-next-line no-unused-vars -- reserved for calendar day links
function createAddExpenseLink(addUrlBase, dateKey, label) {
  const url = buildAddExpenseUrl(addUrlBase, dateKey);
  if (!url) return null;
  const link = document.createElement('a');
  link.className = 'calendar-day-action';
  link.setAttribute('href', url);
  link.setAttribute('data-bs-toggle', 'tooltip');
  link.setAttribute('title', label);
  const icon = document.createElement('i');
  icon.className = 'fas fa-plus';
  link.appendChild(icon);
  return link;
}

function createDayCountBadge(count) {
  const badge = document.createElement('span');
  badge.className = 'calendar-day-count';
  badge.textContent = `${count}`;
  return badge;
}

function buildCalendarDayHeader(dayDate, entries, formatter) {
  const header = document.createElement('div');
  header.className = 'calendar-day-header calendar-day-header-select';
  header.dataset.dateKey = formatDateKey(dayDate);

  const dateNumber = document.createElement('div');
  dateNumber.className = 'calendar-day-number';
  dateNumber.textContent = `${dayDate.getDate()}`;
  header.appendChild(dateNumber);

  if (entries.length > 1) {
    header.appendChild(createDayCountBadge(entries.length));
  }

  if (entries.length) {
    const totalAmount = getDayTotalAmount(entries);
    const totalText = formatAmount(totalAmount, formatter);
    if (totalText) {
      const total = document.createElement('div');
      total.className = 'calendar-day-total';
      total.textContent = totalText;
      header.appendChild(total);
    }
  }

  return header;
}

function createCalendarEntry(entry, formatter) {
  const {
    detailsUrl,
    mealType,
    mealTypeIcon,
    amount,
    restaurantWebsite,
  } = entry || {};
  const mealTypeLabel = formatMealTypeLabel(mealType);
  const amountText = formatAmount(amount, formatter);
  const tooltipText = buildEntryTooltip(entry, amountText, mealTypeLabel);
  const entryLink = document.createElement('a');
  entryLink.className = 'calendar-entry';
  entryLink.setAttribute('data-bs-toggle', 'tooltip');
  entryLink.setAttribute('data-bs-placement', 'top');
  if (tooltipText) {
    entryLink.setAttribute('title', tooltipText);
  }
  if (detailsUrl) {
    entryLink.setAttribute('href', detailsUrl);
  } else {
    entryLink.setAttribute('role', 'button');
  }
  const faviconWrap = document.createElement('span');
  faviconWrap.className = 'calendar-entry-favicon';
  const faviconImg = document.createElement('img');
  faviconImg.className = 'restaurant-favicon calendar-favicon';
  faviconImg.setAttribute('alt', '');
  faviconImg.setAttribute('aria-hidden', 'true');
  faviconImg.setAttribute('width', '16');
  faviconImg.setAttribute('height', '16');
  faviconImg.setAttribute('data-size', '16');
  if (restaurantWebsite) {
    faviconImg.setAttribute('data-website', restaurantWebsite);
  }
  const faviconFallback = document.createElement('i');
  faviconFallback.className = 'fas fa-utensils text-primary restaurant-fallback-icon calendar-fallback-icon';
  faviconWrap.append(faviconImg, faviconFallback);
  const mealIcon = document.createElement('i');
  const resolvedMealTypeIcon = mealTypeIcon ? mealTypeIcon.trim() : 'question';
  mealIcon.className = `fas fa-${resolvedMealTypeIcon || 'question'}`;
  entryLink.append(faviconWrap, mealIcon);
  return entryLink;
}

function buildCalendarEntries(entries, formatter) {
  if (!entries.length) return null;
  const entriesWrap = document.createElement('div');
  entriesWrap.className = 'calendar-day-entries';
  entries.forEach((entry) => {
    entriesWrap.appendChild(createCalendarEntry(entry, formatter));
  });
  return entriesWrap;
}

function formatOrderType(orderType) {
  if (!orderType) return '';
  return orderType.replace(/_/g, ' ').replace(/\b\w/g, (match) => match.toUpperCase());
}

function buildEntryMetaText(entry) {
  const parts = [];
  if (entry.mealType) {
    parts.push(formatMealTypeLabel(entry.mealType));
  }
  if (entry.orderType) {
    parts.push(formatOrderType(entry.orderType));
  }
  if (entry.partySize) {
    parts.push(`${entry.partySize} guest${entry.partySize === 1 ? '' : 's'}`);
  }
  return parts.join(' • ');
}

function createDayDetailEntry(entry, formatter) {
  const entryRow = document.createElement('a');
  entryRow.className = 'calendar-day-entry';
  if (entry.detailsUrl) {
    entryRow.setAttribute('href', entry.detailsUrl);
  } else {
    entryRow.setAttribute('role', 'button');
  }

  const topRow = document.createElement('div');
  topRow.className = 'calendar-entry-top';

  const time = document.createElement('span');
  time.className = 'calendar-day-time';
  time.textContent = entry.timeLabel || '—';

  const amount = document.createElement('span');
  amount.className = 'calendar-day-amount';
  amount.textContent = formatAmount(entry.amount, formatter);

  topRow.append(time, amount);

  const mainRow = document.createElement('div');
  mainRow.className = 'calendar-entry-main';

  const faviconWrap = document.createElement('span');
  faviconWrap.className = 'calendar-entry-favicon';
  const faviconImg = document.createElement('img');
  faviconImg.className = 'restaurant-favicon calendar-favicon';
  faviconImg.setAttribute('alt', '');
  faviconImg.setAttribute('aria-hidden', 'true');
  faviconImg.setAttribute('width', '18');
  faviconImg.setAttribute('height', '18');
  faviconImg.setAttribute('data-size', '18');
  if (entry.restaurantWebsite) {
    faviconImg.setAttribute('data-website', entry.restaurantWebsite);
  }
  const faviconFallback = document.createElement('i');
  faviconFallback.className = 'fas fa-utensils text-primary restaurant-fallback-icon calendar-fallback-icon';
  faviconWrap.append(faviconImg, faviconFallback);

  const detailsWrap = document.createElement('div');
  detailsWrap.className = 'calendar-day-details';
  const restaurant = document.createElement('div');
  restaurant.className = 'calendar-day-restaurant';
  restaurant.textContent = entry.restaurant || 'Unknown restaurant';
  const meta = document.createElement('div');
  meta.className = 'calendar-day-meta';
  meta.textContent = buildEntryMetaText(entry);
  detailsWrap.append(restaurant, meta);

  mainRow.append(faviconWrap, detailsWrap);
  entryRow.append(topRow, mainRow);
  return entryRow;
}

function buildWeekDayColumn(date, entries, formatter) {
  const column = document.createElement('div');
  column.className = 'calendar-week-day';
  column.dataset.dateKey = formatDateKey(date);

  const header = document.createElement('div');
  header.className = 'calendar-week-day-header';
  const label = document.createElement('span');
  label.textContent = new Intl.DateTimeFormat('en-US', { weekday: 'short', day: 'numeric' }).format(date);
  header.appendChild(label);
  column.appendChild(header);

  const list = document.createElement('div');
  list.className = 'calendar-week-day-list';
  if (!entries.length) {
    const empty = document.createElement('div');
    empty.className = 'text-muted small';
    empty.textContent = 'No expenses';
    list.appendChild(empty);
  } else {
    sortEntriesByDateTime(entries).forEach((entry) => {
      list.appendChild(createDayDetailEntry(entry, formatter));
    });
  }
  column.appendChild(list);
  return column;
}

function createCalendarDayCell(dayDate, monthIndex, grouped, formatter, _addUrlBase) {
  const cell = document.createElement('div');
  cell.className = 'calendar-day';
  cell.dataset.dateKey = formatDateKey(dayDate);
  if (dayDate.getMonth() !== monthIndex) {
    cell.classList.add('is-outside');
  }

  const dateKey = formatDateKey(dayDate);
  if (isTodayDateKey(dateKey)) {
    cell.classList.add('is-today');
  }
  const entries = grouped.get(dateKey) || [];

  cell.appendChild(buildCalendarDayHeader(dayDate, entries, formatter));

  const entriesWrap = buildCalendarEntries(entries, formatter);
  if (entriesWrap) {
    cell.appendChild(entriesWrap);
  }
  return cell;
}

function disposeCalendarTooltips(container) {
  const tooltips = container.querySelectorAll('[data-bs-toggle="tooltip"]');
  tooltips.forEach((element) => {
    const instance = bootstrap.Tooltip.getInstance(element);
    if (instance) {
      instance.dispose();
    }
  });
}

function initCalendarTooltips(container) {
  if (!container || typeof bootstrap === 'undefined') return;
  container.querySelectorAll('[data-bs-toggle="tooltip"]').forEach((element) => {
    new bootstrap.Tooltip(element); // eslint-disable-line no-new
  });
}

function renderWeekView(container, calendarData, referenceDate) {
  const weekContainer = document.querySelector('[data-expense-calendar-week]');
  if (!weekContainer) return;
  weekContainer.innerHTML = '';
  const grouped = groupExpensesByDate(calendarData);
  const formatter = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' });
  buildWeekDates(referenceDate).forEach((date) => {
    const dateKey = formatDateKey(date);
    const entries = grouped.get(dateKey) || [];
    const column = buildWeekDayColumn(date, entries, formatter);
    if (isTodayDateKey(dateKey)) {
      column.classList.add('is-today');
    }
    if (isSameDate(dateKey, referenceDate)) {
      column.classList.add('is-selected');
    }
    weekContainer.appendChild(column);
  });
  initializeRobustFaviconHandling('.calendar-favicon');
  initCalendarTooltips(weekContainer);
}

function renderDayView(container, calendarData, referenceDate) {
  const dayContainer = document.querySelector('[data-expense-calendar-day]');
  if (!dayContainer) return;
  dayContainer.innerHTML = '';
  const formatter = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' });
  const entries = sortEntriesByDateTime(
    calendarData.filter((entry) => isSameDate(entry?.date, referenceDate)),
  );
  const dayHeader = document.createElement('div');
  dayHeader.className = 'calendar-day-selected';
  const dayLabel = document.createElement('span');
  dayLabel.textContent = new Intl.DateTimeFormat('en-US', {
    weekday: 'long',
    month: 'long',
    day: 'numeric',
    year: 'numeric',
  }).format(referenceDate);
  dayHeader.appendChild(dayLabel);
  dayContainer.appendChild(dayHeader);
  if (!entries.length) {
    const empty = document.createElement('div');
    empty.className = 'text-muted small';
    empty.textContent = 'No expenses for this day.';
    dayContainer.appendChild(empty);
    return;
  }
  entries.forEach((entry) => {
    dayContainer.appendChild(createDayDetailEntry(entry, formatter));
  });
  initializeRobustFaviconHandling('.calendar-favicon');
  initCalendarTooltips(dayContainer);
}

function setCalendarView(view) {
  const monthContainer = document.querySelector('[data-expense-calendar]');
  const weekContainer = document.querySelector('[data-expense-calendar-week]');
  const dayContainer = document.querySelector('[data-expense-calendar-day]');
  if (!monthContainer || !weekContainer || !dayContainer) return;
  monthContainer.classList.toggle('d-none', view !== CALENDAR_VIEWS.month);
  weekContainer.classList.toggle('d-none', view !== CALENDAR_VIEWS.week);
  dayContainer.classList.toggle('d-none', view !== CALENDAR_VIEWS.day);
  monthContainer.dataset.calendarView = view;
}

function setActiveCalendarViewButton(view) {
  document.querySelectorAll('[data-calendar-view]').forEach((button) => {
    button.classList.toggle('active', button.dataset.calendarView === view);
  });
}

function getCalendarView(container) {
  return container.dataset.calendarView || CALENDAR_VIEWS.month;
}

function getCalendarViewFromUrl() {
  const urlParams = getUrlParams();
  const view = urlParams.get('calendar_view');
  if (view === CALENDAR_VIEWS.week || view === CALENDAR_VIEWS.day || view === CALENDAR_VIEWS.month) return view;
  return CALENDAR_VIEWS.month;
}

function updateCalendarViewInUrl(view) {
  const nextParams = getUrlParams();
  if (view === CALENDAR_VIEWS.month) {
    nextParams.delete('calendar_view');
  } else {
    nextParams.set('calendar_view', view);
  }
  const nextUrl = `${window.location.pathname}?${nextParams.toString()}`.replace(/\?$/, '');
  window.history.replaceState({}, '', nextUrl);
}

function updateCalendarEmptyState(calendarData, referenceDate, view) {
  const emptyState = document.querySelector('[data-calendar-empty]');
  if (!emptyState) return;
  let count = 0;
  if (view === 'day') {
    count = calendarData.filter((entry) => isSameDate(entry?.date, referenceDate)).length;
  } else if (view === 'week') {
    const weekKeys = new Set(buildWeekDateKeys(referenceDate));
    count = calendarData.filter((entry) => entry?.date && weekKeys.has(entry.date)).length;
  } else {
    count = getMonthlyEntryCount(calendarData, referenceDate);
  }
  emptyState.classList.toggle('d-none', count > 0);
}

function updateExpenseNavigationButtons(calendarData, referenceDate, _view) {
  const prevButton = document.querySelector('[data-calendar-prev-expense]');
  const nextButton = document.querySelector('[data-calendar-next-expense]');
  if (!prevButton || !nextButton) return;
  const prevKey = findNeighborExpenseDate(calendarData, referenceDate, 'prev');
  const nextKey = findNeighborExpenseDate(calendarData, referenceDate, 'next');
  prevButton.disabled = !prevKey;
  nextButton.disabled = !nextKey;
}

function updatePeriodNavigationTooltips(view) {
  const prevButton = document.querySelector('[data-calendar-prev]');
  const nextButton = document.querySelector('[data-calendar-next]');
  if (!prevButton || !nextButton) return;
  const label = view === CALENDAR_VIEWS.day ? 'Day' : view === CALENDAR_VIEWS.week ? 'Week' : 'Month';
  const prevTitle = `Previous ${label}`;
  const nextTitle = `Next ${label}`;
  prevButton.setAttribute('title', prevTitle);
  nextButton.setAttribute('title', nextTitle);

  if (typeof bootstrap !== 'undefined') {
    [prevButton, nextButton].forEach((btn, idx) => {
      const instance = bootstrap.Tooltip.getInstance(btn);
      if (instance) instance.dispose();
      new bootstrap.Tooltip(btn, { title: idx === 0 ? prevTitle : nextTitle }); // eslint-disable-line no-new
    });
  }
}

function scrollToSelectedView(view) {
  let target = null;
  if (view === CALENDAR_VIEWS.week) {
    target = document.querySelector('.calendar-week-day.is-selected');
  } else if (view === CALENDAR_VIEWS.day) {
    target = document.querySelector('.calendar-day-selected');
  } else {
    target = document.querySelector('.calendar-day.is-selected');
  }
  if (!target) return;
  target.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

function buildCalendarFilterSummary() {
  const urlParams = getUrlParams();
  const count = getActiveExpenseFilterCount();
  if (count === 0) return 'All expenses';

  const summaryParts = [];
  const mealType = urlParams.get('meal_type');
  if (mealType && mealType !== 'None') {
    summaryParts.push(`Meal: ${formatMealTypeLabel(mealType)}`);
  }
  const orderType = urlParams.get('order_type');
  if (orderType && orderType !== 'None') {
    summaryParts.push(`Order: ${formatMealTypeLabel(orderType.replace(/_/g, ' '))}`);
  }
  const category = urlParams.get('category');
  if (category && category !== 'None') {
    summaryParts.push(`Category: ${category}`);
  }
  const tags = urlParams.getAll('tags').filter((tag) => tag && tag !== 'None');
  if (tags.length) {
    summaryParts.push(`Tags: ${tags.length}`);
  }
  const startDate = urlParams.get('start_date');
  const endDate = urlParams.get('end_date');
  if (startDate || endDate) {
    summaryParts.push(`Dates: ${startDate || '…'}–${endDate || '…'}`);
  }
  return summaryParts.length ? summaryParts.join(' • ') : 'Filtered expenses';
}

export function updateCalendarFilterSummary() {
  const summary = document.querySelector('[data-calendar-filter-summary]');
  if (!summary) return;
  summary.textContent = buildCalendarFilterSummary();
}

function renderExpenseCalendar(container, calendarData, referenceDate, selectedDate) {
  const label = document.querySelector('[data-calendar-label]');
  if (label) {
    label.textContent = formatMonthLabel(referenceDate.getFullYear(), referenceDate.getMonth());
  }
  const grouped = groupExpensesByDate(calendarData);
  const dates = buildCalendarDates(referenceDate);
  const formatter = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' });
  disposeCalendarTooltips(container);
  container.innerHTML = '';
  dates.forEach((date) => {
    const cell = createCalendarDayCell(date, referenceDate.getMonth(), grouped, formatter);
    if (selectedDate && formatDateKey(date) === formatDateKey(selectedDate)) {
      cell.classList.add('is-selected');
    }
    container.appendChild(cell);
  });
  initializeRobustFaviconHandling('.calendar-favicon');
  initCalendarTooltips(container);
}

function renderCalendarView(container, calendarData, referenceDate) {
  const view = getCalendarView(container);
  setActiveCalendarViewButton(view);
  const selectedDate = normalizeSelectedDate(container, referenceDate, view);
  updateSelectedDateLabel(container, selectedDate);
  updateAddExpenseButton(container, selectedDate);
  updateTodayButtonState(selectedDate);
  if (view === 'week') {
    renderWeekView(container, calendarData, selectedDate);
  } else if (view === 'day') {
    renderDayView(container, calendarData, selectedDate);
  } else {
    renderExpenseCalendar(container, calendarData, referenceDate, selectedDate);
  }
  updateCalendarEmptyState(calendarData, view === 'month' ? referenceDate : selectedDate, view);
  updateExpenseNavigationButtons(calendarData, selectedDate, view);
  updatePeriodNavigationTooltips(view);
  if (container.dataset.calendarScrollOnRender === 'true') {
    container.dataset.calendarScrollOnRender = 'false';
    requestAnimationFrame(() => {
      scrollToSelectedView(view);
    });
  }
}

function getCalendarCurrentDate(container) {
  const raw = container.dataset.calendarMonth;
  if (raw) {
    const parsed = new Date(raw);
    if (!Number.isNaN(parsed.getTime())) {
      return parsed;
    }
  }
  const initial = getInitialCalendarDate(container);
  if (initial) return initial;
  return new Date();
}

function setCalendarCurrentDate(container, date) {
  container.dataset.calendarMonth = date.toISOString();
}

export function initExpenseCalendar() {
  const container = document.querySelector('[data-expense-calendar]');
  if (!container) return;
  if (container.dataset.calendarInitialized === 'true') {
    const currentDate = getCalendarCurrentDate(container);
    renderCalendarView(container, getCalendarData(), currentDate);
    return;
  }

  container.dataset.calendarInitialized = 'true';
  setCalendarView(getCalendarViewFromUrl());
  let currentDate = getCalendarCurrentDate(container);

  const renderCalendar = () => {
    renderCalendarView(container, getCalendarData(), currentDate);
    setCalendarCurrentDate(container, currentDate);
  };

  function selectDate(dateKey, shouldUpdateMonth) {
    const selectedDate = parseDateKey(dateKey);
    if (!selectedDate) return;
    setSelectedDateKey(container, dateKey);
    if (shouldUpdateMonth) {
      currentDate = selectedDate;
    }
    renderCalendar();
  }

  function attachMonthSelectionHandlers() {
    if (container.dataset.monthSelectionAttached === 'true') return;
    container.dataset.monthSelectionAttached = 'true';
    container.addEventListener('click', (event) => {
      const view = getCalendarView(container);
      if (view !== 'month') return;
      const cell = event.target.closest('.calendar-day');
      if (!cell || !container.contains(cell)) return;
      const { dateKey } = cell.dataset;
      if (!dateKey) return;
      const shouldUpdateMonth = cell.classList.contains('is-outside');
      selectDate(dateKey, shouldUpdateMonth);
    }, true);
  }

  function attachWeekSelectionHandlers() {
    const weekContainer = document.querySelector('[data-expense-calendar-week]');
    if (!weekContainer) return;
    if (weekContainer.dataset.weekSelectionAttached === 'true') return;
    weekContainer.dataset.weekSelectionAttached = 'true';
    weekContainer.addEventListener('click', (event) => {
      const cell = event.target.closest('.calendar-week-day');
      if (!cell || !weekContainer.contains(cell)) return;
      const { dateKey } = cell.dataset;
      if (!dateKey) return;
      selectDate(dateKey, true);
    });
  }

  document.querySelectorAll('[data-calendar-view]').forEach((button) => {
    if (button.dataset.listenerAttached === 'true') return;
    button.dataset.listenerAttached = 'true';
    button.addEventListener('click', () => {
      const view = button.dataset.calendarView || 'month';
      setCalendarView(view);
      updateCalendarViewInUrl(view);
      renderCalendar();
    });
  });

  const prevButton = document.querySelector('[data-calendar-prev]');
  if (prevButton) {
    prevButton.addEventListener('click', () => {
      const view = getCalendarView(container);
      if (view === 'day') {
        currentDate = new Date(currentDate.getFullYear(), currentDate.getMonth(), currentDate.getDate() - 1);
        setSelectedDateKey(container, formatDateKey(currentDate));
      } else if (view === 'week') {
        currentDate = new Date(currentDate.getFullYear(), currentDate.getMonth(), currentDate.getDate() - 7);
        setSelectedDateKey(container, formatDateKey(currentDate));
      } else {
        currentDate = new Date(currentDate.getFullYear(), currentDate.getMonth() - 1, 1);
      }
      renderCalendar();
    });
  }

  const nextButton = document.querySelector('[data-calendar-next]');
  if (nextButton) {
    nextButton.addEventListener('click', () => {
      const view = getCalendarView(container);
      if (view === 'day') {
        currentDate = new Date(currentDate.getFullYear(), currentDate.getMonth(), currentDate.getDate() + 1);
        setSelectedDateKey(container, formatDateKey(currentDate));
      } else if (view === 'week') {
        currentDate = new Date(currentDate.getFullYear(), currentDate.getMonth(), currentDate.getDate() + 7);
        setSelectedDateKey(container, formatDateKey(currentDate));
      } else {
        currentDate = new Date(currentDate.getFullYear(), currentDate.getMonth() + 1, 1);
      }
      renderCalendar();
    });
  }

  const todayButton = document.querySelector('[data-calendar-today]');
  if (todayButton) {
    todayButton.addEventListener('click', () => {
      currentDate = new Date();
      setSelectedDateKey(container, formatDateKey(currentDate));
      renderCalendar();
    });
  }

  const prevExpenseButton = document.querySelector('[data-calendar-prev-expense]');
  if (prevExpenseButton) {
    prevExpenseButton.addEventListener('click', () => {
      const prevKey = findNeighborExpenseDate(getCalendarData(), currentDate, 'prev');
      const targetDate = parseDateKey(prevKey);
      if (!targetDate) return;
      currentDate = targetDate;
      setSelectedDateKey(container, formatDateKey(targetDate));
      container.dataset.calendarScrollOnRender = 'true';
      renderCalendar();
    });
  }

  const nextExpenseButton = document.querySelector('[data-calendar-next-expense]');
  if (nextExpenseButton) {
    nextExpenseButton.addEventListener('click', () => {
      const nextKey = findNeighborExpenseDate(getCalendarData(), currentDate, 'next');
      const targetDate = parseDateKey(nextKey);
      if (!targetDate) return;
      currentDate = targetDate;
      setSelectedDateKey(container, formatDateKey(targetDate));
      container.dataset.calendarScrollOnRender = 'true';
      renderCalendar();
    });
  }

  const calendarTab = document.getElementById('calendar-tab');
  if (calendarTab) {
    calendarTab.addEventListener('shown.bs.tab', () => {
      renderCalendar();
      const pane = document.getElementById('calendar-pane');
      if (pane) {
        pane.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    });
  }

  renderCalendar();
  attachMonthSelectionHandlers();
  attachWeekSelectionHandlers();
}
