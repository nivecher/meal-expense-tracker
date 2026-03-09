# Favicon System Setup

## Overview

The app loads restaurant and merchant favicons using a canonical website URL (backend-normalized) and tries multiple host candidates (www and apex) and multiple favicon sources until one succeeds. Initialization is centralized in `main.js`; dynamic content (e.g. after HTMX) re-initializes only where needed.

## Standard Setup

### 1. Main app integration

- **Entry point**: `main.js` calls `initializeFaviconSystem()` once when the app loads (deferred via `runWhenIdle`).
- **Selectors**: `.restaurant-favicon` and `.restaurant-favicon-table` are initialized by that call.
- **Dynamic content**: Pages that inject new HTML (e.g. restaurant list, expense list after HTMX swap) call `initializeRobustFaviconHandling` for those selectors again so new elements get favicons.

### 2. Favicon source order

Sources are tried in this order (per host candidate):

1. **DuckDuckGo** – `icons.duckduckgo.com/ip3/{domain}.ico`
2. **Direct** – `https://{domain}/favicon.ico`
3. **Google Legacy** – `google.com/s2/favicons?domain=...`
4. **Google Favicon V2** – `t3.gstatic.com/faviconV2?client=SOCIAL&...`

For each website, the handler derives **host candidates** (canonical host plus www/apex alternate) and tries all sources for the first candidate, then all sources for the second. That way sites like `chick-fil-a.com` and `www.chick-fil-a.com` resolve consistently.

### 3. Favicon policy (who shows which icon)

**Precedence** (highest first):

1. **Merchant favicon override** – If a merchant has an optional **Favicon URL** set (Edit Merchant), that URL is used for that merchant everywhere (merchant list/detail, restaurant list/detail/form when the restaurant is linked to that merchant). No website-derived lookup is done.
2. **Website-derived** – Restaurant or merchant website URL is used to resolve favicon via host candidates and the fixed source order above.
3. **Fallback icon** – Utensils or building icon when all else fails.

- **Restaurant views**: Merchant `favicon_url` if present and restaurant linked to that merchant; else restaurant website.
- **Merchant views**: Merchant `favicon_url` if set; else merchant website.
- **Restaurant form preview**: Same: merchant favicon override when linked and set; else restaurant website or merchant website.

### 4. Backend canonicalization

Website URLs are normalized on ingest (restaurants, merchants, Google Places) via `canonicalize_website_for_storage()` in `app/utils/url_utils.py`, so stored values have lowercase host, no query params, and a consistent path. Favicon host candidates are derived from that canonical URL.

### 5. Error handling

- Minimal global suppression: one `error` listener stops propagation for IMG load errors from our favicon URLs (DuckDuckGo, Google, gstatic) so expected 404s don’t clutter the console.
- Failed domains are cached (one failure per domain) so we don’t retry known-bad hosts.
- Known problematic root domains (e.g. wix.com, squarespace.com, weebly.com) are skipped entirely.
- When all sources fail, the UI shows the fallback icon (utensils or building).

## File structure

- **Handler**: `app/static/js/utils/robust-favicon-handler.js` (fixed source order, `data-favicon-url` for merchant override)
- **Initialization**: `main.js` → `initializeFaviconSystem()`
- **URL helpers**: `app/utils/url_utils.py` (`canonicalize_website_for_storage`, `get_favicon_host_candidates`, `validate_favicon_url`)
- **Merchant override**: `Merchant.favicon_url` in `app/merchants/models.py`; validated in services and shown in merchant/restaurant templates

## Debug (development)

- **URL**: Add `?debug=favicon` to the page URL for favicon debug logs.
- **Console**: On localhost, `window.faviconDebug.clearCache()` clears the favicon cache.
- **Global**: `window.RobustFaviconHandler` exposes `initialize`, `clearCache`, `getCacheStats`, `getFaviconHostCandidates`, etc.

## Manual init for dynamic content

```javascript
// After injecting HTML that contains favicon placeholders
import { initializeRobustFaviconHandling } from "./utils/robust-favicon-handler.js";
initializeRobustFaviconHandling(".restaurant-favicon");
initializeRobustFaviconHandling(".restaurant-favicon-table");
```
