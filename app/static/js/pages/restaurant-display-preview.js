import { initializeRobustFaviconHandling } from '../utils/robust-favicon-handler.js';

function cleanDisplayText(value) {
  if (value === null || value === undefined) return '';
  const text = String(value).trim();
  if (!text) return '';
  const lower = text.toLowerCase();
  if (lower === 'none' || lower === 'null' || lower === 'n/a' || lower === 'na') {
    return '';
  }
  return text;
}

function normalizeForCompare(value) {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim().replace(/\s+/g, ' ');
}

function deriveLocationFromName(restaurantName, merchantBase) {
  const name = cleanDisplayText(restaurantName);
  const merchant = cleanDisplayText(merchantBase);
  if (!name || !merchant) return '';
  const separator = ' - ';
  if (!name.includes(separator)) return '';
  const [prefix, suffix] = name.split(separator, 2);
  if (normalizeForCompare(prefix) !== normalizeForCompare(merchant)) return '';
  return cleanDisplayText(suffix);
}

function computePreviewText() {
  const restaurantName = cleanDisplayText(document.getElementById('name')?.value);
  const locationName = cleanDisplayText(document.getElementById('location_name')?.value);
  const restaurantWebsite = cleanDisplayText(document.getElementById('website')?.value);
  const merchantInput = document.getElementById('merchant_name');
  const merchantAlias = cleanDisplayText(document.getElementById('merchant_alias')?.value);
  const merchantFromSelection = cleanDisplayText(merchantInput?.dataset.merchantDisplayBase);
  const merchantWebsite = cleanDisplayText(merchantInput?.dataset.merchantWebsite);
  const merchantTyped = cleanDisplayText(merchantInput?.value);
  const merchantBase = merchantFromSelection || merchantAlias || merchantTyped;

  let location = locationName;
  if (!location) {
    location = deriveLocationFromName(restaurantName, merchantBase);
  }

  let text = 'Not enough information yet';
  if (merchantBase && location) text = `${merchantBase} - ${location}`;
  else if (merchantBase) text = merchantBase;
  else if (restaurantName && location) text = `${restaurantName} - ${location}`;
  else if (location) text = location;
  else if (restaurantName) text = restaurantName;

  // Favicon policy: restaurant website first, fall back to merchant website only when absent.
  return {
    text,
    website: restaurantWebsite || merchantWebsite || '',
  };
}

function renderPreview() {
  const previewEl = document.getElementById('restaurant-display-name-preview');
  if (!previewEl) return;
  const preview = computePreviewText();
  previewEl.textContent = preview.text;

  const faviconEl = document.getElementById('restaurant-display-preview-favicon');
  const fallbackEl = document.getElementById('restaurant-display-preview-fallback');
  if (!faviconEl) return;

  if (preview.website) {
    faviconEl.dataset.website = preview.website;
    faviconEl.style.display = 'inline-block';
    faviconEl.style.opacity = '0';
    if (fallbackEl) {
      fallbackEl.classList.add('d-none');
      fallbackEl.style.display = 'none';
      fallbackEl.style.opacity = '0';
    }
    initializeRobustFaviconHandling('#restaurant-display-preview-favicon');
  } else {
    delete faviconEl.dataset.website;
    faviconEl.style.display = 'none';
    if (fallbackEl) {
      fallbackEl.classList.remove('d-none');
      fallbackEl.style.display = 'inline-block';
      fallbackEl.style.opacity = '1';
    }
  }
}

function initPreview() {
  const fields = ['name', 'location_name', 'merchant_name', 'website'];
  fields.forEach((id) => {
    const field = document.getElementById(id);
    if (!field) return;
    field.addEventListener('input', renderPreview);
    field.addEventListener('change', renderPreview);
  });

  document.addEventListener('merchant-selected', renderPreview);
  document.addEventListener('merchant-cleared', renderPreview);
  renderPreview();
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initPreview);
} else {
  initPreview();
}
