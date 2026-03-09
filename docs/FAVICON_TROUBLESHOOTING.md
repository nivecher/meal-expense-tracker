# Favicon Troubleshooting Guide

## How it works

- **Backend**: Website URLs are canonicalized on save (lowercase host, no query params) via `app/utils/url_utils.py`. See `docs/FAVICON_SETUP.md` for the full flow.
- **Explicit URL**: If an element has `data-favicon-url` (e.g. merchant favicon override), that URL is loaded directly and no website-derived lookup is done.
- **Frontend**: For each `data-website` value, the handler derives **host candidates** (canonical host plus www/apex alternate). It then tries each candidate with favicon sources in a fixed order (DuckDuckGo, direct, Google Legacy, Google Favicon V2).
- **Fallback**: If all candidates and sources fail, the UI shows the fallback icon (utensils or building). Failed domains are cached so we don’t retry them.

## Common issues

### Favicon never loads / always shows fallback

- **Cause**: All sources 404 for that domain (e.g. no favicon, or blocked).
- **What we do**: We try both www and apex host; if both fail, we show the fallback and cache the failure.
- **Action**: Normal. No code change needed. Optionally add the domain’s root (e.g. `wix.com`) to the problematic-domains skip list in `robust-favicon-handler.js` if it never works.

### 404 or CORS in console for favicon URLs

- **Cause**: Browsers log failed image requests. We use a single global `error` listener to stop propagation for our favicon IMG URLs (DuckDuckGo, Google, gstatic) so expected 404s don’t clutter the console.
- **Action**: If you still see 404s for those domains, check that `initializeFaviconSystem()` runs (it sets up the listener). Use `?debug=favicon` for favicon debug logs.

### Chick-fil-A (or similar) sometimes shows icon, sometimes not

- **Cause**: Previously, only one host was tried. If the stored website was apex and the icon only worked for www (or vice versa), behaviour was inconsistent.
- **What we do**: We now try **host candidates** (www and apex). Backend stores a canonical URL; the handler tries both host forms. So both `chick-fil-a.com` and `www.chick-fil-a.com` should resolve consistently.
- **Action**: Ensure website URLs are being canonicalized on save (restaurant, merchant, Google Places). If the issue persists, use `?debug=favicon` and `window.RobustFaviconHandler.getFaviconHostCandidates(website)` to confirm candidates.

### Debug commands (localhost)

- `window.faviconDebug.clearCache()` – clear favicon cache.
- `window.RobustFaviconHandler.getCacheStats()` – cache stats.
- `window.RobustFaviconHandler.getFailedDomainsCacheStats()` – failed domains.
- `window.RobustFaviconHandler.getFaviconHostCandidates('https://example.com/')` – host candidates for a URL.
- Add `?debug=favicon` to the page URL for console debug output.

### Brand icon wrong or missing (e.g. Chick-fil-A)

- **Cause**: Website-derived favicon may 404 or return a generic icon.
- **Action**: Set a **Merchant Favicon URL** on the merchant (Edit Merchant → Favicon URL). Use a direct link to the brand’s official favicon (e.g. `https://.../favicon.ico`). This overrides website-derived resolution for that merchant everywhere.

### Key files

- **Handler**: `app/static/js/utils/robust-favicon-handler.js`
- **URL helpers**: `app/utils/url_utils.py` (`canonicalize_website_for_storage`, `get_favicon_host_candidates`, `validate_favicon_url`)
- **Setup**: `docs/FAVICON_SETUP.md`
