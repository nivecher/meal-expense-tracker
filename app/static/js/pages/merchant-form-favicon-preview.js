/**
 * Merchant form favicon preview: try all favicon sources for the merchant website
 * and show previews so the user can pick one to set as Favicon URL.
 */
import { getFaviconHostCandidates, debugFaviconSources } from '../utils/robust-favicon-handler.js';

const WEBSITE_INPUT_ID = 'website';
const FAVICON_URL_INPUT_ID = 'favicon_url';
const PREVIEW_BUTTON_ID = 'favicon-preview-btn';
const PREVIEW_RESULTS_ID = 'favicon-preview-results';
const PREVIEW_LOADING_ID = 'favicon-preview-loading';
const OPEN_WEBSITE_BUTTON_ID = 'open-website-btn';

/**
 * Ensure URL has a protocol for host extraction.
 * @param {string} raw - User input
 * @returns {string} - URL with protocol
 */
function normalizeWebsiteUrl(raw) {
  const trimmed = (raw || '').trim();
  if (!trimmed) return '';
  if (/^https?:\/\//i.test(trimmed)) return trimmed;
  return `https://${trimmed}`;
}

function updateWebsiteButton(websiteInput, openWebsiteButton) {
  if (!websiteInput || !openWebsiteButton) return;
  const website = websiteInput.value.trim();
  openWebsiteButton.disabled = website.length === 0;
  openWebsiteButton.dataset.website = website;
}

function openWebsiteInNewTab(websiteInput) {
  if (!websiteInput) return;
  const website = normalizeWebsiteUrl(websiteInput.value);
  if (!website) return;
  window.open(website, '_blank', 'noopener,noreferrer');
}

/**
 * Build list of { host, results } for all host candidates.
 * @param {string} website - Normalized website URL
 * @returns {Promise<Array<{ host: string, results: Object }>>}
 */
async function fetchPreviewResults(website) {
  const candidates = getFaviconHostCandidates(website);
  if (candidates.length === 0) return [];

  const promises = candidates.map((host) =>
    debugFaviconSources(host).then((results) => (results.error ? null : { host, results })),
  );
  const settled = await Promise.all(promises);
  return settled.filter(Boolean);
}

/**
 * Render one source result: preview image and "Use this" button if successful.
 * @param {HTMLElement} container
 * @param {string} host
 * @param {Object} sourceResult - { name, url, success }
 * @param {HTMLInputElement} faviconUrlInput
 */
function renderSourcePreview(container, host, sourceResult, faviconUrlInput) {
  const card = document.createElement('div');
  card.className = 'favicon-preview-card border rounded p-2 d-flex flex-column align-items-center';

  const label = document.createElement('span');
  label.className = 'small text-muted mb-1';
  label.textContent = `${sourceResult.name} (${host})`;

  const imgWrap = document.createElement('div');
  imgWrap.className = 'favicon-preview-img-wrap d-flex align-items-center justify-content-center bg-light rounded mb-2';
  imgWrap.style.width = '48px';
  imgWrap.style.height = '48px';

  if (sourceResult.success) {
    const img = document.createElement('img');
    img.src = sourceResult.url;
    img.alt = '';
    img.style.maxWidth = '32px';
    img.style.maxHeight = '32px';
    img.setAttribute('loading', 'lazy');
    imgWrap.appendChild(img);
  } else {
    imgWrap.classList.add('favicon-preview-failed');
    const fail = document.createElement('span');
    fail.className = 'small text-muted';
    fail.textContent = '—';
    imgWrap.appendChild(fail);
  }

  card.appendChild(label);
  card.appendChild(imgWrap);

  if (sourceResult.success) {
    const useBtn = document.createElement('button');
    useBtn.type = 'button';
    useBtn.className = 'btn btn-sm btn-outline-primary';
    useBtn.textContent = 'Use this';
    useBtn.addEventListener('click', () => {
      faviconUrlInput.value = sourceResult.url;
      faviconUrlInput.dispatchEvent(new Event('input', { bubbles: true }));
    });
    card.appendChild(useBtn);
  } else {
    const failLabel = document.createElement('span');
    failLabel.className = 'small text-danger';
    failLabel.textContent = 'Failed';
    card.appendChild(failLabel);
  }

  container.appendChild(card);
}

/**
 * Render the full preview results grid.
 * @param {HTMLElement} resultsEl
 * @param {HTMLInputElement} faviconUrlInput
 * @param {Array<{ host: string, results: Object }>} hostResults
 */
function renderResults(resultsEl, faviconUrlInput, hostResults) {
  resultsEl.innerHTML = '';

  if (hostResults.length === 0) {
    resultsEl.innerHTML =
      '<p class="text-muted small mb-0">Enter a website above and click "Load favicon previews".</p>';
    return;
  }

  const grid = document.createElement('div');
  grid.className = 'favicon-preview-grid d-flex flex-wrap gap-2';

  for (const { host, results } of hostResults) {
    const sources = results.sources || [];
    for (const sr of sources) {
      renderSourcePreview(grid, host, sr, faviconUrlInput);
    }
  }

  resultsEl.appendChild(grid);
}

/**
 * Run preview: fetch results for current website and render.
 * @param {HTMLInputElement} websiteInput
 * @param {HTMLInputElement} faviconUrlInput
 * @param {HTMLElement} resultsEl
 * @param {HTMLElement} loadingEl
 */
async function runPreview(websiteInput, faviconUrlInput, resultsEl, loadingEl) {
  const website = normalizeWebsiteUrl(websiteInput.value);
  if (!website) {
    renderResults(resultsEl, faviconUrlInput, []);
    resultsEl.innerHTML =
      '<p class="text-warning small mb-0">Enter a website URL first.</p>';
    return;
  }

  loadingEl.classList.remove('d-none');
  resultsEl.innerHTML = '';

  try {
    const hostResults = await fetchPreviewResults(website);
    renderResults(resultsEl, faviconUrlInput, hostResults);
    if (hostResults.length === 0) {
      resultsEl.innerHTML =
        '<p class="text-muted small mb-0">Could not derive host from URL.</p>';
    }
  } catch (err) {
    resultsEl.innerHTML = `<p class="text-danger small mb-0">Error: ${err.message || 'Failed to load previews'}.</p>`;
  } finally {
    loadingEl.classList.add('d-none');
  }
}

/**
 * Initialize favicon preview UI when DOM is ready.
 */
function initFaviconPreview() {
  const websiteInput = document.getElementById(WEBSITE_INPUT_ID);
  const faviconUrlInput = document.getElementById(FAVICON_URL_INPUT_ID);
  const previewBtn = document.getElementById(PREVIEW_BUTTON_ID);
  const resultsEl = document.getElementById(PREVIEW_RESULTS_ID);
  const loadingEl = document.getElementById(PREVIEW_LOADING_ID);
  const openWebsiteButton = document.getElementById(OPEN_WEBSITE_BUTTON_ID);

  if (!websiteInput || !faviconUrlInput || !previewBtn || !resultsEl || !loadingEl) {
    return;
  }

  if (openWebsiteButton) {
    websiteInput.addEventListener('input', () => updateWebsiteButton(websiteInput, openWebsiteButton));
    openWebsiteButton.addEventListener('click', () => openWebsiteInNewTab(websiteInput));
    updateWebsiteButton(websiteInput, openWebsiteButton);
  }

  previewBtn.addEventListener('click', () => {
    runPreview(websiteInput, faviconUrlInput, resultsEl, loadingEl);
  });

  renderResults(resultsEl, faviconUrlInput, []);
}

document.addEventListener('DOMContentLoaded', initFaviconPreview);
